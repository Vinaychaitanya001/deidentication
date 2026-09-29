"""L4 evidence fusion & decision — Phase 1: rules only (DECISIONS D12).

No calibration: candidates carry raw detector scores and each decision is a rule outcome. The
calibrated fusion model (P2.2) will replace RuleBasedDecider behind the same `Decider` interface.
"""

from typing import Dict, List, Optional

from deid.contracts import Candidate, Decision, Document
from deid.hard_negatives import find_hard_negatives, vetoing_region

# Presidio's weak patterns (driver licence: any 6-14 digits at 0.01 or letter+digits at 0.3; bank
# number: any 8-17 digits at 0.05) fire on MRNs, accession numbers and other clinical numbers.
# They are kept only when a context word ("license", "account" ...) lifted the score to 0.4.
MIN_SCORES: Dict[str, float] = {"US_DRIVER_LICENSE": 0.4, "US_BANK_NUMBER": 0.4}

# A value read from a labelled field ("MRN: ...") is never vetoed by a look-alike rule.
NEVER_VETOED_SOURCES = frozenset({"FieldKeyDetector"})


class RuleBasedDecider:
    """Per-entity minimum scores, then hard-negative vetoes (P1.6). Default minimum 0.0, as in Presidio."""

    def __init__(self, min_scores: Optional[Dict[str, float]] = None, default_min_score: float = 0.0):
        self.min_scores = dict(MIN_SCORES if min_scores is None else min_scores)
        self.default_min_score = default_min_score

    def decide(self, document: Document, candidates: List[Candidate], use_vetoes: bool = True) -> List[Decision]:
        regions = find_hard_negatives(document.text) if use_vetoes else []
        decisions = []
        for c in candidates:
            minimum = self.min_scores.get(c.entity, self.default_min_score)
            if c.type_hint is None:
                decisions.append(Decision(c, False, "not_phi"))
            elif c.raw_score < minimum:
                decisions.append(Decision(c, False, f"below_min_score:{minimum}"))
            else:
                region = None
                if use_vetoes and c.source not in NEVER_VETOED_SOURCES:
                    region = vetoing_region(c.start, c.end, c.type_hint, regions)
                decisions.append(Decision(c, False, f"veto:{region.kind}") if region else Decision(c, True, "accepted"))
        return decisions
