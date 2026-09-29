# CLAUDE.md — project source of truth

Clinical PHI de-identification (Independent Study). English clinical notes first; the
architecture must extend to Telugu/Indic languages later without a redesign. Built on
Presidio, used as a pinned dependency.

## Read before changing anything

| File | What it holds |
|---|---|
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | The agreed L0–L7 architecture, contracts and invariants. Do not redesign. |
| [docs/ROADMAP.md](docs/ROADMAP.md) | Phases, task list and phase boundaries: what may be built now. |
| [docs/DECISIONS.md](docs/DECISIONS.md) | Decisions with rationale, plus open questions awaiting the team. |
| [docs/CURRENT_STATE.md](docs/CURRENT_STATE.md) | Implemented / verified / in progress / remaining, and the next allowed task. |

Background (historical, still accurate for what they describe): `ARCHITECTURE.md` at the repo
root explains Presidio's internals (not our target architecture); `RESULTS.md`,
`SYSTEM_OVERVIEW.md`, `TEST_REPORT.md`, `PRESENTATION_GUIDE.md` cover the regex-only and
stock-Presidio baselines scored with the legacy scorer; `IMPLEMENTATION_PLAN.md` is the earlier
vendoring + i2b2 plan; `VENDORED_FILES.md` documents the vendored copy that has been removed.
The agreed plan was also shared as `PHI_Deidentification_Architecture_and_Plan.pdf` (outside the repo).

## Ground rules

1. Follow docs/ARCHITECTURE.md. Any architectural change needs a DECISIONS.md entry and team approval first.
2. Current phase: **Phase 1 (Foundations)**. Do not implement Phase-2/3 components; add interfaces only (see ROADMAP).
3. Measure every change with `evaluate_v2.py` (one scorer, same datasets). Never fabricate or overstate
   results; claim no novelty, calibration or research improvement unless implemented and measured.
4. Keep the baselines runnable and comparable: B0 `regex_engine.py`, B1 `build_analyzer.py`.
5. No real PHI anywhere (code, data, issues, screenshots). Synthetic data only.
6. Update docs/CURRENT_STATE.md after every meaningful milestone; record decisions in docs/DECISIONS.md.
7. Commit only when asked. No `Co-Authored-By` or other AI-contributor lines.

## Environment and commands

Python ≥ 3.10 is required (current Presidio, transformers and torch). The local `.venv` uses 3.12.

```bash
python3.12 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m pytest                                                # all tests (incl. the 29 legacy regex cases)
.venv/bin/python demo_clinical.py                                         # one note through L0-L7, stage by stage
.venv/bin/python evaluate_v2.py                                           # Evaluation v2: B0 B1 B2 P1-spacy P1-noveto P1
.venv/bin/python evaluate_v2.py --systems B0,B1 --datasets clinical_dev   # a subset
.venv/bin/python data/synthetic_clinical/generate.py                      # regenerate the synthetic set (deterministic)
.venv/bin/python compare_architectures.py                                 # legacy A/B with the legacy scorer
```

The clinical NER model `obi/deid_roberta_i2b2` (~1.4 GB) downloads from Hugging Face on first use.
Tune on `clinical_dev` only; `clinical_test` is for the final report run.
Set `DEID_HMAC_KEY` for pseudonyms and date shifts; without it a demo key is used (never on real data).

## Layout

| Path | Layer / role |
|---|---|
| `deid/` | Phase-1 pipeline package, one module per stage (L0 `ingest`, L1 `structure`, L2 `langpack_en`, L3 `engine` + `detectors`, L4 `decision` + `hard_negatives`, L5 `consistency` + `spans`, L6 `transform`, L7 `assurance`; `pipeline` wires them, `contracts` + `ontology` are shared) |
| `tests/`, `pytest.ini` | pytest suite: scorer, detectors, vetoes, decider/resolver, transformation, end to end |
| `demo_clinical.py` | Phase-1 demonstration script |
| `evaluation/`, `evaluate_v2.py` | Evaluation v2: datasets, the one scorer, system adapters, CLI |
| `data/synthetic_clinical/` | Synthetic clinical dev/test notes and their generator |
| `data/synth_dataset_v2.json` | Presidio-research general-PII set (regression check) |
| `regex_engine.py`, `build_analyzer.py` | Baselines B0 and B1 (kept for comparison) |
| `compat/` | Shim for a recognizer missing from the pinned Presidio release |
| `entity_mapping.py`, `scoring.py`, `evaluate*.py`, `compare_architectures.py`, `test_on_presidio_data.py`, `demo.py`, `trace_example.py`, `generate_report_data.py` | Legacy (pre-v2) harnesses, still runnable |
| `results/` | Legacy results; Evaluation v2 writes `results/v2/REPORT.md` and one JSON per dataset |
