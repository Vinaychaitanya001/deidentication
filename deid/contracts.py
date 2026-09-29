"""Data contracts passed between the L0-L7 stages, and the interfaces Phase-2 parts will implement.

See docs/ARCHITECTURE.md ("Data contracts"). Phase 1 carries raw detector scores and rule
outcomes; calibrated probabilities arrive with the Phase-2 fusion model (P2.2).
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Protocol, Tuple

Evidence = Tuple[Tuple[str, str], ...]


@dataclass(frozen=True)
class KeyValueField:
    """L1: a field such as "MRN: 4829173"; `kind` says what the value holds (e.g. "ID.MRN")."""

    key: str
    kind: str
    key_start: int
    key_end: int
    value_start: int
    value_end: int


@dataclass
class Document:
    """One note flowing through L0-L7; each stage adds its layer. Offsets refer to `text`."""

    doc_id: str
    text: str
    language: str = "en"
    fields: List[KeyValueField] = field(default_factory=list)  # L1 (Phase 1: field keys only)


@dataclass(frozen=True)
class Candidate:
    """L3: one detector's proposal. `type_hint` is None when the entity is not PHI (e.g. NRP)."""

    start: int
    end: int
    type_hint: Optional[str]
    entity: str
    source: str
    raw_score: float
    evidence: Evidence = ()


@dataclass(frozen=True)
class Decision:
    """L4: the rule outcome for one candidate (Phase 1 has no calibrated probability)."""

    candidate: Candidate
    accepted: bool
    reason: str


@dataclass(frozen=True)
class FinalSpan:
    """L5: one span of the clean, non-overlapping set that L6 transforms."""

    start: int
    end: int
    type: str
    score: float
    sources: Tuple[str, ...]
    evidence: Evidence = ()


@dataclass
class DetectionResult:
    document: Document
    candidates: List[Candidate]
    decisions: List[Decision]
    final_spans: List[FinalSpan]


@dataclass
class DeidResult:
    detection: DetectionResult
    text: str
    manifest: Dict


class Decider(Protocol):
    """L4. Phase 1: RuleBasedDecider. Phase 2 (P2.2): calibrated fusion behind the same call."""

    def decide(self, document: Document, candidates: List[Candidate], use_vetoes: bool = True) -> List[Decision]:
        ...


class ConsistencyStep(Protocol):
    """L5. Phase 1: OverlapResolver. Phase 2 (P2.4): entity memory / propagation."""

    def resolve(self, document: Document, accepted: List[Candidate]) -> List[FinalSpan]:
        ...
