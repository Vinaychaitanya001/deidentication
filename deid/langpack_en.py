"""L2 English language pack: cue lexicons for the clinical detector pack (L3) and veto rules (L4).

Phase 1 ships English only. A pack loader and other languages (e.g. Telugu) are P2.9 / P3.3;
a new pack provides the same names.
"""

CODE = "en"

# L1 field labels -> what the value holds. Matching is case-insensitive; an optional suffix
# "#", "no.", "number" or "id" and a ":"/"#"/"=" separator may follow the label.
FIELD_KEYS = {
    "ID.MRN": ["mrn", "mr", "mr#", "med rec", "medical record", "unit no", "unit number", "hospital number",
               "chart"],
    "ID.ACCOUNT": ["acct", "account", "billing account", "encounter", "fin", "csn", "visit"],
    "ID.OTHER": ["accession", "acc", "specimen", "case", "requisition", "npi"],
    "ID.HEALTHPLAN": ["member", "insurance", "subscriber", "policy", "medicaid", "medicare", "health plan",
                      "beneficiary"],
    "ID.DEVICE": ["serial", "implant serial", "s/n", "device"],
    "ID.LICENSE": ["license", "licence", "dea"],
    "ID.SSN": ["ssn", "social security", "ss#"],
    "NAME.PATIENT": ["patient", "patient name", "pt", "pt name", "name", "re"],
    "NAME.CLINICIAN": ["attending", "attending physician", "attending md", "pcp", "primary care physician",
                       "primary care provider", "referring physician", "referring provider", "referring md",
                       "ordering physician", "ordering provider", "provider", "surgeon", "assistant",
                       "anesthesiologist", "consultant", "resident", "fellow", "dictated by", "signed by",
                       "electronically signed by", "cosigned", "cosigned by", "reviewed by", "read by", "seen by",
                       "prescriber", "pathologist", "radiologist", "charge rn", "nurse", "submitting physician", "cc"],
    "NAME.OTHER": ["emergency contact", "next of kin", "nok", "caller", "guardian", "contact person"],
    "DATE.BIRTH": ["dob", "d.o.b", "date of birth", "birth date", "birthdate"],
}
# Labels unambiguous enough to count without a ":"/"#" separator or suffix ("MRN 4829173", "DOB 3/1/50").
# Every other label needs one ("Account Number: ...", "Name: ...").
FIELD_KEYS_WITHOUT_SEPARATOR = {"mrn", "mr", "mr#", "med rec", "medical record", "unit no", "unit number", "acct",
                                "fin", "csn", "accession", "specimen", "npi", "dea", "ssn", "ss#", "dob", "d.o.b",
                                "date of birth", "birth date", "birthdate", "patient", "pt", "emergency contact"}

PERSON_TITLES = ["Dr", "DR", "Doctor", "Mr", "MR", "Mrs", "MRS", "Ms", "MS", "Miss", "Mx"]
CLINICIAN_TITLES = ["Dr", "DR", "Doctor"]
CREDENTIALS = ["MD", "M.D.", "DO", "D.O.", "RN", "NP", "PA-C", "PA", "FNP", "FNP-C", "DNP", "APRN", "CNM",
               "CRNA", "PharmD", "MBBS", "LPN"]

# Capitalised words that end a name match (field labels, credentials, common sentence starters).
NAME_STOPWORDS = {
    "MD", "DO", "RN", "NP", "PA", "DNP", "FNP", "APRN", "CNM", "CRNA", "PharmD", "MBBS", "LPN",
    "DOB", "MRN", "MR", "Age", "Sex", "Date", "Phone", "Tel", "Fax", "Pager", "Admitted", "Discharged", "Room",
    "Rm", "Unit", "Account", "Acct", "Accession", "Provider", "Attending", "Name", "Patient", "Pt", "Follow",
    "Call", "Please", "The", "On", "In", "At", "For", "With", "And", "Or", "Of", "To", "From", "Is", "Was",
    "Hospital", "Clinic", "Center", "Medical", "Encounter", "Visit", "Specimen", "Exam", "Study", "Procedure",
    "Surgeon", "Assistant", "Diagnosis", "History", "Plan", "Impression", "Findings", "Comparison", "Reports",
    "Denies", "Presents", "Seen", "Signed", "Dictated", "Cosigned", "Read", "Referring", "Submitting",
}

US_STATE_CODES = ["AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "DC", "FL", "GA", "HI", "ID", "IL", "IN", "IA",
                  "KS", "KY", "LA", "ME", "MD", "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ", "NM",
                  "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA",
                  "WV", "WI", "WY", "PR"]
US_STATE_NAMES = ["Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado", "Connecticut", "Delaware",
                  "Florida", "Georgia", "Hawaii", "Idaho", "Illinois", "Indiana", "Iowa", "Kansas", "Kentucky",
                  "Louisiana", "Maine", "Maryland", "Massachusetts", "Michigan", "Minnesota", "Mississippi",
                  "Missouri", "Montana", "Nebraska", "Nevada", "New Hampshire", "New Jersey", "New Mexico",
                  "New York", "North Carolina", "North Dakota", "Ohio", "Oklahoma", "Oregon", "Pennsylvania",
                  "Rhode Island", "South Carolina", "South Dakota", "Tennessee", "Texas", "Utah", "Vermont",
                  "Virginia", "Washington", "West Virginia", "Wisconsin", "Wyoming"]

HOSPITAL_SUFFIXES = ["Medical Center", "Medical Centre", "Health Center", "Health System", "Healthcare", "Hospital",
                     "Clinic", "Infirmary", "Rehabilitation Center", "Nursing Home", "Nursing Facility",
                     "Care Center", "Cancer Center", "Cancer Institute", "Heart Institute", "Surgical Center",
                     "Surgery Center"]
HOSPITAL_LEADING_STOPWORDS = {"The", "A", "An", "At", "To", "From", "In", "Our", "His", "Her", "Their", "This",
                              "That", "Transferred", "Admitted", "Seen", "Discharged", "And", "Or", "Dear", "Re",
                              "Prior", "Comparison", "Referred", "Pathologist"}
# Real, widely known US hospitals (a starter list; sites add their own facilities as a deny list).
HOSPITAL_GAZETTEER = ["Mayo Clinic", "Cleveland Clinic", "Johns Hopkins Hospital", "Massachusetts General Hospital",
                      "Brigham and Women's Hospital", "Beth Israel Deaconess Medical Center", "Mount Sinai Hospital",
                      "Cedars-Sinai Medical Center", "NewYork-Presbyterian Hospital", "Stanford Health Care",
                      "UCSF Medical Center", "Duke University Hospital", "Boston Children's Hospital",
                      "Dana-Farber Cancer Institute", "MD Anderson Cancer Center", "Memorial Sloan Kettering",
                      "Kaiser Permanente", "Northwestern Memorial Hospital", "Barnes-Jewish Hospital",
                      "Vanderbilt University Medical Center", "Michigan Medicine", "UCLA Medical Center"]

# Sizes in French units, not ages ("20F Foley"); stops the "72F" age pattern.
FRENCH_SIZE_NOUNS = ["Foley", "catheter", "cath", "sheath", "tube", "chest tube", "NG", "NGT", "OG", "drain",
                     "French", "Fr", "stent", "dilator", "introducer"]

# Hard-negative cues (P1.6).
BP_CUES = ["BP", "B/P", "blood pressure"]
SCALE_CUES = ["strength", "power", "motor", "MMT", "reflex", "reflexes", "DTR", "DTRs", "pain", "murmur",
              "visual acuity", "acuity", "vision", "graded", "grade", "score", "scored", "scale", "rated"]
SCALE_TRAILING_CUES = ["strength", "power", "reflexes", "DTRs", "systolic", "diastolic", "holosystolic", "murmur",
                       "pain"]
GCS_CUES = ["GCS", "Glasgow coma scale", "Apgar", "Apgars", "Apgar score", "Apgar scores"]
NAMED_SCORES = ["NIHSS", "MMSE", "MoCA", "PHQ-9", "PHQ-2", "GAD-7", "ECOG", "Karnofsky", "KPS", "Braden", "Morse",
                "MELD", "APACHE II", "CHA2DS2-VASc", "HAS-BLED", "CURB-65", "Wells", "Mallampati", "RASS", "CIWA",
                "COWS", "Aldrete", "Bishop"]
DOSE_UNITS = ["mg", "mcg", "µg", "ug", "g", "gm", "grams", "gram", "kg", "mL", "ml", "cc", "L", "units", "unit",
              "IU", "mEq", "meq", "mmol", "tab", "tabs", "tablet", "tablets", "cap", "caps", "capsule",
              "capsules", "puff", "puffs", "drop", "drops", "spray", "sprays"]
FRACTION_DOSE_NOUNS = ["tab", "tabs", "tablet", "tablets", "pill", "pills", "cap", "capsule", "dose", "strength"]
TIME_UNITS = ["minutes", "minute", "mins", "min", "hours", "hour", "hrs", "hr", "h", "days", "day", "d", "weeks",
              "week", "wks", "wk", "w", "months", "month", "mos", "mo", "years", "year", "yrs", "yr"]
DURATION_NOUNS = ["history", "course", "period", "duration", "supply", "trial"]
RELATIVE_WORDS = ["ago", "prior", "earlier", "later", "before"]
HOSPITAL_DAY_CUES = ["POD", "HD", "post-op day", "postop day", "postoperative day", "hospital day"]
FREQUENCY_ABBREVIATIONS = ["bid", "b.i.d.", "tid", "t.i.d.", "qid", "q.i.d.", "qhs", "q.h.s.", "prn", "p.r.n.",
                           "qd", "q.d.", "qod", "qam", "qpm", "qshift", "qweek", "qwk", "qday"]
FREQUENCY_PHRASES = ["once daily", "twice daily", "three times daily", "four times daily", "once a day",
                     "twice a day", "three times a day", "at bedtime", "nightly", "daily", "weekly",
                     "every other day", "as needed", "three times", "once", "twice"]
