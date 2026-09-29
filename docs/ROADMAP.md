# Roadmap (agreed, 28 Sep 2026)

Source: team plan `PHI_Deidentification_Architecture_and_Plan.pdf` §8, refined by the Phase-1
instruction of 29 Sep 2026 (below). Weeks count from kickoff; if the term is shorter, shrink
Phase 3 first. Progress lives in CURRENT_STATE.md, not here.

Workstreams: **A** evaluation & data · **B** rules & structure · **C** models ·
**D** fusion & decision · **E** transformation & privacy · **F** platform & multilingual.

## Phase 1 — Foundations (weeks 1–4). Goal: measure honestly, strong clinical baseline.

| ID | WS | Task | Deliverable | Done when |
|---|---|---|---|---|
| P1.1 | A | Scorer v2 | strict, relaxed, token, character-leak metrics; binary + typed; F2; note zero-leak rate; bootstrap CIs | re-scores B0 and B1 on the synthetic set; scorer has unit tests |
| P1.2 | A | Data access + clinical dev set | n2c2 and PhysioNet requests; 50–100 synthetic notes with PHI and hard negatives; annotation guideline v1 | dev set and guideline in repo; access requests submitted |
| P1.3 | F | Project skeleton + CI | own package; Presidio pinned; adapters for its validators; pytest and CI; config profiles | CI green; a Presidio validator runs through the adapter |
| P1.4 | C | Clinical NER integration | clinical de-id transformer behind the NER detector; label map keeps PATIENT vs STAFF | compared with spaCy (sm/lg) on dev with scorer v2 |
| P1.5 | B | Clinical detector pack v1 | AGE (+90 flag), US ZIP, MRN/account/accession via field keys, fax/pager, clinician cues, hospital patterns + list; enable NPI and member ID; gate weak licence/bank patterns | ≥ 10 positive and ≥ 10 hard-negative tests per detector |
| P1.6 | B | Hard-negative rules | vetoes for fractions and scales, blood pressure, durations, frequencies, doses | hard-negative suite passes; no recall loss on dev |
| P1.7 | E | Transformation v1 | HMAC pseudonyms, date shift (plan: per patient; see DECISIONS Q1), 90+ bucketing, ZIP3 rule, span manifest | tests: same input → same pseudonym; date intervals preserved |
| P1.8 | A | Baseline report (M1) | B0, B1, B2 (and the Phase-1 system) on synthetic and clinical dev sets with scorer v2 | reviewed by team and mentor |

### Phase-1 instruction (29 Sep 2026) → plan tasks

| Instruction item | Plan task |
|---|---|
| 1 Evaluation v2 first (ontology, strict/exact/partial/token/char-leak, binary + typed, P/R/F1/F2, zero-leak docs, final resolved spans, every PHI type in the denominator, one scorer, bootstrap CIs) | P1.1 |
| 2 Synthetic clinical dev set (50–100 notes, hard negatives) | P1.2 |
| 3 Clinical de-id NER via Presidio `TransformersNlpEngine`, compared with spaCy, PATIENT/STAFF kept | P1.4 |
| 4 Clinical detector pack (incl. whole-word context matching) | P1.5 |
| 5 Hard-negative vetoes: fractions, scales, BP, durations, doses | P1.6 |
| 6 HMAC pseudonyms, per-document date shifting, age ≥ 90 → 90+, span manifest | P1.7 |
| 7 Pin Presidio, pytest for clinical hard negatives, preserve existing functionality | P1.3 |

The instruction also requires: keep baselines B0 and B1 and compare B0 vs B1 vs the Phase-1
system on the same datasets; no fabricated improvements; clean interfaces for Phase-2 parts;
target: a professor demonstration of Phase 1.

### Phase boundary — NOT allowed in Phase 1

Calibrated candidate/evidence fusion (P2.2) · numeric-mention ML classifier (P2.5) ·
UMLS/RxNorm concept suppression (P2.6) · document-level propagation (P2.4) ·
multilingual/Telugu scaffolding (P2.9, P3.3) · GLiNER · LLM adjudication (P3.2) ·
fine-tuning our own model and ONNX export (P2.7) · conformal methods (P3.1) ·
surrogates, leak scan, review queue (P2.8) · sectionizer (P2.3).
Phase 1 may add **interfaces** these will plug into, but no implementations.

## Phase 2 — Clinical system v1 (weeks 5–10). Goal: new architecture end to end, beating Phase 1.

| ID | WS | Task | Deliverable | Done when |
|---|---|---|---|---|
| P2.1 | D | Candidate contracts + grouping | every detector emits Candidates; one place resolves overlaps | end-to-end run on dev through the new contracts |
| P2.2 | D | Calibrated fusion v1 | LR / gradient boosting + isotonic calibration; per-type thresholds from recall targets | reliability diagram; beats max-score at matched recall on dev |
| P2.3 | B | Sections + key:value fields | sectionizer and field extractor as detectors and features | all dev headers parsed; section feature available to fusion |
| P2.4 | D | Propagation | entity memory, name variants, overlap resolution | repeated-mention recall before/after |
| P2.5 | C | Numeric-mention classifier | labels, features, small model; replaces weak numeric regexes | numeric false alarms down, no recall loss |
| P2.6 | C | Negative evidence | concept NER + UMLS/RxNorm lists with guards (a title such as "Dr." overrides) | eponym/drug false alarms down, no recall loss |
| P2.7 | C | Fine-tuned de-id model | i2b2 train + MIMIC-III surrogate-injected text; casing/noise augmentation; ONNX int8 | beats P1.4 model on dev; latency measured |
| P2.8 | E | Surrogates + leak scan + review | format-preserving, locale-aware surrogates; output leak scan; review queue | leak scan catches seeded leaks in tests |
| P2.9 | F | Multilingual scaffolding | OffsetMap, per-segment language ID, language-pack loader, Indian ID detectors | mixed Telugu–English sample runs end to end |
| P2.10 | A | Benchmarks + M3 report | latency/throughput per profile; full evaluation with ablations | M3 report reviewed |

## Phase 3 — Research extensions (weeks 11–16). A menu: R1 is the core.

| ID | WS | Task | Deliverable |
|---|---|---|---|
| P3.1 | D | Risk-controlled thresholds (R1) | conformal risk control on per-note miss rate; shift study i2b2-2014 → CEGS N-GRID |
| P3.2 | C | LLM adjudication cascade (R4) | local model on uncertain spans only; offsets verified; accuracy vs latency |
| P3.3 | F | Telugu pilot (R3) | guideline, synthetic + validated test set, te language pack, transfer experiment |
| P3.4 | E | Privacy evaluation | surrogate distinguishability; leak analysis |
| P3.5 | A | Final evaluation + write-up (M5) | final tables, ablations, demo, report |

## Milestones

| ID | When | Name | Evidence |
|---|---|---|---|
| M1 | end wk 4 | Honest baseline | scorer v2 numbers for B0/B1/B2; clinical detector pack v1 |
| M2 | end wk 7 | One decision point | whole pipeline on Candidate/Decision contracts (simple fusion) |
| M3 | end wk 10 | Clinical system v1 | fusion + structure + propagation + numeric classifier + surrogates, ablations, latency |
| M4 | end wk 14 | Research results | R1 (plus R3 or R4 if chosen) |
| M5 | end wk 16 | Final report & demo | write-up, slides, reproducible scripts, demo on synthetic notes |

## Risks

| Risk | Mitigation |
|---|---|
| Clinical data access delayed (n2c2 portal returned 403 / registration closed, Sept 2026 — see IMPLEMENTATION_PLAN.md §0) | synthetic dev set now; PhysioNet credentialing in parallel |
| DUAs forbid third-party services | local models only; check the DUA before moving data |
| Limited compute | CPU profile; distilled/ONNX models later; GPU only for fine-tuning |
| Model licence or test contamination | read model cards; never use a model trained on our test split |
| Phase-3 scope creep | R1 is the core; the rest is optional |
| Too little Telugu data | structured IDs + synthetic set first; report as a pilot |
