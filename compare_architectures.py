"""
THE HEADLINE RESULT — regex-only vs full Presidio architecture, same records.

OUR OWN code (not from the Presidio repo).

Both architectures are run over the SAME records from
`data/synth_dataset_v2.json` (Microsoft's own evaluation set) and scored by
the SAME code in scoring.py. The only variable that changes is the
architecture:

    A. REGEX-ONLY   10 pattern/checksum recognizers, no NLP model,
                    3 pip packages, 0 bytes of model weights.
    B. FULL         AnalyzerEngine + spaCy NlpEngine + SpacyRecognizer +
                    ContextAwareEnhancer + RecognizerRegistry + country
                    recognizers.

Usage
-----
    python compare_architectures.py
    python compare_architectures.py --limit 300
    python compare_architectures.py --org      # un-ignore ORGANIZATION
"""

import argparse
import json
import sys
from pathlib import Path

from build_analyzer import build_analyzer
from regex_engine import RegexAnalyzerEngine
from scoring import Scorer

DATA_PATH = Path(__file__).parent / "data" / "synth_dataset_v2.json"


def run(analyzer, dataset, use_full: bool) -> Scorer:
    sc = Scorer()
    for n, record in enumerate(dataset, start=1):
        if n % 250 == 0:
            print(f"    ...{n}/{len(dataset)}")
        text = record["full_text"]
        truths = [
            (s["entity_type"], s["start_position"], s["end_position"])
            for s in record["spans"]
        ]
        if use_full:
            results = analyzer.analyze(text=text, language="en")
        else:
            results = analyzer.analyze(text)
        preds = [(r.entity_type, r.start, r.end) for r in results]
        sc.add_record(truths, preds)
    return sc


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--model", default="en_core_web_sm")
    ap.add_argument("--org", action="store_true")
    ap.add_argument("--out", default="results/architecture_comparison.json")
    args = ap.parse_args()

    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    with open(DATA_PATH, encoding="utf-8") as f:
        dataset = json.load(f)
    if args.limit:
        dataset = dataset[: args.limit]

    print(f"Dataset: synth_dataset_v2.json ({len(dataset)} records)")
    print("\n[A] REGEX-ONLY architecture")
    regex_sc = run(RegexAnalyzerEngine(), dataset, use_full=False)

    print(f"\n[B] FULL architecture (model={args.model}, "
          f"ORGANIZATION={'on' if args.org else 'ignored'})")
    full = build_analyzer(model_name=args.model, include_organization=args.org)
    print(f"    recognizers loaded: {len(full.registry.recognizers)}")
    full_sc = run(full, dataset, use_full=True)

    a, b = regex_sc.totals(), full_sc.totals()

    w = 78
    print("\n" + "=" * w)
    print(f"ARCHITECTURE COMPARISON — {len(dataset)} identical records")
    print("=" * w)
    print(f"{'METRIC':<36}{'REGEX-ONLY':>14}{'FULL':>14}{'CHANGE':>14}")
    print("-" * w)

    def row(name, ka, kb, pct=False, fmt="{:,}"):
        va, vb = a[ka], b[kb]
        if pct:
            print(f"{name:<36}{va:>14.2f}{vb:>14.2f}{vb - va:>+14.2f}")
        else:
            delta = vb - va
            print(f"{name:<36}{fmt.format(va):>14}{fmt.format(vb):>14}{fmt.format(delta) if delta < 0 else '+' + fmt.format(delta):>14}")

    row("PII spans found", "found", "found")
    row("PII spans missed", "missed", "missed")
    row("Labeled spans in reach", "labeled_reachable", "labeled_reachable")
    print("-" * w)
    row("Recall", "recall", "recall", pct=True)
    row("Precision", "precision", "precision", pct=True)
    row("F1", "f1", "f1", pct=True)
    print("-" * w)
    row("Unmeasurable predictions", "unmeasurable_predictions", "unmeasurable_predictions")
    row("Ground truth out of reach", "unreachable_ground_truth", "unreachable_ground_truth")
    print("=" * w)

    # per-label recall, side by side
    ra = {r["label"]: r for r in regex_sc.recall_rows()}
    rb = {r["label"]: r for r in full_sc.recall_rows()}
    print("\nRECALL BY DATASET LABEL")
    print(f"{'LABEL':<20}{'TOTAL':>8}{'REGEX':>10}{'FULL':>10}   {'':<12}")
    print("-" * 62)
    for label in sorted(set(ra) | set(rb), key=lambda k: -(rb.get(k, ra.get(k))["total"])):
        tot = (rb.get(label) or ra.get(label))["total"]
        va = ra[label]["recall"] if label in ra else 0.0
        vb = rb[label]["recall"] if label in rb else 0.0
        newly_reached = (label not in ra or ra[label]["found"] == 0) and vb > 0
        if not newly_reached:
            note = ""
        elif label in ("PERSON", "GPE", "STREET_ADDRESS", "ORGANIZATION", "NRP"):
            note = "NEW — unlocked by NER"
        else:
            note = "NEW — unlocked by country recognizer"
        print(f"{label:<20}{tot:>8}{va:>10.2f}{vb:>10.2f}   {note}")

    out = Path(args.out)
    out.parent.mkdir(exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump({
            "records": len(dataset),
            "config": {"model": args.model, "include_organization": args.org},
            "regex_only": {"totals": a, "recall": regex_sc.recall_rows(),
                           "precision": regex_sc.precision_rows()},
            "full_architecture": {"totals": b, "recall": full_sc.recall_rows(),
                                  "precision": full_sc.precision_rows()},
        }, f, indent=2)
    print(f"\nSaved: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
