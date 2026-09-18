# Vendored, unmodified, from microsoft/presidio (MIT License).
# Source: https://github.com/microsoft/presidio/blob/main/presidio-analyzer/presidio_analyzer/predefined_recognizers/country_specific/poland/__init__.py
# Copyright (c) Presidio Contributors.

"""Poland-specific recognizers."""

from .pl_pesel_recognizer import PlPeselRecognizer

__all__ = [
    "PlPeselRecognizer",
]
