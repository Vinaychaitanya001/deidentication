# Vendored, unmodified, from microsoft/presidio (MIT License).
# Source: https://github.com/microsoft/presidio/blob/main/presidio-analyzer/presidio_analyzer/predefined_recognizers/country_specific/finland/__init__.py
# Copyright (c) Presidio Contributors.

"""Finland-specific recognizers."""

from .fi_personal_identity_code_recognizer import FiPersonalIdentityCodeRecognizer

__all__ = [
    "FiPersonalIdentityCodeRecognizer",
]
