# Vendored, unmodified, from microsoft/presidio (MIT License).
# Source: https://github.com/microsoft/presidio/blob/main/presidio-analyzer/presidio_analyzer/predefined_recognizers/country_specific/india/__init__.py
# Copyright (c) Presidio Contributors.

"""India-specific recognizers."""

from .in_aadhaar_recognizer import InAadhaarRecognizer
from .in_gstin_recognizer import InGstinRecognizer
from .in_pan_recognizer import InPanRecognizer
from .in_passport_recognizer import InPassportRecognizer
from .in_vehicle_registration_recognizer import InVehicleRegistrationRecognizer
from .in_voter_recognizer import InVoterRecognizer

__all__ = [
    "InAadhaarRecognizer",
    "InGstinRecognizer",
    "InPanRecognizer",
    "InVoterRecognizer",
    "InVehicleRegistrationRecognizer",
    "InPassportRecognizer",
]
