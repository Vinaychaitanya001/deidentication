# Current state

_Last updated: 29 Sep 2026 — Phase-1 pipeline implemented and evaluated; awaiting team/mentor review
(P1.8) and answers to the open questions in DECISIONS.md. Nothing below is committed yet (working tree only)._

## Implemented and verified

| Item | Evidence |
|---|---|
| Environment: `.venv` Python 3.12.14; presidio-analyzer/anonymizer 2.2.364, spaCy 3.8.16 + `en_core_web_sm` 3.8.0, transformers 4.57.6, torch 2.14.0, spacy-huggingface-pipelines 0.0.4, pytest 9.1.1 | pinned in `requirements.txt` |
| Vendored Presidio removed (D3); `compat/uuid_recognizer.py`; `build_analyzer.py` reads the installed config | legacy 29 regex cases pass (now also run by pytest); `compare_architectures.py` reproduced the committed results |
| P1.1 canonical ontology + Evaluation v2 (scorer, datasets, adapters, CLI) | `deid/ontology.py`, `evaluation/`, `evaluate_v2.py`; 12 scorer unit tests |
| P1.2 synthetic clinical set: dev 60 notes / 606 PHI / 450 look-alikes; test 40 / 396 / 308 | `data/synthetic_clinical/` (deterministic generator) |
| P1.4 clinical NER `obi/deid_roberta_i2b2` via Presidio `TransformersNlpEngine`, PATIENT/STAFF kept apart; BILOU→BIO (D6); "simple" aggregation + word continuation (D16) | `deid/engine.py`; ablations `B2-max`, `B2-nobio` |
| P1.5 clinical detector pack: field keys (MRN, account, accession/other, member ID, device, licence, SSN, NPI; patient/clinician/other name fields; DOB), AGE (+over-89 flag), US ZIP, fax/pager, clinician cues, hospital patterns + gazetteer; NPI + MBI enabled; whole-word context matching; every recognizer result reaches L4 (D17) | `deid/detectors.py`, `deid/structure.py`, `deid/langpack_en.py`, `deid/engine.py`; 141 detector tests (≥ 10 positive + ≥ 10 hard-negative per detector) |
| L4 rule-based decider: gates weak driver-licence/bank patterns (< 0.4 rejected), NRP not PHI, hard-negative vetoes (D12) | `deid/decision.py` |
| P1.6 hard-negative rules: blood pressure, scales, fractions of a dose, doses, durations, frequencies (D18) | `deid/hard_negatives.py`; 83 veto tests (68 look-alikes vetoed, ≥ 10 per kind; 13 real-PHI cases not vetoed; 2 type rules) |
| L5 overlap resolution (D14) and candidate trimming (D15) | `deid/consistency.py`, `deid/spans.py`; 21 decider/resolver/trim tests |
| P1.7 transformation (HMAC pseudonyms, per-document date shift, 90+ incl. birth date, ZIP3, keep state) and L7 span manifest (D19) | `deid/transform.py`, `deid/assurance.py`; 29 tests (same input → same pseudonym, intervals preserved, no original values in the manifest) |
| Pipeline L0–L7 (`ClinicalDeidPipeline.detect/deidentify`), demo script | `deid/pipeline.py`, `demo_clinical.py`; 8 tests (end to end with spaCy and with the clinical NER, analyzer set-up, legacy regex suite) |
| Test suite | `python -m pytest`: **294 passed** (29 Sep 2026) |
| P1.8 baseline report | `results/v2/REPORT.md` + JSON per dataset (numbers below) |

## Results — Evaluation v2 (29 Sep 2026)

`evaluate_v2.py --systems B0,B1,B2,B2-max,P1-spacy,P1-noveto,P1 --datasets clinical_dev,clinical_test,synth_v2 --bootstrap 1000`.
Percentages; full tables with CIs, per-category recall and look-alike rates in `results/v2/REPORT.md`.
Rules were tuned on `clinical_dev` only; `clinical_test` was run once, for this report.

| Dataset | System | Strict F2 | Partial R | Partial P | Token F2 | Char leak | Zero-leak docs | Look-alikes redacted |
|---|---|---|---|---|---|---|---|---|
| clinical_test (40) | B0 regex-only | 26.4 | 23.5 | 90.3 | 36.5 | 77.9 | 0.0 | 3.2 |
| clinical_test | B1 Presidio + spaCy | 54.1 | 73.0 | 66.1 | 70.9 | 29.3 | 2.5 | 25.6 |
| clinical_test | B2 Presidio + clinical NER | 77.5 | 99.0 | 90.9 | 98.0 | 0.9 | 90.0 | 7.8 |
| clinical_test | P1 Phase-1 | **97.9** | 99.0 | **96.8** | 99.0 | 0.9 | 90.0 | **1.9** |
| clinical_dev (60) | B0 / B1 / B2 / P1 strict F2 | 23.0 / 61.5 / 91.1 / 98.7 | P1 R 98.8 | P1 P 98.4 | | P1 1.1 | P1 88.3 | P1 1.3 |
| synth_v2 (1,500) | B1 / B2 / P1 strict F2 | 40.3 / 55.0 / 58.1 | P1 R 88.8 | P1 P 95.2 | P1 80.4 | P1 16.8 | P1 70.3 | — |

Paired differences (percentage points, 95% bootstrap CI over documents):

| Comparison | clinical_test | clinical_dev | synth_v2 |
|---|---|---|---|
| P1 − B1 strict F2 / char leak | +43.8 [+40.6, +47.1] / −28.4 [−32.9, −24.1] | +37.3 / −24.9 | +17.9 / −28.4 |
| P1 − B2 strict F2 | +20.4 [+17.6, +23.5] | +7.6 [+5.6, +9.8] | +3.1 [+1.9, +4.4] |
| P1 − B2 partial recall, char leak | 0.0, 0.0 | 0.0, 0.0 | 0.0, 0.0 |
| P1 − P1-noveto strict F2 (recall change) | +0.5 [+0.2, +0.8] (0.0) | +0.5 [+0.3, +0.7] (0.0) | 0.0 (0.0) |
| B2 − B2-max (D16) strict F2 | +26.0 [+22.7, +29.7] | +38.3 [+35.1, +41.8] | +15.9 [+14.3, +17.6] |

How to read this honestly:
- Most of the gain over B1 comes from the clinical NER, once integrated correctly (B2 − B1, D16). P1
  adds exact boundaries and subtypes (field keys, clinician cues, overlap rules), precision, and
  look-alike suppression. **P1 does not find more PHI than B2**: recall and character leak are
  identical on all three datasets.
- Vetoes: no recall loss on dev (P1.6 done-when met); P1 redacts 0% of blood-pressure, scale, dose,
  duration and frequency look-alikes on dev and test. Codes stay redacted (Q9); the gate on weak
  licence patterns removes the "x7" (from "x7 days") false alarms that B2 has.
- The synthetic notes were written by the same team that wrote the rules, so rule-based scores are
  optimistic (D9); the test split has only 40 notes (wide CIs, e.g. zero-leak docs 80.0–97.5%).
  No real clinical data yet (i2b2/n2c2 access pending).
- P1-spacy (detector pack on spaCy NER): clinical test strict F2 84.3 vs B1 54.1, but on synth_v2
  its ID recall is lower than B1's (92.1 vs 98.3 partial): the L4 licence/bank gate drops licence
  numbers that have no context word. With the clinical NER (P1) ID recall on synth_v2 is 100%.

### Earlier measurements superseded
- P1.4 (29 Sep, before D16): B2 strict F2 52.8, char leak 17.3% on dev; "the model never tags
  ages" and "truncates long-form dates" were **aggregation artifacts** (D16), not model errors.
  That configuration is kept as ablation `B2-max`.
- Baselines B0/B1 under Evaluation v2 are unchanged (dev: B0 23.0 / B1 61.5 strict F2; synth_v2:
  13.4 / 40.3). Legacy numbers in `RESULTS.md` used a different scorer and are not comparable.

## Remaining Phase-1 gaps

- P1.2 team actions: n2c2 and PhysioNet access requests; meeting-1 guideline decisions (plan §6).
- P1.3: CI not set up (Q6); no config-file policy profiles (the Safe Harbor profile is code in `deid/transform.py`).
- P1.8: review of `results/v2/REPORT.md` by the team and mentor.
- Open questions Q1–Q11 in DECISIONS.md (date-shift key, contracts/grouping scope, measurement and code vetoes, CI, name variants, fragment merging).

## Known issues and limitations (measured, not fixed)

- Professions: no detector (0% recall; GLiNER / later phases). Family members' first names are
  sometimes missed or subtyped as patient ("Robert" → `NAME.PATIENT`, shown as `[PATIENT-…]`).
- Procedure codes: the NER tags "CPT 88305" as ID (all code look-alikes on dev, 75% on test; Q9).
- Note headers: the NER tags "DISCHARGE SUMMARY" as a hospital (sectionizer is P2.3).
- L5 does not merge same-type fragments separated by a space (Presidio's anonymizer does): on
  synth_v2 P1's NAME strict recall is 78.1% vs B2's 80.2% (Q11).
- D14 leftovers can be non-PHI fragments ("year-old" after spaCy tags "27-year-old" as a date).
- Pseudonyms are per exact value: a surname-only mention gets a different code from the full name (Q10, P2.4).
- spacy-huggingface-pipelines prints "Skipping annotation … overlapping" warnings when sub-word
  pieces of one word get different labels; expected, the first piece covers the word.
- Legacy docs point to vendored paths (`presidio_analyzer/...`) that are no longer in the tree (D13).

## Phase-2 components prepared as interfaces only (not implemented)

`Decider` protocol (P2.2 calibrated fusion) · `ConsistencyStep` protocol (P2.4 propagation) ·
`Candidate` / `Decision` / `FinalSpan` contracts with evidence and sources (P2.1) · `Document.fields`
(`KeyValueField`) for the sectionizer and field features (P2.3) · pluggable transformer with a
`profile` (P2.8 surrogates, other profiles) · `ingest(language=…)` + `Document.language` and a
per-language `langpack_*` module (P2.9, P3.3) · `--ner-model` / `build(ner_model=…)` for a
fine-tuned model (P2.7) · manifest structure for the leak scan and review queue (P2.8).

## Next allowed task

Phase-1 close-out only: team/mentor review of the P1.8 report, answers to Q1–Q11, CI (P1.3) if
approved, access requests (P1.2). Phase-2 work starts only after that review (see ROADMAP).
