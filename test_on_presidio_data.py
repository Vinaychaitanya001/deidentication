"""
Full test of the regex-only pipeline against MICROSOFT'S OWN PRESIDIO TEST DATA.
Produces ONE complete report file with every test point plus a failure analysis.

WHERE THE "DESIRED OUTPUT" COMES FROM
-------------------------------------
Every test point is a real record from:

    data/synth_dataset_v2.json
    downloaded from https://github.com/microsoft/presidio-research
    (file: data/synth_dataset_v2.json, main branch, MIT licensed)

That is the evaluation dataset the Presidio team themselves use to score
their recognizers. Each record ships with a "spans" list - the GROUND
TRUTH, written by the Presidio team - stating which character range of
the text is which PII entity:

    {"full_text": "...",
     "spans": [{"entity_type": "EMAIL_ADDRESS", "entity_value": "...",
                "start_position": 45, "end_position": 67}]}

DESIRED OUTPUT = that record's own full_text with every ground-truth span
replaced by its entity tag. Nothing in it is authored by this project.
OUR OUTPUT = what this project's regex/checksum engine actually produces.

Run:
    python test_on_presidio_data.py           (all records containing
                                               regex-detectable PII)
    python test_on_presidio_data.py 25        (first 25 such records only)

Writes everything to:
    results/FULL_TEST_REPORT.txt
"""

import json
import sys
from collections import defaultdict
from pathlib import Path

from presidio_anonymizer import OperatorConfig
from regex_engine import RegexAnalyzerEngine, RegexAnonymizerEngine

DATA_PATH = Path(__file__).parent / "data" / "synth_dataset_v2.json"
OUTPUT_PATH = Path(__file__).parent / "results" / "FULL_TEST_REPORT.txt"

# Entity types our regex-only build detects AND that this dataset labels
# under the same name, so predictions compare directly to ground truth.
SUPPORTED_TYPES = {
    "CREDIT_CARD",
    "DATE_TIME",
    "EMAIL_ADDRESS",
    "IBAN_CODE",
    "IP_ADDRESS",
    "PHONE_NUMBER",
}

MONTH_WORDS = (
    "january february march april may june july august september october "
    "november december jan feb mar apr jun jul aug sep sept oct nov dec"
).split()


def show(text: str) -> str:
    """Render newlines/tabs visibly so multi-line records stay readable."""
    return text.replace("\n", "\\n").replace("\t", "\\t")


def luhn_ok(value: str) -> bool:
    """Luhn checksum - the same test CreditCardRecognizer.validate_result runs."""
    digits = [int(c) for c in value if c.isdigit()]
    if len(digits) < 12:
        return False
    odd = digits[-1::-2]
    even = digits[-2::-2]
    total = sum(odd)
    for d in even:
        total += sum(int(x) for x in str(d * 2))
    return total % 10 == 0


def iban_ok(value: str) -> bool:
    """IBAN mod-97 checksum - same test IbanRecognizer.validate_result runs."""
    cleaned = "".join(ch for ch in value if ch.isalnum()).upper()
    if len(cleaned) < 5:
        return False
    rearranged = cleaned[4:] + cleaned[:4]
    try:
        numeric = "".join(str(int(ch, 36)) for ch in rearranged)
        return int(numeric) % 97 == 1
    except ValueError:
        return False


def diagnose_miss(entity_type: str, value: str) -> str:
    """Best-effort explanation of WHY a ground-truth span was not detected."""
    lowered = value.lower()

    if entity_type == "CREDIT_CARD":
        if not luhn_ok(value):
            return ("the card number in the test data itself FAILS the Luhn "
                    "checksum - the recognizer correctly refused to validate it")
        return "matched no card-prefix pattern (Visa 4/Mastercard 5x/etc.)"

    if entity_type == "IBAN_CODE":
        if not iban_ok(value):
            return ("the IBAN in the test data itself FAILS the mod-97 checksum "
                    "- the recognizer correctly refused to validate it")
        return "checksum passes but the country-format regex did not match"

    if entity_type == "DATE_TIME":
        if any(word in lowered for word in MONTH_WORDS):
            return ("spelled-out month name - DateRecognizer only covers numeric "
                    "formats (2024-03-15, 04/20/2024, 15-MAR-2024)")
        if not any(ch.isdigit() for ch in value):
            return ("relative/verbal date with no digits (e.g. 'last Tuesday') - "
                    "not expressible as a regex")
        return "numeric layout not covered by the 13 date patterns"

    if entity_type == "PHONE_NUMBER":
        return ("format or region not matched by python-phonenumbers at "
                "leniency=1 across the 8 configured regions")

    if entity_type == "EMAIL_ADDRESS":
        return "failed the tldextract public-suffix validation, or malformed"

    if entity_type == "IP_ADDRESS":
        return "failed the ipaddress module's validity check (octets out of range)"

    return "no matching pattern"


def build_desired_output(text: str, spans: list) -> str:
    """Mask every GROUND-TRUTH span (Presidio's labels) with its entity tag."""
    for span in sorted(spans, key=lambda s: s["start_position"], reverse=True):
        text = (
            text[: span["start_position"]]
            + f"<{span['entity_type']}>"
            + text[span["end_position"] :]
        )
    return text


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    limit = None
    if len(sys.argv) > 1:
        limit = int(sys.argv[1])

    if not DATA_PATH.exists():
        print(f"ERROR: missing {DATA_PATH}")
        print("Download it with the curl command in data/README.md")
        return 1

    with open(DATA_PATH, encoding="utf-8") as f:
        dataset = json.load(f)

    analyzer = RegexAnalyzerEngine()
    anonymizer = RegexAnonymizerEngine()

    # Test points = every record containing at least one regex-detectable entity.
    test_points = [
        (idx, rec)
        for idx, rec in enumerate(dataset)
        if {s["entity_type"] for s in rec["spans"]} & SUPPORTED_TYPES
    ]
    if limit is not None:
        test_points = test_points[:limit]

    print(f"Analyzing {len(test_points)} test points...")

    detail_blocks = []
    failures = []            # missed regex-detectable PII (genuine failures)
    ner_only_records = []    # records left with NER-only PII (expected)
    per_type = defaultdict(lambda: {"hits": 0, "misses": 0})
    reason_counts = defaultdict(int)
    total_ner_spans = 0

    for n, (dataset_index, record) in enumerate(test_points, start=1):
        text = record["full_text"]
        ground_truth = record["spans"]

        desired_output = build_desired_output(text, ground_truth)
        our_results = analyzer.analyze(text)
        our_output = anonymizer.anonymize(
            text, our_results, {"DEFAULT": OperatorConfig("replace")}
        )

        hits, misses, ner_only = [], [], []
        for span in ground_truth:
            etype = span["entity_type"]
            if etype not in SUPPORTED_TYPES:
                ner_only.append(span)
                continue
            found = any(
                r.entity_type == etype
                and r.start < span["end_position"]
                and span["start_position"] < r.end
                for r in our_results
            )
            if found:
                hits.append(span)
                per_type[etype]["hits"] += 1
            else:
                misses.append(span)
                per_type[etype]["misses"] += 1
                reason = diagnose_miss(etype, span["entity_value"])
                reason_counts[f"{etype}: {reason}"] += 1
                failures.append({
                    "test_no": n,
                    "dataset_index": dataset_index,
                    "entity_type": etype,
                    "value": span["entity_value"],
                    "reason": reason,
                    "text": text,
                    "our_output": our_output,
                })

        total_ner_spans += len(ner_only)
        if ner_only:
            ner_only_records.append((n, dataset_index, sorted({s["entity_type"] for s in ner_only})))

        block = []
        block.append("=" * 100)
        block.append(f"TEST POINT {n}  |  dataset record #{dataset_index}")
        block.append("=" * 100)
        block.append("INPUT TEXT (dataset 'full_text'):")
        block.append(f"    {show(text)}")
        block.append("")
        block.append("GROUND-TRUTH LABELS (dataset 'spans' - written by the Presidio team):")
        for span in sorted(ground_truth, key=lambda s: s["start_position"]):
            etype = span["entity_type"]
            tag = "regex-detectable" if etype in SUPPORTED_TYPES else "needs NER - out of scope"
            block.append(
                f"    {etype:<16} [{span['start_position']:>4}:{span['end_position']:<4}] "
                f"{show(span['entity_value'])!r}   ({tag})"
            )
        block.append("")
        block.append("DESIRED OUTPUT (every ground-truth span masked):")
        block.append(f"    {show(desired_output)}")
        block.append("")
        block.append("OUR OUTPUT (regex-only engine):")
        block.append(f"    {show(our_output)}")
        block.append("")
        block.append("OUR DETECTIONS:")
        if our_results:
            for r in our_results:
                block.append(
                    f"    {r.entity_type:<16} [{r.start:>4}:{r.end:<4}] "
                    f"{show(text[r.start:r.end])!r}   score={r.score:.2f}"
                )
        else:
            block.append("    (nothing detected)")
        block.append("")
        block.append("VERDICT:")
        block.append(f"    Regex-detectable ground truth : {len(hits) + len(misses)}")
        block.append(f"    Correctly de-identified by us : {len(hits)}")
        if misses:
            block.append(f"    NOT DE-IDENTIFIED (FAILURE)   : {len(misses)}")
            for span in misses:
                block.append(
                    f"        -> {span['entity_type']} {show(span['entity_value'])!r}"
                )
                block.append(
                    f"           reason: {diagnose_miss(span['entity_type'], span['entity_value'])}"
                )
        else:
            block.append("    NOT DE-IDENTIFIED (FAILURE)   : 0")
        block.append(f"    Left in clear, needs NER      : {len(ner_only)} "
                     f"{sorted({s['entity_type'] for s in ner_only}) if ner_only else ''}")
        block.append("")
        detail_blocks.append("\n".join(block))

    # ---------------- assemble the single report file ----------------
    total_hits = sum(v["hits"] for v in per_type.values())
    total_misses = sum(v["misses"] for v in per_type.values())
    total_supported = total_hits + total_misses

    out = []
    out.append("=" * 100)
    out.append("REGEX-ONLY PII DE-IDENTIFICATION - FULL TEST REPORT")
    out.append("=" * 100)
    out.append("")
    out.append("DATA SOURCE")
    out.append("-" * 100)
    out.append(f"  File            : data/synth_dataset_v2.json ({len(dataset)} records total)")
    out.append("  Origin          : github.com/microsoft/presidio-research (main branch, MIT)")
    out.append("  What it is      : the evaluation dataset the Presidio team uses to score")
    out.append("                    their own recognizers")
    out.append("  Desired output  : built from each record's own ground-truth 'spans' labels,")
    out.append("                    written by the Presidio team - NOT authored by this project")
    out.append("  Our output      : produced by this project's regex/checksum engine")
    out.append("  Note            : newlines in source text are displayed as \\n")
    out.append("")
    out.append("PART 1 - SUMMARY")
    out.append("-" * 100)
    out.append(f"  Test points (records with regex-detectable PII) : {len(test_points)}")
    out.append(f"  Regex-detectable ground-truth spans             : {total_supported}")
    out.append(f"  Successfully de-identified                      : {total_hits}")
    out.append(f"  NOT de-identified (failures)                    : {total_misses}")
    if total_supported:
        out.append(f"  Recall on regex-detectable PII                  : "
                   f"{total_hits / total_supported:.1%}")
    out.append(f"  Spans left in clear because they need NER       : {total_ner_spans}")
    out.append("")
    out.append("  Per entity type:")
    out.append(f"  {'ENTITY TYPE':<18}{'DE-IDENTIFIED':>15}{'FAILED':>10}{'RECALL':>10}")
    for etype in sorted(per_type):
        h = per_type[etype]["hits"]
        m = per_type[etype]["misses"]
        rec = h / (h + m) if (h + m) else 0
        out.append(f"  {etype:<18}{h:>15}{m:>10}{rec:>9.0%}")
    out.append("")
    out.append("PART 2 - DATA POINTS THAT COULD NOT BE DE-IDENTIFIED")
    out.append("-" * 100)
    out.append("")
    out.append(f"2A. MISSED REGEX-DETECTABLE PII - genuine failures ({len(failures)})")
    out.append("    These are entity types our architecture claims to handle, but did not")
    out.append("    detect on this record. The PII is still visible in our output.")
    out.append("")
    if failures:
        for f_item in failures:
            out.append(f"    [Test point {f_item['test_no']} | dataset record #{f_item['dataset_index']}]")
            out.append(f"      Entity type   : {f_item['entity_type']}")
            out.append(f"      PII left open : {show(f_item['value'])!r}")
            out.append(f"      Why           : {f_item['reason']}")
            out.append(f"      Input text    : {show(f_item['text'])}")
            out.append(f"      Our output    : {show(f_item['our_output'])}")
            out.append("")
    else:
        out.append("    (none)")
        out.append("")
    out.append("    Failure reasons, grouped:")
    for reason, count in sorted(reason_counts.items(), key=lambda kv: -kv[1]):
        out.append(f"      {count:>4}x  {reason}")
    out.append("")
    out.append(f"2B. PII LEFT IN CLEAR BECAUSE IT NEEDS NER - expected, out of scope "
               f"({total_ner_spans} spans across {len(ner_only_records)} records)")
    out.append("    PERSON, STREET_ADDRESS, GPE, ORGANIZATION, TITLE, AGE, NRP, ZIP_CODE,")
    out.append("    DOMAIN_NAME, US_SSN, US_DRIVER_LICENSE. A regex cannot recognise a")
    out.append("    person's name or a company name - that requires an NER model, which")
    out.append("    this architecture deliberately excludes.")
    out.append("    First 15 affected records:")
    for n, idx, types in ner_only_records[:15]:
        out.append(f"      Test point {n:<5} dataset record #{idx:<6} {types}")
    if len(ner_only_records) > 15:
        out.append(f"      ... and {len(ner_only_records) - 15} more records")
    out.append("")
    out.append("PART 3 - ALL TEST POINTS IN DETAIL")
    out.append("-" * 100)
    out.append("")
    out.extend(detail_blocks)
    out.append("=" * 100)
    out.append("END OF REPORT")
    out.append(f"For the scored precision/recall run over all {len(dataset)} records: python evaluate.py")
    out.append("=" * 100)

    OUTPUT_PATH.parent.mkdir(exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(out))

    print()
    print(f"  Test points               : {len(test_points)}")
    print(f"  Regex-detectable PII spans: {total_supported}")
    print(f"  De-identified             : {total_hits}")
    print(f"  FAILED to de-identify     : {total_misses}")
    print(f"  Left in clear (needs NER) : {total_ner_spans}")
    print()
    print(f"Full report written to: {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
