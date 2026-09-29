"""L7 assurance — Phase 1: the span manifest (positions, types, actions, sources; never original values).

An independent leak scan of the output and a human review queue are P2.8.
"""

from typing import Dict, List

from deid.contracts import DetectionResult

# Replacements that repeat part of the original value; the manifest omits them.
_KEEPS_ORIGINAL = {"keep_year", "keep_age_under_90", "keep_state", "zip3"}


def build_manifest(detection: DetectionResult, actions: List[Dict], profile: str, demo_key: bool) -> Dict:
    rejected: Dict[str, int] = {}
    for d in detection.decisions:
        if not d.accepted:
            reason = d.reason.split(":")[0] if not d.reason.startswith("veto:") else d.reason
            rejected[reason] = rejected.get(reason, 0) + 1
    spans = []
    for a in actions:
        s = a["span"]
        spans.append({
            "start": s.start, "end": s.end, "length": s.end - s.start, "type": s.type, "action": a["action"],
            "output_start": a["output_start"], "output_end": a["output_end"],
            "replacement": None if a["action"] in _KEEPS_ORIGINAL else a["replacement"],
            "score": s.score, "sources": list(s.sources),
            "evidence": [list(e) for e in s.evidence if e[0] in ("field_kind", "pattern", "context_word", "over_89")],
        })
    return {
        "doc_id": detection.document.doc_id,
        "language": detection.document.language,
        "profile": profile,
        "hmac_key": "DEMO KEY - not for real data" if demo_key else "DEID_HMAC_KEY",
        "date_shift": "one offset per document, derived from the key; not recorded",
        "n_candidates": len(detection.candidates),
        "n_final_spans": len(detection.final_spans),
        "rejected_candidates": dict(sorted(rejected.items())),
        "spans": spans,
    }
