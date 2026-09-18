# Vendored, unmodified, from microsoft/presidio (MIT License).
# Source: https://github.com/microsoft/presidio/blob/main/presidio-anonymizer/presidio_anonymizer/entities/engine/__init__.py
# Copyright (c) Presidio Contributors.

"""Engine request entities."""

from .operator_config import OperatorConfig
from .pii_entity import PIIEntity
from .recognizer_result import RecognizerResult

__all__ = ["PIIEntity", "OperatorConfig", "RecognizerResult"]
