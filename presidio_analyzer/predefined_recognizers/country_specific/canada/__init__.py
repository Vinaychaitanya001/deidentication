# Vendored, unmodified, from microsoft/presidio (MIT License).
# Source: https://github.com/microsoft/presidio/blob/main/presidio-analyzer/presidio_analyzer/predefined_recognizers/country_specific/canada/__init__.py
# Copyright (c) Presidio Contributors.

"""Canada-specific recognizers package."""

from .ca_postal_code_recognizer import CaPostalCodeRecognizer
from .ca_sin_recognizer import CaSinRecognizer

__all__ = [
    "CaPostalCodeRecognizer",
    "CaSinRecognizer",
]
