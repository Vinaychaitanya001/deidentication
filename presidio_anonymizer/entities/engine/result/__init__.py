# Vendored, unmodified, from microsoft/presidio (MIT License).
# Source: https://github.com/microsoft/presidio/blob/main/presidio-anonymizer/presidio_anonymizer/entities/engine/result/__init__.py
# Copyright (c) Presidio Contributors.

"""Engine result items either for anonymize or decrypt."""

from .operator_result import OperatorResult  # isort:skip
from .engine_result import EngineResult

__all__ = [
    "OperatorResult",
    "EngineResult",
]
