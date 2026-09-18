# Vendored, unmodified, from microsoft/presidio (MIT License).
# Source: https://github.com/microsoft/presidio/blob/main/presidio-analyzer/presidio_analyzer/predefined_recognizers/nlp_engine_recognizers/__init__.py
# Copyright (c) Presidio Contributors.

"""NLP engine recognizers package."""

from .spacy_recognizer import SpacyRecognizer
from .stanza_recognizer import StanzaRecognizer
from .transformers_recognizer import TransformersRecognizer

__all__ = [
    "SpacyRecognizer",
    "StanzaRecognizer",
    "TransformersRecognizer",
]
