"""
Step-by-step trace of one sentence through the whole pipeline.

Prints what each stage produces, so the flow can be followed by hand:
  stage 1  NLP engine      -> tokens, lemmas, NER entities
  stage 2  recognizers     -> raw candidate detections
  stage 3  context + score -> final detections
  stage 4  anonymizer      -> de-identified text

Run:  python trace_example.py
"""

import sys

from build_analyzer import build_analyzer, build_anonymizer
from presidio_anonymizer import OperatorConfig

TEXT = (
    "Dr. Sarah Johnson from Boston General Hospital called on March 15, 2024. "
    "Her email is sarah.johnson@bgh.org, phone +1 415-555-2671, "
    "SSN 457-55-5462, card 4111 1111 1111 1111."
)


def rule(title):
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    analyzer = build_analyzer()
    anonymizer = build_anonymizer()

    rule("INPUT TEXT")
    print(TEXT)

    # ---- stage 1: the NLP engine runs once over the whole sentence ----
    rule("STAGE 1 — NlpEngine (spaCy) reads the sentence")
    artifacts = analyzer.nlp_engine.process_text(TEXT, "en")
    print("tokens (first 12) :", [t.text for t in artifacts.tokens][:12])
    print("lemmas (first 12) :", artifacts.lemmas[:12])
    print("NER entities found:")
    for ent in artifacts.entities:
        print(f"    {ent.label_:<12} {ent.text!r}")

    # ---- stage 2 + 3: recognizers, context boost, scoring ----
    rule("STAGE 2+3 — Recognizers run, then scores are adjusted")
    results = sorted(analyzer.analyze(text=TEXT, language="en"),
                     key=lambda r: r.start)
    print(f"{'ENTITY':<16}{'SPAN':<12}{'SCORE':<8}{'FOUND BY':<24}TEXT")
    print("-" * 78)
    for r in results:
        who = (r.recognition_metadata or {}).get("recognizer_name", "?")
        print(f"{r.entity_type:<16}{f'{r.start}:{r.end}':<12}"
              f"{r.score:<8.2f}{who:<24}{TEXT[r.start:r.end]!r}")

    # ---- stage 4: anonymization ----
    rule("STAGE 4 — Anonymizer replaces each detected span")
    operators = {
        "PERSON": OperatorConfig("replace", {"new_value": "<NAME>"}),
        "DATE_TIME": OperatorConfig("replace", {"new_value": "<DATE>"}),
        "EMAIL_ADDRESS": OperatorConfig("hash"),
        "PHONE_NUMBER": OperatorConfig("redact"),
        "CREDIT_CARD": OperatorConfig(
            "mask", {"masking_char": "*", "chars_to_mask": 15, "from_end": False}
        ),
        "US_SSN": OperatorConfig("replace", {"new_value": "<SSN>"}),
        "DEFAULT": OperatorConfig("replace"),
    }
    print("operator per entity type:")
    for k, v in operators.items():
        print(f"    {k:<16} {v.operator_name}")
    out = anonymizer.anonymize(text=TEXT, analyzer_results=results,
                               operators=operators)
    print("\nOUTPUT TEXT:")
    print(out.text)


if __name__ == "__main__":
    main()
