"""L1 clinical structure — Phase-1 subset: "key: value" fields used by the field-key detector (P1.5).

The sectionizer and fields exposed as fusion features are P2.3 (DECISIONS Q3) and not implemented.
"""

import re
from typing import List, Optional, Tuple

from deid import langpack_en as lp
from deid.contracts import KeyValueField

_KEY_KIND = {key: kind for kind, keys in lp.FIELD_KEYS.items() for key in keys}
_KEY_RE = re.compile(
    r"(?<![A-Za-z0-9])(?P<key>"
    + "|".join(re.escape(k).replace(r"\ ", r"[ \t]+") for k in sorted(_KEY_KIND, key=len, reverse=True))
    + r")(?![A-Za-z])(?P<suffix>[ \t]*(?:#|no\.?|num(?:ber)?|id)(?![A-Za-z]))?[ \t]*(?P<sep>[:#=])?[ \t]*",
    re.IGNORECASE,
)

NAME_TOKEN = r"[A-Z][A-Za-z]*(?:['’\-][A-Z][A-Za-z]+)?"
_TITLE = r"(?:(?:" + "|".join(lp.PERSON_TITLES) + r")\.?[ \t]+)?"
NAME_PATTERN = (r"(?:" + NAME_TOKEN + r",[ \t]+" + NAME_TOKEN + r"(?:[ \t]+[A-Z]\.)?"
                r"|(?:[A-Z]\.[ \t]+)?" + NAME_TOKEN + r"(?:[ \t]+[A-Z]\.)?(?:[ \t]+" + NAME_TOKEN + r"){0,2})")
_NAME_VALUE_RE = re.compile(_TITLE + r"(?P<name>" + NAME_PATTERN + r")")
_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z'’.\-]*")
_ID_VALUE_RE = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?")
_DATE_VALUE_RE = re.compile(
    r"\d{1,4}[/-]\d{1,2}[/-]\d{1,4}|\d{1,2}-[A-Za-z]{3}-\d{2,4}"
    r"|[A-Z][a-z]{2,8}\.?[ \t]+\d{1,2},?[ \t]+\d{4}|\d{1,2}[ \t]+[A-Z][a-z]{2,8}[ \t]+\d{4}")


def clean_name(text: str, start: int, end: int) -> Optional[Tuple[int, int, int]]:
    """Cut a matched name at the first stopword; return (start, end, n_tokens) or None."""
    kept = []
    for m in _TOKEN_RE.finditer(text, start, end):
        if m.group().rstrip(",.") in lp.NAME_STOPWORDS:
            break
        kept.append(m)
    if not kept:
        return None
    s, e = kept[0].start(), kept[-1].end()
    while e > s and text[e - 1] in ",":
        e -= 1
    if sum(ch.isalpha() for ch in text[s:e]) < 2:
        return None
    return s, e, len(kept)


def _value_span(text: str, kind: str, pos: int, has_separator: bool) -> Optional[Tuple[int, int]]:
    if kind.startswith("ID."):
        m = _ID_VALUE_RE.match(text, pos)
        if not m or len(m.group()) < 4 or sum(ch.isdigit() for ch in m.group()) < 3:
            return None
        return m.span()
    if kind.startswith("NAME"):
        m = _NAME_VALUE_RE.match(text, pos)
        if not m:
            return None
        cleaned = clean_name(text, *m.span("name"))
        if not cleaned or (not has_separator and cleaned[2] < 2):
            return None
        return cleaned[0], cleaned[1]
    if kind == "DATE.BIRTH":
        m = _DATE_VALUE_RE.match(text, pos)
        return m.span() if m else None
    return None


def find_fields(text: str) -> List[KeyValueField]:
    fields = []
    for m in _KEY_RE.finditer(text):
        key = " ".join(m.group("key").lower().split())
        has_separator = bool(m.group("sep") or m.group("suffix"))
        if not has_separator and key not in lp.FIELD_KEYS_WITHOUT_SEPARATOR:
            continue
        kind = _KEY_KIND[key]
        span = _value_span(text, kind, m.end(), has_separator)
        if span:
            fields.append(KeyValueField(key, kind, m.start("key"), m.end("key"), span[0], span[1]))
    return fields
