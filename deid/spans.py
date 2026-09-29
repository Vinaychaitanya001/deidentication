"""Span boundary helpers (DECISIONS D15)."""

import re
from typing import Tuple

_ALWAYS = " \t\r\n,;:\"'|"
_PAIRS = {"(": ")", "[": "]", "{": "}"}
_CLOSERS = {v: k for k, v in _PAIRS.items()}
_ABBREVIATION_END = re.compile(r"(?:\b(?:Dr|Mr|Mrs|Ms|Jr|Sr|St|Mt|Inc|Co|Ltd)|\b[A-Z])\.$")


def trim(text: str, start: int, end: int) -> Tuple[int, int]:
    """Drop surrounding whitespace and separator punctuation.

    Brackets are removed only when unbalanced inside the span ("(617) 555-0142" keeps its
    parenthesis); a final "." is kept when it ends an abbreviation or an initial.
    """
    changed = True
    while changed and start < end:
        changed = False
        first, last, span = text[start], text[end - 1], text[start:end]
        if first in _ALWAYS or (first in _PAIRS and span.count(first) > span.count(_PAIRS[first])):
            start, changed = start + 1, True
        elif last in _ALWAYS or (last in _CLOSERS and span.count(last) > span.count(_CLOSERS[last])):
            end, changed = end - 1, True
        elif last == "." and not _ABBREVIATION_END.search(text[start:end]):
            end, changed = end - 1, True
    return start, end


def has_alnum(text: str, start: int, end: int) -> bool:
    return any(ch.isalnum() for ch in text[start:end])
