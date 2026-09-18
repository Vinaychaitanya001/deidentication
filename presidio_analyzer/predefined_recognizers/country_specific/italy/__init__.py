# Vendored, unmodified, from microsoft/presidio (MIT License).
# Source: https://github.com/microsoft/presidio/blob/main/presidio-analyzer/presidio_analyzer/predefined_recognizers/country_specific/italy/__init__.py
# Copyright (c) Presidio Contributors.

"""Italy-specific recognizers."""

from .it_driver_license_recognizer import ItDriverLicenseRecognizer
from .it_fiscal_code_recognizer import ItFiscalCodeRecognizer
from .it_identity_card_recognizer import ItIdentityCardRecognizer
from .it_passport_recognizer import ItPassportRecognizer
from .it_vat_code import ItVatCodeRecognizer

__all__ = [
    "ItFiscalCodeRecognizer",
    "ItDriverLicenseRecognizer",
    "ItIdentityCardRecognizer",
    "ItPassportRecognizer",
    "ItVatCodeRecognizer",
]
