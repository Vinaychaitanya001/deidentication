"""
Regex-only analyzer/anonymizer orchestration - OUR OWN code.

Nothing in this file is copied from microsoft/presidio. The real
AnalyzerEngine and AnonymizerEngine (presidio-analyzer/analyzer_engine.py,
presidio-anonymizer/anonymizer_engine.py) pull in a RecognizerRegistryProvider,
an NlpEngineProvider (which imports spaCy/Stanza/transformers unconditionally),
an OperatorsFactory, conflict-resolution strategies for overlapping/nested
entities across recognizer types, batch and dict-input handling, etc. That
machinery exists to support NER recognizers, YAML-driven recognizer loading,
and de-anonymization - none of which apply here.

This module reimplements just the two loops that matter for a pure
regex/checksum pipeline, built directly on the vendored
presidio_analyzer / presidio_anonymizer classes:

  RegexAnalyzerEngine.analyze()   - run every registered PatternRecognizer
                                     (or PhoneRecognizer) over the text and
                                     merge/deduplicate their RecognizerResults.

  RegexAnonymizerEngine.anonymize() - apply an Operator (mask/redact/replace/
                                     hash) per entity type, right-to-left over
                                     the text, using the vendored
                                     TextReplaceBuilder to keep offsets valid.
"""

from typing import Dict, List, Optional

from presidio_analyzer import EntityRecognizer, RecognizerResult
from presidio_analyzer.predefined_recognizers import (
    CreditCardRecognizer,
    CryptoRecognizer,
    DateRecognizer,
    EmailRecognizer,
    IbanRecognizer,
    IpRecognizer,
    MacAddressRecognizer,
    PhoneRecognizer,
    UrlRecognizer,
    UuidRecognizer,
)
from presidio_anonymizer import OperatorConfig
from presidio_anonymizer.core import TextReplaceBuilder
from presidio_anonymizer.operators import Hash, Mask, Redact, Replace


def default_recognizers() -> List[EntityRecognizer]:
    """Instantiate one of each vendored regex/checksum recognizer."""
    return [
        CreditCardRecognizer(),
        CryptoRecognizer(),
        DateRecognizer(),
        EmailRecognizer(),
        IbanRecognizer(),
        IpRecognizer(),
        MacAddressRecognizer(),
        PhoneRecognizer(),
        UrlRecognizer(),
        UuidRecognizer(),
    ]


class RegexAnalyzerEngine:
    """Runs a set of regex/checksum recognizers over text - no NLP engine."""

    def __init__(
        self,
        recognizers: Optional[List[EntityRecognizer]] = None,
        supported_language: str = "en",
    ):
        self.recognizers = recognizers if recognizers is not None else default_recognizers()
        self.supported_language = supported_language

    def get_supported_entities(self) -> List[str]:
        """List every entity type any registered recognizer can detect."""
        entities = set()
        for recognizer in self.recognizers:
            entities.update(recognizer.get_supported_entities())
        return sorted(entities)

    def analyze(
        self,
        text: str,
        entities: Optional[List[str]] = None,
        language: Optional[str] = None,
        score_threshold: float = 0.0,
    ) -> List[RecognizerResult]:
        """
        Detect PII in ``text`` using only regex/checksum recognizers.

        :param text: text to scan
        :param entities: restrict detection to these entity types
            (None = every entity any recognizer supports)
        :param language: recognizer language filter (default: "en")
        :param score_threshold: drop results scoring below this value
        :return: deduplicated, sorted RecognizerResult list
        """
        language = language or self.supported_language
        results: List[RecognizerResult] = []

        for recognizer in self.recognizers:
            if recognizer.get_supported_language() != language:
                continue
            supported = recognizer.get_supported_entities()
            if entities is not None and not set(entities) & set(supported):
                continue
            results.extend(recognizer.analyze(text=text, entities=supported))

        results = EntityRecognizer.remove_duplicates(results)
        results = [r for r in results if r.score >= score_threshold]
        return sorted(results, key=lambda r: r.start)


class RegexAnonymizerEngine:
    """Applies Mask/Redact/Replace/Hash operators to analyzer results."""

    _OPERATOR_CLASSES = {
        "mask": Mask,
        "redact": Redact,
        "replace": Replace,
        "hash": Hash,
    }
    DEFAULT_OPERATOR = OperatorConfig("replace")

    def anonymize(
        self,
        text: str,
        analyzer_results: List[RecognizerResult],
        operators: Optional[Dict[str, OperatorConfig]] = None,
    ) -> str:
        """
        Replace every detected span in ``text`` per its configured operator.

        :param text: the original text
        :param analyzer_results: output of RegexAnalyzerEngine.analyze()
        :param operators: entity_type -> OperatorConfig; "DEFAULT" sets the
            fallback for entity types without an explicit entry (falls back
            to ``replace``, matching real Presidio's default)
        :return: the anonymized text
        """
        operators = operators or {}
        default_operator = operators.get("DEFAULT", self.DEFAULT_OPERATOR)

        resolved_results = self._resolve_overlaps(analyzer_results)

        # Apply right-to-left so earlier (lower-index) spans keep valid
        # offsets as later ones are replaced - the same ordering
        # TextReplaceBuilder was designed for.
        results_desc = sorted(resolved_results, key=lambda r: r.start, reverse=True)
        builder = TextReplaceBuilder(original_text=text)

        for result in results_desc:
            config = operators.get(result.entity_type, default_operator)
            operator_cls = self._OPERATOR_CLASSES.get(config.operator_name)
            if operator_cls is None:
                raise ValueError(f"Unknown operator '{config.operator_name}'")

            original_span = builder.get_text_in_position(result.start, result.end)
            params = self._with_defaults(config.operator_name, config.params, original_span)
            params.setdefault("entity_type", result.entity_type)

            operator = operator_cls()
            operator.validate(params)
            new_text = operator.operate(text=original_span, params=params)
            builder.replace_text_get_insertion_index(new_text, result.start, result.end)

        return builder.output_text

    @staticmethod
    def _resolve_overlaps(results: List[RecognizerResult]) -> List[RecognizerResult]:
        """Drop lower-scoring results whose span overlaps a kept one.

        EntityRecognizer.remove_duplicates (vendored, used by
        RegexAnalyzerEngine.analyze) only drops overlaps *within the same
        entity_type*. It's intentionally permissive across types, so
        analyze() can surface e.g. both EMAIL_ADDRESS and a same-text URL
        match for inspection. But replacing both spans independently here
        would corrupt the output (two operators writing into overlapping
        ranges). Real Presidio's AnonymizerEngine has dedicated conflict-
        resolution-strategy code for this; this is our minimal equivalent -
        highest score wins, ties broken by the longer span.
        """
        ordered = sorted(results, key=lambda r: (-r.score, -(r.end - r.start)))
        kept: List[RecognizerResult] = []
        for result in ordered:
            if not any(result.intersects(other) for other in kept):
                kept.append(result)
        return sorted(kept, key=lambda r: r.start)

    @staticmethod
    def _with_defaults(operator_name: str, params: dict, original_span: str) -> dict:
        params = dict(params)
        if operator_name == "mask":
            params.setdefault("masking_char", "*")
            params.setdefault("chars_to_mask", len(original_span))
            params.setdefault("from_end", False)
        elif operator_name == "hash":
            params.setdefault("hash_type", "sha256")
        elif operator_name == "replace":
            params.setdefault("new_value", None)
        return params
