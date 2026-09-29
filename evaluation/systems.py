"""Adapters that turn every compared system into the same thing: final resolved spans.

    B0        regex-only baseline (regex_engine.py), its own overlap resolution
    B1        current full Presidio baseline (build_analyzer.py: spaCy en_core_web_sm),
              Presidio AnonymizerEngine conflict resolution
    B2        B1 with the NER swapped for the clinical de-id transformer (NER ablation); same NLP
              engine as P1, incl. the label-grouping fixes of DECISIONS D6/D16
    P1        Phase-1 clinical pipeline (deid/): clinical NER + detector pack + L4/L5 rules
    P1-noveto P1 without the hard-negative veto rules (veto ablation)
    P1-spacy  P1 with spaCy NER instead of the clinical transformer (detector-pack ablation)

Optional ablations (not in the default run): B2-max = B2 with Presidio's default "max"
aggregation and no word continuation (the configuration first measured in P1.4, D16);
B2-nobio = B2 without the BILOU relabel (D6).

Systems that use the same NLP engine share one cached NlpArtifacts per text, so the
transformer runs once per document for B2, P1 and P1-noveto.
"""

from typing import Callable, Dict, List, Optional

from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import ConflictResolutionStrategy
from presidio_anonymizer.entities import RecognizerResult as AnonymizerResult

from deid.ontology import PRESIDIO_TO_CANONICAL
from evaluation.scorer import Span

_ANONYMIZER = AnonymizerEngine()


def presidio_type(entity_type: str) -> str:
    """Canonical code for scoring. Non-PHI entities (e.g. NRP) keep their name so they still count as redactions."""
    return PRESIDIO_TO_CANONICAL.get(entity_type, entity_type)


def presidio_final_spans(text: str, analyzer_results) -> List[Span]:
    """The spans Presidio's AnonymizerEngine would actually replace, using its own conflict resolution."""
    results = sorted((AnonymizerResult(r.entity_type, r.start, r.end, r.score) for r in analyzer_results),
                     key=lambda r: (r.start, r.end))
    results = _ANONYMIZER._remove_conflicts_and_get_text_manipulation_data(
        results, ConflictResolutionStrategy.MERGE_SIMILAR_OR_CONTAINED)
    results = _ANONYMIZER._merge_entities_with_spaces_between(text, results)
    return [Span(r.start, r.end, presidio_type(r.entity_type)) for r in results]


class ArtifactCache:
    """Runs an NLP engine once per text and shares the NlpArtifacts between analyzers."""

    def __init__(self, nlp_engine):
        self.nlp_engine = nlp_engine
        self._cache: Dict[str, object] = {}

    def __call__(self, text: str):
        if text not in self._cache:
            self._cache[text] = self.nlp_engine.process_text(text, "en")
        return self._cache[text]


class RegexOnlySystem:
    name = "B0 regex-only"

    def __init__(self):
        from regex_engine import RegexAnalyzerEngine, RegexAnonymizerEngine

        self.analyzer = RegexAnalyzerEngine()
        self.resolve = RegexAnonymizerEngine._resolve_overlaps

    def predict(self, text: str) -> List[Span]:
        final = self.resolve(self.analyzer.analyze(text))
        return [Span(r.start, r.end, presidio_type(r.entity_type)) for r in final]


class PresidioSystem:
    def __init__(self, name: str, analyzer, artifacts: Optional[Callable] = None):
        self.name, self.analyzer, self.artifacts = name, analyzer, artifacts

    def predict(self, text: str) -> List[Span]:
        arts = self.artifacts(text) if self.artifacts else None
        results = self.analyzer.analyze(text=text, language="en", nlp_artifacts=arts)
        return presidio_final_spans(text, results)


class Phase1System:
    def __init__(self, name: str, pipeline, artifacts: Callable, use_vetoes: bool = True):
        self.name, self.pipeline, self.artifacts, self.use_vetoes = name, pipeline, artifacts, use_vetoes

    def predict(self, text: str) -> List[Span]:
        result = self.pipeline.detect(text, nlp_artifacts=self.artifacts(text), use_vetoes=self.use_vetoes)
        return [Span(s.start, s.end, s.type) for s in result.final_spans]


def build_systems(names: List[str], ner_model: Optional[str] = None) -> Dict[str, object]:
    """Instantiate the requested systems, sharing NLP engines and artifacts where possible."""
    systems: Dict[str, object] = {}
    spacy_arts = clinical_arts = None

    if "B0" in names:
        systems["B0"] = RegexOnlySystem()

    if {"B1", "P1-spacy"} & set(names):
        from build_analyzer import build_analyzer

        b1 = build_analyzer()
        spacy_arts = ArtifactCache(b1.nlp_engine)
        if "B1" in names:
            systems["B1"] = PresidioSystem("B1 Presidio + spaCy (current full)", b1, spacy_arts)

    if {"B2", "P1", "P1-noveto"} & set(names):
        from deid.engine import build_clinical_nlp_engine, build_presidio_default_analyzer

        engine = build_clinical_nlp_engine(ner_model)
        clinical_arts = ArtifactCache(engine)
        if "B2" in names:
            systems["B2"] = PresidioSystem("B2 Presidio + clinical NER", build_presidio_default_analyzer(engine),
                                           clinical_arts)

    ablations = {  # optional NER-integration ablations (decisions D6, D16)
        "B2-nobio": ("B2 without BILOU relabel", {"relabel_bilou": False}),
        "B2-max": ("B2 with Presidio's default max aggregation",
                   {"aggregation_strategy": "max", "continue_words": False}),
    }
    for key, (label, options) in ablations.items():
        if key in names:
            from deid.engine import build_clinical_nlp_engine, build_presidio_default_analyzer

            engine = build_clinical_nlp_engine(ner_model, **options)
            systems[key] = PresidioSystem(label, build_presidio_default_analyzer(engine), ArtifactCache(engine))

    if {"P1", "P1-noveto"} & set(names):
        from deid.pipeline import ClinicalDeidPipeline

        pipe = ClinicalDeidPipeline.from_nlp_engine(clinical_arts.nlp_engine)
        if "P1" in names:
            systems["P1"] = Phase1System("P1 Phase-1 clinical", pipe, clinical_arts)
        if "P1-noveto" in names:
            systems["P1-noveto"] = Phase1System("P1 without hard-negative vetoes", pipe, clinical_arts,
                                                use_vetoes=False)

    if "P1-spacy" in names:
        from deid.pipeline import ClinicalDeidPipeline

        pipe = ClinicalDeidPipeline.from_nlp_engine(spacy_arts.nlp_engine)
        systems["P1-spacy"] = Phase1System("P1 with spaCy NER", pipe, spacy_arts)

    return {n: systems[n] for n in names if n in systems}
