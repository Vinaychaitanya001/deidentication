"""L6 transformation — Phase 1: HIPAA Safe Harbor profile (P1.7).

    names, IDs, contacts, places, organisations   HMAC-SHA256 pseudonym "[LABEL-xxxxxx]" (same value → same code)
    dates                                         shifted back 1-365 days, one offset per document (DECISIONS Q1)
    birth dates of patients aged 90+              removed: "[DOB 90+]" (plan §4.6)
    ages ≥ 90                                     "90+"; younger ages kept
    ZIP codes                                     first three digits kept ("021**"); restricted ZIP3 → "000**"
    states                                        kept

The key comes from the DEID_HMAC_KEY environment variable (key vault in later phases). Without it a
fixed demo key is used and the manifest says so; never use the demo key on real data.
Surrogates that look like real values are P2.8.
"""

import calendar
import datetime as dt
import hashlib
import hmac
import os
import re
from typing import Dict, List, Optional, Tuple

from deid import langpack_en as lp
from deid.contracts import DetectionResult, FinalSpan
from deid.ontology import category

DEMO_KEY = b"phase1-demo-key-not-for-real-data"

# ZIP3 areas with 20,000 or fewer residents (HHS de-identification guidance, 2000 Census); replaced by 000.
RESTRICTED_ZIP3 = frozenset({"036", "059", "063", "102", "203", "556", "692", "790", "821", "823", "830", "831",
                             "878", "879", "884", "890", "893"})

_STATES = {s.lower() for s in lp.US_STATE_CODES + lp.US_STATE_NAMES}
_MONTHS = {m.lower(): i for i, m in enumerate(calendar.month_name) if m}
_MONTHS.update({m.lower(): i for i, m in enumerate(calendar.month_abbr) if m})
_MONTHS["sept"] = 9


def _month(name: str) -> Optional[int]:
    return _MONTHS.get(name.lower().rstrip("."))


def _year(text: str) -> int:
    y = int(text)
    if len(text) == 2:  # two-digit years: 00-30 → 2000s, else 1900s
        y += 2000 if y <= 30 else 1900
    return y


def _build(y: int, m: int, d: int) -> Optional[dt.date]:
    try:
        return dt.date(y, m, d)
    except ValueError:
        return None


def _padded(*fields: str) -> bool:
    """Zero-padded style ("03/14") when a numeric field has a leading zero or all fields have two digits."""
    return any(f.startswith("0") for f in fields) or all(len(f) == 2 for f in fields)


def _num(n: int, pad: bool) -> str:
    return f"{n:02d}" if pad else str(n)


def _yy(d: dt.date, year_field: str) -> str:
    return str(d.year) if len(year_field) == 4 else d.strftime("%y")


def _month_name(d: dt.date, original: str) -> str:
    name = original.rstrip(".")
    full = len(name) > 3 and name.lower() != "sept"
    return (calendar.month_name if full else calendar.month_abbr)[d.month]


# (regex, parse(match) -> date, render(date, match) -> str). The rendering keeps the original style.
_DATE_FORMATS = [
    (re.compile(r"(\d{4})-(\d{1,2})-(\d{1,2})"),
     lambda m: _build(int(m[1]), int(m[2]), int(m[3])),
     lambda d, m: f"{d.year:04d}-{_num(d.month, _padded(m[2], m[3]))}-{_num(d.day, _padded(m[2], m[3]))}"),
    (re.compile(r"(\d{1,2})([/-])(\d{1,2})\2(\d{4}|\d{2})"),
     lambda m: _build(_year(m[4]), int(m[1]), int(m[3])),
     lambda d, m: f"{_num(d.month, _padded(m[1], m[3]))}{m[2]}{_num(d.day, _padded(m[1], m[3]))}{m[2]}{_yy(d, m[4])}"),
    (re.compile(r"(\d{1,2})-([A-Za-z]{3})-(\d{4}|\d{2})"),
     lambda m: _build(_year(m[3]), _month(m[2]) or 0, int(m[1])),
     lambda d, m: f"{_num(d.day, _padded(m[1]))}-{calendar.month_abbr[d.month]}-{_yy(d, m[3])}"),
    (re.compile(r"([A-Za-z]{3,9})(\.?)[ \t]+(\d{1,2})(?:st|nd|rd|th)?(,?)[ \t]+(\d{4})"),
     lambda m: _build(int(m[5]), _month(m[1]) or 0, int(m[3])),
     lambda d, m: f"{_month_name(d, m[1])}{m[2]} {d.day}{m[4]} {d.year}"),
    (re.compile(r"(\d{1,2})[ \t]+([A-Za-z]{3,9})\.?,?[ \t]+(\d{4})"),
     lambda m: _build(int(m[3]), _month(m[2]) or 0, int(m[1])),
     lambda d, m: f"{d.day} {_month_name(d, m[2])} {d.year}"),
    (re.compile(r"([A-Za-z]{3,9})\.?[ \t]+(\d{4})"),
     lambda m: _build(int(m[2]), _month(m[1]) or 0, 15),
     lambda d, m: f"{_month_name(d, m[1])} {d.year}"),
    (re.compile(r"(\d{1,2})/(\d{4})"),
     lambda m: _build(int(m[2]), int(m[1]), 15),
     lambda d, m: f"{_num(d.month, _padded(m[1]))}/{d.year}"),
    (re.compile(r"(\d{1,2})/(\d{1,2})"),  # month/day without a year (leap year so 2/29 parses)
     lambda m: _build(2000, int(m[1]), int(m[2])),
     lambda d, m: f"{_num(d.month, _padded(m[1], m[2]))}/{_num(d.day, _padded(m[1], m[2]))}"),
]


def shift_date(value: str, days: int) -> Optional[str]:
    """The date moved back `days` days in its original format, or None if it cannot be parsed."""
    for rx, parse, render in _DATE_FORMATS:
        m = rx.fullmatch(value.strip())
        if m:
            parsed = parse(m)
            return render(parsed - dt.timedelta(days=days), m) if parsed else None
    return None


def parse_year(value: str) -> Optional[int]:
    for rx, parse, _ in _DATE_FORMATS:
        m = rx.fullmatch(value.strip())
        if m:
            parsed = parse(m)
            return parsed.year if parsed and rx.pattern != r"(\d{1,2})/(\d{1,2})" else None
    return None


def _normalize(type_code: str, value: str) -> str:
    """Pseudonym key: the same entity gets the same code ("OKAFOR, LAKSHMI" = "Lakshmi Okafor"; "123-45" = "12345")."""
    tokens = re.findall(r"[^\W_]+", value.casefold())
    if category(type_code) == "NAME":
        tokens = sorted(tokens)
        return " ".join(tokens)
    return "".join(tokens)


def _label(type_code: str) -> str:
    return type_code.split(".")[-1]


class SafeHarborTransformer:
    profile = "hipaa_safe_harbor"

    def __init__(self, key: Optional[bytes] = None):
        env_key = os.environ.get("DEID_HMAC_KEY")
        self.key = key or (env_key.encode() if env_key else DEMO_KEY)
        self.demo_key = self.key == DEMO_KEY

    def _hmac(self, message: str) -> str:
        return hmac.new(self.key, message.encode("utf-8"), hashlib.sha256).hexdigest()

    def pseudonym(self, type_code: str, value: str) -> str:
        return f"[{_label(type_code)}-{self._hmac(category(type_code) + '|' + _normalize(type_code, value))[:6]}]"

    def date_shift_days(self, doc_id: str) -> int:
        return 1 + int(self._hmac("date-shift|" + doc_id)[:8], 16) % 365

    @staticmethod
    def _is_birth_date(span: FinalSpan, detection: DetectionResult) -> bool:
        """A date read from a DOB field (field-key evidence, or overlapping an L1 DATE.BIRTH field value)."""
        return ("field_kind", "DATE.BIRTH") in span.evidence or any(
            f.kind == "DATE.BIRTH" and f.value_start < span.end and span.start < f.value_end
            for f in detection.document.fields)

    def _patient_is_90_plus(self, detection: DetectionResult) -> bool:
        """True when any detected age is ≥ 90 (a relative's age also counts: the safe direction), or a
        birth date lies ≥ 90 years before another date in the note."""
        text = detection.document.text
        for s in detection.final_spans:
            age = re.match(r"\d+", text[s.start:s.end]) if s.type == "AGE" else None
            if age and int(age.group()) >= 90:
                return True
        birth, other = [], []
        for s in detection.final_spans:
            if category(s.type) == "DATE":
                year = parse_year(text[s.start:s.end])
                if year:
                    (birth if self._is_birth_date(s, detection) else other).append(year)
        return bool(birth and other and max(other) - min(birth) >= 90)

    def _transform(self, span: FinalSpan, value: str, shift: int, dob_90_plus: bool, is_birth_date: bool
                   ) -> Tuple[str, str]:
        cat = category(span.type)
        if cat == "DATE":
            if is_birth_date and dob_90_plus:
                return "[DOB 90+]", "remove_birth_date_90_plus"
            if re.fullmatch(r"(?:19|20)\d{2}", value.strip()):
                return value, "keep_year"
            shifted = shift_date(value, shift)
            return (shifted, "date_shift") if shifted else ("[DATE]", "tag_unparsed_date")
        if cat == "AGE":
            age = re.match(r"\d+", value)
            if age and int(age.group()) >= 90:
                return "90+" + value[age.end():], "age_90_plus"
            return value, "keep_age_under_90"
        if span.type == "LOCATION.ZIP" or (cat == "LOCATION" and re.fullmatch(r"\d{5}(?:-\d{4})?", value)):
            zip3 = value[:3]
            return ("000**" if zip3 in RESTRICTED_ZIP3 else zip3 + "**"), "zip3"
        if cat == "LOCATION" and value.strip().lower().rstrip(".") in _STATES:
            return value, "keep_state"
        return self.pseudonym(span.type, value), "hmac_pseudonym"

    def apply(self, detection: DetectionResult) -> Tuple[str, List[Dict]]:
        """The transformed text and one action record per final span (no original values)."""
        text = detection.document.text
        shift = self.date_shift_days(detection.document.doc_id)
        dob_90_plus = self._patient_is_90_plus(detection)
        out, actions, pos = [], [], 0
        for span in sorted(detection.final_spans, key=lambda s: s.start):
            replacement, action = self._transform(span, text[span.start:span.end], shift, dob_90_plus,
                                                  self._is_birth_date(span, detection))
            out.append(text[pos:span.start])
            new_start = sum(len(p) for p in out)
            out.append(replacement)
            actions.append({"span": span, "action": action, "replacement": replacement,
                            "output_start": new_start, "output_end": new_start + len(replacement)})
            pos = span.end
        out.append(text[pos:])
        return "".join(out), actions
