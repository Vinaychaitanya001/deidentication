"""P1.7 transformation (L6) and span manifest (L7).

Done-when (ROADMAP P1.7): same input -> same pseudonym; date intervals preserved.
"""

import datetime as dt
import json
import re

import pytest

from deid.assurance import build_manifest
from deid.contracts import DetectionResult, Document, FinalSpan
from deid.transform import RESTRICTED_ZIP3, SafeHarborTransformer, shift_date

KEY = b"unit-test-key"


def detection(text, spans, doc_id="note-1"):
    """spans: (value, type[, evidence]) in order of appearance."""
    final, pos = [], 0
    for value, type_, *rest in spans:
        start = text.index(value, pos)
        final.append(FinalSpan(start, start + len(value), type_, 0.9, ("test",), rest[0] if rest else ()))
        pos = start + len(value)
    return DetectionResult(Document(doc_id, text), [], [], final)


def transform(text, spans, doc_id="note-1", key=KEY):
    t = SafeHarborTransformer(key)
    out, actions = t.apply(detection(text, spans, doc_id))
    return out, actions, t


# --- pseudonyms -------------------------------------------------------------------------------------
def test_same_value_same_pseudonym_within_and_across_documents():
    a, _, _ = transform("Seen John Smith. John Smith agrees.", [("John Smith", "NAME.PATIENT"), ("John Smith", "NAME.PATIENT")])
    b, _, _ = transform("Call John Smith.", [("John Smith", "NAME.PATIENT")], doc_id="note-2")
    codes = re.findall(r"\[PATIENT-[0-9a-f]{6}\]", a + b)
    assert len(codes) == 3 and len(set(codes)) == 1


def test_name_variants_share_a_pseudonym():
    t = SafeHarborTransformer(KEY)
    assert t.pseudonym("NAME.PATIENT", "OKAFOR, LAKSHMI")[-8:] == t.pseudonym("NAME.PATIENT", "Lakshmi Okafor")[-8:]
    assert t.pseudonym("NAME", "Lakshmi Okafor")[-8:] == t.pseudonym("NAME.PATIENT", "Lakshmi Okafor")[-8:]


def test_id_formatting_does_not_change_the_pseudonym():
    t = SafeHarborTransformer(KEY)
    assert t.pseudonym("ID.MRN", "482-9173") == t.pseudonym("ID.MRN", "4829173")


def test_different_values_and_keys_give_different_pseudonyms():
    t1, t2 = SafeHarborTransformer(KEY), SafeHarborTransformer(b"another-key")
    assert t1.pseudonym("NAME.PATIENT", "John Smith") != t1.pseudonym("NAME.PATIENT", "Jane Smith")
    assert t1.pseudonym("NAME.PATIENT", "John Smith") != t2.pseudonym("NAME.PATIENT", "John Smith")


def test_demo_key_is_flagged(monkeypatch):
    monkeypatch.delenv("DEID_HMAC_KEY", raising=False)
    assert SafeHarborTransformer().demo_key
    monkeypatch.setenv("DEID_HMAC_KEY", "from-the-vault")
    assert not SafeHarborTransformer().demo_key


# --- dates ------------------------------------------------------------------------------------------
@pytest.mark.parametrize("value,expected", [
    ("03/14/2024", "03/04/2024"),
    ("3/14/24", "3/4/24"),
    ("March 14, 2024", "March 4, 2024"),
    ("Mar 14, 2024", "Mar 4, 2024"),
    ("14-Mar-2024", "04-Mar-2024"),
    ("2024-03-14", "2024-03-04"),
    ("14 March 2024", "4 March 2024"),
    ("3/14", "3/4"),
    ("1/5/2024", "12/26/2023"),
])
def test_shift_keeps_the_format(value, expected):
    assert shift_date(value, 10) == expected


def test_date_intervals_are_preserved_within_a_document():
    text = "Admitted 6/30/24. Surgery July 1, 2024. Discharged 07/07/2024."
    values = ["6/30/24", "July 1, 2024", "07/07/2024"]
    out, actions, t = transform(text, [(v, "DATE") for v in values])
    shifted = [a["replacement"] for a in actions]
    parse = [lambda s: dt.datetime.strptime(s, "%m/%d/%y"), lambda s: dt.datetime.strptime(s, "%B %d, %Y"),
             lambda s: dt.datetime.strptime(s, "%m/%d/%Y")]
    before = [p(v) for p, v in zip(parse, values)]
    after = [p(v) for p, v in zip(parse, shifted)]
    assert [(b - before[0]).days for b in before] == [(a - after[0]).days for a in after]
    assert (before[0] - after[0]).days == t.date_shift_days("note-1")


def test_one_offset_per_document():
    t = SafeHarborTransformer(KEY)
    offsets = {t.date_shift_days(f"note-{i}") for i in range(50)}
    assert all(1 <= d <= 365 for d in offsets)
    assert t.date_shift_days("note-7") == t.date_shift_days("note-7")
    assert len(offsets) > 1


def test_years_are_kept_and_unparsed_dates_are_tagged():
    out, actions, _ = transform("Diagnosed in 2019, seen last Tuesday.", [("2019", "DATE"), ("last Tuesday", "DATE")])
    assert out == "Diagnosed in 2019, seen [DATE]."
    assert [a["action"] for a in actions] == ["keep_year", "tag_unparsed_date"]


# --- ages, birth dates, ZIP, states -------------------------------------------------------------------
def test_ages_over_89_are_bucketed():
    out, _, _ = transform("a 95-year-old and an 89-year-old", [("95", "AGE"), ("89", "AGE")])
    assert out == "a 90+-year-old and an 89-year-old"


def test_birth_date_removed_when_patient_is_90_plus():
    dob = (("field_kind", "DATE.BIRTH"),)
    out, actions, _ = transform("DOB: 03/14/1931. A 93-year-old woman.", [("03/14/1931", "DATE", dob), ("93", "AGE")])
    assert out == "DOB: [DOB 90+]. A 90+-year-old woman."


def test_birth_date_removed_when_dates_imply_90_plus():
    dob = (("field_kind", "DATE.BIRTH"),)
    out, _, _ = transform("DOB: 01/02/1930. Seen 03/04/2024.", [("01/02/1930", "DATE", dob), ("03/04/2024", "DATE")])
    assert out.startswith("DOB: [DOB 90+].")


def test_birth_date_of_younger_patient_is_shifted():
    dob = (("field_kind", "DATE.BIRTH"),)
    out, actions, _ = transform("DOB: 11/10/1996. A 27-year-old.", [("11/10/1996", "DATE", dob), ("27", "AGE")])
    assert actions[0]["action"] == "date_shift"
    assert "11/10/1996" not in out


@pytest.mark.parametrize("zip_code,expected", [("02114", "021**"), ("02114-1234", "021**"), ("45402", "454**"),
                                              ("03601", "000**"), ("89001", "000**")])
def test_zip3_rule(zip_code, expected):
    out, _, _ = transform(f"Dayton, OH {zip_code}", [(zip_code, "LOCATION.ZIP")])
    assert out == f"Dayton, OH {expected}"


def test_restricted_zip3_list_has_17_entries():
    assert len(RESTRICTED_ZIP3) == 17


def test_state_is_kept_city_is_pseudonymised():
    out, actions, _ = transform("Dayton, OH", [("Dayton", "LOCATION"), ("OH", "LOCATION")])
    assert out.endswith(", OH") and "Dayton" not in out
    assert [a["action"] for a in actions] == ["hmac_pseudonym", "keep_state"]


# --- manifest -----------------------------------------------------------------------------------------
def test_manifest_has_positions_types_actions_and_no_original_values():
    text = "Patient: John Smith  MRN: 4829173  DOB: 11/10/1996  Dayton, OH 45402  age 27"
    spans = [("John Smith", "NAME.PATIENT"), ("4829173", "ID.MRN"), ("11/10/1996", "DATE", (("field_kind", "DATE.BIRTH"),)),
             ("Dayton", "LOCATION"), ("OH", "LOCATION"), ("45402", "LOCATION.ZIP"), ("27", "AGE")]
    det = detection(text, spans)
    t = SafeHarborTransformer(KEY)
    out, actions = t.apply(det)
    manifest = build_manifest(det, actions, t.profile, t.demo_key)
    dumped = json.dumps(manifest)
    for value, *_ in spans:
        assert value not in dumped
    assert [s["type"] for s in manifest["spans"]] == [s[1] for s in spans]
    for s, a in zip(manifest["spans"], actions):
        assert out[s["output_start"]:s["output_end"]] == a["replacement"]
    assert manifest["profile"] == "hipaa_safe_harbor"
