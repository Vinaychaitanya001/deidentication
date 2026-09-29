"""L5 consistency — Phase 1: deterministic overlap resolution only (DECISIONS D14).

Entity memory and propagation to repeated mentions and name variants are P2.4; they will plug in
behind the same `ConsistencyStep` interface.
"""

from dataclasses import replace
from typing import List, Tuple

from deid.contracts import Candidate, Document, FinalSpan
from deid.ontology import category
from deid.spans import has_alnum, trim

FIELD_KEY_SOURCES = frozenset({"FieldKeyDetector"})
# Clinical detector pack + Presidio recognizers that validate what they match (checksum, parser, TLD ...).
PACK_AND_VALIDATOR_SOURCES = frozenset({
    "AgeDetector", "UsZipDetector", "FaxPagerDetector", "ClinicianCueDetector", "HospitalDetector",
    "EmailRecognizer", "UrlRecognizer", "IpRecognizer", "PhoneRecognizer", "CreditCardRecognizer", "IbanRecognizer",
    "CryptoRecognizer", "UsNpiRecognizer", "UsSsnRecognizer", "MacAddressRecognizer",
})


def priority(c: Candidate) -> int:
    """2 field key > 1 clinical pack / validators > 0 NER and generic patterns."""
    if c.source in FIELD_KEY_SOURCES:
        return 2
    return 1 if c.source in PACK_AND_VALIDATOR_SOURCES else 0


def _uncovered(start: int, end: int, placed: List[FinalSpan]) -> List[Tuple[int, int]]:
    segments, pos = [], start
    for p in sorted(placed, key=lambda s: s.start):
        if p.end <= pos or p.start >= end:
            continue
        if p.start > pos:
            segments.append((pos, p.start))
        pos = max(pos, p.end)
    if pos < end:
        segments.append((pos, end))
    return segments


class OverlapResolver:
    """Highest priority first (ties: longer span, then higher score); a winner keeps its exact
    boundaries, and later candidates keep only characters not yet covered. Nothing a candidate
    covered is lost; fragments without letters or digits are dropped."""

    def resolve(self, document: Document, accepted: List[Candidate]) -> List[FinalSpan]:
        text = document.text
        placed: List[FinalSpan] = []
        for c in sorted(accepted, key=lambda c: (-priority(c), -(c.end - c.start), -c.raw_score, c.start, c.source)):
            for i, p in enumerate(placed):  # record agreement of same-category detectors
                if p.start < c.end and c.start < p.end and category(p.type) == category(c.type_hint) \
                        and c.source not in p.sources:
                    placed[i] = replace(p, sources=p.sources + (c.source,))
            for s, e in _uncovered(c.start, c.end, placed):
                s, e = trim(text, s, e)
                if s < e and has_alnum(text, s, e):
                    placed.append(FinalSpan(s, e, c.type_hint, c.raw_score, (c.source,), c.evidence))
        return sorted(placed, key=lambda s: (s.start, s.end))
