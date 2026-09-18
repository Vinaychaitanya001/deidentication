# Results — Regex-Only vs Full Presidio Architecture

Both architectures run over the **same 1,500 records** from
`data/synth_dataset_v2.json` (Microsoft's own evaluation set from
`presidio-research`), scored by the **same code** (`scoring.py`).
The only variable that changes is the architecture.

Reproduce:
```powershell
python compare_architectures.py          # the headline table
python evaluate_full.py                  # full architecture in detail
python evaluate_full.py --org            # with ORGANIZATION enabled
```

---

## 1. Headline

| Metric | Regex-only | Full architecture | Change |
|---|---:|---:|---:|
| **PII spans found** | 327 | **1,276** | **+949 (3.9×)** |
| PII spans missed | 2,333 | 1,384 | −949 |
| Labeled spans in reach | 2,660 | 2,660 | — |
| **Recall** | 0.12 | **0.48** | **+0.36** |
| **Precision** | **0.83** | 0.52 | **−0.30** |
| **F1** | 0.21 | **0.50** | **+0.29** |

**One sentence:** adding the NLP layer nearly quadruples how much PII is
found, and costs about a third of the precision.

> **Note on the 0.12.** Earlier regex-only reports quoted recall of 0.67.
> Both numbers are correct — different denominators. 0.67 was measured over
> only the 431 spans regex could *reach*; 0.12 is over all 2,660 spans
> reachable by *either* architecture. The second is the fair basis for
> comparison, because "can't even attempt it" is a real failure mode.

---

## 2. Recall by entity type

| Dataset label | Spans | Regex-only | Full | What changed |
|---|---:|---:|---:|---|
| PERSON | 857 | 0.00 | **0.64** | unlocked by NER |
| STREET_ADDRESS | 598 | 0.00 | **0.14** | unlocked by NER (weakly) |
| GPE (cities/countries) | 411 | 0.00 | **0.45** | unlocked by NER |
| ORGANIZATION | 250 | 0.00 | 0.00 | *ignored by Presidio default* |
| CREDIT_CARD | 136 | 0.77 | 0.77 | unchanged (checksum-bound) |
| DATE_TIME | 119 | 0.40 | **1.00** | NER catches spelled-out dates |
| PHONE_NUMBER | 92 | 0.59 | 0.59 | unchanged |
| NRP | 55 | 0.00 | **0.66** | unlocked by NER |
| EMAIL_ADDRESS | 49 | 1.00 | 1.00 | already perfect |
| DOMAIN_NAME | 37 | 1.00 | 1.00 | already perfect |
| IBAN_CODE | 21 | 0.95 | **1.00** | slight gain |
| US_SSN | 16 | 0.00 | **1.00** | unlocked by country recognizer |
| IP_ADDRESS | 14 | 1.00 | 1.00 | already perfect |
| US_DRIVER_LICENSE | 5 | 0.00 | **0.80** | unlocked by country recognizer |

**203 spans remain unreachable by both** — `TITLE` (92), `AGE` (74),
`ZIP_CODE` (37). Presidio has no recognizer for any of them.

---

## 3. Precision by entity type (full architecture)

| Presidio label | Correct | Spurious | Precision |
|---|---:|---:|---:|
| CREDIT_CARD | 105 | 0 | **1.00** |
| EMAIL_ADDRESS | 49 | 0 | **1.00** |
| IBAN_CODE | 21 | 0 | **1.00** |
| US_SSN | 16 | 0 | **1.00** |
| IP_ADDRESS | 14 | 0 | **1.00** |
| LOCATION | 292 | 75 | 0.80 |
| PHONE_NUMBER | 54 | 20 | 0.73 |
| PERSON | 546 | 237 | 0.70 |
| NRP | 36 | 21 | 0.63 |
| URL | 37 | 49 | 0.43 |
| **DATE_TIME** | 123 | **666** | **0.16** |
| **US_DRIVER_LICENSE** | 4 | **117** | **0.03** |

**The checksum-backed types still hold precision 1.00.** Everything that
degraded is either statistical (NER) or a weak regex without a checksum.

### 3.1 Why DATE_TIME precision collapsed to 0.16

spaCy's `DATE` label is extremely liberal. Sampled false positives:

```
'6750'                  (a house number)
'20789', '62488'        (ZIP codes)
'4454794511390933'      (a credit card number)
'79 year old'           (an age)
'next week'             (relative time)
'a couple of months'    (relative time)
```

Several of these are arguably *correct detections of something the dataset
labels differently* — `20789` really is a ZIP code, `79 year old` really is
an age. A de-identification system flagging them is over-cautious, not
wrong. But measured against this ground truth they count as errors.

### 3.2 Why US_DRIVER_LICENSE precision is 0.03

Its weakest pattern is literally:

```python
Pattern("Driver License - Digits (very weak)", r"\b([0-9]{6,14}|[0-9]{16})\b", 0.01)
```

That matches **any 6-to-14 digit number**. It scores 0.01 precisely because
Presidio expects the `ContextAwareEnhancer` to rescue it only when words
like "license" appear nearby. On this dataset the context rarely appears, so
it fires on everything numeric. This is the clearest evidence for the
architectural finding in §5.

---

## 4. The ORGANIZATION experiment

Presidio's `conf/default.yaml` lists `ORGANIZATION` under `labels_to_ignore`
with the comment *"Has many false positives"*. We measured whether that
default is justified:

| Config | Recall | Precision | ORGANIZATION recall | ORGANIZATION precision |
|---|---:|---:|---:|---:|
| Default (ignored) | 0.48 | 0.50 | 0.00 | — |
| `--org` (enabled) | **0.53** | 0.45 | 0.49 | **0.22** |

Enabling it finds 123 more organizations but produces 418 spurious ones.
**Presidio's default is defensible** — and now demonstrated with numbers
rather than accepted on faith.

---

## 5. The architectural finding

Presidio has **three detection tiers**, and they behave very differently:

| Tier | Example | Precision | Needs a model? |
|---|---|---:|---|
| Regex + checksum | CREDIT_CARD, IBAN, US_SSN, IP | **1.00** | no |
| Regex + context | US_DRIVER_LICENSE, weak SSN patterns | **0.03** | **yes** — needs lemmas |
| NER | PERSON, LOCATION, ORGANIZATION | 0.63–0.80 | yes |

The middle tier is the interesting one. Its patterns are deliberately scored
at 0.01–0.05 because they are *designed* to be useless alone — they only
work once the `ContextAwareEnhancer` boosts them using lemmas from the NLP
engine.

**So "regex-only Presidio" has a hard ceiling that isn't about regex at
all.** Only the checksum-backed tier is genuinely self-sufficient. That is
exactly the tier that held precision 1.00 in both architectures, and it is
why the regex-only build could ship with 3 pip packages and zero model
weights.

---

## 6. Cost of the upgrade

| | Regex-only | Full architecture |
|---|---|---|
| pip packages | 3 | 8 |
| Model weights | **0 bytes** | 13 MB (`sm`) — 560 MB (`lg`) |
| Vendored files | 25 | **187** |
| Recognizers active | 10 | 17 (of 97 available) |
| Anonymizer operators | 4 | 10 (incl. reversible AES) |
| Runs on an edge device? | yes | only with the small model |

---

## 7. Honest limitations

1. **`en_core_web_sm` is the small model.** Presidio defaults to
   `en_core_web_lg` (560 MB). PERSON recall would likely improve with `lg`
   or a transformer. Not yet measured — run `--model en_core_web_lg`.
2. **Overlap-based matching.** A prediction counts as a hit if it overlaps a
   ground-truth span. Strict boundary matching would score lower.
3. **Synthetic data.** `synth_dataset_v2.json` is template-generated. Real
   prose would likely be harder for the NER tier.
4. **130 unmeasurable predictions.** `US_BANK_NUMBER` and similar are
   entity types this dataset never labels, so they are reported separately
   rather than counted as errors — we cannot tell if they were right.
