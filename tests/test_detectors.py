"""P1.5 clinical detector pack: >= 10 positive and >= 10 hard-negative cases per detector.

Positive cases give the exact value the detector must report (cue words stay outside the span);
hard-negative cases are look-alikes on which the detector must report nothing. All values are
synthetic.
"""

import pytest

from deid.detectors import (AgeDetector, ClinicianCueDetector, FaxPagerDetector, FieldKeyDetector, HospitalDetector,
                            UsZipDetector)


def found(detector_cls, text):
    detector = detector_cls()
    detector.load()
    return {(text[r.start:r.end], r.entity_type) for r in detector.analyze(text, None)}


# --- AGE (with the over-89 flag) ------------------------------------------------------------
AGE_POSITIVE = [
    ("Ms. Okafor is a 27-year-old woman", "27"),
    ("72 year old male with chest pain", "72"),
    ("a 95-year-old man with COPD", "95"),
    ("45 y/o F presents with cough", "45"),
    ("63yo male, smoker", "63"),
    ("Age: 58", "58"),
    ("patient aged 81 lives alone", "81"),
    ("34 years of age at diagnosis", "34"),
    ("67M with chest pain", "67"),
    ("82F presents after a fall", "82"),
    ("a 101-yr-old resident", "101"),
    ("5 yo boy with fever", "5"),
]
AGE_NEGATIVE = [
    "BP 120/80, HR 72",
    "20F Foley catheter placed",
    "16F chest tube in place",
    "metoprolol 25 mg PO BID",
    "smoked for 30 years",
    "MRN 4829173",
    "Room 12, bed 2",
    "average 45 mmHg",
    "usage 12 units",
    "Page 2 of 3",
    "the 300-year-old building",
    "stage 2 disease",
]


@pytest.mark.parametrize("text,value", AGE_POSITIVE)
def test_age_positive(text, value):
    assert (value, "AGE") in found(AgeDetector, text)


@pytest.mark.parametrize("text", AGE_NEGATIVE)
def test_age_hard_negative(text):
    assert found(AgeDetector, text) == set()


def test_age_over_89_flag():
    detector = AgeDetector()
    detector.load()
    flags = {r.recognition_metadata["age_value"]: r.recognition_metadata["over_89"]
             for r in detector.analyze("a 95-year-old man and his 89-year-old wife", None)}
    assert flags == {95: True, 89: False}


# --- US ZIP -----------------------------------------------------------------------------------
ZIP_POSITIVE = [
    ("Dayton, OH 45402", "45402"),
    ("Boston, MA 02114-1234", "02114-1234"),
    ("Tulsa, OK 74103", "74103"),
    ("Springfield, Illinois 62701", "62701"),
    ("ZIP: 53703", "53703"),
    ("zip code 85701", "85701"),
    ("Fresno CA 93721", "93721"),
    ("New York, NY 10001", "10001"),
    ("Raleigh, NC 27601", "27601"),
    ("Zip Code: 83702", "83702"),
    ("Madison, Wisconsin 53703", "53703"),
]
ZIP_NEGATIVE = [
    "MRN 45402",
    "WBC 12345 cells",
    "Acct # 93721",
    "BP 120/80",
    "CPT 88305",
    "Call 555-0142",
    "specimen 94107",
    "Order 12345 placed",
    "In 2020 she moved",
    "12345 units of heparin",
    "phone 60612",
]


@pytest.mark.parametrize("text,value", ZIP_POSITIVE)
def test_zip_positive(text, value):
    assert (value, "US_ZIP_CODE") in found(UsZipDetector, text)


@pytest.mark.parametrize("text", ZIP_NEGATIVE)
def test_zip_hard_negative(text):
    assert found(UsZipDetector, text) == set()


# --- field keys: MRN / account / accession / member ID / device / names / DOB -----------------
FIELD_POSITIVE = [
    ("MRN: 2305053", "2305053", "MEDICAL_RECORD_NUMBER"),
    ("Pt Sharma, Ahmed, MRN 7045487, Rm 297", "7045487", "MEDICAL_RECORD_NUMBER"),
    ("Med Rec #: 8981353", "8981353", "MEDICAL_RECORD_NUMBER"),
    ("Acct #: A63750417", "A63750417", "ACCOUNT_NUMBER"),
    ("Accession #: RAD-2026-523242", "RAD-2026-523242", "OTHER_ID_NUMBER"),
    ("Member ID: XJH4492017", "XJH4492017", "HEALTH_PLAN_ID"),
    ("Serial #: SN12497310", "SN12497310", "DEVICE_ID"),
    ("NPI: 1234567893", "1234567893", "OTHER_ID_NUMBER"),
    ("SSN: 123-45-6789", "123-45-6789", "US_SSN"),
    ("Patient: OKAFOR, LAKSHMI        MRN: 2305053", "OKAFOR, LAKSHMI", "NAME_PATIENT"),
    ("Attending: Venkata Rao, MD", "Venkata Rao", "NAME_CLINICIAN"),
    ("Emergency contact: Maria Lopez (daughter)", "Maria Lopez", "NAME_OTHER"),
    ("DOB: 03/14/1941", "03/14/1941", "DATE_TIME"),
    ("DOB: November 10, 1996", "November 10, 1996", "DATE_TIME"),
]
FIELD_NEGATIVE = [
    "Patient was seen today",
    "Patient Denies chest pain",
    "Chart reviewed with the team",
    "Visit: follow-up",
    "MRN: pending",
    "Case: 12",
    "Provider: see above",
    "DOB: unknown",
    "Account number to follow",
    "Insurance: Medicare",
    "Device: pacemaker",
    "Name: the patient",
]


@pytest.mark.parametrize("text,value,entity", FIELD_POSITIVE)
def test_field_key_positive(text, value, entity):
    assert (value, entity) in found(FieldKeyDetector, text)


@pytest.mark.parametrize("text", FIELD_NEGATIVE)
def test_field_key_hard_negative(text):
    assert found(FieldKeyDetector, text) == set()


# --- fax and pager -----------------------------------------------------------------------------
FAX_PAGER_POSITIVE = [
    ("fax 617-555-0199", "617-555-0199", "FAX_NUMBER"),
    ("Fax: (617) 555-0199", "(617) 555-0199", "FAX_NUMBER"),
    ("fax results to 312-555-0147.", "312-555-0147", "FAX_NUMBER"),
    ("Facsimile: 617.555.0100", "617.555.0100", "FAX_NUMBER"),
    ("FAX # 555-555-0123", "555-555-0123", "FAX_NUMBER"),
    ("fax number 1-800-555-0100", "1-800-555-0100", "FAX_NUMBER"),
    ("Read by: Noah Smith, MD  Pager 55916", "55916", "PAGER_NUMBER"),
    ("pager: 4-5821", "4-5821", "PAGER_NUMBER"),
    ("pgr 3321", "3321", "PAGER_NUMBER"),
    ("beeper #71234", "71234", "PAGER_NUMBER"),
    ("Pager number: 617 555 0144", "617 555 0144", "PAGER_NUMBER"),
]
FAX_PAGER_NEGATIVE = [
    "Call 617-555-0199 with questions",
    "records faxed to PCP",
    "Fax pending",
    "pager on call",
    "BP 120/80",
    "fax machine broken",
    "page 2 of 3",
    "Pager: see directory",
    "fax 12",
    "pagers 123 were returned",
    "Phone: 617-555-0100",
]


@pytest.mark.parametrize("text,value,entity", FAX_PAGER_POSITIVE)
def test_fax_pager_positive(text, value, entity):
    assert (value, entity) in found(FaxPagerDetector, text)


@pytest.mark.parametrize("text", FAX_PAGER_NEGATIVE)
def test_fax_pager_hard_negative(text):
    assert found(FaxPagerDetector, text) == set()


# --- clinician cues ------------------------------------------------------------------------------
CLINICIAN_POSITIVE = [
    ("Follow up with Dr. Rao on Monday", "Rao"),
    ("Seen by Dr. Maria Lopez today", "Maria Lopez"),
    ("Electronically signed by Venkata Rao, MD on", "Venkata Rao"),
    ("Priya Shah, M.D. reviewed", "Priya Shah"),
    ("Charge nurse Anna Kim, RN notified", "Anna Kim"),
    ("Doctor Ahmed Hassan examined", "Ahmed Hassan"),
    ("Jane Doe, PA-C", "Jane Doe"),
    ("DR. SMITH aware", "SMITH"),
    ("Tom Nguyen NP will call", "Tom Nguyen"),
    ("Dr. O'Brien consulted", "O'Brien"),
    ("Dr. Anne-Marie Dubois", "Anne-Marie Dubois"),
]
CLINICIAN_NEGATIVE = [
    "MD notified of result",
    "Dr. to call family",
    "follow up with the doctor",
    "Patient seen by MD",
    "Denies MD visits",
    "The RN reports no change",
    "Call MD if fever",
    "RN at bedside",
    "Seen by Dr",
    "Plan PA-C to follow",
    "NP",
]


@pytest.mark.parametrize("text,value", CLINICIAN_POSITIVE)
def test_clinician_positive(text, value):
    assert (value, "NAME_CLINICIAN") in found(ClinicianCueDetector, text)


@pytest.mark.parametrize("text", CLINICIAN_NEGATIVE)
def test_clinician_hard_negative(text):
    assert found(ClinicianCueDetector, text) == set()


# --- hospitals (patterns + gazetteer) --------------------------------------------------------------
HOSPITAL_POSITIVE = [
    ("admitted to Riverside Medical Center with fever", "Riverside Medical Center"),
    ("Transferred from St. Anne's Hospital for care", "St. Anne's Hospital"),
    ("PRESCRIPTION\nMercy Regional Medical Center\n847 Medical Plaza", "Mercy Regional Medical Center"),
    ("seen at Mayo Clinic in 2019", "Mayo Clinic"),
    ("Holloway Memorial Hospital - Cardiology", "Holloway Memorial Hospital"),
    ("Pinecrest Health Center\n2045 Oak St", "Pinecrest Health Center"),
    ("Boston Children's Hospital", "Boston Children's Hospital"),
    ("prior study at Lakeshore Community Hospital.", "Lakeshore Community Hospital"),
    ("University Hospital of Cleveland", "University Hospital of Cleveland"),
    ("Saint Mary's Hospital", "Saint Mary's Hospital"),
    ("MD Anderson Cancer Center", "MD Anderson Cancer Center"),
    ("Pathologist: Priya Shah, MD   Holloway Memorial Hospital   CPT 88305", "Holloway Memorial Hospital"),
]
HOSPITAL_NEGATIVE = [
    "Seen in clinic today",
    "Hospital course: uneventful",
    "The Clinic",
    "Discharged from hospital",
    "Clinic visit scheduled",
    "Medical Center",
    "Health System policy",
    "ICU at this Hospital",
    "Nursing Home residents",
    "emergency department",
    "Infirmary",
    "Hospital Day 3",
]


@pytest.mark.parametrize("text,value", HOSPITAL_POSITIVE)
def test_hospital_positive(text, value):
    assert (value, "HOSPITAL") in found(HospitalDetector, text)


@pytest.mark.parametrize("text", HOSPITAL_NEGATIVE)
def test_hospital_hard_negative(text):
    assert found(HospitalDetector, text) == set()
