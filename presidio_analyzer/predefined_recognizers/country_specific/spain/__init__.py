# Vendored, unmodified, from microsoft/presidio (MIT License).
# Source: https://github.com/microsoft/presidio/blob/main/presidio-analyzer/presidio_analyzer/predefined_recognizers/country_specific/spain/__init__.py
# Copyright (c) Presidio Contributors.

"""Spain-specific recognizers package."""

from .es_nie_recognizer import EsNieRecognizer
from .es_nif_recognizer import EsNifRecognizer
from .es_passport_recognizer import EsPassportRecognizer

__all__ = [
    "EsNifRecognizer",
    "EsNieRecognizer",
    "EsPassportRecognizer",
]
