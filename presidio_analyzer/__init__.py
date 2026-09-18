# OUR OWN code (not copied from microsoft/presidio).
#
# Faithful to upstream presidio_analyzer/__init__.py and in the SAME import
# order (each line only resolves because previous lines already bound their
# names into this package's namespace), with three deliberate omissions:
#
#   * LMRecognizer            -> needs presidio_analyzer.llm_utils, which
#                                requires langextract + Azure credentials
#   * AnalyzerRequest         -> REST API request object, unused in a library
#   * AnalyzerEngineProvider  -> REST/YAML bootstrap layer, unused here
#
# Everything the full detection pipeline needs is present. See
# VENDORED_FILES.md for the complete copied-vs-written breakdown.

import logging

from presidio_analyzer.analysis_explanation import AnalysisExplanation
from presidio_analyzer.recognizer_result import RecognizerResult
from presidio_analyzer.dict_analyzer_result import DictAnalyzerResult
from presidio_analyzer.entity_recognizer import EntityRecognizer
from presidio_analyzer.local_recognizer import LocalRecognizer
from presidio_analyzer.pattern import Pattern
from presidio_analyzer.pattern_recognizer import PatternRecognizer
from presidio_analyzer.remote_recognizer import RemoteRecognizer
from presidio_analyzer.recognizer_registry import RecognizerRegistry
from presidio_analyzer.analyzer_engine import AnalyzerEngine
from presidio_analyzer.batch_analyzer_engine import BatchAnalyzerEngine
from presidio_analyzer.context_aware_enhancers import (
    ContextAwareEnhancer,
    LemmaContextAwareEnhancer,
)

logging.getLogger("presidio-analyzer").addHandler(logging.NullHandler())

__all__ = [
    "AnalysisExplanation",
    "RecognizerResult",
    "DictAnalyzerResult",
    "EntityRecognizer",
    "LocalRecognizer",
    "Pattern",
    "PatternRecognizer",
    "RemoteRecognizer",
    "RecognizerRegistry",
    "AnalyzerEngine",
    "BatchAnalyzerEngine",
    "ContextAwareEnhancer",
    "LemmaContextAwareEnhancer",
]
