"""
Runnable test suite - OUR OWN code.

For every test case, prints INPUT / DESIRED (expected) OUTPUT / ACTUAL
OUTPUT side by side and whether it PASSED or FAILED, then a summary count.

Two things are checked per test case:
  1. Which entity types got detected (order-independent set comparison)
  2. The final anonymized text (exact string match, except the Hash test,
     which checks the output's FORMAT instead of an exact string - a
     random salt makes the hash value different on every run by design)

Run:
    pip install -r requirements.txt
    python test_cases.py
"""

import re
import sys

from presidio_anonymizer import OperatorConfig
from regex_engine import RegexAnalyzerEngine, RegexAnonymizerEngine


def is_sha256_hex(value: str) -> bool:
    return bool(re.fullmatch(r"[0-9a-f]{64}", value))


TEST_CASES = [
    {
        "name": "Credit card (Luhn checksum) -> mask",
        "input": "Please charge my card 4111 1111 1111 1111 for the order.",
        "operators": {"CREDIT_CARD": OperatorConfig("mask", {"masking_char": "*", "chars_to_mask": 12, "from_end": False})},
        "expected_entities": {"CREDIT_CARD"},
        "expected_output": "Please charge my card ************11 1111 for the order.",
    },
    {
        "name": "Email address -> replace",
        "input": "You can reach the support team at john.smith@example.com anytime.",
        "operators": {"EMAIL_ADDRESS": OperatorConfig("replace")},
        "expected_entities": {"EMAIL_ADDRESS", "URL"},  # URL also fires on the domain part, then loses the overlap
        "expected_output": "You can reach the support team at <EMAIL_ADDRESS> anytime.",
    },
    {
        "name": "Email address -> hash (non-deterministic value, format-checked)",
        "input": "You can reach the support team at john.smith@example.com anytime.",
        "operators": {"EMAIL_ADDRESS": OperatorConfig("hash")},
        "expected_entities": {"EMAIL_ADDRESS", "URL"},
        "expected_output": None,  # checked via expected_output_check below instead
        "expected_output_check": lambda actual: (
            actual.startswith("You can reach the support team at ")
            and actual.endswith(" anytime.")
            and is_sha256_hex(actual.split(" ")[7])
        ),
        "expected_output_description": "email replaced by a 64-character sha256 hex hash (exact value changes every run - random salt)",
    },
    {
        "name": "Phone number (python-phonenumbers) -> redact",
        "input": "Call the clinic at +1 415-555-2671 to book an appointment.",
        "operators": {"PHONE_NUMBER": OperatorConfig("redact")},
        "expected_entities": {"PHONE_NUMBER"},
        "expected_output": "Call the clinic at  to book an appointment.",
    },
    {
        "name": "IBAN (mod-97 checksum) -> replace with custom value",
        "input": "Please wire the deposit to IBAN DE89370400440532013000 before Friday.",
        "operators": {"IBAN_CODE": OperatorConfig("replace", {"new_value": "<IBAN>"})},
        "expected_entities": {"IBAN_CODE"},
        "expected_output": "Please wire the deposit to IBAN <IBAN> before Friday.",
    },
    {
        "name": "IP address -> mask from end",
        "input": "Suspicious login detected from 192.168.1.10 at 3 AM.",
        "operators": {"IP_ADDRESS": OperatorConfig("mask", {"masking_char": "#", "chars_to_mask": 6, "from_end": True})},
        "expected_entities": {"IP_ADDRESS"},
        "expected_output": "Suspicious login detected from 192.16###### at 3 AM.",
    },
    {
        "name": "MAC address -> replace (default)",
        "input": "The device with MAC 00:1A:2B:3C:4D:5E was flagged by the firewall.",
        "operators": {"MAC_ADDRESS": OperatorConfig("replace")},
        "expected_entities": {"MAC_ADDRESS"},
        "expected_output": "The device with MAC <MAC_ADDRESS> was flagged by the firewall.",
    },
    {
        "name": "Dates (numeric formats) -> replace with custom value",
        "input": "The invoice is dated 2024-03-15 and due on 04/20/2024.",
        "operators": {"DATE_TIME": OperatorConfig("replace", {"new_value": "<DATE>"})},
        "expected_entities": {"DATE_TIME"},
        "expected_output": "The invoice is dated <DATE> and due on <DATE>.",
    },
    {
        "name": "URL -> replace with custom value",
        "input": "Full details are posted at https://billing.example.com/invoice/8842.",
        "operators": {"URL": OperatorConfig("replace", {"new_value": "<LINK>"})},
        "expected_entities": {"URL"},
        "expected_output": "Full details are posted at <LINK>",
    },
    {
        "name": "UUID -> replace (default)",
        "input": "Reference ticket 8f14e45f-ceea-467e-a92c-25f6fdd0e9f1 for details.",
        "operators": {"UUID": OperatorConfig("replace")},
        "expected_entities": {"UUID"},
        "expected_output": "Reference ticket <UUID> for details.",
    },
    {
        "name": "Crypto wallet (Base58 + Bech32 checksum) -> replace with custom value",
        "input": "Send the refund to BTC wallet 1BoatSLRHtKNngkdXEeobR76b53LETtpyT.",
        "operators": {"CRYPTO": OperatorConfig("replace", {"new_value": "<WALLET>"})},
        "expected_entities": {"CRYPTO"},
        "expected_output": "Send the refund to BTC wallet <WALLET>.",
    },
    {
        "name": "Combined text - also proves PERSON/ORG are NOT detected (no NER)",
        "input": "Hi, this is John Smith from Acme Corp. You can reach me at john.smith@example.com or call +1 415-555-2671.",
        "operators": {
            "EMAIL_ADDRESS": OperatorConfig("replace"),
            "PHONE_NUMBER": OperatorConfig("redact"),
            "DEFAULT": OperatorConfig("replace"),
        },
        "expected_entities": {"EMAIL_ADDRESS", "URL", "PHONE_NUMBER"},
        "expected_output": "Hi, this is John Smith from Acme Corp. You can reach me at <EMAIL_ADDRESS> or call .",
    },

    # ------------------------------------------------------------------
    # POSITIVE cases: additional valid formats per entity type, beyond
    # the one "textbook" example each already got above.
    # ------------------------------------------------------------------
    {
        "name": "Mastercard (different card network, same Luhn checksum path)",
        "input": "My mastercard is 5500 0000 0000 0004 for billing.",
        "operators": {"CREDIT_CARD": OperatorConfig("replace", {"new_value": "<CARD>"})},
        "expected_entities": {"CREDIT_CARD"},
        "expected_output": "My mastercard is <CARD> for billing.",
    },
    {
        "name": "Email with plus-addressing and a multi-label domain",
        "input": "Send to jane.doe+newsletter@mail.co.uk please.",
        "operators": {"EMAIL_ADDRESS": OperatorConfig("replace")},
        "expected_entities": {"EMAIL_ADDRESS", "URL"},
        "expected_output": "Send to <EMAIL_ADDRESS> please.",
    },
    {
        "name": "UK phone number format",
        "input": "Ring the office on +44 20 7946 0958 today.",
        "operators": {"PHONE_NUMBER": OperatorConfig("redact")},
        "expected_entities": {"PHONE_NUMBER"},
        "expected_output": "Ring the office on  today.",
    },
    {
        "name": "IBAN from a different country (France, not Germany)",
        "input": "Transfer to FR1420041010050500013M02606 now.",
        "operators": {"IBAN_CODE": OperatorConfig("replace", {"new_value": "<IBAN>"})},
        "expected_entities": {"IBAN_CODE"},
        "expected_output": "Transfer to <IBAN> now.",
    },
    {
        "name": "IPv6 address (not just IPv4)",
        "input": "The server responded from 2001:0db8:85a3:0000:0000:8a2e:0370:7334.",
        "operators": {"IP_ADDRESS": OperatorConfig("replace", {"new_value": "<IP>"})},
        "expected_entities": {"IP_ADDRESS"},
        "expected_output": "The server responded from <IP>.",
    },
    {
        "name": "MAC address in Cisco dot-notation (not colon/hyphen)",
        "input": "Interface shows 0012.3456.789A as the address.",
        "operators": {"MAC_ADDRESS": OperatorConfig("replace")},
        "expected_entities": {"MAC_ADDRESS"},
        "expected_output": "Interface shows <MAC_ADDRESS> as the address.",
    },
    {
        "name": "Date in dd-MMM-yyyy format",
        "input": "Deadline is 15-MAR-2024 for submissions.",
        "operators": {"DATE_TIME": OperatorConfig("replace", {"new_value": "<DATE>"})},
        "expected_entities": {"DATE_TIME"},
        "expected_output": "Deadline is <DATE> for submissions.",
    },
    {
        "name": "Bare domain URL with no http(s):// scheme",
        "input": "See details on billing.example.com/invoice for more.",
        "operators": {"URL": OperatorConfig("replace", {"new_value": "<LINK>"})},
        "expected_entities": {"URL"},
        "expected_output": "See details on <LINK> for more.",
    },
    {
        "name": "Bech32 crypto wallet (not just Base58)",
        "input": "Refund to bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq wallet.",
        "operators": {"CRYPTO": OperatorConfig("replace", {"new_value": "<WALLET>"})},
        "expected_entities": {"CRYPTO"},
        "expected_output": "Refund to <WALLET> wallet.",
    },

    # ------------------------------------------------------------------
    # NEGATIVE cases: text that LOOKS like PII but fails validation, and
    # must be correctly rejected (expected_entities is empty - i.e. the
    # checksum/format logic is doing real work, not just pattern-matching
    # shape). Also one documented known limitation (spelled-out dates).
    # ------------------------------------------------------------------
    {
        "name": "NEGATIVE: credit card with a broken Luhn checksum",
        "input": "My card is 4111 1111 1111 1112 for billing.",
        "operators": {},
        "expected_entities": set(),
        "expected_output": "My card is 4111 1111 1111 1112 for billing.",
    },
    {
        "name": "NEGATIVE: email on a non-public-suffix domain (.local)",
        "input": "Contact admin@myserver.local for access.",
        "operators": {},
        "expected_entities": set(),
        "expected_output": "Contact admin@myserver.local for access.",
    },
    {
        "name": "NEGATIVE: IBAN with a broken mod-97 checksum",
        "input": "Transfer to DE89370400440532013099 now.",
        "operators": {},
        "expected_entities": set(),
        "expected_output": "Transfer to DE89370400440532013099 now.",
    },
    {
        "name": "NEGATIVE: IPv4 octets out of range (999.999.999.999)",
        "input": "Bad address 999.999.999.999 was logged.",
        "operators": {},
        "expected_entities": set(),
        "expected_output": "Bad address 999.999.999.999 was logged.",
    },
    {
        "name": "NEGATIVE: MAC broadcast address is explicitly rejected",
        "input": "Broadcast to FF:FF:FF:FF:FF:FF now.",
        "operators": {},
        "expected_entities": set(),
        "expected_output": "Broadcast to FF:FF:FF:FF:FF:FF now.",
    },
    {
        "name": "NEGATIVE: nil UUID is explicitly excluded as a sentinel value",
        "input": "Ticket ref is 00000000-0000-0000-0000-000000000000 closed.",
        "operators": {},
        "expected_entities": set(),
        "expected_output": "Ticket ref is 00000000-0000-0000-0000-000000000000 closed.",
    },
    {
        "name": "NEGATIVE: UUID with an invalid version nibble",
        "input": "Ticket ref is 8f14e45f-ceea-067e-a92c-25f6fdd0e9f1 closed.",
        "operators": {},
        "expected_entities": set(),
        "expected_output": "Ticket ref is 8f14e45f-ceea-067e-a92c-25f6fdd0e9f1 closed.",
    },
    {
        "name": "KNOWN LIMITATION (not a bug): spelled-out dates are not regex-matched",
        "input": "The meeting is on March 15, 2024 at noon.",
        "operators": {},
        "expected_entities": set(),
        "expected_output": "The meeting is on March 15, 2024 at noon.",
    },
]


def run_test(analyzer, anonymizer, case):
    results = analyzer.analyze(case["input"])
    actual_entities = {r.entity_type for r in results}
    actual_output = anonymizer.anonymize(case["input"], results, case["operators"])

    entities_ok = actual_entities == case["expected_entities"]

    if case.get("expected_output_check"):
        output_ok = case["expected_output_check"](actual_output)
        desired_display = case["expected_output_description"]
    else:
        output_ok = actual_output == case["expected_output"]
        desired_display = case["expected_output"]

    passed = entities_ok and output_ok
    return passed, entities_ok, output_ok, actual_entities, actual_output, desired_display


def main() -> int:
    analyzer = RegexAnalyzerEngine()
    anonymizer = RegexAnonymizerEngine()

    total_pass = 0
    for i, case in enumerate(TEST_CASES, start=1):
        passed, entities_ok, output_ok, actual_entities, actual_output, desired_display = run_test(
            analyzer, anonymizer, case
        )
        total_pass += int(passed)

        print("=" * 90)
        print(f"TEST {i}: {case['name']}")
        print("=" * 90)
        print(f"INPUT:            {case['input']}")
        print(f"DETECTED ENTITIES: {sorted(actual_entities)}  "
              f"(expected: {sorted(case['expected_entities'])})  "
              f"[{'OK' if entities_ok else 'MISMATCH'}]")
        print(f"DESIRED OUTPUT:   {desired_display}")
        print(f"ACTUAL OUTPUT:    {actual_output}")
        print(f"RESULT:           {'PASS' if passed else 'FAIL'}  "
              f"(entities {'OK' if entities_ok else 'MISMATCH'}, output {'OK' if output_ok else 'MISMATCH'})")
        print()

    print("=" * 90)
    print(f"SUMMARY: {total_pass}/{len(TEST_CASES)} test cases passed")
    print("=" * 90)

    return 0 if total_pass == len(TEST_CASES) else 1


if __name__ == "__main__":
    sys.exit(main())
