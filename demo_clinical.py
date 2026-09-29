"""Phase-1 demonstration: one clinical note through L0-L7, stage by stage.

    python demo_clinical.py                         # built-in synthetic note, clinical NER
    python demo_clinical.py --note dev-003          # a note from data/synthetic_clinical/{dev,test}.json
    python demo_clinical.py --file my_note.txt      # your own (synthetic!) text
    python demo_clinical.py --spacy                 # spaCy NER instead of the clinical transformer
    python demo_clinical.py --no-vetoes             # see what the hard-negative rules prevent

All example data is synthetic. Never run the demo key (no DEID_HMAC_KEY set) on real notes.
"""

import argparse
import json
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

DEMO_NOTE = """DISCHARGE SUMMARY
Patient: HALVORSEN, MARGIT        MRN: 7730418
DOB: 02/11/1932                   Admitted: 3/14/2024
Attending: Priya Raman, MD

HPI: Ms. Halvorsen is a 92-year-old woman admitted to Riverside Medical Center with dyspnea x3 days.
Vitals: BP 148/86, HR 96. Exam: strength 4/5 in the left arm. Pain 3/10.
Medications: furosemide 40 mg PO BID; metoprolol 1/2 tab daily.
Social: lives with her son Anders in Duluth, MN 55802.
Plan: follow up with Dr. Okonkwo on April 2, 2024. Call (218) 555-0147; fax 218-555-0199; pager 44317.
"""


def load_note(args) -> tuple:
    if args.file:
        return Path(args.file).stem, Path(args.file).read_text(encoding="utf-8")
    if args.note:
        split = "test" if args.note.startswith("test") else "dev"
        records = json.loads((Path(__file__).parent / "data" / "synthetic_clinical" / f"{split}.json").read_text())
        record = next((r for r in records if r["doc_id"] == args.note), None)
        if record is None:
            sys.exit(f"unknown note id {args.note!r}")
        return record["doc_id"], record["text"]
    return "demo-note", DEMO_NOTE


def show(text: str, start: int, end: int) -> str:
    return repr(text[start:end])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--note", help="note id from the synthetic clinical set, e.g. dev-003")
    ap.add_argument("--file", help="path to a text file")
    ap.add_argument("--spacy", action="store_true", help="use spaCy en_core_web_sm NER (P1-spacy ablation)")
    ap.add_argument("--no-vetoes", action="store_true", help="switch off the hard-negative rules (P1-noveto)")
    args = ap.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    from deid.pipeline import ClinicalDeidPipeline

    if args.spacy:
        from build_analyzer import build_analyzer

        pipe = ClinicalDeidPipeline.from_nlp_engine(build_analyzer().nlp_engine)
    else:
        pipe = ClinicalDeidPipeline.build()
    doc_id, text = load_note(args)
    result = pipe.deidentify(text, doc_id=doc_id, use_vetoes=not args.no_vetoes)
    det = result.detection

    print("=" * 100)
    print(f"INPUT  ({doc_id}, {len(text)} characters)\n" + "=" * 100)
    print(text)

    print("=" * 100 + "\nL0 ingest: language =", det.document.language, "| spans refer to the original text")
    print("L1 clinical structure: key:value fields")
    for f in det.document.fields:
        print(f"   {f.kind:<16} key {text[f.key_start:f.key_end]!r:<24} value {show(text, f.value_start, f.value_end)}")

    print("\nL2 language pack: en (spaCy tokens/lemmas, English cue lists)")
    print(f"L3 candidates: {len(det.candidates)} proposals from {len({c.source for c in det.candidates})} detectors")
    print("L4 decisions (rule-based; scores are raw detector scores, not probabilities):")
    for d in det.decisions:
        c = d.candidate
        mark = "accept" if d.accepted else "REJECT"
        print(f"   {mark}  {show(text, c.start, c.end):<30} {c.entity:<22} {c.source:<24} {c.raw_score:<6} {d.reason}")

    print("\nL5 final spans (overlaps resolved; field keys > clinical pack/validators > NER):")
    for s in det.final_spans:
        print(f"   {show(text, s.start, s.end):<30} {s.type:<18} sources={', '.join(s.sources)}")

    print("\n" + "=" * 100 + "\nL6 OUTPUT (HIPAA Safe Harbor profile)\n" + "=" * 100)
    print(result.text)

    print("=" * 100 + "\nL7 span manifest (positions, types, actions, sources; never original values)\n" + "=" * 100)
    manifest = dict(result.manifest)
    spans = manifest.pop("spans")
    print(json.dumps(manifest, indent=1))
    for s in spans:
        print(f"   [{s['start']:>4},{s['end']:>4}) {s['type']:<18} {s['action']:<26} -> {s['replacement']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
