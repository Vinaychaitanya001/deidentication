"""
Demo of the regex-only Presidio pipeline - OUR OWN code.

Run:
    pip install -r requirements.txt
    python demo.py
"""

from presidio_anonymizer import OperatorConfig
from regex_engine import RegexAnalyzerEngine, RegexAnonymizerEngine

SAMPLE_TEXT = (
    "Hi, this is John Smith from Acme Corp. You can reach me at "
    "john.smith@example.com or call +1 415-555-2671. My card number is "
    "4111 1111 1111 1111 and I'll wire funds to IBAN DE89370400440532013000. "
    "Server logs show a login from 192.168.1.10 (MAC 00:1A:2B:3C:4D:5E) on "
    "2024-03-15. Check the invoice at "
    "https://billing.example.com/invoice/8f14e45f-ceea-467e-a92c-25f6fdd0e9f1 "
    "and my BTC wallet is 1BoatSLRHtKNngkdXEeobR76b53LETtpyT."
)


def main() -> None:
    analyzer = RegexAnalyzerEngine()
    anonymizer = RegexAnonymizerEngine()

    print("=" * 80)
    print("ORIGINAL TEXT")
    print("=" * 80)
    print(SAMPLE_TEXT)

    results = analyzer.analyze(SAMPLE_TEXT)

    print("\n" + "=" * 80)
    print(f"DETECTED ENTITIES ({len(results)})")
    print("=" * 80)
    for r in results:
        span = SAMPLE_TEXT[r.start : r.end]
        print(f"  {r.entity_type:<15} [{r.start:>3}:{r.end:<3}] score={r.score:.2f}  {span!r}")

    print(
        "\nNote: 'John Smith' and 'Acme Corp' are NOT detected - PERSON/ORG "
        "recognition needs an NLP/NER engine, which is out of scope for a "
        "regex-only architecture. See VENDORED_FILES.md."
    )

    # One operator per entity type, deliberately using all four vendored
    # operators to show each in action; anything not listed here falls
    # back to "DEFAULT" (replace).
    operators = {
        "CREDIT_CARD": OperatorConfig(
            "mask", {"masking_char": "*", "chars_to_mask": 12, "from_end": False}
        ),
        "EMAIL_ADDRESS": OperatorConfig("hash"),
        "PHONE_NUMBER": OperatorConfig("redact"),
        "IBAN_CODE": OperatorConfig("replace", {"new_value": "<IBAN>"}),
        "IP_ADDRESS": OperatorConfig(
            "mask", {"masking_char": "#", "chars_to_mask": 6, "from_end": True}
        ),
        "DEFAULT": OperatorConfig("replace"),
    }

    anonymized_text = anonymizer.anonymize(SAMPLE_TEXT, results, operators)

    print("\n" + "=" * 80)
    print("ANONYMIZED TEXT")
    print("=" * 80)
    print(anonymized_text)


if __name__ == "__main__":
    main()
