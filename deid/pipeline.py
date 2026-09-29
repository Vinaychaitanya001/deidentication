"""Phase-1 clinical de-identification pipeline: L0 → L7 on one shared Document.

    L0 ingest (pass-through)          deid/ingest.py
    L1 key:value fields               deid/structure.py
    L2 English language pack          deid/langpack_en.py + the NLP engine's tokens/lemmas
    L3 candidates                     Presidio recognizers + clinical detector pack + clinical NER
    L4 rule-based decision            deid/decision.py (gates + hard-negative vetoes)
    L5 overlap resolution             deid/consistency.py
    L6 Safe Harbor transformation     deid/transform.py
    L7 span manifest                  deid/assurance.py
"""

from typing import List, Optional

from presidio_analyzer import AnalyzerEngine, RecognizerResult

from deid.assurance import build_manifest
from deid.consistency import OverlapResolver
from deid.contracts import Candidate, ConsistencyStep, Decider, DeidResult, DetectionResult
from deid.decision import RuleBasedDecider
from deid.engine import build_clinical_analyzer, build_clinical_nlp_engine
from deid.ingest import ingest
from deid.ontology import NON_PHI_PRESIDIO, PRESIDIO_TO_CANONICAL
from deid.spans import has_alnum, trim
from deid.structure import find_fields
from deid.transform import SafeHarborTransformer

_STANDARD_METADATA = {RecognizerResult.RECOGNIZER_NAME_KEY, RecognizerResult.RECOGNIZER_IDENTIFIER_KEY,
                      RecognizerResult.IS_SCORE_ENHANCED_BY_CONTEXT_KEY}


def presidio_candidates(text: str, results: List[RecognizerResult]) -> List[Candidate]:
    """L3 output as Candidates: canonical type hint, source, raw score, evidence, trimmed edges (D15)."""
    candidates = {}
    for r in results:
        start, end = trim(text, r.start, r.end)
        if start >= end or not has_alnum(text, start, end):
            continue
        meta = r.recognition_metadata or {}
        evidence = [(k, str(v)) for k, v in sorted(meta.items()) if k not in _STANDARD_METADATA]
        explanation = r.analysis_explanation
        if explanation is not None:
            if explanation.pattern_name:
                evidence.append(("pattern", explanation.pattern_name))
            if explanation.supportive_context_word:
                evidence.append(("context_word", explanation.supportive_context_word))
        type_hint = None if r.entity_type in NON_PHI_PRESIDIO else PRESIDIO_TO_CANONICAL.get(r.entity_type, "OTHER")
        c = Candidate(start, end, type_hint, r.entity_type, meta.get(RecognizerResult.RECOGNIZER_NAME_KEY, "unknown"),
                      round(r.score, 4), tuple(evidence))
        key = (c.start, c.end, c.entity, c.source)  # one detector proposing the same span twice counts once
        if key not in candidates or c.raw_score > candidates[key].raw_score:
            candidates[key] = c
    return sorted(candidates.values(), key=lambda c: (c.start, c.end, c.source))


class ClinicalDeidPipeline:
    def __init__(self, analyzer: AnalyzerEngine, decider: Optional[Decider] = None,
                 consistency: Optional[ConsistencyStep] = None, transformer=None):
        self.analyzer = analyzer
        self.decider = decider or RuleBasedDecider()
        self.consistency = consistency or OverlapResolver()
        self.transformer = transformer or SafeHarborTransformer()

    @classmethod
    def from_nlp_engine(cls, nlp_engine, **kwargs) -> "ClinicalDeidPipeline":
        return cls(build_clinical_analyzer(nlp_engine), **kwargs)

    @classmethod
    def build(cls, ner_model: Optional[str] = None, **kwargs) -> "ClinicalDeidPipeline":
        """Clinical NER (obi/deid_roberta_i2b2 by default) + detector pack + Phase-1 rules."""
        return cls.from_nlp_engine(build_clinical_nlp_engine(ner_model), **kwargs)

    def detect(self, text: str, doc_id: str = "doc", nlp_artifacts=None, use_vetoes: bool = True) -> DetectionResult:
        document = ingest(text, doc_id)                                                    # L0
        document.fields = find_fields(text)                                                # L1
        if hasattr(self.analyzer, "candidates"):                                           # L2 + L3
            results = self.analyzer.candidates(text, document.language, nlp_artifacts)
        else:  # a stock AnalyzerEngine has already removed contained same-type results (D17)
            results = self.analyzer.analyze(text=text, language=document.language, nlp_artifacts=nlp_artifacts,
                                            return_decision_process=True)
        candidates = presidio_candidates(text, results)
        decisions = self.decider.decide(document, candidates, use_vetoes=use_vetoes)       # L4
        final_spans = self.consistency.resolve(document, [d.candidate for d in decisions if d.accepted])  # L5
        return DetectionResult(document, candidates, decisions, final_spans)

    def deidentify(self, text: str, doc_id: str = "doc", nlp_artifacts=None, use_vetoes: bool = True) -> DeidResult:
        detection = self.detect(text, doc_id, nlp_artifacts=nlp_artifacts, use_vetoes=use_vetoes)
        output, actions = self.transformer.apply(detection)                                # L6
        manifest = build_manifest(detection, actions, self.transformer.profile, self.transformer.demo_key)  # L7
        return DeidResult(detection, output, manifest)
