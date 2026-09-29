"""L4 rule-based decider (D12), L5 overlap resolver (D14) and candidate trimming (D15)."""

import pytest

from deid.consistency import OverlapResolver, priority
from deid.contracts import Candidate, Document
from deid.decision import RuleBasedDecider
from deid.spans import trim


def cand(text, value, entity, type_hint, source, score=0.9, nth=0, evidence=()):
    start = -1
    for _ in range(nth + 1):
        start = text.index(value, start + 1)
    return Candidate(start, start + len(value), type_hint, entity, source, score, evidence)


def decide(text, candidates, use_vetoes=True):
    return {text[d.candidate.start:d.candidate.end] + "|" + d.candidate.source: d.reason
            for d in RuleBasedDecider().decide(Document("t", text), candidates, use_vetoes)}


# --- L4 -----------------------------------------------------------------------------------------
def test_weak_driver_licence_and_bank_patterns_are_gated():
    text = "Specimen 12345678 received; licence 87654321."
    reasons = decide(text, [
        cand(text, "12345678", "US_DRIVER_LICENSE", "ID.LICENSE", "UsLicenseRecognizer", 0.01),
        cand(text, "12345678", "US_BANK_NUMBER", "ID.ACCOUNT", "UsBankRecognizer", 0.05),
        cand(text, "87654321", "US_DRIVER_LICENSE", "ID.LICENSE", "UsLicenseRecognizer", 0.4),  # context-boosted
    ])
    assert reasons["12345678|UsLicenseRecognizer"] == "below_min_score:0.4"
    assert reasons["12345678|UsBankRecognizer"] == "below_min_score:0.4"
    assert reasons["87654321|UsLicenseRecognizer"] == "accepted"


def test_other_entities_keep_presidios_default_threshold():
    text = "Seen on 3/4/2024"
    assert decide(text, [cand(text, "3/4/2024", "DATE_TIME", "DATE", "DateRecognizer", 0.05)]) == \
        {"3/4/2024|DateRecognizer": "accepted"}


def test_nrp_is_not_phi():
    text = "She is Catholic."
    assert decide(text, [cand(text, "Catholic", "NRP", None, "SpacyRecognizer")]) == {"Catholic|SpacyRecognizer": "not_phi"}


def test_look_alike_is_vetoed_unless_vetoes_are_off():
    text = "Vitals: BP 120/80, HR 72"
    c = [cand(text, "120/80", "DATE_TIME", "DATE", "TransformersRecognizer")]
    assert decide(text, c) == {"120/80|TransformersRecognizer": "veto:blood_pressure"}
    assert decide(text, c, use_vetoes=False) == {"120/80|TransformersRecognizer": "accepted"}


def test_field_key_values_are_never_vetoed():
    text = "Case: 1/2 tab"  # contrived: a field value inside a fraction-of-dose region
    c = [Candidate(6, 9, "ID.OTHER", "OTHER_ID_NUMBER", "FieldKeyDetector", 0.95)]
    assert RuleBasedDecider().decide(Document("t", text), c)[0].accepted


# --- L5 -----------------------------------------------------------------------------------------
def resolve(text, candidates):
    return [(text[s.start:s.end], s.type, s.sources) for s in OverlapResolver().resolve(Document("t", text), candidates)]


def test_priority_order():
    text = "x"
    fk = Candidate(0, 1, "ID.MRN", "MEDICAL_RECORD_NUMBER", "FieldKeyDetector", 0.95)
    pack = Candidate(0, 1, "AGE", "AGE", "AgeDetector", 0.9)
    ner = Candidate(0, 1, "ID", "ID", "TransformersRecognizer", 1.0)
    assert priority(fk) > priority(pack) > priority(ner)


def test_field_key_boundaries_and_type_win_over_ner():
    text = "Patient: OKAFOR, LAKSHMI        MRN: 2305053"
    out = resolve(text, [
        cand(text, "OKAFOR,", "NAME_CLINICIAN", "NAME.CLINICIAN", "TransformersRecognizer", 1.0),
        cand(text, "OKAFOR, LAKSHMI", "NAME_PATIENT", "NAME.PATIENT", "FieldKeyDetector", 0.95),
    ])
    assert out == [("OKAFOR, LAKSHMI", "NAME.PATIENT", ("FieldKeyDetector", "TransformersRecognizer"))]


def test_loser_keeps_only_uncovered_characters():
    text = "admitted to Riverside Medical Center\n2045 Oak Street"
    out = resolve(text, [
        cand(text, "Riverside Medical Center\n2045", "HOSPITAL", "LOCATION.HOSPITAL", "TransformersRecognizer", 0.99),
        cand(text, "Riverside Medical Center", "HOSPITAL", "LOCATION.HOSPITAL", "HospitalDetector", 0.85),
    ])
    assert out == [("Riverside Medical Center", "LOCATION.HOSPITAL", ("HospitalDetector", "TransformersRecognizer")),
                   ("2045", "LOCATION.HOSPITAL", ("TransformersRecognizer",))]


def test_fragments_without_letters_or_digits_are_dropped():
    text = "Call Dr. Rao, today"
    out = resolve(text, [cand(text, "Rao,", "NAME_CLINICIAN", "NAME.CLINICIAN", "TransformersRecognizer"),
                         cand(text, "Rao", "NAME_CLINICIAN", "NAME.CLINICIAN", "ClinicianCueDetector")])
    assert out == [("Rao", "NAME.CLINICIAN", ("ClinicianCueDetector", "TransformersRecognizer"))]


def test_ties_prefer_the_longer_span():
    text = "on July 31, 2024 at noon"
    out = resolve(text, [cand(text, "July 31", "DATE_TIME", "DATE", "DateRecognizer", 0.6),
                         cand(text, "July 31, 2024", "DATE_TIME", "DATE", "TransformersRecognizer", 0.5)])
    assert out[0][0] == "July 31, 2024"


def test_non_overlapping_spans_are_all_kept_in_order():
    text = "Dr. Rao saw Mei Nguyen on 2/5/24"
    out = resolve(text, [cand(text, "2/5/24", "DATE_TIME", "DATE", "DateRecognizer"),
                         cand(text, "Rao", "NAME_CLINICIAN", "NAME.CLINICIAN", "ClinicianCueDetector"),
                         cand(text, "Mei Nguyen", "NAME_PATIENT", "NAME.PATIENT", "TransformersRecognizer")])
    assert [o[0] for o in out] == ["Rao", "Mei Nguyen", "2/5/24"]


# --- D15 trimming ---------------------------------------------------------------------------------
@pytest.mark.parametrize("raw,expected", [
    ("Venkata Rao,", "Venkata Rao"),
    ("55916\n", "55916"),
    ("2/1/24.", "2/1/24"),
    ("(617) 555-0142", "(617) 555-0142"),
    ("(617) 555-0142)", "(617) 555-0142"),
    (" 'Okafor' ", "Okafor"),
    ("St.", "St."),
    ("John A.", "John A."),
    ("Dr.", "Dr."),
    ("Mayo Clinic;", "Mayo Clinic"),
])
def test_trim(raw, expected):
    s, e = trim(raw, 0, len(raw))
    assert raw[s:e] == expected
