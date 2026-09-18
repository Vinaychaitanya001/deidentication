# Vendored, unmodified, from microsoft/presidio (MIT License).
# Source: https://github.com/microsoft/presidio/blob/main/presidio-analyzer/presidio_analyzer/predefined_recognizers/country_specific/__init__.py
# Copyright (c) Presidio Contributors.

"""Country-specific recognizers package."""

from .canada.ca_sin_recognizer import CaSinRecognizer

__all__ = [
    "CaSinRecognizer",
]
