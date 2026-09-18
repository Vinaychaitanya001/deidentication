"""
Entity-name reconciliation between dataset labels and Presidio labels.

OUR OWN code (not from the Presidio repo).

Why this exists
---------------
Even on Presidio's *own* evaluation dataset the label vocabularies differ
from what Presidio's recognizers emit:

    dataset says          Presidio emits
    ------------          --------------
    GPE                   LOCATION        (411 spans in synth_dataset_v2)
    STREET_ADDRESS        LOCATION        (598 spans)
    DOMAIN_NAME           URL             (37 spans)

Our earlier `evaluate.py` compared labels with `==`, which scored every one
of those as a miss even when the span was found perfectly. Both sides are
normalised to a canonical vocabulary here before any scoring happens.
"""

from typing import Dict, Optional, Set

# --- canonical vocabulary -------------------------------------------------
# Deliberately Presidio's own names, so the canonical form is whatever the
# analyzer actually produces.

# How labels used by synth_dataset_v2.json map onto canonical names.
DATASET_TO_CANONICAL: Dict[str, str] = {
    # identical on both sides
    "PERSON": "PERSON",
    "ORGANIZATION": "ORGANIZATION",
    "NRP": "NRP",
    "DATE_TIME": "DATE_TIME",
    "CREDIT_CARD": "CREDIT_CARD",
    "EMAIL_ADDRESS": "EMAIL_ADDRESS",
    "PHONE_NUMBER": "PHONE_NUMBER",
    "IBAN_CODE": "IBAN_CODE",
    "IP_ADDRESS": "IP_ADDRESS",
    "US_SSN": "US_SSN",
    "US_DRIVER_LICENSE": "US_DRIVER_LICENSE",
    # renamed
    "GPE": "LOCATION",           # geo-political entity -> Presidio LOCATION
    "STREET_ADDRESS": "LOCATION",  # partial credit: spaCy tags address fragments
    "DOMAIN_NAME": "URL",        # our UrlRecognizer fires on bare domains
}

# How Presidio's output maps onto canonical names (mostly identity, since the
# canonical vocabulary IS Presidio's).
PRESIDIO_TO_CANONICAL: Dict[str, str] = {
    "PERSON": "PERSON",
    "LOCATION": "LOCATION",
    "ORGANIZATION": "ORGANIZATION",
    "NRP": "NRP",
    "DATE_TIME": "DATE_TIME",
    "CREDIT_CARD": "CREDIT_CARD",
    "EMAIL_ADDRESS": "EMAIL_ADDRESS",
    "PHONE_NUMBER": "PHONE_NUMBER",
    "IBAN_CODE": "IBAN_CODE",
    "IP_ADDRESS": "IP_ADDRESS",
    "US_SSN": "US_SSN",
    "US_DRIVER_LICENSE": "US_DRIVER_LICENSE",
    "URL": "URL",
}

# Dataset labels with no Presidio equivalent at all. Reported separately so
# they are never silently counted as recall failures.
UNREACHABLE_DATASET_LABELS: Set[str] = {
    "TITLE",      # 92 spans  - no Presidio entity
    "AGE",        # 74 spans  - mapping exists but spaCy emits no AGE label
    "ZIP_CODE",   # 37 spans  - Presidio has CA/DE/UK postcodes, no US ZIP
}

# --- which Presidio outputs satisfy which dataset label ---------------------
# Recall is measured per DATASET label and precision per PRESIDIO label, so
# that e.g. GPE recall and STREET_ADDRESS recall stay visible separately even
# though both are satisfied by a Presidio LOCATION prediction. Collapsing them
# into one canonical bucket (as a naive mapping does) hides the fact that
# spaCy handles cities well and street addresses badly.
DATASET_LABEL_ACCEPTS: Dict[str, Set[str]] = {
    "PERSON": {"PERSON"},
    "ORGANIZATION": {"ORGANIZATION"},
    "NRP": {"NRP"},
    "DATE_TIME": {"DATE_TIME"},
    "CREDIT_CARD": {"CREDIT_CARD"},
    "EMAIL_ADDRESS": {"EMAIL_ADDRESS"},
    "PHONE_NUMBER": {"PHONE_NUMBER"},
    "IBAN_CODE": {"IBAN_CODE"},
    "IP_ADDRESS": {"IP_ADDRESS"},
    "US_SSN": {"US_SSN"},
    "US_DRIVER_LICENSE": {"US_DRIVER_LICENSE"},
    "GPE": {"LOCATION"},
    "STREET_ADDRESS": {"LOCATION"},
    "DOMAIN_NAME": {"URL"},
}

# Reverse view: which dataset labels a given Presidio prediction may satisfy.
PRESIDIO_LABEL_SATISFIES: Dict[str, Set[str]] = {}
for _ds, _accepts in DATASET_LABEL_ACCEPTS.items():
    for _p in _accepts:
        PRESIDIO_LABEL_SATISFIES.setdefault(_p, set()).add(_ds)


def accepted_presidio_labels(dataset_label: str) -> Set[str]:
    """Presidio outputs that count as finding this dataset label."""
    return DATASET_LABEL_ACCEPTS.get(dataset_label, set())


def satisfied_dataset_labels(presidio_label: str) -> Set[str]:
    """Dataset labels this Presidio prediction could legitimately be."""
    return PRESIDIO_LABEL_SATISFIES.get(presidio_label, set())


# Entity types the regex-only architecture could reach, for the A/B report.
REGEX_ONLY_REACHABLE: Set[str] = {
    "CREDIT_CARD",
    "DATE_TIME",
    "EMAIL_ADDRESS",
    "IBAN_CODE",
    "IP_ADDRESS",
    "PHONE_NUMBER",
}

# Entity types unlocked by adding the NLP/NER layer.
NER_UNLOCKED: Set[str] = {"PERSON", "LOCATION", "ORGANIZATION", "NRP"}


def canonical_from_dataset(label: str) -> Optional[str]:
    """Canonical name for a ground-truth label, or None if unreachable."""
    return DATASET_TO_CANONICAL.get(label)


def canonical_from_presidio(label: str) -> Optional[str]:
    """Canonical name for a Presidio-emitted label, or None if unmapped."""
    return PRESIDIO_TO_CANONICAL.get(label)


def is_unreachable(label: str) -> bool:
    """True if no Presidio recognizer can produce this dataset label."""
    return label in UNREACHABLE_DATASET_LABELS


def scoreable_canonical_labels() -> Set[str]:
    """Canonical labels that both sides can express — the scoreable set."""
    return set(DATASET_TO_CANONICAL.values()) & set(PRESIDIO_TO_CANONICAL.values())
