# Vendored, unmodified, from microsoft/presidio (MIT License).
# Source: https://github.com/microsoft/presidio/blob/main/presidio-analyzer/presidio_analyzer/recognizer_registry/__init__.py
# Copyright (c) Presidio Contributors.

"""Recognizer Registry."""

from .recognizer_registry import RecognizerRegistry
from .recognizer_registry_provider import RecognizerRegistryProvider

__all__ = ["RecognizerRegistry", "RecognizerRegistryProvider"]
