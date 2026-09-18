# Vendored, unmodified, from microsoft/presidio (MIT License).
# Source: https://github.com/microsoft/presidio/blob/main/presidio-analyzer/presidio_analyzer/predefined_recognizers/country_specific/singapore/__init__.py
# Copyright (c) Presidio Contributors.

"""Singapore-specific recognizers package."""

from .sg_fin_recognizer import SgFinRecognizer
from .sg_uen_recognizer import SgUenRecognizer

__all__ = [
    "SgUenRecognizer",
    "SgFinRecognizer",
]
