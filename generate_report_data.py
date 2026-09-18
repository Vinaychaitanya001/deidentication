"""
Generates results/report_data.json: one real test case per entity type
(input -> detected entities -> anonymized output), plus the evaluation
metrics against Microsoft's own presidio-research dataset.

This is OUR OWN code (not from the repo) - a reporting harness around
regex_engine.py / evaluate.py so the numbers shown to a mentor/reviewer
are captured directly from a real run, not hand-typed.

Run:
    python generate_report_data.py
Writes:
    results/report_data.json
"""

import json
from pathlib import Path

from presidio_anonymizer import OperatorConfig
from regex_engine import RegexAnalyzerEngine, RegexAnonymizerEngine
from evaluate import DATA_PATH, SCORED_TYPES, load_dataset, score_record, overlaps
from collections import defaultdict

RESULTS_DIR = Path(__file__).parent / "results"

# One focused test case per entity type our regex-only build supports.
TEST_CASES = [
    {
        "name": "Credit card (Luhn checksum)",
        "entity_type": "CREDIT_CARD",
        "text": "Please charge my card 4111 1111 1111 1111 for the order.",
        "operator": OperatorConfig("mask", {"masking_char": "*", "chars_to_mask": 12, "from_end": False}),
    },
    {
        "name": "Email address",
        "entity_type": "EMAIL_ADDRESS",
        "text": "You can reach the support team at john.smith@example.com anytime.",
        "operator": OperatorConfig("hash"),
    },
    {
        "name": "Phone number (python-phonenumbers)",
        "entity_type": "PHONE_NUMBER",
        "text": "Call the clinic at +1 415-555-2671 to book an appointment.",
        "operator": OperatorConfig("redact"),
    },
    {
        "name": "IBAN (mod-97 checksum)",
        "entity_type": "IBAN_CODE",
        "text": "Please wire the deposit to IBAN DE89370400440532013000 before Friday.",
        "operator": OperatorConfig("replace", {"new_value": "<IBAN>"}),
    },
    {
        "name": "IP address",
        "entity_type": "IP_ADDRESS",
        "text": "Suspicious login detected from 192.168.1.10 at 3 AM.",
        "operator": OperatorConfig("mask", {"masking_char": "#", "chars_to_mask": 6, "from_end": True}),
    },
    {
        "name": "MAC address",
        "entity_type": "MAC_ADDRESS",
        "text": "The device with MAC 00:1A:2B:3C:4D:5E was flagged by the firewall.",
        "operator": OperatorConfig("replace"),
    },
    {
        "name": "Date (numeric formats)",
        "entity_type": "DATE_TIME",
        "text": "The invoice is dated 2024-03-15 and due on 04/20/2024.",
        "operator": OperatorConfig("replace", {"new_value": "<DATE>"}),
    },
    {
        "name": "URL",
        "entity_type": "URL",
        "text": "Full details are posted at https://billing.example.com/invoice/8842.",
        "operator": OperatorConfig("replace", {"new_value": "<LINK>"}),
    },
    {
        "name": "UUID",
        "entity_type": "UUID",
        "text": "Reference ticket 8f14e45f-ceea-467e-a92c-25f6fdd0e9f1 for details.",
        "operator": OperatorConfig("replace"),
    },
    {
        "name": "Crypto wallet (Base58 + Bech32 checksum)",
        "entity_type": "CRYPTO",
        "text": "Send the refund to BTC wallet 1BoatSLRHtKNngkdXEeobR76b53LETtpyT.",
        "operator": OperatorConfig("replace", {"new_value": "<WALLET>"}),
    },
    {
        "name": "Combined text - shows the NER limitation",
        "entity_type": None,
        "text": (
            "Hi, this is John Smith from Acme Corp. You can reach me at "
            "john.smith@example.com or call +1 415-555-2671."
        ),
        "operator": None,  # uses a per-type map below
        "operator_map": {
            "EMAIL_ADDRESS": OperatorConfig("hash"),
            "PHONE_NUMBER": OperatorConfig("redact"),
            "DEFAULT": OperatorConfig("replace"),
        },
    },
]


def run_test_cases():
    analyzer = RegexAnalyzerEngine()
    anonymizer = RegexAnonymizerEngine()
    output = []

    for case in TEST_CASES:
        text = case["text"]
        results = analyzer.analyze(text)
        detected = [
            {
                "entity_type": r.entity_type,
                "start": r.start,
                "end": r.end,
                "score": round(r.score, 2),
                "matched_text": text[r.start : r.end],
            }
            for r in results
        ]

        if case.get("operator_map"):
            operators = case["operator_map"]
        elif case["operator"] is not None:
            operators = {case["entity_type"]: case["operator"], "DEFAULT": OperatorConfig("replace")}
        else:
            operators = {}

        anonymized = anonymizer.anonymize(text, results, operators)

        output.append(
            {
                "name": case["name"],
                "input_text": text,
                "detected": detected,
                "anonymized_text": anonymized,
            }
        )
    return output


def run_evaluation():
    dataset = load_dataset()
    analyzer = RegexAnalyzerEngine()
    stats = defaultdict(lambda: [0, 0, 0])
    out_of_scope_gt = 0
    unscored_predictions = 0

    for record in dataset:
        text = record["full_text"]
        true_by_type = defaultdict(list)
        for span in record["spans"]:
            etype = span["entity_type"]
            true_by_type[etype].append((span["start_position"], span["end_position"]))
            if etype not in SCORED_TYPES:
                out_of_scope_gt += 1

        pred_by_type = defaultdict(list)
        for result in analyzer.analyze(text):
            if result.entity_type in SCORED_TYPES:
                pred_by_type[result.entity_type].append((result.start, result.end))
            else:
                unscored_predictions += 1

        for etype in SCORED_TYPES:
            tp, fp, fn = score_record(true_by_type.get(etype, []), pred_by_type.get(etype, []))
            stats[etype][0] += tp
            stats[etype][1] += fp
            stats[etype][2] += fn

    per_type = []
    total_tp = total_fp = total_fn = 0
    for etype in sorted(SCORED_TYPES):
        tp, fp, fn = stats[etype]
        total_tp += tp
        total_fp += fp
        total_fn += fn
        precision = tp / (tp + fp) if (tp + fp) else None
        recall = tp / (tp + fn) if (tp + fn) else None
        f1 = (2 * precision * recall / (precision + recall)) if precision and recall and (precision + recall) > 0 else None
        per_type.append({
            "entity_type": etype, "tp": tp, "fp": fp, "fn": fn,
            "precision": round(precision, 2) if precision is not None else None,
            "recall": round(recall, 2) if recall is not None else None,
            "f1": round(f1, 2) if f1 is not None else None,
        })

    micro_p = total_tp / (total_tp + total_fp) if (total_tp + total_fp) else None
    micro_r = total_tp / (total_tp + total_fn) if (total_tp + total_fn) else None
    micro_f1 = (2 * micro_p * micro_r / (micro_p + micro_r)) if micro_p and micro_r and (micro_p + micro_r) > 0 else None

    return {
        "dataset_records": len(dataset),
        "per_type": per_type,
        "micro_avg": {
            "tp": total_tp, "fp": total_fp, "fn": total_fn,
            "precision": round(micro_p, 2) if micro_p is not None else None,
            "recall": round(micro_r, 2) if micro_r is not None else None,
            "f1": round(micro_f1, 2) if micro_f1 is not None else None,
        },
        "out_of_scope_ground_truth_spans": out_of_scope_gt,
        "unscored_predictions": unscored_predictions,
    }


def main():
    RESULTS_DIR.mkdir(exist_ok=True)
    data = {
        "test_cases": run_test_cases(),
        "evaluation": run_evaluation(),
    }
    out_path = RESULTS_DIR / "report_data.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
