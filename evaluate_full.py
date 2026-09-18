"""
Score the FULL Presidio architecture against Presidio's own evaluation set.

OUR OWN code (not from the Presidio repo).

Data source
-----------
    data/synth_dataset_v2.json
    from github.com/microsoft/presidio-research (MIT), 1,500 labeled records.
    Ground truth = each record's own `spans`, written by the Presidio team.

Scoring design
--------------
Recall is measured per DATASET label; precision per PRESIDIO label.

Why not one shared "canonical" label set? Because both `GPE` (cities) and
`STREET_ADDRESS` are satisfied by a Presidio `LOCATION` prediction. Merging
them into one bucket hides the two very different realities underneath —
spaCy handles city names well and full street addresses badly. Reporting
them separately keeps that visible.

A prediction/truth pair matches when their character spans overlap AND the
prediction's label is in that dataset label's accepted set
(see entity_mapping.DATASET_LABEL_ACCEPTS).

Usage
-----
    python evaluate_full.py                 # all 1,500 records
    python evaluate_full.py --limit 200     # quick run
    python evaluate_full.py --org           # un-ignore ORGANIZATION
    python evaluate_full.py --model en_core_web_lg
"""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

from build_analyzer import build_analyzer
from entity_mapping import (
    accepted_presidio_labels,
    is_unreachable,
    satisfied_dataset_labels,
)

DATA_PATH = Path(__file__).parent / "data" / "synth_dataset_v2.json"


def overlaps(a_start, a_end, b_start, b_end) -> bool:
    return a_start < b_end and b_start < a_end


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--model", default="en_core_web_sm")
    ap.add_argument("--org", action="store_true",
                    help="un-ignore ORGANIZATION (Presidio ignores it by default)")
    ap.add_argument("--out", default="results/full_architecture_metrics.json")
    args = ap.parse_args()

    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    if not DATA_PATH.exists():
        print(f"ERROR: missing {DATA_PATH}")
        return 1

    with open(DATA_PATH, encoding="utf-8") as f:
        dataset = json.load(f)
    if args.limit:
        dataset = dataset[: args.limit]

    print(f"Building analyzer (model={args.model}, include_organization={args.org})...")
    analyzer = build_analyzer(model_name=args.model, include_organization=args.org)
    print(f"  recognizers loaded: {len(analyzer.registry.recognizers)}")
    print(f"Analyzing {len(dataset)} records...")

    recall_stats = defaultdict(lambda: {"found": 0, "missed": 0})   # by dataset label
    prec_stats = defaultdict(lambda: {"hit": 0, "spurious": 0})     # by presidio label
    unreachable = defaultdict(int)

    for n, record in enumerate(dataset, start=1):
        if n % 250 == 0:
            print(f"  ...{n}/{len(dataset)}")
        text = record["full_text"]
        truths = [
            (s["entity_type"], s["start_position"], s["end_position"])
            for s in record["spans"]
        ]
        preds = [
            (r.entity_type, r.start, r.end)
            for r in analyzer.analyze(text=text, language="en")
        ]

        # --- recall: did any acceptable prediction cover this truth span? ---
        for label, ts, te in truths:
            if is_unreachable(label) or not accepted_presidio_labels(label):
                unreachable[label] += 1
                continue
            ok = accepted_presidio_labels(label)
            hit = any(
                p_label in ok and overlaps(ps, pe, ts, te)
                for p_label, ps, pe in preds
            )
            recall_stats[label]["found" if hit else "missed"] += 1

        # --- precision: did this prediction land on something it could be? ---
        for p_label, ps, pe in preds:
            candidates = satisfied_dataset_labels(p_label)
            if not candidates:
                prec_stats[p_label]["spurious"] += 1  # label dataset never uses
                continue
            hit = any(
                t_label in candidates and overlaps(ps, pe, ts, te)
                for t_label, ts, te in truths
            )
            prec_stats[p_label]["hit" if hit else "spurious"] += 1

    # ------------------------------ report ------------------------------
    w = 74
    print("\n" + "=" * w)
    print(f"FULL PRESIDIO ARCHITECTURE — {len(dataset)} records, model={args.model}, "
          f"ORGANIZATION={'on' if args.org else 'ignored (Presidio default)'}")
    print("=" * w)

    print("\nRECALL — per dataset label (did we find the labeled PII?)")
    print(f"{'DATASET LABEL':<20}{'FOUND':>8}{'MISSED':>8}{'TOTAL':>8}{'RECALL':>9}")
    print("-" * 53)
    rec_rows, tf, tm = [], 0, 0
    for label in sorted(recall_stats, key=lambda k: -(recall_stats[k]["found"] + recall_stats[k]["missed"])):
        f_, m_ = recall_stats[label]["found"], recall_stats[label]["missed"]
        tot = f_ + m_
        tf, tm = tf + f_, tm + m_
        r = f_ / tot if tot else 0.0
        rec_rows.append({"label": label, "found": f_, "missed": m_, "recall": round(r, 3)})
        print(f"{label:<20}{f_:>8}{m_:>8}{tot:>8}{r:>9.2f}")
    print("-" * 53)
    print(f"{'OVERALL':<20}{tf:>8}{tm:>8}{tf+tm:>8}{(tf/(tf+tm) if tf+tm else 0):>9.2f}")

    print("\nPRECISION — per Presidio label (were our detections real PII?)")
    print(f"{'PRESIDIO LABEL':<20}{'HIT':>8}{'SPURIOUS':>10}{'TOTAL':>8}{'PREC':>9}")
    print("-" * 55)
    prec_rows, th, ts_ = [], 0, 0
    for label in sorted(prec_stats, key=lambda k: -(prec_stats[k]["hit"] + prec_stats[k]["spurious"])):
        h, s = prec_stats[label]["hit"], prec_stats[label]["spurious"]
        tot = h + s
        th, ts_ = th + h, ts_ + s
        p = h / tot if tot else 0.0
        prec_rows.append({"label": label, "hit": h, "spurious": s, "precision": round(p, 3)})
        print(f"{label:<20}{h:>8}{s:>10}{tot:>8}{p:>9.2f}")
    print("-" * 55)
    print(f"{'OVERALL':<20}{th:>8}{ts_:>10}{th+ts_:>8}{(th/(th+ts_) if th+ts_ else 0):>9.2f}")

    total_unreachable = sum(unreachable.values())
    print(f"\nGround-truth spans with no Presidio equivalent: {total_unreachable}")
    for k, v in sorted(unreachable.items(), key=lambda kv: -kv[1]):
        print(f"    {v:>5}  {k}")

    out_path = Path(args.out)
    out_path.parent.mkdir(exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({
            "config": {"model": args.model, "include_organization": args.org,
                       "records": len(dataset)},
            "recall_by_dataset_label": rec_rows,
            "precision_by_presidio_label": prec_rows,
            "overall": {
                "recall": round(tf / (tf + tm), 3) if (tf + tm) else 0,
                "precision": round(th / (th + ts_), 3) if (th + ts_) else 0,
                "found": tf, "missed": tm, "hit": th, "spurious": ts_,
            },
            "unreachable_ground_truth": dict(unreachable),
        }, f, indent=2)
    print(f"\nSaved: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
