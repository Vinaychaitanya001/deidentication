"""Canonical PHI ontology shared by the pipeline, the datasets and the scorer.

Types follow the i2b2-2014 categories (a superset of HIPAA Safe Harbor) and are written
CATEGORY.SUBTYPE. A bare category ("NAME", "LOCATION", "ID") is used when a detector
cannot tell the subtype; it still matches any subtype of that category when scoring.
"""

from dataclasses import dataclass
from typing import Dict, Optional

IGNORE = "IGNORE"  # "don't care" region: neither rewarded nor penalised when scoring

CATEGORIES = ("NAME", "DATE", "AGE", "LOCATION", "ORGANIZATION", "PROFESSION", "CONTACT", "ID", "OTHER")


@dataclass(frozen=True)
class PhiType:
    code: str
    i2b2: Optional[str]
    hipaa: Optional[str]  # None = not required by Safe Harbor (i2b2-only)
    description: str

    @property
    def category(self) -> str:
        return category(self.code)


PHI_TYPES: Dict[str, PhiType] = {t.code: t for t in (
    PhiType("NAME.PATIENT", "PATIENT", "#1 names", "patient name"),
    PhiType("NAME.CLINICIAN", "DOCTOR", None, "clinician / staff name"),
    PhiType("NAME.OTHER", "PATIENT", "#1 names", "relative or other person"),
    PhiType("NAME", None, "#1 names", "person name, subtype unknown (predictions only)"),
    PhiType("DATE", "DATE", "#3 dates (except year)", "date or date expression"),
    PhiType("AGE", "AGE", "#3 ages over 89", "age in years"),
    PhiType("LOCATION.HOSPITAL", "HOSPITAL", None, "hospital or facility name"),
    PhiType("LOCATION.STREET", "STREET", "#2 geography < state", "street address"),
    PhiType("LOCATION.CITY", "CITY", "#2 geography < state", "city"),
    PhiType("LOCATION.STATE", "STATE", None, "state (Safe Harbor may keep it)"),
    PhiType("LOCATION.ZIP", "ZIP", "#2 ZIP (ZIP3 rule)", "ZIP code"),
    PhiType("LOCATION.COUNTRY", "COUNTRY", None, "country"),
    PhiType("LOCATION.OTHER", "LOCATION-OTHER", "#2 geography < state", "other location"),
    PhiType("LOCATION", None, "#2 geography < state", "location, subtype unknown (predictions only)"),
    PhiType("ORGANIZATION", "ORGANIZATION", None, "organization, e.g. employer"),
    PhiType("PROFESSION", "PROFESSION", None, "occupation"),
    PhiType("CONTACT.PHONE", "PHONE", "#4 telephone", "phone or pager number"),
    PhiType("CONTACT.FAX", "FAX", "#5 fax", "fax number"),
    PhiType("CONTACT.EMAIL", "EMAIL", "#6 email", "email address"),
    PhiType("CONTACT.URL", "URL", "#14 URL", "web address"),
    PhiType("CONTACT.IP", "IPADDR", "#15 IP address", "IP address"),
    PhiType("CONTACT", None, "#4-6,14-15", "contact, subtype unknown (predictions only)"),
    PhiType("ID.SSN", "SSN", "#7 SSN", "social security number"),
    PhiType("ID.MRN", "MEDICALRECORD", "#8 medical record number", "medical record number"),
    PhiType("ID.HEALTHPLAN", "HEALTHPLAN", "#9 health plan number", "insurance member / beneficiary id"),
    PhiType("ID.ACCOUNT", "ACCOUNT", "#10 account number", "account, billing or encounter number"),
    PhiType("ID.LICENSE", "LICENSE", "#11 certificate/license", "licence or certificate number"),
    PhiType("ID.VEHICLE", "VEHICLE", "#12 vehicle id", "vehicle identifier"),
    PhiType("ID.DEVICE", "DEVICE", "#13 device id", "device identifier or serial number"),
    PhiType("ID.BIOID", "BIOID", "#16 biometric id", "biometric identifier"),
    PhiType("ID.OTHER", "IDNUM", "#18 other unique id", "other identifier (accession, NPI ...)"),
    PhiType("ID", None, "#18 other unique id", "identifier, subtype unknown (predictions only)"),
    PhiType("OTHER", "OTHERPHI", "#18 other", "other PHI"),
)}


def category(code: str) -> str:
    return code.split(".", 1)[0]


def is_phi(code: str) -> bool:
    return code in PHI_TYPES


# Presidio entity names (predefined recognizers, our clinical detector pack, and the NER mapping) -> canonical.
PRESIDIO_TO_CANONICAL: Dict[str, str] = {
    "PERSON": "NAME",
    "NAME_PATIENT": "NAME.PATIENT",
    "NAME_CLINICIAN": "NAME.CLINICIAN",
    "NAME_OTHER": "NAME.OTHER",
    "DATE_TIME": "DATE",
    "AGE": "AGE",
    "LOCATION": "LOCATION",
    "HOSPITAL": "LOCATION.HOSPITAL",
    "US_ZIP_CODE": "LOCATION.ZIP",
    "ORGANIZATION": "ORGANIZATION",
    "PHONE_NUMBER": "CONTACT.PHONE",
    "PAGER_NUMBER": "CONTACT.PHONE",
    "FAX_NUMBER": "CONTACT.FAX",
    "EMAIL_ADDRESS": "CONTACT.EMAIL",
    "URL": "CONTACT.URL",
    "IP_ADDRESS": "CONTACT.IP",
    "US_SSN": "ID.SSN",
    "MEDICAL_RECORD_NUMBER": "ID.MRN",
    "ACCOUNT_NUMBER": "ID.ACCOUNT",
    "ACCESSION_NUMBER": "ID.OTHER",
    "OTHER_ID_NUMBER": "ID.OTHER",
    "HEALTH_PLAN_ID": "ID.HEALTHPLAN",
    "DEVICE_ID": "ID.DEVICE",
    "LICENSE_NUMBER": "ID.LICENSE",
    "US_DRIVER_LICENSE": "ID.LICENSE",
    "MEDICAL_LICENSE": "ID.LICENSE",
    "US_PASSPORT": "ID.OTHER",
    "US_ITIN": "ID.OTHER",
    "US_NPI": "ID.OTHER",
    "US_MBI": "ID.HEALTHPLAN",
    "US_BANK_NUMBER": "ID.ACCOUNT",
    "ABA_ROUTING_NUMBER": "ID.ACCOUNT",
    "CREDIT_CARD": "ID.ACCOUNT",
    "IBAN_CODE": "ID.ACCOUNT",
    "CRYPTO": "ID.ACCOUNT",
    "UUID": "ID.OTHER",
    "MAC_ADDRESS": "ID.DEVICE",
    "ID": "ID",
    "OTHER_PHI": "OTHER",
    "EMAIL": "CONTACT.EMAIL",
}

# Presidio emits these but they are not PHI in our ontology (nationality/religion/politics).
NON_PHI_PRESIDIO = {"NRP"}


def canonical_from_presidio(entity_type: str) -> Optional[str]:
    """Canonical code for a Presidio entity, or None when it is not PHI / unknown."""
    if entity_type in NON_PHI_PRESIDIO:
        return None
    return PRESIDIO_TO_CANONICAL.get(entity_type)


# Clinical NER model labels (obi/deid_roberta_i2b2) -> Presidio entity names used in this project.
# PATIENT and STAFF stay separate instead of collapsing into PERSON.
OBI_DEID_TO_PRESIDIO: Dict[str, str] = {
    "PATIENT": "NAME_PATIENT",
    "STAFF": "NAME_CLINICIAN",
    "HOSP": "HOSPITAL",
    "PATORG": "ORGANIZATION",
    "LOC": "LOCATION",
    "DATE": "DATE_TIME",
    "AGE": "AGE",
    "PHONE": "PHONE_NUMBER",
    "EMAIL": "EMAIL_ADDRESS",
    "ID": "ID",
    "OTHERPHI": "OTHER_PHI",
}

# Presidio research synthetic dataset (synth_dataset_v2.json) labels -> canonical.
HONORIFICS = {"mr.", "mrs.", "ms.", "miss", "dr.", "mr", "mrs", "ms", "dr", "mx.", "mx", "sir", "madam"}
SYNTH_V2_TO_CANONICAL: Dict[str, str] = {
    "PERSON": "NAME",
    "GPE": "LOCATION",
    "STREET_ADDRESS": "LOCATION.STREET",
    "ZIP_CODE": "LOCATION.ZIP",
    "ORGANIZATION": "ORGANIZATION",
    "DATE_TIME": "DATE",
    "AGE": "AGE",
    "CREDIT_CARD": "ID.ACCOUNT",
    "IBAN_CODE": "ID.ACCOUNT",
    "US_SSN": "ID.SSN",
    "US_DRIVER_LICENSE": "ID.LICENSE",
    "EMAIL_ADDRESS": "CONTACT.EMAIL",
    "PHONE_NUMBER": "CONTACT.PHONE",
    "IP_ADDRESS": "CONTACT.IP",
    "DOMAIN_NAME": "CONTACT.URL",
    "NRP": IGNORE,  # not PHI in our ontology; excluded from both recall and precision
}


def canonical_from_synth_v2(label: str, value: str) -> str:
    if label == "TITLE":  # honorifics are not PHI; job titles are i2b2 PROFESSION
        return IGNORE if value.strip().lower() in HONORIFICS else "PROFESSION"
    return SYNTH_V2_TO_CANONICAL[label]
