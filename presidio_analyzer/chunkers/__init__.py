# Vendored, unmodified, from microsoft/presidio (MIT License).
# Source: https://github.com/microsoft/presidio/blob/main/presidio-analyzer/presidio_analyzer/chunkers/__init__.py
# Copyright (c) Presidio Contributors.

"""Text chunking strategies for handling long texts."""

from presidio_analyzer.chunkers.base_chunker import BaseTextChunker, TextChunk
from presidio_analyzer.chunkers.character_based_text_chunker import (
    CharacterBasedTextChunker,
)
from presidio_analyzer.chunkers.text_chunker_provider import TextChunkerProvider
from presidio_analyzer.chunkers.tokenizer_based_text_chunker import (
    TokenizerBasedTextChunker,
)

__all__ = [
    "BaseTextChunker",
    "TextChunk",
    "CharacterBasedTextChunker",
    "TextChunkerProvider",
    "TokenizerBasedTextChunker",
]
