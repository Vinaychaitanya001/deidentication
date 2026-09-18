# OUR OWN code (not copied from microsoft/presidio).
#
# Upstream's predefined_recognizers/__init__.py additionally imports the
# ner/ (GLiNER, HuggingFaceNer, MedicalNER) and third_party/ (Azure AI
# Language, Azure Health De-identification, LangExtract) recognizers.
# Those require transformers+torch, gliner, azure SDKs and cloud
# credentials, so they are deliberately not vendored - see
# VENDORED_FILES.md. Everything else is imported exactly as upstream does,
# which is what makes RecognizerRegistry's EntityRecognizer.__subclasses__()
# discovery find them.

# --- NLP-engine-backed (NER) recognizers ---
from .nlp_engine_recognizers.spacy_recognizer import SpacyRecognizer
from .nlp_engine_recognizers.stanza_recognizer import StanzaRecognizer
from .nlp_engine_recognizers.transformers_recognizer import TransformersRecognizer

# --- Generic / language-agnostic recognizers ---
from .generic.credit_card_recognizer import CreditCardRecognizer
from .generic.crypto_recognizer import CryptoRecognizer
from .generic.date_recognizer import DateRecognizer
from .generic.email_recognizer import EmailRecognizer
from .generic.iban_recognizer import IbanRecognizer
from .generic.ip_recognizer import IpRecognizer
from .generic.mac_recognizer import MacAddressRecognizer
from .generic.phone_recognizer import PhoneRecognizer
from .generic.url_recognizer import UrlRecognizer
from .generic.uuid_recognizer import UuidRecognizer

# --- Country-specific recognizers ---
from .country_specific.australia.au_abn_recognizer import AuAbnRecognizer
from .country_specific.australia.au_acn_recognizer import AuAcnRecognizer
from .country_specific.australia.au_medicare_recognizer import AuMedicareRecognizer
from .country_specific.australia.au_tfn_recognizer import AuTfnRecognizer
from .country_specific.canada.ca_postal_code_recognizer import CaPostalCodeRecognizer
from .country_specific.canada.ca_sin_recognizer import CaSinRecognizer
from .country_specific.finland.fi_personal_identity_code_recognizer import FiPersonalIdentityCodeRecognizer
from .country_specific.germany.de_bsnr_recognizer import DeBsnrRecognizer
from .country_specific.germany.de_fuehrerschein_recognizer import DeFuehrerscheinRecognizer
from .country_specific.germany.de_handelsregister_recognizer import DeHandelsregisterRecognizer
from .country_specific.germany.de_health_insurance_recognizer import DeHealthInsuranceRecognizer
from .country_specific.germany.de_id_card_recognizer import DeIdCardRecognizer
from .country_specific.germany.de_kfz_recognizer import DeKfzRecognizer
from .country_specific.germany.de_lanr_recognizer import DeLanrRecognizer
from .country_specific.germany.de_passport_recognizer import DePassportRecognizer
from .country_specific.germany.de_plz_recognizer import DePlzRecognizer
from .country_specific.germany.de_social_security_recognizer import DeSocialSecurityRecognizer
from .country_specific.germany.de_tax_id_recognizer import DeTaxIdRecognizer
from .country_specific.germany.de_tax_number_recognizer import DeTaxNumberRecognizer
from .country_specific.germany.de_vat_id_recognizer import DeVatIdRecognizer
from .country_specific.india.in_aadhaar_recognizer import InAadhaarRecognizer
from .country_specific.india.in_gstin_recognizer import InGstinRecognizer
from .country_specific.india.in_pan_recognizer import InPanRecognizer
from .country_specific.india.in_passport_recognizer import InPassportRecognizer
from .country_specific.india.in_vehicle_registration_recognizer import InVehicleRegistrationRecognizer
from .country_specific.india.in_voter_recognizer import InVoterRecognizer
from .country_specific.italy.it_driver_license_recognizer import ItDriverLicenseRecognizer
from .country_specific.italy.it_fiscal_code_recognizer import ItFiscalCodeRecognizer
from .country_specific.italy.it_identity_card_recognizer import ItIdentityCardRecognizer
from .country_specific.italy.it_passport_recognizer import ItPassportRecognizer
from .country_specific.italy.it_vat_code import ItVatCodeRecognizer
from .country_specific.korea.kr_brn_recognizer import KrBrnRecognizer
from .country_specific.korea.kr_driver_license_recognizer import KrDriverLicenseRecognizer
from .country_specific.korea.kr_frn_recognizer import KrFrnRecognizer
from .country_specific.korea.kr_passport_recognizer import KrPassportRecognizer
from .country_specific.korea.kr_rrn_recognizer import KrRrnRecognizer
from .country_specific.nigeria.ng_nin_recognizer import NgNinRecognizer
from .country_specific.nigeria.ng_vehicle_registration_recognizer import NgVehicleRegistrationRecognizer
from .country_specific.philippines.ph_passport_recognizer import PhPassportRecognizer
from .country_specific.philippines.ph_tin_recognizer import PhTinRecognizer
from .country_specific.philippines.ph_umid_recognizer import PhUmidRecognizer
from .country_specific.poland.pl_pesel_recognizer import PlPeselRecognizer
from .country_specific.singapore.sg_fin_recognizer import SgFinRecognizer
from .country_specific.singapore.sg_uen_recognizer import SgUenRecognizer
from .country_specific.south_africa.za_company_registration_recognizer import ZaCompanyRegistrationRecognizer
from .country_specific.south_africa.za_driver_license_recognizer import ZaDriverLicenseRecognizer
from .country_specific.south_africa.za_id_number_recognizer import ZaIdNumberRecognizer
from .country_specific.south_africa.za_income_tax_number_recognizer import ZaIncomeTaxNumberRecognizer
from .country_specific.south_africa.za_license_plate_recognizer import ZaLicensePlateRecognizer
from .country_specific.south_africa.za_passport_recognizer import ZaPassportRecognizer
from .country_specific.south_africa.za_phone_number_recognizer import (
    ZaPhoneNumberRecognizer,
    ZaMobileNumberRecognizer,
    ZaTelephoneNumberRecognizer,
)
from .country_specific.south_africa.za_traffic_register_number_recognizer import ZaTrafficRegisterNumberRecognizer
from .country_specific.south_africa.za_vat_number_recognizer import ZaVatNumberRecognizer
from .country_specific.spain.es_nie_recognizer import EsNieRecognizer
from .country_specific.spain.es_nif_recognizer import EsNifRecognizer
from .country_specific.spain.es_passport_recognizer import EsPassportRecognizer
from .country_specific.sweden.se_organisationsnummer_recognizer import SeOrganisationsnummerRecognizer
from .country_specific.sweden.se_personnummer_recognizer import SePersonnummerRecognizer
from .country_specific.thai.th_tnin_recognizer import ThTninRecognizer
from .country_specific.turkey.tr_license_plate_recognizer import TrLicensePlateRecognizer
from .country_specific.turkey.tr_national_id_recognizer import TrNationalIdRecognizer
from .country_specific.uk.uk_driving_licence_recognizer import UkDrivingLicenceRecognizer
from .country_specific.uk.uk_nhs_recognizer import NhsRecognizer
from .country_specific.uk.uk_nino_recognizer import UkNinoRecognizer
from .country_specific.uk.uk_passport_recognizer import UkPassportRecognizer
from .country_specific.uk.uk_postcode_recognizer import UkPostcodeRecognizer
from .country_specific.uk.uk_vehicle_registration_recognizer import UkVehicleRegistrationRecognizer
from .country_specific.us.aba_routing_recognizer import AbaRoutingRecognizer
from .country_specific.us.medical_license_recognizer import MedicalLicenseRecognizer
from .country_specific.us.us_bank_recognizer import UsBankRecognizer
from .country_specific.us.us_driver_license_recognizer import UsLicenseRecognizer
from .country_specific.us.us_health_insurance_member_id_recognizer import UsHealthInsuranceMemberIdRecognizer
from .country_specific.us.us_healthcare_admin_recognizers import (
    UsPriorAuthorizationNumberRecognizer,
    UsClaimNumberRecognizer,
    UsPrescriptionNumberRecognizer,
    UsReferralNumberRecognizer,
    UsProviderTaxIdRecognizer,
)
from .country_specific.us.us_itin_recognizer import UsItinRecognizer
from .country_specific.us.us_mbi_recognizer import UsMbiRecognizer
from .country_specific.us.us_npi_recognizer import UsNpiRecognizer
from .country_specific.us.us_passport_recognizer import UsPassportRecognizer
from .country_specific.us.us_ssn_recognizer import UsSsnRecognizer

__all__ = [
    "AbaRoutingRecognizer",
    "AuAbnRecognizer",
    "AuAcnRecognizer",
    "AuMedicareRecognizer",
    "AuTfnRecognizer",
    "CaPostalCodeRecognizer",
    "CaSinRecognizer",
    "CreditCardRecognizer",
    "CryptoRecognizer",
    "DateRecognizer",
    "DeBsnrRecognizer",
    "DeFuehrerscheinRecognizer",
    "DeHandelsregisterRecognizer",
    "DeHealthInsuranceRecognizer",
    "DeIdCardRecognizer",
    "DeKfzRecognizer",
    "DeLanrRecognizer",
    "DePassportRecognizer",
    "DePlzRecognizer",
    "DeSocialSecurityRecognizer",
    "DeTaxIdRecognizer",
    "DeTaxNumberRecognizer",
    "DeVatIdRecognizer",
    "EmailRecognizer",
    "EsNieRecognizer",
    "EsNifRecognizer",
    "EsPassportRecognizer",
    "FiPersonalIdentityCodeRecognizer",
    "IbanRecognizer",
    "InAadhaarRecognizer",
    "InGstinRecognizer",
    "InPanRecognizer",
    "InPassportRecognizer",
    "InVehicleRegistrationRecognizer",
    "InVoterRecognizer",
    "IpRecognizer",
    "ItDriverLicenseRecognizer",
    "ItFiscalCodeRecognizer",
    "ItIdentityCardRecognizer",
    "ItPassportRecognizer",
    "ItVatCodeRecognizer",
    "KrBrnRecognizer",
    "KrDriverLicenseRecognizer",
    "KrFrnRecognizer",
    "KrPassportRecognizer",
    "KrRrnRecognizer",
    "MacAddressRecognizer",
    "MedicalLicenseRecognizer",
    "NgNinRecognizer",
    "NgVehicleRegistrationRecognizer",
    "NhsRecognizer",
    "PhPassportRecognizer",
    "PhTinRecognizer",
    "PhUmidRecognizer",
    "PhoneRecognizer",
    "PlPeselRecognizer",
    "SeOrganisationsnummerRecognizer",
    "SePersonnummerRecognizer",
    "SgFinRecognizer",
    "SgUenRecognizer",
    "SpacyRecognizer",
    "StanzaRecognizer",
    "ThTninRecognizer",
    "TrLicensePlateRecognizer",
    "TrNationalIdRecognizer",
    "TransformersRecognizer",
    "UkDrivingLicenceRecognizer",
    "UkNinoRecognizer",
    "UkPassportRecognizer",
    "UkPostcodeRecognizer",
    "UkVehicleRegistrationRecognizer",
    "UrlRecognizer",
    "UsBankRecognizer",
    "UsClaimNumberRecognizer",
    "UsHealthInsuranceMemberIdRecognizer",
    "UsItinRecognizer",
    "UsLicenseRecognizer",
    "UsMbiRecognizer",
    "UsNpiRecognizer",
    "UsPassportRecognizer",
    "UsPrescriptionNumberRecognizer",
    "UsPriorAuthorizationNumberRecognizer",
    "UsProviderTaxIdRecognizer",
    "UsReferralNumberRecognizer",
    "UsSsnRecognizer",
    "UuidRecognizer",
    "ZaCompanyRegistrationRecognizer",
    "ZaDriverLicenseRecognizer",
    "ZaIdNumberRecognizer",
    "ZaIncomeTaxNumberRecognizer",
    "ZaLicensePlateRecognizer",
    "ZaMobileNumberRecognizer",
    "ZaPassportRecognizer",
    "ZaPhoneNumberRecognizer",
    "ZaTelephoneNumberRecognizer",
    "ZaTrafficRegisterNumberRecognizer",
    "ZaVatNumberRecognizer",
]
