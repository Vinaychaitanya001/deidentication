# Decisions

Each entry: decision, why, status. Sources: team plan (28 Sep 2026), Phase-1 instruction
(29 Sep 2026), and verification runs. Open questions at the bottom need the team's answer
before any design change.

## D1 — Evidence-based L0–L7 architecture
Detectors propose candidates with evidence; one decision layer (L4) decides; L5 makes the span
set consistent; policy (L6) transforms; L7 assures. Four invariant rules in ARCHITECTURE.md.
**Why:** the stock Presidio pipeline has no fusion, positive-only context, no structure or memory,
and scores on incomparable scales (plan §1.4). **Status:** agreed (plan §2).

## D2 — Canonical PHI ontology = i2b2-2014 categories
Codes are `CATEGORY.SUBTYPE` (e.g. `NAME.PATIENT`, `ID.MRN`); a bare category is used when a
detector cannot tell the subtype. Each type is mapped to HIPAA Safe Harbor; what to *do* with a
type is the policy profile's job. NRP (nationality/religion/politics) is not PHI.
**Why:** comparability with published clinical de-id work; HIPAA is a subset.
**Status:** implemented, `deid/ontology.py`.

## D3 — Presidio as a pinned dependency, vendored copy removed
`presidio-analyzer[transformers]==2.2.364`, `presidio-anonymizer==2.2.364`. The 196 vendored
files were deleted (they remain in git history at `8088a33`). `UuidRecognizer` is missing from
2.2.364 (added upstream later), so `compat/uuid_recognizer.py` keeps baseline B0 unchanged;
`build_analyzer.py` reads the installed `conf/default.yaml` (byte-identical to the vendored one).
**Why:** the vendored copy was already drifting from upstream. **Verified:** `test_cases.py` 29/29;
`compare_architectures.py` reproduces the committed `results/architecture_comparison.json` exactly.
**Status:** done in the working tree (not committed).

## D4 — Python ≥ 3.10 (local venv 3.12)
Presidio 2.2.364, transformers and torch require ≥ 3.10; the macOS system Python is 3.9.
Local `.venv` = Python 3.12.14 (installed with `uv`). **Status:** done.

## D5 — Clinical NER model `obi/deid_roberta_i2b2`
MIT licence; RoBERTa-large (~1.4 GB); labels AGE, DATE, EMAIL, HOSP, ID, LOC, OTHERPHI,
PATIENT, PATORG, PHONE, STAFF. Also Presidio 2.2.364's default `TransformersNlpEngine` model.
Mapped so PATIENT → `NAME_PATIENT` and STAFF → `NAME_CLINICIAN` stay separate
(`OBI_DEID_TO_PRESIDIO`). Rejected: `StanfordAIMI/stanford-deidentifier-base` (no AGE or LOC
labels), `obi/deid_bert_i2b2` (little use). It was trained on i2b2-2014; check its training
split before any i2b2 test evaluation. **Status:** downloaded; integration in `deid/engine.py`.

## D6 — Relabel BILOU → BIO after loading the NER model
The model emits B-/I-/L-/U- tags. Hugging Face's grouping names each group without its prefix
(so labels stay clean and nothing is dropped — an earlier hypothesis that Presidio drops U-/L-
entities was **wrong**), but an L- or U- token starts a new group, so multi-word entities come
out split. `ClinicalTransformersNlpEngine(relabel_bilou=True)` rewrites U-→B-, L-→I-.
**Measured (clinical dev, 29 Sep, with Presidio's default "max" aggregation):** gold coverage by
kept NER entities is identical with or without the relabel (398/606); the relabel only reduces
fragments (e.g. 149 → 90 patient-name pieces). B2 final spans are identical either way because
Presidio's anonymizer already merges same-type spans separated by spaces. Kept on (cleaner
candidates for P1); ablation system `B2-nobio`. **Re-measured under D16 ("simple" aggregation,
clinical dev):** B2 − B2-nobio strict F2 +0.8 [0.0, +1.8], char leak −0.3 [−0.7, −0.1] points,
zero-leak documents 88.3% vs 81.7%; kept on. **Status:** implemented and verified, `deid/engine.py`.

## D7 — Evaluation v2 definitions
One scorer for every system and dataset, applied to the final resolved spans a system would
redact (B0: its regex resolver; B1/B2: Presidio's anonymizer conflict resolution; P1: L5 output).
Types compared at category level. Every gold PHI span counts in denominators. Don't-care regions
(excluded from recall and precision): honorific TITLEs and NRP in `synth_dataset_v2`; clock times
and room numbers in the synthetic clinical set. Redactions of non-PHI types still count as false
positives. Bootstrap 95% CIs resample documents; paired differences resample the same documents.
**Status:** implemented, `evaluation/scorer.py`; exercised on B0/B1 (unit tests pending).

## D8 — `synth_dataset_v2` label mapping
PERSON → NAME; GPE → LOCATION; STREET_ADDRESS → LOCATION.STREET; ZIP_CODE → LOCATION.ZIP;
CREDIT_CARD, IBAN → ID.ACCOUNT; DOMAIN_NAME → CONTACT.URL; TITLE: honorifics ignored, job titles
→ PROFESSION; NRP ignored. **Status:** implemented, `deid/ontology.py`.

## D9 — Synthetic clinical dataset and interim guideline
10 note types; dev 60 notes / test 40 notes with disjoint name/place pools and different phrasing
and field labels; fictional values (555-01xx phones, example.com). Interim annotation choices:
names without titles or credentials; every age annotated (number only); years annotated as DATE;
street, city, state and ZIP separate; state annotated (Safe Harbor may keep it); clinician names
annotated; clock times and room numbers are don't-care; departments not annotated. Look-alikes
annotated separately (blood_pressure, scale, dose, fraction_dose, duration, frequency,
measurement, eponym, code). **Limitations:** the same team wrote templates and rules, so rule-based
scores are optimistic; notes are short (~70 words). Guideline choices are interim until the team's
meeting-1 decisions (plan §6). **Status:** implemented, `data/synthetic_clinical/`.

## D10 — Baselines preserved; artifacts shared
B0 and B1 are run unchanged through adapters (`evaluation/systems.py`); B2 is the NER ablation.
Systems on the same NLP engine reuse one `NlpArtifacts` per text, so the transformer runs once
per document for B2 and the P1 variants. **Status:** implemented and run for B0, B1, B2, B2-max,
P1, P1-noveto, P1-spacy (`results/v2/`).

## D11 — NPI, MBI and member IDs
NPI and MBI recognizers exist in 2.2.364 but are disabled in Presidio's default YAML; P1 enables
them explicitly. Presidio's member-ID recognizer is not in 2.2.364, so member/insurance IDs come
from field keys (`ID.HEALTHPLAN`). **Status:** implemented, `deid/engine.py`
(`build_clinical_analyzer`), `deid/langpack_en.py` (field keys).

## D12 — Phase-1 decision layer is rule-based
Per-entity minimum scores (gating the weak driver-licence and bank patterns) and hard-negative
vetoes, behind a `Decider` interface that the calibrated fusion model (P2.2) will implement.
No calibration in Phase 1; scores are raw detector scores. Gates: `US_DRIVER_LICENSE` and
`US_BANK_NUMBER` need ≥ 0.4, i.e. a whole-word context word (Presidio's weak patterns score 0.01–0.3
and 0.05); every other entity keeps Presidio's default threshold 0.0. NRP is rejected as not PHI.
**Status:** implemented, `deid/decision.py`; tests in `tests/test_decision_consistency.py`.

## D14 — Phase-1 L5 overlap rule: priority winner keeps its boundaries, others are trimmed
When accepted candidates overlap, the highest-priority one keeps its exact span; lower-priority
overlapping candidates keep only the parts not already covered (dropped if no alphanumeric
character remains). Priority: field-key detector > other clinical-pack and validator detectors >
NER and generic patterns; ties → longer span, then higher score. **Why:** union merging glued
hospitals to the next line's street number and names to punctuation in the P1.4 error analysis;
winner-takes-all would drop characters only the losing span covered. This keeps every covered
character (privacy) with clean boundaries. Same-category detectors that agree are recorded as extra
`sources` of the winning span. Known cost: a loser's leftover can be a non-PHI fragment (e.g.
spaCy tags "27-year-old" as DATE, the AgeDetector wins "27", "year-old" stays as a DATE span).
**Status:** implemented, `deid/consistency.py`; within ARCHITECTURE's L5 "resolve overlaps",
pending confirmation of Q2.

## D15 — Candidate boundary cleanup at the L3 → L4 boundary
Edges of every candidate are trimmed of whitespace and separator punctuation (`,;:` and a
sentence-final `.` that is not part of an abbreviation or initial; brackets only when unbalanced).
**Why:** the clinical NER returned spans such as `'Venkata Rao,'`, `'55916\n'`, `'2/1/24.'`
(P1.4 error analysis), which break exact-boundary matching without changing which characters are
PHI. B2 stays stock (no trimming). **Status:** implemented, `deid/spans.py`,
`deid/pipeline.py` (`presidio_candidates`).

## D16 — NER label grouping: "simple" aggregation + word continuation (corrects P1.4 findings)
`build_clinical_nlp_engine` uses Hugging Face `aggregation_strategy="simple"` instead of Presidio's
default `"max"`, and a B- tag on a sub-word piece glued to a same-type piece continues the entity.
**Why (verified on raw model output, 29 Sep):** for byte-level BPE models Hugging Face guesses word
boundaries from spaces only, so `"2024."`, `"Consultation\nAugust"` and `"27-year-old"` each count
as one word, and "max" gives the whole word the label of its highest-scoring piece — often O. The
model itself tags "July 31, 2024" and ages correctly. With "simple", a B- on a sub-word piece
("Ġ3" B-LOC, "102" B-LOC) made spacy-huggingface-pipelines expand the first piece to the whole
token and then skip the rest of the entity as "overlapping" ("3102 Oak Avenue" → "3102").
**Correction:** the P1.4 findings "the model never tags ages" and "the model truncates long-form
dates" were artifacts of this aggregation setting, not model errors. **Measured (clinical dev,
bootstrap off):** gold spans inside one NER entity 326 → 574 of 606; B2 strict F2 52.8 → 91.1,
char leak 17.3% → 1.1%, AGE recall 0 → 100%. Both fixes are in the shared engine, so B2 and P1 use
them; `B2-max` keeps the P1.4 configuration as an ablation. **Status:** implemented,
`deid/engine.py`; within P1.4 (NER integration), no architecture change.

## D17 — P1 reads every recognizer result (no Presidio de-duplication in L3)
`CandidateAnalyzer.candidates()` runs Presidio's recognizers and context enhancement but skips
`AnalyzerEngine.analyze`'s `remove_duplicates`, which drops a result contained in a
higher-scoring result of the same entity type. **Why:** that is an overlap decision inside L3,
which ARCHITECTURE invariant rule 2 reserves for L4–L5. In the demo note it removed the field-key
DOB candidate (and its DOB evidence) and the AgeDetector match behind identical NER spans; it can
also drop a clean pattern span that lies inside a longer, higher-scoring NER span of the same type.
Identical proposals by the same detector are merged. `analyze()` stays stock for B1/B2.
**Measured (clinical dev):** no metric changes (P1 with vs without Presidio's de-duplication:
identical scores); the benefit is provenance (all sources and evidence reach L4–L5) and
conformance with the invariant, not accuracy. **Status:** implemented, `deid/engine.py`,
`deid/pipeline.py`; test `tests/test_pipeline.py::test_candidates_keep_what_presidio_analyze_would_deduplicate`.

## D18 — Hard-negative veto semantics (P1.6)
A rule marks a region (value plus cue, e.g. "BP 132/84"). A candidate is vetoed only when it lies
**entirely inside** one region and its type is vetoable for that kind: DATE, AGE, ID, CONTACT,
LOCATION.ZIP, OTHER; durations and frequencies never veto AGE. Field-key values are never vetoed;
names are never vetoed. When several regions cover a candidate the most specific kind is reported
(blood pressure > scale > fraction > dose > duration > frequency). Kinds: blood pressure, scales
(cue before/after x/y with x ≤ y ≤ 10, visual acuity, GCS/Apgar and named scores), fractions of a
dose (proper fractions), doses (number + unit, combinations, per-kg rates, dispense/refills),
durations, frequencies. **Why:** containment never cuts a real PHI span partially (recall
first); P1.6 done-when requires no recall loss on dev (see CURRENT_STATE for P1 vs P1-noveto).
**Status:** implemented, `deid/hard_negatives.py`; tests in `tests/test_hard_negatives.py`.

## D19 — Safe Harbor transformation details (P1.7)
Pseudonym `[LABEL-xxxxxx]` = first 6 hex digits of HMAC-SHA256(key, category | normalized value);
names are normalized to sorted lower-case tokens ("OKAFOR, LAKSHMI" = "Lakshmi Okafor"), IDs to
their letters and digits. One date offset per document: 1–365 days back from
HMAC(key, "date-shift" | document id) (Q1), rendered in the original format; year-only dates
kept; unparseable dates → `[DATE]`. Ages ≥ 90 → "90+"; the birth date (DOB field evidence or L1
DOB field) → `[DOB 90+]` when any age ≥ 90 is detected or a DOB lies ≥ 90 years before another date
in the note (a relative's age also triggers it: the safe direction). ZIP → first three digits +
"**", or "000**" for the 17 restricted ZIP3 areas of the HHS guidance (2000 Census list; should be
checked against current Census data before real use). States kept. Key from `DEID_HMAC_KEY`;
without it a demo key is used and the manifest says so. The manifest records positions, types,
actions, sources and replacement codes, never original values (replacements that keep part of the
value — year, age < 90, state, ZIP3 — are omitted). **Status:** implemented, `deid/transform.py`,
`deid/assurance.py`; tests in `tests/test_transform.py`. Surrogates are P2.8.

## D13 — Legacy documents kept
Root `ARCHITECTURE.md`, `RESULTS.md`, `SYSTEM_OVERVIEW.md`, `TEST_REPORT.md`,
`PRESENTATION_GUIDE.md`, `IMPLEMENTATION_PLAN.md` stay unchanged as the historical record of the
regex/stock-Presidio phase (their file paths point into the removed vendored copy, available in
git history). `VENDORED_FILES.md` carries a status note on top. **Status:** done.

## Open questions (conflicts or uncertainty — confirm before any design change)

| # | Conflict / uncertainty | Interim choice (no design change) |
|---|---|---|
| Q1 | Date-shift key: plan P1.7 / L6 say one offset **per patient**; the 29 Sep instruction says **per document**. | Per document (offset from HMAC(key, document id)). Should it be keyed by patient ID when one is available? |
| Q2 | P2.1 ("Candidate contracts + grouping; one place resolves overlaps") is Phase 2, but P1.1 must score final resolved spans and the instruction asks for clean Phase-2 interfaces. | Phase 1 adds the contracts as interfaces and a deterministic overlap resolver in L5 (where the architecture puts it); grouping-as-features for fusion stays P2.1/P2.2. |
| Q3 | P1.5 uses field keys for MRN/account/accession; P2.3 is "sections + key:value fields as detectors and features". | Phase 1 implements only the field-key patterns the P1.5 detector needs (IDs, name fields, DOB); sectionizer and fields-as-features stay P2.3. |
| Q4 | P1.6 includes frequencies; the 29 Sep list omits them. The dataset also has measurement (vitals/labs), eponym and code look-alikes that neither list covers. | Implement P1.6 as written (incl. frequencies). No measurement or code vetoes, no eponym handling (P2.6); their false-alarm rates are reported, not fixed. Add rule-based measurement vetoes in Phase 1? |
| Q5 | ZIP3 rule is in P1.7 but not in the 29 Sep list. | Implement it (part of the agreed Phase 1). |
| Q6 | CI is part of P1.3, not in the 29 Sep list, and cannot be verified without pushing. | Not added yet; tracked as a Phase-1 gap. |
| Q7 | P1.4 compares against spaCy sm/lg; only `en_core_web_sm` (baseline B1) is installed. | Compare against sm; lg (~560 MB) optional. |
| Q8 | ~~P1.4 found the clinical NER truncates long-form dates; add a date grammar?~~ **Resolved by D16:** the truncation was an aggregation artifact; with D16 every long-form date on dev is found with exact boundaries. A date grammar (plan §3.2) remains a later option, not needed for this failure. | — |
| Q9 | The clinical NER tags ICD/CPT codes as IDs ("CPT 88305": all code look-alikes on dev). Code vetoes are in neither list (see Q4). | Reported, not fixed. |
| Q10 | L6 pseudonyms are consistent per exact value (up to case/order), but a surname-only mention gets a different code from the full name ("HALVORSEN, MARGIT" vs "Halvorsen"). Name-variant linking is P2.4 (propagation). | Phase 1 leaves it; reported as a known issue. |
| Q11 | P1's L5 (D14) does not merge same-type fragments separated only by a space; Presidio's anonymizer does, so on synth_v2 P1's NAME strict recall is 78.1% vs B2's 80.2% (found in the final run, not tuned). | Not changed after seeing synth_v2/test results. Add Presidio's merge rule to L5 (then re-measure on dev first)? |
