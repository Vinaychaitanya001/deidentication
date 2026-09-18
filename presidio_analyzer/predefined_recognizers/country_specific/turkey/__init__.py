# Vendored, unmodified, from microsoft/presidio (MIT License).
# Source: https://github.com/microsoft/presidio/blob/main/presidio-analyzer/presidio_analyzer/predefined_recognizers/country_specific/turkey/__init__.py
# Copyright (c) Presidio Contributors.

"""Turkey-specific recognizers."""

from .tr_license_plate_recognizer import TrLicensePlateRecognizer
from .tr_national_id_recognizer import TrNationalIdRecognizer

__all__ = [
    "TrLicensePlateRecognizer",
    "TrNationalIdRecognizer",
]
