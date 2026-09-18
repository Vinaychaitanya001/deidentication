# What's copied from Presidio vs. what we wrote

This directory is **not** a fork or clone of `microsoft/presidio`. Individual
files were fetched from GitHub and placed here, each carrying a header
comment with its exact source URL.

- **Source repo:** https://github.com/microsoft/presidio (`main` branch)
- **License:** MIT (Copyright (c) Presidio Contributors)
- **Evaluation data:** https://github.com/microsoft/presidio-research (MIT)

## Summary

| | Count |
|---|---:|
| Files vendored verbatim from Presidio | **187** |
| Files we wrote inside the packages (`__init__.py` only) | 3 |
| Scripts we wrote at the project root | 11 |

Every vendored file is **unmodified**. There are currently **zero** patches
against upstream. (Two files — `iban_recognizer.py` and `phone_recognizer.py`
— carried a temporary `TYPE_CHECKING` patch during the regex-only phase, to
avoid pulling in spaCy. Both were reverted to upstream once the real
`nlp_engine` package was vendored.)

---

## Vendored: `presidio_analyzer/` (154 .py + 6 .yaml)

| Group | Files | What it does |
|---|---:|---|
| Core | 12 | `analyzer_engine.py`, `entity_recognizer.py`, `pattern_recognizer.py`, `pattern.py`, `recognizer_result.py`, `analysis_explanation.py`, `local_recognizer.py`, `remote_recognizer.py`, `score_thresholds.py`, `app_tracer.py`, `dict_analyzer_result.py`, `batch_analyzer_engine.py` |
| `nlp_engine/` | 11 | spaCy / SlimSpacy / Stanza / Transformers / NoOp engines, `NlpArtifacts`, `NerModelConfiguration`, provider, device detector |
| `context_aware_enhancers/` | 3 | `LemmaContextAwareEnhancer` — boosts weak pattern scores from nearby lemmas |
| `recognizer_registry/` | 4 | registry, YAML provider, 837-line recognizer loader |
| `input_validation/` | 4 | pydantic schemas for YAML config validation |
| `chunkers/` | 5 | text chunking (used by NER recognizers) |
| `predefined_recognizers/generic/` | 11 | credit card, IBAN, email, IP, MAC, phone, URL, UUID, crypto, date |
| `predefined_recognizers/nlp_engine_recognizers/` | 4 | `SpacyRecognizer`, `StanzaRecognizer`, `TransformersRecognizer` |
| `predefined_recognizers/country_specific/` | 97 | ~80 recognizers across 18 countries |
| `conf/` | 6 yaml | `default.yaml`, `default_recognizers.yaml`, `spacy.yaml`, `no_op.yaml`, `slim.yaml`, `default_analyzer.yaml` |

## Vendored: `presidio_anonymizer/` (36 .py)

Complete package — engines, `EngineBase`, `OperatorsFactory`,
`TextReplaceBuilder`, all entity classes, and all operators:
`mask`, `redact`, `replace`, `hash`, `keep`, `custom`, `encrypt` (AES),
`decrypt`, `deanonymize_keep`, `surrogate_ahds`.

---

## Deliberately NOT vendored

| Skipped | Files | Reason |
|---|---:|---|
| `llm_utils/` + `lm_recognizer.py` | 7 | LLM recognizers; need `langextract` + Azure credentials |
| `predefined_recognizers/third_party/` | 6 | Azure AI Language / Health De-id; need cloud subscription keys |
| `predefined_recognizers/ner/` | 4 | GLiNER / HuggingFaceNer / MedicalNER; need `transformers` + `torch` |
| `analyzer_engine_provider.py`, `analyzer_request.py` | 2 | REST API layer, unused in a library |

---

## Written by us — inside the packages (3 files)

| File | Why not vendored |
|---|---|
| `presidio_analyzer/__init__.py` | Upstream's version imports `LMRecognizer`, `AnalyzerRequest` and `AnalyzerEngineProvider`, which drag in langextract/Azure. Ours keeps the **same import order** (required — the imports are order-dependent) minus those three. |
| `presidio_analyzer/predefined_recognizers/__init__.py` | Upstream also imports the `ner/` and `third_party/` recognizers above. Ours imports all 97 vendored recognizer classes, which is what makes `RecognizerRegistry`'s `EntityRecognizer.__subclasses__()` discovery find them. |
| `presidio_anonymizer/services/__init__.py` | vendored (upstream is effectively empty) |

## Written by us — project scripts (11 files)

| File | Purpose |
|---|---|
| `build_analyzer.py` | Wires up `AnalyzerEngine` + spaCy + registry. Two documented config overrides (see below). |
| `entity_mapping.py` | Reconciles dataset labels with Presidio labels (`GPE`→`LOCATION`, `DOMAIN_NAME`→`URL`, …) |
| `scoring.py` | Shared recall/precision logic, used by both evaluators so the A/B is apples-to-apples |
| `evaluate_full.py` | Scores the full architecture on all 1,500 records |
| `compare_architectures.py` | **The headline result** — regex-only vs full, identical records |
| `regex_engine.py` | The regex-only baseline (kept deliberately, for comparison) |
| `evaluate.py`, `test_on_presidio_data.py`, `test_cases.py`, `demo.py`, `generate_report_data.py` | Regex-era harnesses, still runnable |

---

## Configuration deviations from Presidio defaults

Both live in `build_analyzer.py` and are toggleable, not hard-coded:

1. **spaCy model.** Presidio's `conf/default.yaml` specifies
   `en_core_web_lg` (~560 MB). We default to `en_core_web_sm` (~13 MB).
   Override with `--model en_core_web_lg`.

2. **ORGANIZATION.** Presidio's default config lists `ORGANIZATION` under
   `labels_to_ignore`, commented *"Has many false positives"* — so org
   detections are discarded out of the box. Our `--org` flag un-ignores it.
   Measured effect on 1,500 records: recall 0.48 → 0.53, precision
   0.50 → 0.45. Presidio's default is defensible.

## Dependencies

```
spacy  numpy  regex  tldextract  pyyaml  phonenumbers  pydantic  cryptography
+ python -m spacy download en_core_web_sm
```

Verified working on **Python 3.14** (spaCy 3.8.16, `en_core_web_sm` 3.8.0).
