# Vendored, unmodified, from microsoft/presidio (MIT License).
# Source: https://github.com/microsoft/presidio/blob/main/presidio-analyzer/presidio_analyzer/predefined_recognizers/country_specific/south_africa/__init__.py
# Copyright (c) Presidio Contributors.

"""South Africa-specific recognizers."""

from .za_company_registration_recognizer import ZaCompanyRegistrationRecognizer
from .za_driver_license_recognizer import ZaDriverLicenseRecognizer
from .za_id_number_recognizer import ZaIdNumberRecognizer
from .za_income_tax_number_recognizer import ZaIncomeTaxNumberRecognizer
from .za_license_plate_recognizer import ZaLicensePlateRecognizer
from .za_passport_recognizer import ZaPassportRecognizer
from .za_phone_number_recognizer import (
    ZaMobileNumberRecognizer,
    ZaTelephoneNumberRecognizer,
)
from .za_traffic_register_number_recognizer import ZaTrafficRegisterNumberRecognizer
from .za_vat_number_recognizer import ZaVatNumberRecognizer

__all__ = [
    "ZaCompanyRegistrationRecognizer",
    "ZaDriverLicenseRecognizer",
    "ZaIdNumberRecognizer",
    "ZaIncomeTaxNumberRecognizer",
    "ZaLicensePlateRecognizer",
    "ZaMobileNumberRecognizer",
    "ZaPassportRecognizer",
    "ZaTelephoneNumberRecognizer",
    "ZaTrafficRegisterNumberRecognizer",
    "ZaVatNumberRecognizer",
]
