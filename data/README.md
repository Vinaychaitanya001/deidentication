# Evaluation data

`synth_dataset_v2.json` is downloaded, unmodified, from Microsoft's own
Presidio evaluation repository — **this is the actual dataset the Presidio
team uses to score their recognizers' accuracy**, not a dataset we built.

- **Source:** https://github.com/microsoft/presidio-research
- **File:** `data/synth_dataset_v2.json` on the `main` branch
- **License:** MIT (Copyright (c) Presidio contributors)
- **Format:** 1,500 synthetic sentences/paragraphs, each with:
  ```json
  {
    "full_text": "...",
    "masked": "... {{ENTITY_TYPE}} ...",
    "spans": [
      {"entity_type": "EMAIL_ADDRESS", "entity_value": "...", "start_position": 12, "end_position": 34}
    ],
    "template_id": 87,
    "metadata": null
  }
  ```
  Every span is ground truth: ("this exact character range in `full_text`
  is really this entity type"), generated from templates + Faker-style fake
  data by the Presidio team for their own accuracy benchmarking.

## Ground-truth entity types in this file, and what our regex-only build covers

| Entity type | Count in dataset | Covered by our regex-only recognizers? |
|---|---:|---|
| PERSON | 857 | No — needs NER |
| STREET_ADDRESS | 598 | No — needs NER |
| GPE (geo-political entity) | 411 | No — needs NER |
| ORGANIZATION | 250 | No — needs NER |
| CREDIT_CARD | 136 | **Yes** |
| DATE_TIME | 119 | **Yes** |
| TITLE | 92 | No — needs NER |
| PHONE_NUMBER | 92 | **Yes** |
| AGE | 74 | No — needs NER |
| NRP (nationality/religious/political) | 55 | No — needs NER |
| EMAIL_ADDRESS | 49 | **Yes** |
| ZIP_CODE | 37 | No (not vendored; regex-detectable in principle) |
| DOMAIN_NAME | 37 | Partial — our `URL` recognizer may catch some, but the entity-type label won't match (`URL` vs `DOMAIN_NAME`) |
| IBAN_CODE | 21 | **Yes** |
| US_SSN | 16 | No — country-specific recognizer not vendored (regex-only architecture, out of scope) |
| IP_ADDRESS | 14 | **Yes** |
| US_DRIVER_LICENSE | 5 | No — country-specific recognizer not vendored |

This split is exactly the point of the exercise: it's a real, measured
demonstration of what a regex/checksum-only architecture can and can't do,
run against Microsoft's own evaluation set rather than a hand-picked example.

Re-download fresh at any time:
```
curl -L -o data/synth_dataset_v2.json https://raw.githubusercontent.com/microsoft/presidio-research/main/data/synth_dataset_v2.json
```
