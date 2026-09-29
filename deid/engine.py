"""L2/L3 engine factory: NLP engines and Presidio analyzers for the pipeline and the baselines."""

import types
from typing import Dict, List, Optional

from presidio_analyzer import AnalyzerEngine, RecognizerRegistry, RecognizerResult
from presidio_analyzer.context_aware_enhancers import LemmaContextAwareEnhancer
from presidio_analyzer.nlp_engine import NerModelConfiguration, TransformersNlpEngine
from presidio_analyzer.predefined_recognizers import UsMbiRecognizer, UsNpiRecognizer

from deid.detectors import clinical_detector_pack
from deid.ontology import OBI_DEID_TO_PRESIDIO

DEFAULT_NER_MODEL = "obi/deid_roberta_i2b2"
SPACY_MODEL = "en_core_web_sm"


def _bilou_to_bio(label: str) -> str:
    if label.startswith("U-"):
        return "B-" + label[2:]
    if label.startswith("L-"):
        return "I-" + label[2:]
    return label


def _group_entities_continuing_words(self, entities: List[Dict]) -> List[Dict]:
    """Hugging Face `group_entities`, except that a B- piece glued to a same-type piece inside one
    word continues that entity: "3"(B-LOC) + "102 Oak Avenue"(B-LOC) → "3102 Oak Avenue"."""
    fixed: List[Dict] = []
    for e in entities:
        if fixed and e["entity"].startswith("B-"):
            prev = fixed[-1]
            prev_text = self.tokenizer.convert_tokens_to_string([prev["word"]])
            text = self.tokenizer.convert_tokens_to_string([e["word"]])
            if (prev["end"] == e["start"] and prev["entity"][2:] == e["entity"][2:]
                    and prev_text[-1:].isalnum() and text[:1].isalnum()):
                e = dict(e, entity="I-" + e["entity"][2:])
        fixed.append(e)
    return type(self).group_entities(self, fixed)


class ClinicalTransformersNlpEngine(TransformersNlpEngine):
    """Presidio's TransformersNlpEngine with two label-grouping fixes for obi/deid_* models.

    relabel_bilou: the model emits B-/I-/L-/U- tags. Hugging Face's grouping only treats B- as the
    start of an entity, so an L- or U- token opens a new group and multi-word entities come out
    split ("Lakshmi" + "Okafor"); labels stay clean because the group name drops the prefix.
    Relabelling U-→B- and L-→I- keeps each entity as one span (DECISIONS D6).

    continue_words: the model sometimes starts an entity again on a sub-word piece ("Ġ3" B-LOC,
    "102" B-LOC). spacy-huggingface-pipelines expands the first piece to the whole token and then
    drops the rest of the entity as "overlapping", so "3102 Oak Avenue" became "3102". Such a B-
    piece continues the entity instead (DECISIONS D16).
    """

    def __init__(self, *args, relabel_bilou: bool = True, continue_words: bool = True, **kwargs):
        super().__init__(*args, **kwargs)
        self.relabel_bilou = relabel_bilou
        self.continue_words = continue_words

    def load(self) -> None:
        super().load()
        for nlp in self.nlp.values():
            hf_pipeline = nlp.get_pipe("hf_token_pipe").hf_pipeline
            if self.relabel_bilou:
                config = hf_pipeline.model.config
                config.id2label = {i: _bilou_to_bio(label) for i, label in config.id2label.items()}
            if self.continue_words:
                hf_pipeline.group_entities = types.MethodType(_group_entities_continuing_words, hf_pipeline)


def build_clinical_nlp_engine(model_name: Optional[str] = None, relabel_bilou: bool = True,
                              aggregation_strategy: str = "simple",
                              continue_words: bool = True) -> ClinicalTransformersNlpEngine:
    """Clinical de-id NER; keeps PATIENT and STAFF as separate Presidio entities.

    Aggregation is "simple", not Presidio's default "max" (DECISIONS D16): for byte-level BPE models
    Hugging Face guesses word boundaries from spaces only, so "2024." or "Consultation\nAugust" or
    "27-year-old" count as one word and "max" gives the whole word the label of its highest-scoring
    piece, often O. "simple" groups the model's own token labels; spans are expanded to whole spaCy
    tokens by alignment_mode="expand".
    """
    conf = NerModelConfiguration(
        model_to_presidio_entity_mapping=dict(OBI_DEID_TO_PRESIDIO),
        labels_to_ignore=["O"],
        aggregation_strategy=aggregation_strategy,
        stride=16,
        alignment_mode="expand",
    )
    engine = ClinicalTransformersNlpEngine(
        models=[{"lang_code": "en",
                 "model_name": {"spacy": SPACY_MODEL, "transformers": model_name or DEFAULT_NER_MODEL}}],
        ner_model_configuration=conf,
        relabel_bilou=relabel_bilou,
        continue_words=continue_words,
    )
    engine.load()
    return engine


def build_presidio_default_analyzer(nlp_engine) -> AnalyzerEngine:
    """Presidio's default English + US recognizers on top of the given NLP engine (baseline B2)."""
    registry = RecognizerRegistry(supported_languages=["en"])
    registry.load_predefined_recognizers(languages=["en"], nlp_engine=nlp_engine, countries=["us"])
    return AnalyzerEngine(registry=registry, nlp_engine=nlp_engine, supported_languages=["en"])


class CandidateAnalyzer(AnalyzerEngine):
    """Presidio's AnalyzerEngine plus `candidates()`: the same recognizers and context enhancement,
    but every result is returned (DECISIONS D17).

    `analyze()` drops a result contained in a higher-scoring result of the same entity type. That is
    an overlap decision, which the architecture reserves for L4-L5 (invariant rule 2): a field-key DOB
    or an AgeDetector match disappears behind an identical NER span, and a clean pattern span can
    disappear inside a longer NER span of the same type. `analyze()` itself is unchanged.
    """

    def candidates(self, text: str, language: str = "en", nlp_artifacts=None) -> List[RecognizerResult]:
        recognizers = self.registry.get_recognizers(language=language, all_fields=True)
        entities = self.get_supported_entities(language=language)
        if nlp_artifacts is None:
            nlp_artifacts = self.nlp_engine.process_text(text, language)
        results: List[RecognizerResult] = []
        for recognizer in recognizers:
            if not recognizer.is_loaded:
                recognizer.load()
                recognizer.is_loaded = True
            for r in recognizer.analyze(text=text, entities=entities, nlp_artifacts=nlp_artifacts) or []:
                r.recognition_metadata = r.recognition_metadata or {}
                r.recognition_metadata.setdefault(RecognizerResult.RECOGNIZER_NAME_KEY, recognizer.name)
                r.recognition_metadata.setdefault(RecognizerResult.RECOGNIZER_IDENTIFIER_KEY, recognizer.id)
                results.append(r)
        results = self._enhance_using_context(text, results, nlp_artifacts, recognizers, None)
        return [r for r in results if r.score > 0]


def build_clinical_analyzer(nlp_engine) -> CandidateAnalyzer:
    """P1 (L3): Presidio's predefined en/US recognizers, NPI and MBI enabled (off in Presidio's
    default config), the clinical detector pack, and whole-word context matching (P1.5).

    Weak driver-licence and bank-number patterns are gated later, in the L4 decider.
    """
    registry = RecognizerRegistry(supported_languages=["en"])
    registry.load_predefined_recognizers(languages=["en"], nlp_engine=nlp_engine, countries=["us"])
    for recognizer in [UsNpiRecognizer(), UsMbiRecognizer(), *clinical_detector_pack()]:
        registry.add_recognizer(recognizer)
    return CandidateAnalyzer(registry=registry, nlp_engine=nlp_engine, supported_languages=["en"],
                             context_aware_enhancer=LemmaContextAwareEnhancer(context_matching_mode="whole_word"))
