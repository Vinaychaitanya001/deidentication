"""P1.6 hard-negative rules: clinical numbers that look like PHI but are not.

Each rule marks a region (the value plus its cue, e.g. "BP 132/84"). The L4 decider rejects a
candidate of a vetoable type that lies entirely inside one region; field-key candidates are never
vetoed. Measurement (vitals/labs), code and eponym look-alikes are not handled in Phase 1
(DECISIONS Q4, Q9); they are reported by the evaluation instead.
"""

import re
from dataclasses import dataclass
from typing import Callable, List, Optional, Sequence, Tuple

from deid import langpack_en as lp
from deid.ontology import category


@dataclass(frozen=True)
class HardNegative:
    start: int
    end: int
    kind: str


# Types a region may veto (canonical codes or categories). Durations and frequencies never veto AGE,
# so an age such as "85 years" survives even if a duration pattern also covers it.
_NUMERIC = frozenset({"DATE", "AGE", "ID", "CONTACT", "LOCATION.ZIP", "OTHER"})
VETOABLE = {
    "blood_pressure": _NUMERIC,
    "scale": _NUMERIC,
    "fraction_dose": _NUMERIC,
    "dose": _NUMERIC,
    "duration": _NUMERIC - {"AGE"},
    "frequency": _NUMERIC - {"AGE"},
}


def _alt(words: Sequence[str]) -> str:
    return "|".join(re.escape(w) for w in sorted(words, key=len, reverse=True))


def _proper_fraction(m: re.Match) -> bool:
    num, den = (int(g) for g in re.findall(r"\d+", m.group("v"))[:2])
    return num < den


def _scale_ok(m: re.Match) -> bool:
    """x/y reads as a clinical scale only when x <= y <= 10 (4/5 strength, 9/10 pain, 2+/4 reflexes)."""
    num, den = (int(g) for g in re.findall(r"\d+", m.group("v"))[:2])
    return num <= den <= 10


_NUM = r"\d+(?:\.\d+)?"
_RANGE = _NUM + r"(?:[ \t]*(?:-|–|to)[ \t]*" + _NUM + r")?"
_TIME_UNIT = r"(?:" + _alt(lp.TIME_UNITS) + r")(?![A-Za-z])"
_LONG_TIME_UNIT = r"(?:minutes?|mins?|hours?|hrs?|days?|weeks?|wks?|months?|mos?|years?|yrs?)(?![A-Za-z])"
_NOT_AGE = r"(?![ \t]*-?[ \t]*old)(?![ \t]+of[ \t]+age)"
_SCALE_VALUE = r"(?<![\d/])\d{1,2}\+?[ \t]*/[ \t]*\d{1,2}(?![\d/])"
_CONNECTORS = r"(?:[ \t]*[:=,]?[ \t]*(?:is|was|of|at|now|remains|score|scored|scale|rated|graded|level)\b)*[ \t]*[:=]?[ \t]*"
_SNELLEN = r"20[ \t]*/[ \t]*(?:10|12|15|16|20|25|30|32|40|50|60|63|70|80|100|125|160|200|400|800)(?![\d/])"

_RULES: List[Tuple[str, "re.Pattern[str]", Optional[Callable[[re.Match], bool]]]] = [(kind, re.compile(rx, flags), check)
    for kind, rx, flags, check in (
        # blood pressure: a BP cue, or an mmHg unit
        ("blood_pressure", r"\b(?:" + _alt(lp.BP_CUES) + r")(?![A-Za-z])[^\d\n]{0,20}?\d{2,3}[ \t]*/[ \t]*\d{2,3}"
                           r"(?![\d/])(?:[ \t]*mm[ \t]*Hg)?", re.I, None),
        ("blood_pressure", r"(?<![\d/])\d{2,3}[ \t]*/[ \t]*\d{2,3}(?![\d/])[ \t]*mm[ \t]*Hg\b", re.I, None),
        # scales: a scale cue before or after x/y, visual acuity, named scores (GCS, Apgar ...)
        ("scale", r"\b(?:" + _alt(lp.SCALE_CUES) + r")\b" + _CONNECTORS + r"(?P<v>" + _SCALE_VALUE + r")", re.I,
         _scale_ok),
        ("scale", r"(?P<v>" + _SCALE_VALUE + r")[ \t]+(?:" + _alt(lp.SCALE_TRAILING_CUES) + r")\b", re.I, _scale_ok),
        ("scale", r"\b(?:VA|visual acuity|vision|acuity|Snellen|OD|OS|OU)\b[^\d\n]{0,15}?" + _SNELLEN
                  + r"(?:[ \t]*,?[ \t]*(?:OD|OS|OU)?[ \t]*" + _SNELLEN + r")*", 0, None),
        ("scale", r"\b(?:" + _alt(lp.GCS_CUES + lp.NAMED_SCORES) + r")(?![A-Za-z])" + _CONNECTORS
                  + r"\d{1,2}(?:[ \t]*(?:/|,|and|&)[ \t]*\d{1,2}){0,2}\b", re.I, None),
        # fractions of a dose: "1/2 tab", "1/2 of a tablet", "take 1/2", "2/3 of the", "1/2 NS"
        ("fraction_dose", r"(?<![\d/])(?P<v>[1-9][ \t]*/[ \t]*[2-8])(?![\d/])(?:[ \t]+of[ \t]+(?:a|an|one|the))?[ \t]+"
                          r"(?:" + _alt(lp.FRACTION_DOSE_NOUNS) + r")\b", re.I, _proper_fraction),
        ("fraction_dose", r"\b(?:take|takes|taking|give|given|use)[ \t]+[1-9][ \t]*/[ \t]*[2-8](?![\d/])", re.I, None),
        ("fraction_dose", r"(?<![\d/])(?P<v>[1-9][ \t]*/[ \t]*[2-9])(?![\d/])[ \t]+of[ \t]+(?:the|a|an|his|her|their)\b",
         re.I, _proper_fraction),
        ("fraction_dose", r"(?<![\d/])1[ \t]*/[ \t]*[24][ \t]*(?:NS|normal saline)\b", re.I, None),
        # doses: number (or range / combination) + unit, optionally per kg/day/hr; dispensed quantities
        ("dose", r"(?<![\w.])" + _NUM + r"(?:[ \t]*(?:-|–|to|/)[ \t]*" + _NUM + r")?[ \t]*(?:" + _alt(lp.DOSE_UNITS)
                 + r")(?:[ \t]*/[ \t]*(?:kg|m2|dose|day|d|hr|h|min|mL|L))*(?![A-Za-z])", re.I, None),
        ("dose", r"\b(?:dispense|disp|qty|quantity|refills?)\b[ \t:]*#?[ \t]*\d+", re.I, None),
        # durations: "x3 days", "for 2 weeks", "3-day history", "2 days ago", "POD 2", "12 months"
        ("duration", r"\bx[ \t]*" + _RANGE + r"[ \t]*" + _TIME_UNIT, re.I, None),
        ("duration", r"\b(?:for|over|past|last|in|within|after|next|about|approximately|since|of)[ \t]+(?:the[ \t]+)?"
                     r"(?:past[ \t]+|last[ \t]+|next[ \t]+|previous[ \t]+|additional[ \t]+|another[ \t]+)?"
                     + _RANGE + r"[ \t]*" + _LONG_TIME_UNIT + _NOT_AGE, re.I, None),
        ("duration", r"(?<![\w/.:-])" + _RANGE + r"[ \t]*-?[ \t]*(?:minute|hour|hr|day|week|wk|month|year|yr)s?"
                     r"[ \t]*-?[ \t]*(?:" + _alt(lp.DURATION_NOUNS) + r")\b", re.I, None),
        ("duration", r"(?<![\w/.:-])" + _RANGE + r"[ \t]*" + _LONG_TIME_UNIT + r"[ \t]+(?:" + _alt(lp.RELATIVE_WORDS)
                     + r")\b", re.I, None),
        ("duration", r"\b(?:" + _alt(lp.HOSPITAL_DAY_CUES) + r")(?![A-Za-z])[ \t]*#?[ \t]*\d{1,3}\b", re.I, None),
        ("duration", r"(?<![\w/.:-])" + _RANGE + r"[ \t]*" + _LONG_TIME_UNIT + _NOT_AGE, re.I, None),
        # frequencies: "q6h", "q4-6h", "BID", "every 6 hours", "twice daily", "3x/day"
        ("frequency", r"\bq[ \t.]?\d{1,2}(?:[ \t]*(?:-|to)[ \t]*\d{1,2})?[ \t.]?(?:h|hr|hrs|hours?|min|mins|minutes?|d|days?"
                      r"|wk|wks|weeks?)\b", re.I, None),
        ("frequency", r"(?<![A-Za-z])(?:" + _alt(lp.FREQUENCY_ABBREVIATIONS) + r")(?![A-Za-z])", re.I, None),
        ("frequency", r"\bevery[ \t]+(?:other[ \t]+)?(?:" + _RANGE + r"[ \t]*)?(?:minutes?|mins?|hours?|hrs?|days?|"
                      r"weeks?|months?|morning|evening|night)\b", re.I, None),
        ("frequency", r"\b(?:" + _alt(lp.FREQUENCY_PHRASES) + r")\b", re.I, None),
        ("frequency", r"\b\d+[ \t]*(?:x|times)[ \t]*(?:a|per|/)[ \t]*(?:day|week|month|d|wk)\b", re.I, None),
    )]


def find_hard_negatives(text: str) -> List[HardNegative]:
    """Every hard-negative region in the text (regions of different rules may overlap)."""
    regions = []
    for kind, rx, check in _RULES:
        for m in rx.finditer(text):
            if m.end() > m.start() and (check is None or check(m)):
                regions.append(HardNegative(m.start(), m.end(), kind))
    return sorted(set(regions), key=lambda r: (r.start, -r.end, r.kind))


_KIND_ORDER = {kind: i for i, kind in enumerate(VETOABLE)}  # most specific kind first


def vetoing_region(start: int, end: int, type_code: str, regions: List[HardNegative]) -> Optional[HardNegative]:
    """The region that vetoes a candidate [start, end) of this type, if any (most specific kind wins)."""
    covering = [r for r in regions if r.start <= start and end <= r.end
                and (type_code in VETOABLE[r.kind] or category(type_code) in VETOABLE[r.kind])]
    return min(covering, key=lambda r: _KIND_ORDER[r.kind], default=None)
