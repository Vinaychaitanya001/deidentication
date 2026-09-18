# Vendored, unmodified, from microsoft/presidio (MIT License).
# Source: https://github.com/microsoft/presidio/blob/main/presidio-analyzer/presidio_analyzer/local_recognizer.py
# Copyright (c) Presidio Contributors.

from abc import ABC

from presidio_analyzer import EntityRecognizer


class LocalRecognizer(ABC, EntityRecognizer):
    """PII entity recognizer which runs on the same process as the AnalyzerEngine."""
