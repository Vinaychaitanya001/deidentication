# Regex-Only Presidio — Test Cases & Results

Built from files vendored out of `github.com/microsoft/presidio` (MIT
license) — see `VENDORED_FILES.md` for the exact source of every file.
Every input/output pair below is captured directly from a real run of
`generate_report_data.py` (raw data in `results/report_data.json`), not
typed by hand.

Regenerate this data anytime:
```
python generate_report_data.py
```

---

## 1. Test cases — one per entity type

Each row shows: the input sentence, what the analyzer detected (entity
type, character span, matched text, confidence score), the anonymization
operator applied, and the final output text.

### 1.1 Credit card (Luhn checksum)
- **Input:** `Please charge my card 4111 1111 1111 1111 for the order.`
- **Detected:** `CREDIT_CARD` [22:41] score=1.00 → `"4111 1111 1111 1111"`
- **Operator:** `mask` (mask first 12 chars with `*`)
- **Output:** `Please charge my card ************11 1111 for the order.`

### 1.2 Email address
- **Input:** `You can reach the support team at john.smith@example.com anytime.`
- **Detected:**
  - `EMAIL_ADDRESS` [34:56] score=1.00 → `"john.smith@example.com"`
  - `URL` [34:41] score=0.50 → `"john.sm"` *(discarded — overlaps the higher-scoring email match)*
  - `URL` [45:56] score=0.50 → `"example.com"` *(discarded — same reason)*
- **Operator:** `hash` (SHA-256 + random salt)
- **Output:** `You can reach the support team at 9e97297761c898e4f65e61c9a677d53030472caf19e8a8bf31698e1ba9cd7593 anytime.`

### 1.3 Phone number (python-phonenumbers)
- **Input:** `Call the clinic at +1 415-555-2671 to book an appointment.`
- **Detected:** `PHONE_NUMBER` [19:34] score=0.40 → `"+1 415-555-2671"`
- **Operator:** `redact` (deleted entirely)
- **Output:** `Call the clinic at  to book an appointment.`

### 1.4 IBAN (mod-97 checksum)
- **Input:** `Please wire the deposit to IBAN DE89370400440532013000 before Friday.`
- **Detected:** `IBAN_CODE` [32:54] score=1.00 → `"DE89370400440532013000"`
- **Operator:** `replace` → `<IBAN>`
- **Output:** `Please wire the deposit to IBAN <IBAN> before Friday.`

### 1.5 IP address
- **Input:** `Suspicious login detected from 192.168.1.10 at 3 AM.`
- **Detected:** `IP_ADDRESS` [31:43] score=0.60 → `"192.168.1.10"`
- **Operator:** `mask` (mask last 6 chars with `#`)
- **Output:** `Suspicious login detected from 192.16###### at 3 AM.`

### 1.6 MAC address
- **Input:** `The device with MAC 00:1A:2B:3C:4D:5E was flagged by the firewall.`
- **Detected:** `MAC_ADDRESS` [20:37] score=0.60 → `"00:1A:2B:3C:4D:5E"`
- **Operator:** `replace` (default) → `<MAC_ADDRESS>`
- **Output:** `The device with MAC <MAC_ADDRESS> was flagged by the firewall.`

### 1.7 Date (numeric formats)
- **Input:** `The invoice is dated 2024-03-15 and due on 04/20/2024.`
- **Detected:**
  - `DATE_TIME` [21:31] score=0.60 → `"2024-03-15"`
  - `DATE_TIME` [43:53] score=0.60 → `"04/20/2024"`
- **Operator:** `replace` → `<DATE>`
- **Output:** `The invoice is dated <DATE> and due on <DATE>.`

### 1.8 URL
- **Input:** `Full details are posted at https://billing.example.com/invoice/8842.`
- **Detected:** `URL` [27:68] score=0.60 → `"https://billing.example.com/invoice/8842."` *(note: trailing period got swept into the match — a known quirk of the vendored regex, not something we introduced)*
- **Operator:** `replace` → `<LINK>`
- **Output:** `Full details are posted at <LINK>`

### 1.9 UUID
- **Input:** `Reference ticket 8f14e45f-ceea-467e-a92c-25f6fdd0e9f1 for details.`
- **Detected:** `UUID` [17:53] score=0.50 → `"8f14e45f-ceea-467e-a92c-25f6fdd0e9f1"`
- **Operator:** `replace` (default) → `<UUID>`
- **Output:** `Reference ticket <UUID> for details.`

### 1.10 Crypto wallet (Base58 + Bech32 checksum)
- **Input:** `Send the refund to BTC wallet 1BoatSLRHtKNngkdXEeobR76b53LETtpyT.`
- **Detected:** `CRYPTO` [30:64] score=1.00 → `"1BoatSLRHtKNngkdXEeobR76b53LETtpyT"`
- **Operator:** `replace` → `<WALLET>`
- **Output:** `Send the refund to BTC wallet <WALLET>.`

### 1.11 Combined text — shows the NER limitation on purpose
- **Input:** `Hi, this is John Smith from Acme Corp. You can reach me at john.smith@example.com or call +1 415-555-2671.`
- **Detected:**
  - `EMAIL_ADDRESS` [59:81] score=1.00 → `"john.smith@example.com"`
  - `URL` [59:66] / [70:81] score=0.50 *(discarded, overlap)*
  - `PHONE_NUMBER` [90:105] score=0.40 → `"+1 415-555-2671"`
  - **`John Smith` and `Acme Corp` are NOT detected** — PERSON/ORG needs an NLP/NER engine, which this regex-only architecture deliberately excludes.
- **Operators:** email → `hash`, phone → `redact`
- **Output:** `Hi, this is John Smith from Acme Corp. You can reach me at 804e9e5b966bf110f64e82ab4733f77b72a27a3dbd6d05b8264b64343b9ad919 or call .`

---

## 2. Evaluation against Microsoft's own test data

Instead of hand-picked sentences, this section scores the pipeline against
**Presidio's own evaluation dataset** — `presidio-research`'s
`synth_dataset_v2.json`, 1,500 labeled synthetic records, downloaded from
`github.com/microsoft/presidio-research` (see `data/README.md`). A
prediction counts as a hit if it overlaps a ground-truth span of the same
entity type.

| Entity type | TP | FP | FN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| CREDIT_CARD | 105 | 0 | 31 | 1.00 | 0.77 | 0.87 |
| DATE_TIME | 48 | 0 | 71 | 1.00 | 0.40 | 0.57 |
| EMAIL_ADDRESS | 49 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| IBAN_CODE | 20 | 0 | 1 | 1.00 | 0.95 | 0.98 |
| IP_ADDRESS | 14 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| PHONE_NUMBER | 54 | 20 | 38 | 0.73 | 0.59 | 0.65 |
| **MICRO-AVERAGE** | **290** | **20** | **141** | **0.94** | **0.67** | **0.78** |

**Reading these numbers:**
- **Precision stays at 1.00 for every format-checkable type** (credit card, IBAN, date, email, IP) — when the recognizer has a checksum or a well-defined format to validate against, it essentially never fires on a false match.
- **`DATE_TIME` recall is the weakest (0.40)** — the vendored `DateRecognizer` only covers numeric/slash/dash formats (`2024-03-15`, `04/20/2024`). This dataset also contains spelled-out dates ("March 15th, 2020") that no regex here matches — a real, expected gap for a regex-only design, not a bug.
- **`PHONE_NUMBER` is the only type with false positives (20)** — the `phonenumbers` library scans 8 regions per text and occasionally matches a numeric sequence that isn't actually a phone number.
- **2,432 ground-truth spans in the dataset are out of scope by design** — PERSON, STREET_ADDRESS, GPE, ORGANIZATION, TITLE, AGE, NRP, ZIP_CODE, DOMAIN_NAME, US_SSN, US_DRIVER_LICENSE. None of these are regex-detectable without either an NER model or an unvendored country-specific recognizer.
- **86 of our predictions have no matching label in this dataset** (CRYPTO, MAC_ADDRESS, URL, UUID — the dataset simply never labels these types), so they're reported separately rather than counted as false positives.

---

## 3. What this demonstrates

A pure regex/checksum architecture (zero NLP models, zero ML, ~3 small pip
dependencies: `regex`, `tldextract`, `phonenumbers`) gets **near-perfect
precision** on any PII type with a fixed format or a checksum, and
**zero recall** on anything requiring free-text understanding (names,
addresses, organizations). That tradeoff — not a bug in this
implementation — is the architectural ceiling of "regex-only," measured
against Microsoft's own evaluation data rather than asserted.
