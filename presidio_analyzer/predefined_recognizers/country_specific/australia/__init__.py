# Vendored, unmodified, from microsoft/presidio (MIT License).
# Source: https://github.com/microsoft/presidio/blob/main/presidio-analyzer/presidio_analyzer/predefined_recognizers/country_specific/australia/__init__.py
# Copyright (c) Presidio Contributors.

"""Australia-specific recognizers."""

from .au_abn_recognizer import AuAbnRecognizer
from .au_acn_recognizer import AuAcnRecognizer
from .au_medicare_recognizer import AuMedicareRecognizer
from .au_tfn_recognizer import AuTfnRecognizer

__all__ = [
    "AuAbnRecognizer",
    "AuAcnRecognizer",
    "AuMedicareRecognizer",
    "AuTfnRecognizer",
]
