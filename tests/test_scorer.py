"""Evaluation v2 scorer (P1.1 done-when: the scorer has unit tests)."""

import pytest

from evaluation.scorer import (EvalDoc, Span, doc_counts, evaluate, hard_negative_rate, paired_difference_ci,
                               summarize)

TEXT = "Seen by John Smith on 03/04/2024, MRN 123456, room 12."


def span(text, value, type_, nth=0):
    start = -1
    for _ in range(nth + 1):
        start = text.index(value, start + 1)
    return Span(start, start + len(value), type_)


def make_doc(doc_id="d1", text=TEXT, ignore=(), hard_negatives=()):
    gold = [span(text, "John Smith", "NAME.CLINICIAN"), span(text, "03/04/2024", "DATE"), span(text, "123456", "ID.MRN")]
    return EvalDoc(doc_id, text, gold, list(ignore), list(hard_negatives))


def score(doc, preds):
    return summarize(doc_counts(doc, preds))


def test_perfect_prediction():
    doc = make_doc()
    s = score(doc, doc.gold)
    for level in ("entity_strict", "entity_exact", "entity_partial", "entity_partial_typed", "token_binary", "token_typed"):
        assert s[level]["precision"] == s[level]["recall"] == s[level]["f2"] == 1.0
    assert s["char"]["leak_rate"] == 0.0
    assert s["doc_zero_leak_rate"] == 1.0


def test_no_prediction_leaks_everything():
    s = score(make_doc(), [])
    assert s["entity_strict"]["recall"] == s["entity_partial"]["recall"] == 0.0
    assert s["entity_partial"]["precision"] == 0.0
    assert s["char"]["leak_rate"] == 1.0
    assert s["doc_zero_leak_rate"] == 0.0


def test_boundary_error_counts_as_partial_but_not_strict():
    doc = make_doc()
    preds = [span(TEXT, "John", "NAME.CLINICIAN"), doc.gold[1], doc.gold[2]]
    s = score(doc, preds)
    assert s["entity_strict"]["recall"] == pytest.approx(2 / 3)
    assert s["entity_partial"]["recall"] == 1.0
    assert s["char"]["leak_rate"] == pytest.approx(len("Smith") / len("JohnSmith030420241234" "56"))
    assert s["doc_zero_leak_rate"] == 0.0


def test_types_compared_at_category_level():
    doc = make_doc()
    generic_name = [Span(doc.gold[0].start, doc.gold[0].end, "NAME"), doc.gold[1], doc.gold[2]]
    assert score(doc, generic_name)["entity_strict"]["recall"] == 1.0
    wrong_type = [Span(doc.gold[0].start, doc.gold[0].end, "LOCATION"), doc.gold[1], doc.gold[2]]
    s = score(doc, wrong_type)
    assert s["entity_strict"]["recall"] == pytest.approx(2 / 3)
    assert s["entity_exact"]["recall"] == 1.0  # exact ignores the type
    assert s["entity_partial"]["recall"] == 1.0
    assert s["entity_partial_typed"]["recall"] == pytest.approx(2 / 3)


def test_non_phi_redaction_is_a_false_positive():
    doc = make_doc()
    s = score(doc, doc.gold + [span(TEXT, "Seen", "NRP")])
    assert s["entity_partial"]["precision"] == pytest.approx(3 / 4)
    assert s["token_binary"]["precision"] == pytest.approx(len(["John", "Smith", "03", "04", "2024", "123456"]) / 7)


def test_dont_care_regions_are_neither_rewarded_nor_penalised():
    room = span(TEXT, "12.", "X")
    doc = make_doc(ignore=[(room.start, room.start + 2)])
    s = score(doc, doc.gold + [Span(room.start, room.start + 2, "ID")])
    assert s["entity_partial"]["precision"] == 1.0
    assert s["token_binary"]["precision"] == 1.0


def test_every_gold_span_counts_in_the_denominator():
    doc = make_doc()
    s = score(doc, [doc.gold[0]])
    assert s["counts"]["partial_gold"] == 3
    assert s["entity_partial"]["recall"] == pytest.approx(1 / 3)


def test_char_leak_counts_letters_and_digits_only():
    doc = make_doc()
    s = score(doc, [doc.gold[0], doc.gold[2], span(TEXT, "03/04", "DATE")])
    assert s["char"]["leak_rate"] == pytest.approx(4 / 23)  # "2024" of 23 alphanumeric gold characters


def test_duplicate_predictions_are_counted_once():
    doc = make_doc()
    s = score(doc, doc.gold + doc.gold)
    assert s["entity_strict"]["precision"] == 1.0


def test_bootstrap_ci_brackets_the_point_estimate():
    docs = [make_doc(f"d{i}") for i in range(12)]
    preds = {d.doc_id: d.gold if i % 3 else d.gold[:1] for i, d in enumerate(docs)}
    result = evaluate(docs, preds, bootstrap=200)
    lo, hi = result["ci95"]["partial_recall"]
    assert lo <= result["entity_partial"]["recall"] <= hi
    assert lo < hi


def test_paired_difference_of_identical_systems_is_zero():
    docs = [make_doc(f"d{i}") for i in range(8)]
    rows = [doc_counts(d, d.gold[:2]) for d in docs]
    diff = paired_difference_ci(rows, rows, n=100)
    assert diff["strict_f2"]["diff"] == 0.0
    assert diff["strict_f2"]["ci"] == [0.0, 0.0]


def test_hard_negative_rate():
    bp = span(TEXT, "12", "X", nth=1)  # "room 12", a look-alike
    doc = make_doc(hard_negatives=[(bp.start, bp.end, "scale")])
    assert hard_negative_rate([doc], {"d1": doc.gold})["rate"] == 0.0
    assert hard_negative_rate([doc], {"d1": doc.gold + [Span(bp.start, bp.end, "AGE")]})["rate"] == 1.0
