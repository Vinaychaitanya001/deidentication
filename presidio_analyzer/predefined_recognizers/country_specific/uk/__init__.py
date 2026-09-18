# Vendored, unmodified, from microsoft/presidio (MIT License).
# Source: https://github.com/microsoft/presidio/blob/main/presidio-analyzer/presidio_analyzer/predefined_recognizers/country_specific/uk/__init__.py
# Copyright (c) Presidio Contributors.

"""UK-specific recognizers package."""

from .uk_driving_licence_recognizer import UkDrivingLicenceRecognizer
from .uk_nhs_recognizer import NhsRecognizer
from .uk_nino_recognizer import UkNinoRecognizer
from .uk_passport_recognizer import UkPassportRecognizer
from .uk_postcode_recognizer import UkPostcodeRecognizer
from .uk_vehicle_registration_recognizer import UkVehicleRegistrationRecognizer

__all__ = [
    "NhsRecognizer",
    "UkDrivingLicenceRecognizer",
    "UkNinoRecognizer",
    "UkPassportRecognizer",
    "UkPostcodeRecognizer",
    "UkVehicleRegistrationRecognizer",
]
