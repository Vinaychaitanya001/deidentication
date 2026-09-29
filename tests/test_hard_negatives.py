"""P1.6 hard-negative rules: every look-alike below must be vetoed; real PHI must not be.

Each case gives the text, the value a detector might wrongly propose, and the type it would give
it. `vetoing_region` must return a region of the expected kind (or None for real PHI).
"""

import pytest

from deid.hard_negatives import find_hard_negatives, vetoing_region


def veto_kind(text, value, type_code, nth=0):
    start = -1
    for _ in range(nth + 1):
        start = text.index(value, start + 1)
    region = vetoing_region(start, start + len(value), type_code, find_hard_negatives(text))
    return region.kind if region else None


LOOK_ALIKES = [
    # blood pressure
    ("Vitals: BP 120/80, HR 72", "120/80", "DATE", "blood_pressure"),
    ("BP: 132/84", "132/84", "DATE", "blood_pressure"),
    ("B/P 150/95 sitting", "150/95", "DATE", "blood_pressure"),
    ("blood pressure 118/76 today", "118/76", "ID", "blood_pressure"),
    ("BP was 160/100 on arrival", "160/100", "DATE", "blood_pressure"),
    ("Reports home BP 144/74 and dizziness", "144/74", "DATE", "blood_pressure"),
    ("BP 90/60 mmHg", "90/60", "DATE", "blood_pressure"),
    ("pressure 130/85 mmHg supine", "130/85", "DATE", "blood_pressure"),
    ("BP of 110/70", "110/70", "ID", "blood_pressure"),
    ("blood pressure elevated at 170/95", "170/95", "DATE", "blood_pressure"),
    # scales
    ("strength 4/5 in the left leg", "4/5", "DATE", "scale"),
    ("left leg, 5/5 strength on the right", "5/5", "DATE", "scale"),
    ("Pain 9/10. Reflexes 2+/4", "9/10", "DATE", "scale"),
    ("pain score 7/10", "7/10", "DATE", "scale"),
    ("Reflexes 2+/4 and symmetric", "2+/4", "DATE", "scale"),
    ("2/6 holosystolic murmur", "2/6", "DATE", "scale"),
    ("3/10 pain with movement", "3/10", "DATE", "scale"),
    ("GCS 15. Vitals stable", "15", "AGE", "scale"),
    ("GCS of 14 on arrival", "14", "AGE", "scale"),
    ("Apgars 8 and 9", "8", "AGE", "scale"),
    ("visual acuity 20/40 OD", "20/40", "DATE", "scale"),
    ("NIHSS 4 on admission", "4", "AGE", "scale"),
    ("MMSE 28/30", "28/30", "DATE", "scale"),
    # fractions of a dose
    ("take 1/2 tab at night", "1/2", "DATE", "fraction_dose"),
    ("1/2 tablet by mouth", "1/2", "DATE", "fraction_dose"),
    ("take 1/2 by mouth daily", "1/2", "DATE", "fraction_dose"),
    ("reduce to 3/4 tab", "3/4", "DATE", "fraction_dose"),
    ("1/2 of a tablet", "1/2", "DATE", "fraction_dose"),
    ("2/3 of the lesion", "2/3", "DATE", "fraction_dose"),
    ("D5 1/2 NS at 75 mL/hr", "1/2", "DATE", "fraction_dose"),
    ("1/4 pill twice", "1/4", "DATE", "fraction_dose"),
    ("give 1/2 now", "1/2", "DATE", "fraction_dose"),
    ("1/2 dose tonight", "1/2", "DATE", "fraction_dose"),
    # doses
    ("apixaban 5 mg PO BID", "5 mg", "ID", "dose"),
    ("lorazepam 0.5 mg", "0.5", "AGE", "dose"),
    ("oxycodone 10-20 mg", "10-20", "DATE", "dose"),
    ("Percocet 5/325 mg", "5/325", "DATE", "dose"),
    ("Cefazolin 2 g IV", "2", "AGE", "dose"),
    ("insulin glargine 13 units qHS", "13", "AGE", "dose"),
    ("heparin 18 units/kg/hr", "18", "AGE", "dose"),
    ("albuterol 2 puffs", "2", "AGE", "dose"),
    ("vitamin B12 500 mcg", "500", "ID", "dose"),
    ("KCl 40 mEq", "40", "AGE", "dose"),
    ("Dispense #60, refills 2", "60", "ID", "dose"),
    # durations
    ("cough x1 week", "1 week", "DATE", "duration"),
    ("amoxicillin 500 mg q8h x7 days", "7 days", "DATE", "duration"),
    ("dizziness for 3 days", "3 days", "DATE", "duration"),
    ("Follow-up CT in 12 months", "12 months", "DATE", "duration"),
    ("a 3-day history of fever", "3-day", "DATE", "duration"),
    ("10 day course of antibiotics", "10 day", "DATE", "duration"),
    ("symptoms began 2 days ago", "2 days ago", "DATE", "duration"),
    ("POD 2 was uneventful", "2", "DATE", "duration"),
    ("Hospital day 3 he walked", "3", "DATE", "duration"),
    ("over the past 2 weeks", "2 weeks", "DATE", "duration"),
    ("30-day supply", "30-day", "DATE", "duration"),
    ("shortness of breath x2 hours", "2 hours", "DATE", "duration"),
    # frequencies
    ("amoxicillin 500 mg q8h", "q8h", "ID", "frequency"),
    ("morphine q4-6h prn", "q4-6h", "ID", "frequency"),
    ("Tylenol Q6H", "Q6H", "ID", "frequency"),
    ("metoprolol 25 mg BID", "BID", "ID", "frequency"),
    ("take b.i.d. with food", "b.i.d.", "ID", "frequency"),
    ("insulin 13 units qHS", "qHS", "ID", "frequency"),
    ("every 6 hours as needed", "every 6 hours", "DATE", "frequency"),
    ("every other day", "every other day", "DATE", "frequency"),
    ("twice daily with meals", "twice daily", "DATE", "frequency"),
    ("atorvastatin at bedtime", "at bedtime", "DATE", "frequency"),
    ("atorvastatin 40 mg PO nightly", "nightly", "DATE", "frequency"),
    ("walk 3x/day", "3x/day", "DATE", "frequency"),
]


@pytest.mark.parametrize("text,value,type_code,kind", LOOK_ALIKES)
def test_look_alike_is_vetoed(text, value, type_code, kind):
    assert veto_kind(text, value, type_code) == kind


REAL_PHI = [
    ("seen on 3/4/2024 for 3 days", "3/4/2024", "DATE"),
    ("Follow up on 12/5 with Dr. Rao", "12/5", "DATE"),
    ("Pain since 3/4, worse today", "3/4", "DATE"),
    ("BP check on 12/15/2024", "12/15/2024", "DATE"),
    ("DOB 1/2/1950", "1/2/1950", "DATE"),
    ("on 1/2 she fell", "1/2", "DATE"),
    ("Call 617-555-0100 twice daily", "617-555-0100", "CONTACT.PHONE"),
    ("MRN 4829173, BP 120/80", "4829173", "ID.MRN"),
    ("85 years of age", "85", "AGE"),
    ("a 92-year-old man for 3 days", "92", "AGE"),
    ("ZIP 02114 x3 days", "02114", "LOCATION.ZIP"),
    ("seen 2 days ago on 5/6/2024", "5/6/2024", "DATE"),
    ("Dr. Rao BID rounds", "Rao", "NAME.CLINICIAN"),
]


@pytest.mark.parametrize("text,value,type_code", REAL_PHI)
def test_real_phi_is_not_vetoed(text, value, type_code):
    assert veto_kind(text, value, type_code) is None


def test_durations_and_frequencies_never_veto_ages():
    assert veto_kind("stable for 3 years", "3", "AGE") is None
    assert veto_kind("stable for 3 years", "3", "DATE") == "duration"


def test_names_are_never_vetoed():
    assert veto_kind("BP 120/80", "BP", "NAME") is None
