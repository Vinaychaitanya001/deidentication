"""Evaluation datasets converted to canonical gold spans."""

import json
from pathlib import Path
from typing import List, Optional

from deid.ontology import IGNORE, canonical_from_synth_v2, is_phi
from evaluation.scorer import EvalDoc, Span

ROOT = Path(__file__).resolve().parent.parent
SYNTHETIC_CLINICAL_DIR = ROOT / "data" / "synthetic_clinical"
SYNTH_V2_PATH = ROOT / "data" / "synth_dataset_v2.json"


def load_synthetic_clinical(split: str) -> List[EvalDoc]:
    """Our synthetic clinical notes (split = "dev" or "test")."""
    records = json.loads((SYNTHETIC_CLINICAL_DIR / f"{split}.json").read_text(encoding="utf-8"))
    docs = []
    for r in records:
        for s in r["phi"]:
            assert is_phi(s["type"]) and r["text"][s["start"]:s["end"]] == s["text"], s
        docs.append(EvalDoc(
            doc_id=r["doc_id"],
            text=r["text"],
            gold=[Span(s["start"], s["end"], s["type"]) for s in r["phi"]],
            ignore=[(s["start"], s["end"]) for s in r["ignore"]],
            hard_negatives=[(h["start"], h["end"], h["kind"]) for h in r["hard_negatives"]],
            meta={"note_type": r["note_type"]},
        ))
    return docs


def load_synth_v2(limit: Optional[int] = None) -> List[EvalDoc]:
    """Presidio-research synth_dataset_v2 (general PII, not clinical), mapped to canonical types."""
    records = json.loads(SYNTH_V2_PATH.read_text(encoding="utf-8"))
    docs = []
    for i, r in enumerate(records[:limit]):
        gold, ignore = [], []
        for s in r["spans"]:
            code = canonical_from_synth_v2(s["entity_type"], s["entity_value"])
            if code == IGNORE:
                ignore.append((s["start_position"], s["end_position"]))
            else:
                gold.append(Span(s["start_position"], s["end_position"], code))
        docs.append(EvalDoc(doc_id=f"synth-{i:04d}", text=r["full_text"], gold=gold, ignore=ignore))
    return docs


DATASETS = {
    "clinical_dev": lambda limit=None: load_synthetic_clinical("dev")[:limit],
    "clinical_test": lambda limit=None: load_synthetic_clinical("test")[:limit],
    "synth_v2": load_synth_v2,
}
