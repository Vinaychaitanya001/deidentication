# Implementation Plan — Full Presidio Architecture on i2b2

Goal: replace the regex-only build with Presidio's **actual architecture**
(AnalyzerEngine + NlpEngine + RecognizerRegistry + ContextAwareEnhancer +
full Anonymizer), then evaluate it on the i2b2 2014 de-identification
dataset.

Sources (read via `raw.githubusercontent.com`, no cloning):
- `github.com/microsoft/presidio` — `main` branch
- `github.com/microsoft/presidio-research` — `main` branch (i2b2 formatter)

---

## 0. STRATEGY — Presidio's own dataset first, i2b2 later

**Decision:** build and validate the full architecture against
`synth_dataset_v2.json` (already in `data/`, 1,500 records), then move to
i2b2 once access is obtained.

Reasons:
1. **Zero blockers** — the data is already on disk, and our evaluation
   harness already reads it.
2. **The comparison is cleaner** — regex-only and full architecture scored on
   *identical* records is the single most valuable result of this study.
   Switching datasets at the same time as switching architectures would
   confound the two variables.
3. **i2b2 access is currently uncertain** — as of Sept 2026 the Harvard DBMI
   portal returns 403 and `i2b2.org` returns HTTP 500; registration was
   reported closed since late July 2026. Apply through an institutional
   advisor in parallel, but do not let it gate the work.

### 0.1 The one real blocker: spaCy on Python 3.14
Presidio's `pyproject.toml` carries a special constraint for 3.14. Verify
before building:
```powershell
pip install spacy
python -m spacy download en_core_web_sm
python -c "import spacy; nlp=spacy.load('en_core_web_sm'); print(nlp('Dr. Sarah Johnson called').ents)"
```
If wheels are unavailable on 3.14/Windows, fall back to a Python 3.11 or
3.12 virtual environment.

---

## 1. What happens to the regex-only build

**Nothing is deleted.** The full architecture is a *superset*: it adds
`AnalyzerEngine`, `NlpEngine`, `RecognizerRegistry` and the NER recognizers
to the same `presidio_analyzer/` package. All 10 generic recognizers stay
byte-identical.

The only file that becomes redundant is `regex_engine.py` (our hand-written
orchestrator). **Recommendation: keep it.** It costs nothing and gives a
direct A/B comparison — "regex-only vs full architecture on identical data"
is the strongest result this study can produce. The two patches in
`iban_recognizer.py` / `phone_recognizer.py` get **reverted** to upstream,
since the real `nlp_engine` package will now exist.

---

## 2. Files to COPY verbatim from Presidio

### 2A. Analyzer core — 5 new (7 already vendored)
| File | Lines | Why |
|---|---:|---|
| `analyzer_engine.py` | 510 | the real orchestrator |
| `app_tracer.py` | 27 | decision-process logging |
| `remote_recognizer.py` | 56 | base class referenced by `__init__` |
| `dict_analyzer_result.py` | 29 | referenced by `__init__` |
| `batch_analyzer_engine.py` | 159 | batch API (optional but small) |

*Already vendored, unchanged:* `analysis_explanation.py`,
`recognizer_result.py`, `entity_recognizer.py`, `local_recognizer.py`,
`pattern.py`, `pattern_recognizer.py`, `score_thresholds.py`

### 2B. `nlp_engine/` — 11 files
| File | Lines | Notes |
|---|---:|---|
| `__init__.py` | 26 | |
| `nlp_engine.py` | 65 | abstract base |
| `nlp_artifacts.py` | 88 | tokens/lemmas/entities container |
| `ner_model_configuration.py` | 128 | **needs pydantic**; holds the clinical label mapping |
| `device_detector.py` | 92 | CPU/GPU selection |
| `spacy_nlp_engine.py` | 290 | **the main one** |
| `slim_spacy_nlp_engine.py` | 269 | lighter spaCy variant |
| `no_op_nlp_engine.py` | 168 | no-NLP mode |
| `stanza_nlp_engine.py` | ~250 | import is `try/except` guarded — safe |
| `transformers_nlp_engine.py` | ~200 | import is guarded — safe |
| `nlp_engine_provider.py` | 133 | YAML → engine |

### 2C. `context_aware_enhancers/` — 3 files
`__init__.py`, `context_aware_enhancer.py` (66), `lemma_context_aware_enhancer.py` (370)

### 2D. `recognizer_registry/` — 4 files
`__init__.py`, `recognizer_registry.py` (422),
`recognizer_registry_provider.py` (248), `recognizers_loader_utils.py` (833)

### 2E. `input_validation/` — 4 files
`__init__.py`, `language_validation.py` (18), `schemas.py` (156),
`yaml_recognizer_models.py` (659) — **pydantic schemas**

### 2F. Recognizers
| Group | Files | Status |
|---|---:|---|
| `predefined_recognizers/generic/` | 11 | **already vendored** — 2 patches reverted |
| `predefined_recognizers/nlp_engine_recognizers/` | 4 | NEW — `SpacyRecognizer` is the one that matters |
| `predefined_recognizers/country_specific/us/` | 12 | NEW — SSN, driver licence, MRN-adjacent, medical licence, NPI, MBI, ITIN, passport, bank, ABA routing |

### 2G. `conf/` — 5 YAML files
`default.yaml`, `default_recognizers.yaml`, `spacy.yaml`, `no_op.yaml`, `slim.yaml`

### 2H. Anonymizer — full package, ~19 new files
| Group | Files |
|---|---|
| engines | `anonymizer_engine.py` (270), `deanonymize_engine.py` |
| `core/` | `__init__.py`, `engine_base.py` (122) — *`text_replace_builder.py` already vendored* |
| `entities/` | `__init__.py`, `conflict_resolution_strategy.py`, `engine/__init__.py`, `engine/pii_entity.py`, `engine/recognizer_result.py`, `engine/dict_recognizer_result.py`, `engine/result/__init__.py`, `engine/result/engine_result.py`, `engine/result/operator_result.py` |
| `operators/` | `__init__.py`, `operators_factory.py` (157), `aes_cipher.py`, `custom.py`, `encrypt.py`, `decrypt.py`, `keep.py`, `deanonymize_keep.py` — *mask/redact/replace/hash/operator already vendored* |
| `services/` | `app_entities_convertor.py` — *`validators.py` already vendored* |

**Total to copy: ~85 files.**

---

## 3. Files to DELIBERATELY SKIP

| Skipped | Files | Reason |
|---|---:|---|
| `llm_utils/` + `lm_recognizer.py` | 7 | LLM recognizers; need `langextract` + Azure credentials |
| `predefined_recognizers/third_party/` | 6 | Azure cloud services; need subscription keys |
| `predefined_recognizers/ner/` | 4 | GLiNER / HuggingFace / MedicalNER — need `transformers`+`torch`. **Candidate for a later phase** |
| `chunkers/` | 5 | only used by the `ner/` recognizers above |
| `analyzer_engine_provider.py`, `analyzer_request.py` | 2 | REST API layer, not needed for a library |
| `country_specific/` non-US | 66 | i2b2 is US clinical data |

---

## 4. Files WE WRITE (7)

| File | Purpose |
|---|---|
| `presidio_analyzer/__init__.py` | trimmed export list — excludes `lm_recognizer` / `analyzer_engine_provider` so LLM deps aren't required |
| `presidio_analyzer/predefined_recognizers/__init__.py` | trimmed — generic + nlp_engine_recognizers + US only |
| `i2b2_loader.py` | i2b2 XML → our JSON format. Adapted from Microsoft's `i2b2_formatter.py`, rewritten standalone so it doesn't drag in the whole `presidio_evaluator` package |
| `i2b2_entity_mapping.py` | i2b2 PHI taxonomy → Presidio entity names (see §5) |
| `build_analyzer.py` | constructs `AnalyzerEngine` in Python (spaCy engine + registry + enhancer) |
| `evaluate_i2b2.py` | scoring harness — same TP/FP/FN logic as `evaluate.py` |
| `compare_architectures.py` | regex-only vs full, on identical records |

---

## 5. The i2b2 entity mapping problem

i2b2 uses its own PHI taxonomy. It must be mapped onto Presidio's entity
names before anything can be scored. **This is the main hidden work item.**

| i2b2 TYPE | Presidio entity | Covered by |
|---|---|---|
| `PATIENT`, `DOCTOR`, `USERNAME` | `PERSON` | SpacyRecognizer ✔ |
| `HOSPITAL`, `ORGANIZATION` | `ORGANIZATION` | SpacyRecognizer ✔ |
| `CITY`, `STATE`, `COUNTRY`, `STREET`, `LOCATION-OTHER` | `LOCATION` | SpacyRecognizer ✔ |
| `DATE` | `DATE_TIME` | SpacyRecognizer + DateRecognizer ✔ |
| `PHONE`, `FAX` | `PHONE_NUMBER` | PhoneRecognizer ✔ |
| `EMAIL` | `EMAIL_ADDRESS` | EmailRecognizer ✔ |
| `URL` | `URL` | UrlRecognizer ✔ |
| `IPADDRESS` | `IP_ADDRESS` | IpRecognizer ✔ |
| `SSN` | `US_SSN` | UsSsnRecognizer ✔ (new) |
| `ZIP` | — | ✘ no recognizer — custom regex needed |
| `AGE` | `AGE` | ✘ mapping exists, but spaCy emits no AGE label |
| `PROFESSION` | — | ✘ nothing in Presidio |
| `MEDICALRECORD`, `HEALTHPLAN`, `ACCOUNT`, `LICENSE`, `VEHICLE`, `DEVICE`, `BIOID`, `IDNUM` | — | ✘ custom recognizers needed |

**Notable discovery:** Presidio's `MODEL_TO_PRESIDIO_ENTITY_MAPPING` already
contains `PATIENT`, `STAFF`, `HCW`, `HOSP`, `PATORG` → PERSON/ORGANIZATION.
Those are labels produced by **clinical** NER models, not spaCy's generic
one. Presidio anticipates clinical de-identification models being plugged in
— relevant if we later add a model like `obi/deid_roberta_i2b2`.

---

## 6. Phases

### Track A — full architecture on Presidio's dataset (start now)

| Phase | Work | Deliverable |
|---|---|---|
| **1** | Verify spaCy installs; vendor analyzer core + `nlp_engine/` + `context_aware_enhancers/` | `AnalyzerEngine` imports and runs with `NoOpNlpEngine` |
| **2** | Vendor `recognizer_registry/` + `input_validation/` + `SpacyRecognizer`; wire spaCy engine | `PERSON`/`LOCATION`/`ORGANIZATION` start appearing in output |
| **3** | Vendor US country recognizers + full anonymizer (all 7 operators + factory) | `US_SSN`, `US_DRIVER_LICENSE` reachable; `encrypt`/`decrypt` work |
| **4** | Write `entity_mapping.py` — dataset labels ↔ Presidio labels (see §5.1) | `GPE`→`LOCATION`, `DOMAIN_NAME`→`URL` scored correctly |
| **5** | `evaluate_full.py` — scored run over all 1,500 records | precision/recall table per entity type |
| **6** | `compare_architectures.py` — regex-only vs full, identical records | **the headline result** |

### Track B — i2b2 (once access lands)

| Phase | Work |
|---|---|
| **7** | `i2b2_loader.py` — XML → our JSON format |
| **8** | `i2b2_entity_mapping.py` — i2b2 taxonomy → Presidio (see §5) |
| **9** | `evaluate_i2b2.py` — scored run on clinical text |
| **10** *(optional)* | Add `ner/` recognizers + a clinical model (e.g. `obi/deid_roberta_i2b2`) |

Track A requires nothing we don't already have.

---

## 6.1 Expected gain on `synth_dataset_v2.json`

This is what the full architecture should unlock on the dataset we already
have. Current regex-only reach is **431 of 2,863 spans (15%)**.

| Dataset label | Spans | Regex-only | Full architecture | Via |
|---|---:|:---:|:---:|---|
| `PERSON` | 857 | ✘ | **✔** | SpacyRecognizer |
| `GPE` | 411 | ✘ | **✔** | SpacyRecognizer → `LOCATION` (needs mapping) |
| `ORGANIZATION` | 250 | ✘ | **✔** | SpacyRecognizer |
| `NRP` | 55 | ✘ | **✔** | SpacyRecognizer (spaCy `NORP`) |
| `US_SSN` | 16 | ✘ | **✔** | UsSsnRecognizer + context enhancer |
| `US_DRIVER_LICENSE` | 5 | ✘ | **✔** | UsLicenseRecognizer + context enhancer |
| `CREDIT_CARD`, `DATE_TIME`, `EMAIL_ADDRESS`, `IBAN_CODE`, `IP_ADDRESS`, `PHONE_NUMBER` | 431 | ✔ | ✔ | unchanged |
| `STREET_ADDRESS` | 598 | ✘ | ~partial | spaCy may tag fragments as `LOC`/`FAC` |
| `TITLE` | 92 | ✘ | ✘ | no Presidio entity |
| `AGE` | 74 | ✘ | ✘ | mapping exists but spaCy emits no `AGE` label |
| `ZIP_CODE` | 37 | ✘ | ✘ | no US ZIP recognizer in Presidio |
| `DOMAIN_NAME` | 37 | ~ | ~ | `URL` recognizer fires, label differs |

**Projected reach: 431 → ~2,025 spans (15% → ~71%)**, with `STREET_ADDRESS`
(598) the largest remaining gap. That jump *is* the result to present.

Note this is a projection of what becomes *reachable*, not a recall
prediction — spaCy will miss some `PERSON`s and invent others. Measuring the
real number is Phase 5's job.

---

## 5.1 Entity-name mapping for `synth_dataset_v2.json`

Even on Presidio's own dataset, label names don't all line up with what
Presidio's recognizers emit. A mapping layer is required before scoring:

| Dataset says | Presidio emits | Action |
|---|---|---|
| `GPE` | `LOCATION` | map |
| `STREET_ADDRESS` | `LOCATION` | map (partial credit) |
| `DOMAIN_NAME` | `URL` | map |
| `PERSON`, `ORGANIZATION`, `NRP`, `DATE_TIME`, `CREDIT_CARD`, `EMAIL_ADDRESS`, `IBAN_CODE`, `IP_ADDRESS`, `PHONE_NUMBER`, `US_SSN`, `US_DRIVER_LICENSE` | same | none |
| `TITLE`, `AGE`, `ZIP_CODE` | — | out of scope, report separately |

Our current `evaluate.py` compares labels with `==`, which would score every
`GPE` as a miss even when `LOCATION` was correctly found. Fixing this is
Phase 4 and it materially changes the numbers.

---

## 7. Dependencies

| | Now | After |
|---|---|---|
| pip | `regex`, `tldextract`, `phonenumbers` | + `spacy`, `numpy`, `pyyaml`, `pydantic`, `cryptography`, `xmltodict` |
| model | none | `en_core_web_sm` (13 MB) or `en_core_web_lg` (560 MB) |
| disk | ~1 MB | ~600 MB with `lg` |

`cryptography` is only for the `encrypt`/`decrypt` operators.
`xmltodict` is for the i2b2 XML parser (Microsoft's formatter uses it with
`strip_whitespace=False`, which matters because i2b2 annotations are
character-offset based).

---

## 8. Expectations to set before the mentor sees results

spaCy's `en_core_web_*` models are trained on **news and web text**
(OntoNotes). Clinical notes are a different domain: abbreviations, section
headers, telegraphic style, names in unusual positions. Published work
consistently shows generic NER underperforming on clinical de-identification
relative to models fine-tuned on i2b2 itself.

**Predict this now:** expect solid `DATE`/`CONTACT` scores (regex-backed),
moderate `PERSON`, and weaker `LOCATION`/`ORGANIZATION`. That domain-shift
gap is a legitimate finding and is exactly the argument for Phase 7.
