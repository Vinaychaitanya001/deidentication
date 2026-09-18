# Vendored, unmodified, from microsoft/presidio (MIT License).
# Source: https://github.com/microsoft/presidio/blob/main/presidio-anonymizer/presidio_anonymizer/core/__init__.py
# Copyright (c) Presidio Contributors.

"""The core text functionality."""

from .engine_base import EngineBase
from .text_replace_builder import TextReplaceBuilder

__all__ = ["EngineBase", "TextReplaceBuilder"]
