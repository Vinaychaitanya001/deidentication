"""Evaluation v2 - every system, every dataset, one scorer (evaluation/scorer.py).

    python evaluate_v2.py                                   # all systems, all datasets
    python evaluate_v2.py --systems B0,B1 --datasets clinical_dev
    python evaluate_v2.py --limit 200 --bootstrap 200       # quicker run
    python evaluate_v2.py --systems B2,B2-max,B2-nobio      # optional NER-integration ablations

Writes results/v2/<dataset>.json and results/v2/REPORT.md.
"""

import argparse
import json
import sys
import time
from pathlib import Path

from evaluation.datasets import DATASETS
from evaluation.scorer import evaluate, paired_difference_ci
from evaluation.systems import build_systems

ALL_SYSTEMS = ["B0", "B1", "B2", "P1-spacy", "P1-noveto", "P1"]
ALL_DATASETS = ["clinical_dev", "clinical_test", "synth_v2"]
OUT_DIR = Path(__file__).parent / "results" / "v2"
COMPARISONS = [("P1", "B1"), ("P1", "B0"), ("B2", "B1"), ("P1", "B2"), ("P1", "P1-noveto"), ("P1", "P1-spacy"),
               ("B2", "B2-max")]


def pct(x):
    return "—" if x is None else f"{100 * x:.1f}"


def ci(res, key):
    lo, hi = res["ci95"].get(key, [None, None])
    return "" if lo is None else f" [{pct(lo)}–{pct(hi)}]"


def dataset_section(name, n_docs, n_gold, results, diffs):
    lines = [f"## {name}  ({n_docs} documents, {n_gold} gold PHI spans)", ""]
    lines += ["| System | Strict P | Strict R | Strict F1 | Strict F2 | Exact F2 | Partial P | Partial R | Partial F2 "
              "| Token F2 | Token-typed F2 | Char leak % | Zero-leak docs % | Hard-neg redacted % |",
              "|---" * 14 + "|"]
    for key, r in results.items():
        s, e, p = r["entity_strict"], r["entity_exact"], r["entity_partial"]
        hn = r.get("hard_negatives", {}).get("rate")
        lines.append(f"| {r['system']} | {pct(s['precision'])} | {pct(s['recall'])} | {pct(s['f1'])} | {pct(s['f2'])} "
                     f"| {pct(e['f2'])} | {pct(p['precision'])} | {pct(p['recall'])} | {pct(p['f2'])} "
                     f"| {pct(r['token_binary']['f2'])} | {pct(r['token_typed']['f2'])} | {pct(r['char']['leak_rate'])} "
                     f"| {pct(r['doc_zero_leak_rate'])} | {pct(hn)} |")
    lines += ["", "95% bootstrap confidence intervals (resampling documents):", "",
              "| System | Strict F2 | Partial recall | Token F2 | Char leak % | Zero-leak docs % |", "|---|---|---|---|---|---|"]
    for key, r in results.items():
        lines.append(f"| {r['system']} | {pct(r['entity_strict']['f2'])}{ci(r, 'strict_f2')} "
                     f"| {pct(r['entity_partial']['recall'])}{ci(r, 'partial_recall')} "
                     f"| {pct(r['token_binary']['f2'])}{ci(r, 'token_f2')} "
                     f"| {pct(r['char']['leak_rate'])}{ci(r, 'char_leak_rate')} "
                     f"| {pct(r['doc_zero_leak_rate'])}{ci(r, 'doc_zero_leak_rate')} |")
    if diffs:
        lines += ["", "Paired differences (A − B, same documents; percentage points, 95% CI):", "",
                  "| A − B | Strict F2 | Partial recall | Token F2 | Char leak | Zero-leak docs |", "|---|---|---|---|---|---|"]
        for (a, b), d in diffs.items():
            cells = []
            for m in ("strict_f2", "partial_recall", "token_f2", "char_leak_rate", "doc_zero_leak_rate"):
                lo, hi = d[m]["ci"]
                cells.append(f"{100 * d[m]['diff']:+.1f} [{100 * lo:+.1f}, {100 * hi:+.1f}]")
            lines.append(f"| {a} − {b} | " + " | ".join(cells) + " |")
    cats = sorted({c for r in results.values() for c in r["recall_by_gold_category"]},
                  key=lambda c: -max(r["recall_by_gold_category"].get(c, {}).get("support", 0) for r in results.values()))
    lines += ["", "Recall by gold category (partial / strict):", "",
              "| Category | Support | " + " | ".join(results) + " |", "|---|---|" + "---|" * len(results)]
    for c in cats:
        sup = max(r["recall_by_gold_category"].get(c, {}).get("support", 0) for r in results.values())
        cells = []
        for r in results.values():
            v = r["recall_by_gold_category"].get(c)
            cells.append("—" if not v else f"{pct(v['partial_recall'])} / {pct(v['strict_recall'])}")
        lines.append(f"| {c} | {sup} | " + " | ".join(cells) + " |")
    if any("hard_negatives" in r for r in results.values()):
        kinds = sorted({k for r in results.values() for k in r["hard_negatives"]["by_kind"]})
        lines += ["", "Hard negatives redacted (lower is better):", "",
                  "| Kind | Total | " + " | ".join(results) + " |", "|---|---|" + "---|" * len(results)]
        for k in kinds:
            tot = next(r["hard_negatives"]["by_kind"][k]["total"] for r in results.values())
            cells = [pct(r["hard_negatives"]["by_kind"][k]["rate"]) for r in results.values()]
            lines.append(f"| {k} | {tot} | " + " | ".join(cells) + " |")
    subs = {k: r["name_subtypes"] for k, r in results.items() if r["name_subtypes"]["compared"]}
    if subs:
        lines += ["", "Patient vs clinician subtype (names found by a subtyped prediction):", ""]
        for k, s in subs.items():
            lines.append(f"- {results[k]['system']}: {s['subtype_correct']}/{s['compared']} correct ({pct(s['accuracy'])}%)")
    return lines + [""]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--systems", default=",".join(ALL_SYSTEMS))
    ap.add_argument("--datasets", default=",".join(ALL_DATASETS))
    ap.add_argument("--limit", type=int, default=None, help="evaluate only the first N documents per dataset")
    ap.add_argument("--bootstrap", type=int, default=1000)
    ap.add_argument("--ner-model", default=None, help="Hugging Face model id for the clinical NER")
    ap.add_argument("--out", default=str(OUT_DIR))
    args = ap.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    names = [s.strip() for s in args.systems.split(",") if s.strip()]
    print(f"Building systems: {', '.join(names)}")
    systems = build_systems(names, ner_model=args.ner_model)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    report = ["# Evaluation v2 results", "",
              "All numbers are percentages computed by `evaluation/scorer.py` on the final resolved spans each system "
              "would redact. Types are compared at category level. See the scorer docstring for metric definitions.", ""]

    for ds in [d.strip() for d in args.datasets.split(",") if d.strip()]:
        docs = DATASETS[ds](args.limit)
        n_gold = sum(len(d.gold) for d in docs)
        results, rows = {}, {}
        for key, system in systems.items():
            t0 = time.time()
            preds = {d.doc_id: system.predict(d.text) for d in docs}
            res = evaluate(docs, preds, bootstrap=args.bootstrap)
            res["system"] = system.name
            res["seconds"] = round(time.time() - t0, 1)
            rows[key] = res.pop("_rows")
            results[key] = res
            s, p = res["entity_strict"], res["entity_partial"]
            print(f"[{ds}] {system.name:<36} strict F2 {pct(s['f2']):>5}  partial R {pct(p['recall']):>5}  "
                  f"P {pct(p['precision']):>5}  char leak {pct(res['char']['leak_rate']):>5}%  "
                  f"zero-leak docs {pct(res['doc_zero_leak_rate']):>5}%  ({res['seconds']}s)")
        diffs = {(a, b): paired_difference_ci(rows[a], rows[b], n=args.bootstrap)
                 for a, b in COMPARISONS if a in rows and b in rows}
        payload = {"dataset": ds, "documents": len(docs), "gold_spans": n_gold, "results": results,
                   "paired_differences": {f"{a} - {b}": d for (a, b), d in diffs.items()}}
        (out_dir / f"{ds}.json").write_text(json.dumps(payload, indent=1), encoding="utf-8")
        report += dataset_section(ds, len(docs), n_gold, results, diffs)

    (out_dir / "REPORT.md").write_text("\n".join(report), encoding="utf-8")
    print(f"\nWrote {out_dir / 'REPORT.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
