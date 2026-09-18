"""
Evaluate the regex-only pipeline against Microsoft's own Presidio evaluation
dataset (presidio-research's synth_dataset_v2.json) - OUR OWN code.

This is a deliberately simple span-overlap evaluator (a prediction "hits" a
ground-truth span of the same entity_type if their character ranges
overlap at all). It is NOT the full scoring methodology presidio-research's
own `presidio_evaluator` package uses (that does token-level, boundary-aware
scoring) - this is a lightweight stand-in good enough to see, on Presidio's
own data, exactly what a regex-only architecture catches and what it misses.

Run:
    pip install -r requirements.txt
    python evaluate.py
"""

import json
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

from regex_engine import RegexAnalyzerEngine

DATA_PATH = Path(__file__).parent / "data" / "synth_dataset_v2.json"

# Entity types where our vendored recognizers use the SAME label the
# dataset uses, so predictions can be scored directly against ground truth.
SCORED_TYPES = {
    "CREDIT_CARD",
    "DATE_TIME",
    "EMAIL_ADDRESS",
    "IBAN_CODE",
    "IP_ADDRESS",
    "PHONE_NUMBER",
}


def load_dataset() -> list:
    with open(DATA_PATH, encoding="utf-8") as f:
        return json.load(f)


def overlaps(a: Tuple[int, int], b: Tuple[int, int]) -> bool:
    return a[0] < b[1] and b[0] < a[1]


def score_record(
    true_spans: List[Tuple[int, int]], pred_spans: List[Tuple[int, int]]
) -> Tuple[int, int, int]:
    """Greedy overlap matching. Returns (true_positives, false_positives, false_negatives)."""
    used = [False] * len(true_spans)
    tp = fp = 0
    for pred in pred_spans:
        matched = False
        for i, true in enumerate(true_spans):
            if not used[i] and overlaps(pred, true):
                used[i] = True
                matched = True
                break
        if matched:
            tp += 1
        else:
            fp += 1
    fn = used.count(False)
    return tp, fp, fn


def main() -> None:
    if not DATA_PATH.exists():
        raise SystemExit(
            f"Missing {DATA_PATH}. See data/README.md to (re)download it."
        )

    dataset = load_dataset()
    analyzer = RegexAnalyzerEngine()

    # Per scored entity type: [tp, fp, fn]
    stats: Dict[str, List[int]] = defaultdict(lambda: [0, 0, 0])
    out_of_scope_gt = 0  # ground-truth spans of a type we never attempt
    unscored_predictions = 0  # our predictions with no matching label in this dataset

    for record in dataset:
        text = record["full_text"]
        true_by_type: Dict[str, List[Tuple[int, int]]] = defaultdict(list)
        for span in record["spans"]:
            etype = span["entity_type"]
            true_by_type[etype].append((span["start_position"], span["end_position"]))
            if etype not in SCORED_TYPES:
                out_of_scope_gt += 1

        pred_by_type: Dict[str, List[Tuple[int, int]]] = defaultdict(list)
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

    print("=" * 78)
    print(f"Dataset: {DATA_PATH.name}  ({len(dataset)} records)")
    print("Matching: any character overlap between a prediction and a ground-truth")
    print("span of the SAME entity_type counts as a hit.")
    print("=" * 78)
    header = f"{'ENTITY_TYPE':<16}{'TP':>6}{'FP':>6}{'FN':>6}{'PRECISION':>11}{'RECALL':>9}{'F1':>7}"
    print(header)
    print("-" * len(header))

    total_tp = total_fp = total_fn = 0
    for etype in sorted(SCORED_TYPES):
        tp, fp, fn = stats[etype]
        total_tp += tp
        total_fp += fp
        total_fn += fn
        precision = tp / (tp + fp) if (tp + fp) else float("nan")
        recall = tp / (tp + fn) if (tp + fn) else float("nan")
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) and precision == precision and recall == recall and (precision + recall) > 0 else float("nan")
        print(f"{etype:<16}{tp:>6}{fp:>6}{fn:>6}{precision:>11.2f}{recall:>9.2f}{f1:>7.2f}")

    print("-" * len(header))
    micro_p = total_tp / (total_tp + total_fp) if (total_tp + total_fp) else float("nan")
    micro_r = total_tp / (total_tp + total_fn) if (total_tp + total_fn) else float("nan")
    micro_f1 = 2 * micro_p * micro_r / (micro_p + micro_r) if (micro_p + micro_r) > 0 else float("nan")
    print(f"{'MICRO-AVERAGE':<16}{total_tp:>6}{total_fp:>6}{total_fn:>6}{micro_p:>11.2f}{micro_r:>9.2f}{micro_f1:>7.2f}")

    print()
    print(f"Ground-truth spans of a type we never attempt (PERSON, STREET_ADDRESS,")
    print(f"GPE, ORGANIZATION, TITLE, AGE, NRP, ZIP_CODE, DOMAIN_NAME, US_SSN,")
    print(f"US_DRIVER_LICENSE - all need NER or an unvendored country recognizer):")
    print(f"  {out_of_scope_gt} spans, out of scope by design (see data/README.md).")
    print()
    print(f"Our predictions of a type this dataset never labels (CRYPTO, MAC_ADDRESS,")
    print(f"URL, UUID) - not counted as false positives above, shown separately:")
    print(f"  {unscored_predictions} predictions.")


if __name__ == "__main__":
    main()
