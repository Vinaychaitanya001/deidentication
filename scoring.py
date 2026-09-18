"""
Shared scoring logic — OUR OWN code.

Used by BOTH evaluate_full.py and compare_architectures.py so the two
architectures are scored by byte-identical rules. If this file is wrong,
it is wrong for both, and the A/B comparison stays valid.

Design
------
* Recall is measured per DATASET label: "was this labeled PII span found?"
* Precision is measured per PREDICTED label: "was this detection real PII?"
* Predictions whose entity type the dataset NEVER labels (US_BANK_NUMBER,
  CRYPTO, MAC_ADDRESS, UUID, MEDICAL_LICENSE, US_ITIN, US_PASSPORT) are
  counted as UNMEASURABLE, not as false positives. The dataset provides no
  ground truth for them, so we cannot tell whether they are right or wrong;
  scoring them as errors would understate precision for reasons that have
  nothing to do with the architecture.
"""

from collections import defaultdict
from typing import Dict, List, Tuple

from entity_mapping import (
    accepted_presidio_labels,
    is_unreachable,
    satisfied_dataset_labels,
)

Span = Tuple[str, int, int]  # (label, start, end)


def overlaps(a_start: int, a_end: int, b_start: int, b_end: int) -> bool:
    return a_start < b_end and b_start < a_end


class Scorer:
    """Accumulates recall/precision counts across many records."""

    def __init__(self) -> None:
        self.recall = defaultdict(lambda: {"found": 0, "missed": 0})
        self.precision = defaultdict(lambda: {"hit": 0, "spurious": 0})
        self.unmeasurable = defaultdict(int)   # predicted type dataset never labels
        self.unreachable = defaultdict(int)    # labeled type Presidio cannot emit

    def add_record(self, truths: List[Span], preds: List[Span]) -> None:
        # --- recall ---
        for label, ts, te in truths:
            if is_unreachable(label) or not accepted_presidio_labels(label):
                self.unreachable[label] += 1
                continue
            ok = accepted_presidio_labels(label)
            hit = any(
                p in ok and overlaps(ps, pe, ts, te) for p, ps, pe in preds
            )
            self.recall[label]["found" if hit else "missed"] += 1

        # --- precision ---
        for p_label, ps, pe in preds:
            candidates = satisfied_dataset_labels(p_label)
            if not candidates:
                self.unmeasurable[p_label] += 1
                continue
            hit = any(
                t in candidates and overlaps(ps, pe, ts, te) for t, ts, te in truths
            )
            self.precision[p_label]["hit" if hit else "spurious"] += 1

    # ---------------- summary helpers ----------------
    def recall_rows(self) -> List[Dict]:
        rows = []
        for label, c in self.recall.items():
            total = c["found"] + c["missed"]
            rows.append({
                "label": label, "found": c["found"], "missed": c["missed"],
                "total": total,
                "recall": round(c["found"] / total, 3) if total else 0.0,
            })
        return sorted(rows, key=lambda r: -r["total"])

    def precision_rows(self) -> List[Dict]:
        rows = []
        for label, c in self.precision.items():
            total = c["hit"] + c["spurious"]
            rows.append({
                "label": label, "hit": c["hit"], "spurious": c["spurious"],
                "total": total,
                "precision": round(c["hit"] / total, 3) if total else 0.0,
            })
        return sorted(rows, key=lambda r: -r["total"])

    def totals(self) -> Dict:
        f = sum(c["found"] for c in self.recall.values())
        m = sum(c["missed"] for c in self.recall.values())
        h = sum(c["hit"] for c in self.precision.values())
        s = sum(c["spurious"] for c in self.precision.values())
        rec = f / (f + m) if (f + m) else 0.0
        prec = h / (h + s) if (h + s) else 0.0
        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
        return {
            "found": f, "missed": m, "labeled_reachable": f + m,
            "hit": h, "spurious": s, "predictions_scored": h + s,
            "recall": round(rec, 3), "precision": round(prec, 3), "f1": round(f1, 3),
            "unmeasurable_predictions": sum(self.unmeasurable.values()),
            "unreachable_ground_truth": sum(self.unreachable.values()),
        }
