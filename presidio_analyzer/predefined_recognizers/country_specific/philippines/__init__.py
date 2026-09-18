# Vendored, unmodified, from microsoft/presidio (MIT License).
# Source: https://github.com/microsoft/presidio/blob/main/presidio-analyzer/presidio_analyzer/predefined_recognizers/country_specific/philippines/__init__.py
# Copyright (c) Presidio Contributors.

"""Philippines-specific recognizers."""

from .ph_passport_recognizer import PhPassportRecognizer
from .ph_tin_recognizer import PhTinRecognizer
from .ph_umid_recognizer import PhUmidRecognizer

__all__ = [
    "PhPassportRecognizer",
    "PhTinRecognizer",
    "PhTinRecognizer",
    "PhUmidRecognizer",
]
