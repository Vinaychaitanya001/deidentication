# Architecture (agreed, 28 Sep 2026)

This is **our** target architecture and how Phase 1 realises it. It was agreed in the team plan
(`PHI_Deidentification_Architecture_and_Plan.pdf`, §2–§3, §5–§7). Do not replace or simplify it;
changes need a DECISIONS.md entry and team approval. For how Presidio itself works internally,
see `/ARCHITECTURE.md` at the repo root. What exists in code today is tracked in CURRENT_STATE.md.

## Principles

1. Recall first; precision is managed per type with explicit recall targets. A miss is a privacy breach.
2. Detectors emit **evidence**; one decision layer decides. Detectors never change text.
3. One canonical PHI ontology (`deid/ontology.py`), independent of any model's labels.
4. Language is data (language packs), not code; every span refers to original-text offsets.
5. Clinical structure and consistency across mentions are first-class.
6. Local-first privacy: remote components are opt-in and gated by policy.
7. Every component can be ablated and measured with the same scorer.

**Four invariant rules**
1. Detectors propose; they never change the text.
2. Only L4–L5 decide what is PHI and resolve overlaps.
3. Every span points into the original text (via the OffsetMap once normalization exists).
4. Policy is configuration, not code.

## Pipeline

```
Control plane (config): PHI ontology · policy profiles · detector registry · language packs · key vault
                                   │ read by every stage
raw note → L0 → L1 → L2 → L3 → L4 ⇄ (optional local LLM) → L5 → L6 → L7 → output + span manifest + audit log
                                   ▲                        │ human review of high-risk notes
                                   └──── corrections retrain detectors (L3) and recalibrate fusion (L4)
One shared Document object flows through all stages; each stage adds a stand-off layer.
```

| Stage | Target responsibility | Phase-1 scope | Later |
|---|---|---|---|
| **L0** Ingest & normalize | Unicode NFC, whitespace/digit normalization, OffsetMap back to original text, script + language ID per segment | Identity pass-through: English, spans on the original text | OffsetMap, per-segment language ID (P2.9) |
| **L1** Clinical structure | Sectionizer, key:value fields (MRN:, DOB:, Attending:), header/signature/cc blocks; used as detectors **and** features | Only the key:value field patterns the P1.5 field-key detector needs (IDs, patient/clinician name fields, DOB) | Sectionizer + fields as fusion features (P2.3) |
| **L2** Language pack | Tokenizer, sentences, cue words (+ and −), abbreviations, gazetteers per language | English only: spaCy `en_core_web_sm` tokens/lemmas inside the Presidio NLP engine; English cue lists and hospital gazetteer | Pack loader + routing (P2.9), Telugu pack (P3.3) |
| **L3** Candidate generation | Six detector families (below), run in parallel, emit Candidates with evidence | Presidio predefined recognizers (en + US, NPI and MBI enabled) + clinical detector pack (P1.5) + clinical de-id NER (P1.4) | Numeric-mention classifier (P2.5), concept NER (P2.6), GLiNER (max-recall profile), fine-tuned model (P2.7) |
| **L4** Evidence fusion & decision | Group spans → features → calibrated meta-classifier → P(PHI), P(type) → per-type thresholds from recall targets; uncertain band → optional local LLM, else recall-first default (PHI + review flag) | Rule-based decider behind the same interface: canonical mapping, per-entity minimum scores (gates weak patterns), hard-negative vetoes (P1.6). No calibration, no LLM | Calibrated fusion (P2.2), LLM adjudication (P3.2), conformal thresholds (P3.1) |
| **L5** Consistency | Entity memory; propagate to repeats and name variants; resolve overlaps into one non-overlapping span set | Deterministic overlap resolution only | Propagation / entity memory (P2.4) |
| **L6** Transformation | Operators: tag, HMAC pseudonym, surrogate, date shift, age bucket, ZIP3, keep; profiles: Safe Harbor, Limited Data Set, research, DPDP; keys in a vault | Safe Harbor profile: HMAC pseudonyms, date shifting, age ≥ 90 → "90+" (birth date removed for patients aged 90+, plan §4.6), ZIP3 rule, keep state; span manifest (P1.7) | Surrogates (P2.8), other profiles |
| **L7** Assurance | Leak scan of the output (independent detector, surrogates excluded), risk score, human review queue, corrections → training | Span manifest with positions, types, actions and sources — never original values | Leak scan + review queue (P2.8), privacy evaluation (P3.4) |

### L3 detector families

| # | Family | Proposes | Phase |
|---|---|---|---|
| 1 | Structured IDs + validators | phone, fax, email, URL, IP, SSN, NPI, ZIP; MRN/account/accession via field keys | 1 |
| 2 | Numeric-mention classifier | kind of every number-like span (date/age/ID/dose/lab…) | 2 (P2.5) |
| 3 | Gazetteers + deny lists | names, cities, hospitals, known staff | 1 (hospital list only) |
| 4 | Clinical de-id NER | patient/clinician names, hospitals, places, dates, ages, IDs | 1 (`obi/deid_roberta_i2b2`) |
| 5 | Zero-shot NER (GLiNER) | rare types: profession, device and other IDs | later (max-recall profile) |
| 6 | Clinical concept NER | diseases, drugs, procedures — evidence **against** PHI | 2 (P2.6) |

Phase-1 clinical detector pack (P1.5): AGE (with over-89 flag), US ZIP (state/ZIP-key context),
field-key IDs (MRN, account, accession/other, health-plan/member ID, device, licence) and name
fields, fax and pager numbers, clinician cues ("Dr.", credentials such as ", MD"), hospital name
patterns + gazetteer. Presidio's weak driver-licence and bank-number patterns are gated in L4;
context words match whole words only. In Phase 1 every recognizer result reaches L4 as a
candidate: Presidio's own same-type de-duplication is skipped, so that only L4–L5 resolve
overlaps (invariant rule 2; DECISIONS D17).

## Data contracts

Agreed contracts (plan §3.9):

```
Candidate(start, end, type_hint, source, raw_score, evidence)   # emitted by every detector
Decision(start, end, p_phi, type_dist, action, provenance)      # written only by L4/L5
```

Phase 1 fills these without calibration: the decision carries the supporting candidates' raw
scores and a rule outcome (accepted / rejected + reason); `p_phi` as a calibrated probability
arrives with P2.2. Types are canonical ontology codes (`CATEGORY.SUBTYPE`, e.g. `NAME.PATIENT`;
a bare category when a detector cannot tell the subtype). Interfaces for the Phase-2 components
(`Decider` for fusion, a consistency step for propagation) keep the same inputs and outputs.
In code (`deid/contracts.py`, Phase 1): `Candidate` (L3), `Decision` (L4: one rule outcome per
candidate, accepted or rejected with a reason), `FinalSpan` (L5: type, raw score of the winning
candidate, all agreeing sources, evidence), carried on one `Document` with its L1 `fields`.

## Control plane

- **PHI ontology** — `deid/ontology.py`: i2b2-2014 categories (superset of HIPAA Safe Harbor) with
  HIPAA mapping and label maps for Presidio, the clinical NER model and `synth_dataset_v2`.
- **Policy profiles** — what L6 does per type. Phase 1: HIPAA Safe Harbor only.
- **Detector registry** — Phase 1 uses Presidio's `RecognizerRegistry`.
- **Language packs** — Phase 1: English module only.
- **Key vault** — Phase 1: HMAC key from an environment variable; never committed.

## Evaluation architecture (Evaluation v2)

One scorer (`evaluation/scorer.py`) for every system and dataset, applied to the **final resolved
spans** each system would redact. Metrics: entity strict / exact / partial (binary and typed at
category level), token binary/typed, character leak rate, zero-leak document rate, P/R/F1/F2,
hard-negative redaction rate, bootstrap 95% CIs, paired differences. Datasets: synthetic clinical
dev/test (`data/synthetic_clinical/`), `synth_dataset_v2.json`; i2b2/n2c2 and MIMIC when access
is granted.

| System | Definition |
|---|---|
| B0 | Regex-only baseline (`regex_engine.py`) with its own overlap resolution |
| B1 | Current full Presidio baseline (`build_analyzer.py`: spaCy `en_core_web_sm`, ORGANIZATION ignored, en + US), Presidio anonymizer conflict resolution |
| B2 | B1 with the NER swapped for the clinical de-id model (NER ablation) |
| P1 | Phase-1 clinical pipeline; ablations P1-noveto (no hard-negative vetoes) and P1-spacy (spaCy NER) |

## Execution profiles (plan §3.9)

| Profile | What runs | Hardware |
|---|---|---|
| Edge / fast | validators, numeric classifier, gazetteers, structure rules, small distilled NER (ONNX int8) | CPU |
| Standard | + base-size clinical de-id transformer, concept NER, fusion, propagation | CPU or small GPU |
| Max-recall | + GLiNER, local LLM on uncertain spans, second leak-scan pass | GPU |

Phase 1 runs a single configuration: CPU, `obi/deid_roberta_i2b2` (RoBERTa-large) plus rules.

## Multilingual extension points (Telugu later)

Language-independent (build once): Document model and OffsetMap, orchestration, registry,
structured-ID validators (phone, Aadhaar/Verhoeff, PAN, ABHA, PIN, UHID), fusion framework,
propagation algorithm, transformation engine and policies, character-level evaluation.
Language-specific (one pack per language): normalization rules, tokenizer, cue and unit words,
fusion weights, name-variant rules, gazetteers, NER model, surrogate generators.
Decisions already taken for this: character offsets everywhere, segment-level routing,
detectors declare languages, cues reach the decision only as evidence, policy per jurisdiction.
