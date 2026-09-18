# Vendored, unmodified, from microsoft/presidio (MIT License).
# Source: https://github.com/microsoft/presidio/blob/main/presidio-analyzer/presidio_analyzer/predefined_recognizers/country_specific/nigeria/__init__.py
# Copyright (c) Presidio Contributors.

"""Nigeria-specific recognizers."""

from .ng_nin_recognizer import NgNinRecognizer
from .ng_vehicle_registration_recognizer import NgVehicleRegistrationRecognizer

__all__ = [
    "NgNinRecognizer",
    "NgVehicleRegistrationRecognizer",
]
