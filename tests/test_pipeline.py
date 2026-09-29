"""End-to-end L0-L7 checks, the clinical analyzer set-up (P1.5), and the legacy baseline suite."""

import json
import warnings

import pytest

warnings.filterwarnings("ignore")

from presidio_analyzer.context_aware_enhancers import LemmaContextAwareEnhancer  # noqa: E402
from presidio_analyzer.nlp_engine import NlpEngineProvider  # noqa: E402

from deid.engine import DEFAULT_NER_MODEL, build_clinical_analyzer  # noqa: E402
from deid.pipeline import ClinicalDeidPipeline  # noqa: E402
from evaluation.datasets import load_synthetic_clinical  # noqa: E402

NOTE = ("DISCHARGE SUMMARY\nPatient: OKAFOR, LAKSHMI        MRN: 2305053\nDOB: 11/10/1996\n"
        "Attending: Venkata Rao, MD\nMs. Okafor is a 27-year-old woman. BP 169/69. apixaban 5 mg PO BID x7 days.\n"
        "Lives in Dayton, OH 45402. Call (937) 555-0141. Fax 937-555-0199.\n")


@pytest.fixture(scope="module")
def spacy_engine():
    return NlpEngineProvider(nlp_configuration={
        "nlp_engine_name": "spacy", "models": [{"lang_code": "en", "model_name": "en_core_web_sm"}]}).create_engine()


def test_clinical_analyzer_registers_npi_mbi_and_the_detector_pack(spacy_engine):
    names = {type(r).__name__ for r in build_clinical_analyzer(spacy_engine).registry.recognizers}
    assert {"UsNpiRecognizer", "UsMbiRecognizer", "FieldKeyDetector", "AgeDetector", "UsZipDetector",
            "FaxPagerDetector", "ClinicianCueDetector", "HospitalDetector"} <= names


def test_npi_with_valid_checksum_is_found(spacy_engine):
    results = build_clinical_analyzer(spacy_engine).analyze("Provider 1234567893 signed", "en")
    assert any(r.entity_type == "US_NPI" and r.score >= 0.5 for r in results)


def test_context_words_match_whole_words_only(spacy_engine):
    """'lic' (driver-licence context) is inside 'Duplicate': substring matching would lift the weak
    licence pattern to 0.4 and past the L4 gate."""
    text = "Duplicate order; specimen 12345678 sent."
    analyzer = build_clinical_analyzer(spacy_engine)
    assert analyzer.context_aware_enhancer.context_matching_mode == "whole_word"
    licence = [r.score for r in analyzer.analyze(text, "en") if r.entity_type == "US_DRIVER_LICENSE"]
    assert licence and max(licence) < 0.4
    analyzer.context_aware_enhancer = LemmaContextAwareEnhancer(context_matching_mode="substring")
    assert max(r.score for r in analyzer.analyze(text, "en") if r.entity_type == "US_DRIVER_LICENSE") >= 0.4


def test_candidates_keep_what_presidio_analyze_would_deduplicate(spacy_engine):
    """Overlap decisions belong to L4-L5 (invariant rule 2, DECISIONS D17)."""
    text = "DOB: 02/11/1932"
    analyzer = build_clinical_analyzer(spacy_engine)

    def dob_sources(results):
        return sorted(r.recognition_metadata["recognizer_name"] for r in results
                      if text[r.start:r.end] == "02/11/1932" and r.entity_type == "DATE_TIME")

    assert len(dob_sources(analyzer.analyze(text, "en"))) == 1
    assert dob_sources(analyzer.candidates(text)) == ["DateRecognizer", "FieldKeyDetector"]


def test_pipeline_runs_l0_to_l7(spacy_engine):
    pipe = ClinicalDeidPipeline.from_nlp_engine(spacy_engine)
    result = pipe.deidentify(NOTE, doc_id="note-1")
    det = result.detection
    assert {f.kind for f in det.document.fields} >= {"NAME.PATIENT", "ID.MRN", "DATE.BIRTH", "NAME.CLINICIAN"}  # L1
    assert len(det.decisions) == len(det.candidates)  # L4 decides every candidate
    assert any(d.reason == "veto:blood_pressure" for d in det.decisions) or not any(
        NOTE[d.candidate.start:d.candidate.end] == "169/69" for d in det.decisions)
    spans = det.final_spans  # L5: sorted, non-overlapping
    assert all(a.end <= b.start for a, b in zip(spans, spans[1:]))
    for value in ("OKAFOR, LAKSHMI", "2305053", "11/10/1996", "Venkata Rao", "(937) 555-0141", "937-555-0199", "45402"):
        assert value not in result.text  # L6
    for value in ("BP 169/69", "5 mg", "BID", "x7 days"):
        assert value in result.text  # look-alikes are kept (spaCy's own NER errors are not tested here)
    manifest = result.manifest  # L7
    assert len(manifest["spans"]) == len(spans)
    assert "OKAFOR" not in json.dumps(manifest) and "2305053" not in json.dumps(manifest)


def test_vetoes_can_be_switched_off_for_the_ablation(spacy_engine):
    pipe = ClinicalDeidPipeline.from_nlp_engine(spacy_engine)
    with_vetoes = pipe.detect(NOTE, use_vetoes=True)
    without = pipe.detect(NOTE, use_vetoes=False)
    assert not any(d.reason.startswith("veto:") for d in without.decisions)
    assert len(without.final_spans) >= len(with_vetoes.final_spans)


def _model_cached() -> bool:
    try:
        from huggingface_hub import try_to_load_from_cache
        return isinstance(try_to_load_from_cache(DEFAULT_NER_MODEL, "config.json"), str)
    except Exception:
        return False


@pytest.mark.skipif(not _model_cached(), reason="clinical NER model not in the local Hugging Face cache")
def test_clinical_pipeline_on_a_synthetic_dev_note():
    doc = load_synthetic_clinical("dev")[0]
    result = ClinicalDeidPipeline.build().deidentify(doc.text, doc_id=doc.doc_id)
    kept_actions = {"keep_year", "keep_age_under_90", "keep_state", "zip3"}
    leaked = [doc.text[g.start:g.end] for g in doc.gold
              if doc.text[g.start:g.end] in result.text
              and g.type not in ("AGE", "LOCATION.STATE", "PROFESSION")]
    assert leaked == []
    for value in ("27-year-old", "Dayton, OH", "BP 169/69", "5 mg PO BID"):
        assert value.replace("Dayton", "") in result.text  # age < 90, state and look-alikes kept
    assert all(s["action"] in kept_actions or s["replacement"] for s in result.manifest["spans"])


def test_legacy_regex_baseline_suite_still_passes(capsys):
    import test_cases

    assert test_cases.main() == 0
