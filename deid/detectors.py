"""L3 clinical detector pack (P1.5), as Presidio recognizers.

Each detector reports only the value (named group "v"); cue words such as "MRN:" or "Dr." stay
outside the span. Detectors only propose — the L4 decider and L5 resolver decide.
"""

import re
from typing import Dict, List, Optional, Sequence, Tuple

from presidio_analyzer import AnalysisExplanation, EntityRecognizer, LocalRecognizer, RecognizerResult

from deid import langpack_en as lp
from deid.structure import NAME_PATTERN, clean_name, find_fields


def _alt(words: Sequence[str]) -> str:
    return "|".join(re.escape(w) for w in sorted(words, key=len, reverse=True))


def _result(recognizer: EntityRecognizer, entity: str, start: int, end: int, score: float, pattern: str,
            extra: Dict) -> RecognizerResult:
    explanation = AnalysisExplanation(recognizer=recognizer.name, original_score=score, pattern_name=pattern,
                                      textual_explanation=f"{recognizer.name}: {pattern}")
    metadata = {RecognizerResult.RECOGNIZER_NAME_KEY: recognizer.name,
                RecognizerResult.RECOGNIZER_IDENTIFIER_KEY: recognizer.id, **extra}
    return RecognizerResult(entity, start, end, score, analysis_explanation=explanation,
                            recognition_metadata=metadata)


class _PatternDetector(LocalRecognizer):
    """Runs (name, regex, score, entity, flags) patterns and emits each match's group "v"."""

    PATTERNS: Sequence[Tuple[str, str, float, str, int]] = ()

    def __init__(self):
        super().__init__(supported_entities=sorted({p[3] for p in self.PATTERNS}), name=type(self).__name__,
                         supported_language="en")

    def load(self) -> None:
        self._compiled = [(name, re.compile(rx, flags), score, entity)
                          for name, rx, score, entity, flags in self.PATTERNS]

    def refine(self, text: str, start: int, end: int) -> Optional[Tuple[int, int, Dict]]:
        return start, end, {}

    def analyze(self, text, entities, nlp_artifacts=None) -> List[RecognizerResult]:
        out = []
        for name, rx, score, entity in self._compiled:
            if entities and entity not in entities:
                continue
            for m in rx.finditer(text):
                refined = self.refine(text, *m.span("v"))
                if refined:
                    out.append(_result(self, entity, refined[0], refined[1], score, name, refined[2]))
        return out


class AgeDetector(_PatternDetector):
    """Ages written with an age cue; flags ages over 89 for the L6 90+ rule."""

    PATTERNS = (
        ("n-year-old", r"(?<![\d/.:-])(?P<v>\d{1,3})[ \t]*-?[ \t]*(?:years?|yrs?|y)[ \t]*-?[ \t]*old\b", 0.9, "AGE", re.I),
        ("n y/o", r"(?<![\d/.:-])(?P<v>\d{1,3})[ \t]*(?:y/o|y\.o\.?|yo|yr old)(?![A-Za-z])", 0.9, "AGE", re.I),
        ("age n", r"\b(?:age|aged)[ \t]*[:=]?[ \t]*(?P<v>\d{1,3})\b", 0.85, "AGE", re.I),
        ("n years of age", r"\b(?P<v>\d{1,3})[ \t]+years?[ \t]+of[ \t]+age\b", 0.9, "AGE", re.I),
        ("nnM/F", r"(?<![\w/.:-])(?P<v>\d{2,3})(?:M|F)\b(?![ \t]*(?:" + _alt(lp.FRENCH_SIZE_NOUNS) + r")\b)", 0.8, "AGE",
         0),
    )

    def refine(self, text, start, end):
        age = int(text[start:end])
        if not 0 < age <= 125:
            return None
        return start, end, {"age_value": age, "over_89": age >= 90}


class UsZipDetector(_PatternDetector):
    """US ZIP codes after a state name/abbreviation or a ZIP label."""

    PATTERNS = (
        ("state code + zip", r"\b(?:" + _alt(lp.US_STATE_CODES) + r")\.?,?[ \t]+(?P<v>\d{5}(?:-\d{4})?)\b", 0.9,
         "US_ZIP_CODE", 0),
        ("state name + zip", r"\b(?:" + _alt(lp.US_STATE_NAMES) + r"),?[ \t]+(?P<v>\d{5}(?:-\d{4})?)\b", 0.9,
         "US_ZIP_CODE", 0),
        ("zip label", r"\bzip(?:[ \t]*code)?[ \t]*[:#]?[ \t]*(?P<v>\d{5}(?:-\d{4})?)\b", 0.9, "US_ZIP_CODE", re.I),
    )


class FaxPagerDetector(_PatternDetector):
    """Fax numbers and pagers, identified by their cue word."""

    PHONE = r"(?:\+?1[ \t.-]?)?(?:\(\d{3}\)|\d{3})[ \t.-]?\d{3}[ \t.-]?\d{4}"
    PATTERNS = (
        ("fax", r"\b(?:fax|facsimile)\b(?:[ \t]*(?:#|no\.?|number))?[ \t]*[:#]?[ \t]*"
                r"(?:(?:results|records|report|it)[ \t]+)?(?:to[ \t]+)?(?P<v>" + PHONE + r")\b", 0.9, "FAX_NUMBER", re.I),
        ("pager", r"\b(?:pager|pgr|beeper)\b(?:[ \t]*(?:#|no\.?|number))?[ \t]*[:#]?[ \t]*(?P<v>\d(?:[ \t-]?\d){3,9})\b",
         0.85, "PAGER_NUMBER", re.I),
    )


class ClinicianCueDetector(_PatternDetector):
    """Clinician names after "Dr." or before a credential ("Maria Lopez, MD")."""

    PATTERNS = (
        ("title + name", r"\b(?:" + _alt(lp.CLINICIAN_TITLES) + r")\.?[ \t]+(?P<v>" + NAME_PATTERN + r")", 0.85,
         "NAME_CLINICIAN", 0),
        ("name + credential", r"(?P<v>" + NAME_PATTERN + r"),?[ \t]+(?:" + _alt(lp.CREDENTIALS) + r")(?![A-Za-z:])",
         0.85, "NAME_CLINICIAN", 0),
    )

    def refine(self, text, start, end):
        cleaned = clean_name(text, start, end)
        return (cleaned[0], cleaned[1], {}) if cleaned else None


class HospitalDetector(_PatternDetector):
    """Facility names by suffix pattern ("<Name> Medical Center") plus a gazetteer of real hospitals.

    Name words are joined by single spaces: runs of spaces or tabs separate columns in note headers
    ("Pathologist: Priya Shah, MD   Holloway Memorial Hospital").
    """

    TOKEN = r"[A-Z][A-Za-z'’.\-]+"
    PATTERNS = (
        ("facility suffix",
         r"(?P<v>(?:(?:St|Mt)\. |(?:Saint|Mount) )?(?:" + TOKEN + r" ){0,4}(?:"
         + _alt(lp.HOSPITAL_SUFFIXES) + r")(?: of " + TOKEN + r"(?: " + TOKEN + r")?)?)(?![A-Za-z])",
         0.85, "HOSPITAL", 0),
        ("gazetteer", r"\b(?P<v>" + _alt(lp.HOSPITAL_GAZETTEER) + r")(?![A-Za-z])", 0.95, "HOSPITAL", 0),
    )
    _SUFFIX_RE = re.compile(r"(?:" + _alt(lp.HOSPITAL_SUFFIXES) + r")(?:[ \t]+of[ \t].*)?$")

    _GAZETTEER = frozenset(lp.HOSPITAL_GAZETTEER)

    def refine(self, text, start, end):
        if text[start:end] in self._GAZETTEER:
            return start, end, {}
        while True:  # drop leading words such as "The", "Transferred" or a credential ("MD")
            m = re.match(r"([A-Za-z'’.\-]+)[ \t]+", text[start:end])
            if not m or m.group(1) not in lp.HOSPITAL_LEADING_STOPWORDS and m.group(1) not in lp.CREDENTIALS:
                break
            start += m.end()
        suffix = self._SUFFIX_RE.search(text[start:end])
        if not suffix or suffix.start() == 0:  # a bare "Clinic" or "Hospital" is not a name
            return None
        return start, end, {}


class FieldKeyDetector(LocalRecognizer):
    """Values of L1 key:value fields (MRN, account, accession, member ID, name fields, DOB ...)."""

    KIND_TO_ENTITY = {
        "ID.MRN": "MEDICAL_RECORD_NUMBER", "ID.ACCOUNT": "ACCOUNT_NUMBER", "ID.OTHER": "OTHER_ID_NUMBER",
        "ID.HEALTHPLAN": "HEALTH_PLAN_ID", "ID.DEVICE": "DEVICE_ID", "ID.LICENSE": "LICENSE_NUMBER",
        "ID.SSN": "US_SSN", "NAME.PATIENT": "NAME_PATIENT", "NAME.CLINICIAN": "NAME_CLINICIAN",
        "NAME.OTHER": "NAME_OTHER", "DATE.BIRTH": "DATE_TIME",
    }

    def __init__(self):
        super().__init__(supported_entities=sorted(set(self.KIND_TO_ENTITY.values())), name="FieldKeyDetector",
                         supported_language="en")

    def load(self) -> None:
        pass

    def analyze(self, text, entities, nlp_artifacts=None) -> List[RecognizerResult]:
        out = []
        for f in find_fields(text):
            entity = self.KIND_TO_ENTITY[f.kind]
            if entities and entity not in entities:
                continue
            extra = {"field_key": f.key, "field_kind": f.kind}
            out.append(_result(self, entity, f.value_start, f.value_end, 0.95, f"field '{f.key}'", extra))
        return out


def clinical_detector_pack() -> List[EntityRecognizer]:
    return [FieldKeyDetector(), AgeDetector(), UsZipDetector(), FaxPagerDetector(), ClinicianCueDetector(),
            HospitalDetector()]
