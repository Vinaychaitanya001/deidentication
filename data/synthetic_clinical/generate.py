"""Generate the synthetic clinical de-identification sets (dev.json, test.json).

Everything is invented: names, numbers, dates and places. Phone numbers use the
fictional 555-01xx range and emails use example.com.

Annotation guideline (gold PHI spans, canonical types from deid/ontology.py)
  * names: the name only - no title ("Mr.", "Dr.") and no credential ("MD");
    "SMITH, JOHN" is one span; patient / clinician / other person are separate types
  * ages: the number only ("92" in "92 y/o"); all ages are annotated
  * dates: the full date expression; years alone are annotated; clock times are
    "don't care" regions (ignored by the scorer)
  * addresses: street, city, state and ZIP are separate spans
  * IDs, phone, fax, pager, email: the value only, not the field label
  * hospitals, employers (ORGANIZATION) and occupations (PROFESSION)
Hard negatives (not PHI, annotated separately so false alarms can be counted):
  blood_pressure, scale, dose, fraction_dose, duration, frequency, measurement, eponym, code.

Dev and test use disjoint name/place pools and different phrasing and field labels,
so test is not the text the rules were tuned on. The same team wrote both splits,
so scores on this set are still optimistic for rule-based components.

    python data/synthetic_clinical/generate.py        # rewrites dev.json and test.json
"""

import datetime as dt
import json
import random
import re
from pathlib import Path

OUT_DIR = Path(__file__).resolve().parent
SEED = 20260929
SLOT = re.compile(r"\{(\w+)(?::([A-Z][A-Z.]*)|!([a-z_]+)|(~))?\}")


class Note:
    def __init__(self):
        self.parts, self.pos = [], 0
        self.phi, self.neg, self.ignore = [], [], []

    def _emit(self, s):
        self.parts.append(s)
        self.pos += len(s)

    def add(self, template, **v):
        last = 0
        for m in SLOT.finditer(template):
            self._emit(template[last:m.start()])
            key, typ, kind, ign = m.groups()
            val = str(v[key])
            rec = {"start": self.pos, "end": self.pos + len(val), "text": val}
            if typ:
                self.phi.append({**rec, "type": typ})
            elif kind:
                self.neg.append({**rec, "kind": kind})
            elif ign:
                self.ignore.append(rec)
            self._emit(val)
            last = m.end()
        self._emit(template[last:])

    def build(self):
        text = "".join(self.parts)
        for rec in self.phi + self.neg + self.ignore:
            assert text[rec["start"]:rec["end"]] == rec["text"], rec
        return text


# --------------------------------------------------------------------------- pools

POOLS = {
    "dev": dict(
        first_m=["John", "Robert", "James", "Michael", "David", "Carlos", "Wei", "Aarav", "Venkata", "Kwame", "Ahmed", "Noah", "Diego", "Hiroshi"],
        first_f=["Maria", "Linda", "Patricia", "Jennifer", "Elizabeth", "Sofia", "Mei", "Priya", "Lakshmi", "Amara", "Fatima", "Olivia", "Lucia", "Yuki"],
        last=["Smith", "Lopez", "Johnson", "Garcia", "Brown", "Nguyen", "Patel", "Reddy", "Chen", "Kim", "Okafor", "Hassan", "Miller", "Davis", "Wilson", "Rodriguez", "Anderson", "Thompson", "Rao", "Sharma", "Tanaka", "Mensah", "O'Brien", "Kowalski"],
        places=[("Quincy", "MA", "02169", "617"), ("Springfield", "IL", "62704", "217"), ("Dayton", "OH", "45402", "937"), ("Tucson", "AZ", "85701", "520"), ("Fresno", "CA", "93721", "559"), ("Albany", "NY", "12207", "518"), ("Madison", "WI", "53703", "608"), ("Tulsa", "OK", "74103", "918"), ("Raleigh", "NC", "27601", "919"), ("Boise", "ID", "83702", "208")],
        streets=["Maple Street", "Oak Avenue", "Pine Road", "Cedar Lane", "Elm Street", "Birch Drive", "Willow Way", "Lakeview Terrace"],
        hospitals=["{city} General Hospital", "St. Anne's Hospital", "Riverside Medical Center", "Lakeshore Community Hospital", "Mercy Regional Medical Center", "Holloway Memorial Hospital", "Mayo Clinic"],
        professions=["machinist", "school teacher", "truck driver", "accountant", "electrician", "software engineer"],
        employers=["Harbor Freight Logistics", "Northwind Foods", "Summit Tool Works"],
    ),
    "test": dict(
        first_m=["William", "Richard", "Joseph", "Thomas", "Daniel", "Luis", "Jian", "Rohan", "Srinivas", "Kofi", "Omar", "Ethan", "Mateo", "Kenji", "Ifeanyi"],
        first_f=["Barbara", "Susan", "Jessica", "Sarah", "Karen", "Valentina", "Lin", "Ananya", "Padma", "Zainab", "Leila", "Ava", "Isabella", "Sakura", "Chloe"],
        last=["Walker", "Hernandez", "Clark", "Lewis", "Young", "Tran", "Shah", "Naidu", "Wang", "Park", "Adeyemi", "Rahman", "Moore", "Taylor", "Jackson", "White", "Harris", "Sanchez", "Ramirez", "Chowdary", "Iyer", "Sato", "Boateng", "McCarthy", "Novak"],
        places=[("Worcester", "MA", "01608", "508"), ("Peoria", "IL", "61602", "309"), ("Akron", "OH", "44308", "330"), ("Mesa", "AZ", "85201", "480"), ("Modesto", "CA", "95354", "209"), ("Syracuse", "NY", "13202", "315"), ("Green Bay", "WI", "54301", "920"), ("Norman", "OK", "73069", "405"), ("Durham", "NC", "27701", "919"), ("Pocatello", "ID", "83201", "208")],
        streets=["Harbor Road", "River Street", "Hillcrest Drive", "Chestnut Avenue", "Meadow Lane", "Park Place", "Spring Street", "Orchard Court"],
        hospitals=["{city} Medical Center", "St. Catherine's Hospital", "Northgate Medical Center", "Valley View Hospital", "Brennan Memorial Hospital", "Pinecrest Health Center", "Cleveland Clinic"],
        professions=["carpenter", "bus driver", "pharmacist", "farmer", "chef", "librarian"],
        employers=["Bluestone Construction", "Crescent Textiles", "Pioneer Freight"],
    ),
}

CONDITIONS = ["hypertension", "type 2 diabetes", "hyperlipidemia", "COPD", "atrial fibrillation", "chronic kidney disease", "heart failure", "osteoarthritis"]
EPONYMS = ["Parkinson's disease", "Graves disease", "Hodgkin lymphoma", "Crohn's disease", "Bell's palsy", "Alzheimer's dementia", "Cushing syndrome", "Addison's disease"]
COMPLAINTS = ["chest pain", "shortness of breath", "abdominal pain", "fever and cough", "dizziness", "left leg swelling"]
MEDS = [("metoprolol", "25 mg", "BID"), ("lisinopril", "10 mg", "daily"), ("atorvastatin", "40 mg", "nightly"), ("furosemide", "40 mg", "BID"), ("apixaban", "5 mg", "BID"), ("metformin", "500 mg", "BID")]


def luhn_npi(rng):
    body = [rng.choice("12")] + [str(rng.randint(0, 9)) for _ in range(8)]
    digits = [int(x) for x in "80840" + "".join(body)]
    total = 0
    for i, d in enumerate(reversed(digits)):
        if i % 2 == 0:
            d *= 2
            d = d - 9 if d > 9 else d
        total += d
    return "".join(body) + str((10 - total % 10) % 10)


def fmt_date(d, style, rng):
    choice = rng.choice(style)
    if choice == "mdy":
        return d.strftime("%m/%d/%Y")
    if choice == "mdy_short":
        return f"{d.month}/{d.day}/{d.strftime('%y')}"
    if choice == "long":
        return f"{d.strftime('%B')} {d.day}, {d.year}"
    if choice == "iso":
        return d.isoformat()
    if choice == "dmy_mon":
        return d.strftime("%d-%b-%Y")
    if choice == "mon":
        return f"{d.strftime('%b')} {d.day}, {d.year}"
    raise ValueError(choice)


class Case:
    """One fictional patient encounter with consistent values."""

    def __init__(self, rng, pool, split):
        self.sex = rng.choice("MF")
        self.first = rng.choice(pool["first_m"] if self.sex == "M" else pool["first_f"])
        self.last = rng.choice(pool["last"])
        self.title = "Mr." if self.sex == "M" else rng.choice(["Ms.", "Mrs."])
        self.he, self.his = ("He", "his") if self.sex == "M" else ("She", "her")
        self.man = "man" if self.sex == "M" else "woman"
        self.admit = dt.date(2024, 1, 1) + dt.timedelta(days=rng.randint(0, 900))
        age = rng.randint(90, 97) if rng.random() < 0.18 else rng.randint(24, 88)
        self.dob = self.admit - dt.timedelta(days=int(age * 365.25) + rng.randint(1, 300))
        self.age = (self.admit - self.dob).days * 100 // 36525
        self.disch = self.admit + dt.timedelta(days=rng.randint(2, 9))
        self.fu = self.disch + dt.timedelta(days=rng.randint(7, 30))
        self.clin = (rng.choice(pool["first_f"] + pool["first_m"]), rng.choice(pool["last"]))
        self.clin2 = (rng.choice(pool["first_f"] + pool["first_m"]), rng.choice(pool["last"]))
        self.rel = (rng.choice(pool["first_f"] if self.sex == "M" else pool["first_m"]), self.last)
        self.relation = "wife" if self.sex == "M" else rng.choice(["husband", "son"])
        city, state, zipc, area = rng.choice(pool["places"])
        self.city, self.state, self.zip, self.area = city, state, zipc, area
        self.street = f"{rng.randint(12, 4899)} {rng.choice(pool['streets'])}"
        self.hospital = rng.choice(pool["hospitals"]).format(city=city)
        self.hospital2 = rng.choice([h for h in pool["hospitals"] if not h.startswith("{")])
        self.prof = rng.choice(pool["professions"])
        self.employer = rng.choice(pool["employers"])
        self.phone = f"({area}) 555-01{rng.randint(10, 99)}" if rng.random() < 0.5 else f"{area}-555-01{rng.randint(10, 99)}"
        self.fax = f"{area}-555-01{rng.randint(10, 99)}"
        self.rel_phone = f"{area}-555-01{rng.randint(10, 99)}"
        self.pager = str(rng.randint(40000, 79999)) if split == "dev" else f"{rng.randint(2, 8)}-{rng.randint(1000, 9999)}"
        self.email = f"{self.first.lower()}.{self.last.lower().replace(chr(39), '')}{rng.randint(10, 99)}@example.com"
        if split == "dev":
            self.mrn = str(rng.randint(1000000, 9999999))
            self.acct = f"A{rng.randint(10000000, 99999999)}"
            self.accession = f"RAD-{self.admit.year}-{rng.randint(1000, 999999):06d}"
            self.member = "".join(rng.choice("ABCDEFGHJKLMNPRSTUVWXYZ") for _ in range(3)) + str(rng.randint(100000000, 999999999))
        else:
            self.mrn = f"{rng.randint(10, 99)}-{rng.randint(100, 999)}-{rng.randint(100, 999)}"
            self.acct = str(rng.randint(10 ** 11, 10 ** 12 - 1))
            self.accession = f"S{self.admit.strftime('%y')}-{rng.randint(10000, 99999)}"
            self.member = rng.choice("WXYZ") + str(rng.randint(100000000, 999999999))
        self.npi = luhn_npi(rng)
        self.ssn = f"{rng.randint(100, 665)}-{rng.randint(10, 99)}-{rng.randint(1000, 9999)}"
        self.bp = f"{rng.randint(104, 178)}/{rng.randint(58, 102)}"
        self.pmh = rng.sample(CONDITIONS, 2)
        self.eponym = rng.choice(EPONYMS)
        self.complaint = rng.choice(COMPLAINTS)
        self.meds = rng.sample(MEDS, 3)


# --------------------------------------------------------------------------- building blocks
# Each block takes (note, case, rng, split). Dev and test use different phrasing and field labels.

def header(n, c, rng, split, title):
    d = lambda x: fmt_date(x, DATE_STYLES[split], rng)
    if split == "dev":
        n.add(f"{title}\nPatient: {{p:NAME.PATIENT}}        MRN: {{mrn:ID.MRN}}\n",
              p=f"{c.last.upper()}, {c.first.upper()}", mrn=c.mrn)
        n.add("DOB: {dob:DATE}             Admitted: {ad:DATE}\n", dob=d(c.dob), ad=d(c.admit))
        n.add("Attending: {cl:NAME.CLINICIAN}, MD\n", cl=f"{c.clin[0]} {c.clin[1]}")
    else:
        n.add(f"{title} - {{h:LOCATION.HOSPITAL}}\nPt Name: {{p:NAME.PATIENT}}   Medical Record Number: {{mrn:ID.MRN}}\n",
              h=c.hospital, p=f"{c.first} {c.last}", mrn=c.mrn)
        n.add("Date of Birth: {dob:DATE}   Admission Date: {ad:DATE}   Account Number: {acct:ID.ACCOUNT}\n",
              dob=d(c.dob), ad=d(c.admit), acct=c.acct)
        n.add("Attending Physician: Dr. {cl:NAME.CLINICIAN}\n", cl=f"{c.clin[0]} {c.clin[1]}")


def hpi(n, c, rng, split):
    comp_dur = rng.choice(["x3 days", "x2 days", "x1 week"]) if split == "dev" else rng.choice(["for 2 weeks", "for 4 days", "for the past 3 days"])
    if split == "dev":
        n.add("\nHPI: {t} {last:NAME.PATIENT} is a {age:AGE}-year-old {man} with {c1}, {c2} and {ep!eponym} "
              "admitted to {h:LOCATION.HOSPITAL} with {comp} {dur!duration}.\n",
              t=c.title, last=c.last, age=c.age, man=c.man, c1=c.pmh[0], c2=c.pmh[1], ep=c.eponym,
              h=c.hospital, comp=c.complaint, dur=comp_dur)
    else:
        n.add("\nHistory of present illness: {first:NAME.PATIENT} is a {age:AGE} y/o {man} with a history of {ep!eponym} "
              "and {c1} who reports {comp} {dur!duration}.\n",
              first=f"{c.first} {c.last}", age=c.age, man=c.man, ep=c.eponym, c1=c.pmh[0],
              comp=c.complaint, dur=comp_dur)


def vitals(n, c, rng, split):
    hr, rr, o2 = rng.randint(58, 118), rng.randint(12, 26), rng.randint(88, 99)
    t = f"{rng.uniform(36.4, 38.9):.1f}"
    if split == "dev":
        n.add("Vitals: BP {bp!blood_pressure}, HR {hr!measurement}, RR {rr!measurement}, T {t!measurement}, "
              "SpO2 {o2!measurement} on RA.\n", bp=c.bp, hr=hr, rr=rr, t=t, o2=f"{o2}%")
    else:
        n.add("On arrival blood pressure {bp!blood_pressure} mmHg, pulse {hr!measurement}, "
              "respiratory rate {rr!measurement}, temperature {t!measurement} C, O2 sat {o2!measurement}.\n",
              bp=c.bp, hr=hr, rr=rr, t=t, o2=f"{o2}%")


def exam(n, c, rng, split):
    s, p, r = rng.choice(["4/5", "3/5", "4+/5"]), f"{rng.randint(3, 9)}/10", rng.choice(["2+/4", "1+/4"])
    if split == "dev":
        n.add("Exam: strength {s!scale} in the left leg, {full!scale} strength on the right. Pain {p!scale}. "
              "Reflexes {r!scale} and symmetric.\n", s=s, full="5/5", p=p, r=r)
    else:
        n.add("Neuro: motor {s!scale} left upper extremity; DTRs {r!scale}. Reports pain {p!scale}; "
              "a {m!scale} systolic murmur is heard. Visual acuity {va!scale} OU.\n",
              s=s, r=r, p=p, m=rng.choice(["2/6", "3/6"]), va=rng.choice(["20/40", "20/25"]))


def labs(n, c, rng, split):
    vals = dict(na=rng.randint(131, 146), k=f"{rng.uniform(3.2, 5.4):.1f}", cr=f"{rng.uniform(0.6, 2.4):.1f}",
                wbc=f"{rng.uniform(4, 16):.1f}", hgb=f"{rng.uniform(8, 15):.1f}", a1c=f"{rng.uniform(5.6, 10.5):.1f}%",
                glu=rng.randint(78, 310))
    if split == "dev":
        n.add("Labs: Na {na!measurement}, K {k!measurement}, Cr {cr!measurement}, WBC {wbc!measurement}, "
              "Hgb {hgb!measurement}, A1c {a1c!measurement}.\n", **vals)
    else:
        n.add("Results: sodium {na!measurement}, potassium {k!measurement}, creatinine {cr!measurement}, "
              "glucose {glu!measurement}, hemoglobin {hgb!measurement}.\n", **vals)


def meds(n, c, rng, split):
    n.add("\nMedications:\n")
    for name, dose, freq in c.meds:
        if split == "dev":
            n.add("- {name} {dose!dose} PO {freq!frequency}\n", name=name, dose=dose, freq=freq)
        else:
            n.add("- {name} {dose!dose} by mouth {freq!frequency}\n", name=name, dose=dose,
                  freq={"BID": "twice daily", "daily": "once daily", "nightly": "at bedtime"}[freq])
    if split == "dev":
        n.add("- insulin glargine {u!dose} {f!frequency}\n", u=f"{rng.randint(10, 40)} units", f="qHS")
        n.add("- amoxicillin {d!dose} {f!frequency} {du!duration}\n", d="500 mg", f="q8h", du="x7 days")
    else:
        n.add("- acetaminophen {d!dose} {f!frequency} as needed\n", d="650 mg", f="every 6 hours")
        n.add("- take {fr!fraction_dose} tablet of warfarin daily\n", fr="1/2")


def social(n, c, rng, split):
    if split == "dev":
        n.add("\nSOCIAL: Retired {prof:PROFESSION}; lives with {his} {rel_type} {rel:NAME.OTHER} in {city:LOCATION.CITY}, "
              "{st:LOCATION.STATE}.\n", prof=c.prof, his=c.his, rel_type=c.relation, rel=c.rel[0],
              city=c.city, st=c.state)
    else:
        n.add("\nSocial history: works at {emp:ORGANIZATION} as a {prof:PROFESSION}. Lives at {street:LOCATION.STREET}, "
              "{city:LOCATION.CITY}, {st:LOCATION.STATE} {zip:LOCATION.ZIP}.\n",
              emp=c.employer, prof=c.prof, street=c.street, city=c.city, st=c.state, zip=c.zip)


def address_block(n, c, rng, split):
    if split == "dev":
        n.add("Address: {street:LOCATION.STREET}, {city:LOCATION.CITY}, {st:LOCATION.STATE} {zip:LOCATION.ZIP}\n",
              street=c.street, city=c.city, st=c.state, zip=c.zip)
        n.add("Phone: {ph:CONTACT.PHONE}   Email: {em:CONTACT.EMAIL}\n", ph=c.phone, em=c.email)
    else:
        n.add("Home address: {street:LOCATION.STREET}\n{city:LOCATION.CITY}, {st:LOCATION.STATE} {zip:LOCATION.ZIP}\n",
              street=c.street, city=c.city, st=c.state, zip=c.zip)
        n.add("Contact number {ph:CONTACT.PHONE}\n", ph=c.phone)


def plan(n, c, rng, split):
    d = lambda x: fmt_date(x, DATE_STYLES[split], rng)
    if split == "dev":
        n.add("\nPLAN: Follow up with Dr. {cl:NAME.CLINICIAN} on {fu:DATE}. Call {ph:CONTACT.PHONE} with questions.\n",
              cl=c.clin[1], fu=d(c.fu), ph=c.phone)
    else:
        n.add("\nPlan: return visit with {cl:NAME.CLINICIAN}, NP in {wk!duration}, on {fu:DATE}. "
              "Questions: {ph:CONTACT.PHONE}.\n", cl=f"{c.clin2[0]} {c.clin2[1]}", wk=rng.choice(["2 weeks", "10 days"]),
              fu=d(c.fu), ph=c.phone)


def signature(n, c, rng, split):
    d = lambda x: fmt_date(x, DATE_STYLES[split], rng)
    time = f"{rng.randint(7, 19):02d}:{rng.randint(0, 59):02d}"
    if split == "dev":
        n.add("\nElectronically signed by {cl:NAME.CLINICIAN}, MD on {sd:DATE} {tm~}\n",
              cl=f"{c.clin[0]} {c.clin[1]}", sd=d(c.disch), tm=time)
        n.add("cc: Dr. {cc:NAME.CLINICIAN}\n", cc=c.clin2[1])
    else:
        n.add("\nDictated by: {cl:NAME.CLINICIAN}, PA-C   Date: {sd:DATE} {tm~}\n",
              cl=f"{c.clin2[0]} {c.clin2[1]}", sd=d(c.disch), tm=time)
        n.add("Cosigned: {cl:NAME.CLINICIAN}, MD\n", cl=f"{c.clin[0]} {c.clin[1]}")


DATE_STYLES = {"dev": ["mdy", "mdy_short", "long"], "test": ["iso", "dmy_mon", "mon", "mdy"]}


# --------------------------------------------------------------------------- note types

def discharge(n, c, rng, split):
    header(n, c, rng, split, "DISCHARGE SUMMARY")
    hpi(n, c, rng, split)
    d = lambda x: fmt_date(x, DATE_STYLES[split], rng)
    if split == "dev":
        n.add("Hospital course: on {d1:DATE} {he} underwent cardiac catheterization. POD {pod!duration} was uneventful. "
              "Transferred from {h2:LOCATION.HOSPITAL} for further care.\n", d1=d(c.admit + dt.timedelta(days=1)),
              he=c.he.lower(), pod=rng.randint(1, 3), h2=c.hospital2)
    else:
        n.add("Course: {he} was started on IV antibiotics on {d1:DATE} and a {ep!eponym} was placed. "
              "Hospital day {hd!duration} {he2} was ambulating.\n", he=c.he, d1=d(c.admit + dt.timedelta(days=1)),
              ep="Foley catheter", hd=rng.randint(2, 4), he2=c.he.lower())
    vitals(n, c, rng, split)
    labs(n, c, rng, split)
    meds(n, c, rng, split)
    social(n, c, rng, split)
    plan(n, c, rng, split)
    signature(n, c, rng, split)


def progress(n, c, rng, split):
    d = lambda x: fmt_date(x, DATE_STYLES[split], rng)
    if split == "dev":
        n.add("PROGRESS NOTE\nName: {p:NAME.PATIENT} | Med Rec #: {mrn:ID.MRN} | Acct #: {acct:ID.ACCOUNT}\n"
              "Date of service: {ds:DATE}\nProvider: {cl:NAME.CLINICIAN}, MD\n",
              p=f"{c.first} {c.last}", mrn=c.mrn, acct=c.acct, ds=d(c.admit), cl=f"{c.clin[0]} {c.clin[1]}")
        n.add("\nS: {t} {last:NAME.PATIENT} reports {comp} since {since:DATE}. Denies fever.\n",
              t=c.title, last=c.last, comp=c.complaint, since=d(c.admit - dt.timedelta(days=4)))
    else:
        n.add("SOAP NOTE\nPatient: {p:NAME.PATIENT}   Unit No: {mrn:ID.MRN}\nVisit date: {ds:DATE}   "
              "Seen by: Dr. {cl:NAME.CLINICIAN}\n", p=f"{c.last}, {c.first}", mrn=c.mrn, ds=d(c.admit),
              cl=c.clin[1])
        n.add("\nSubjective: {age:AGE}{sx} with {c1}, feels better today. Wife {rel:NAME.OTHER} at bedside.\n",
              age=c.age, sx=c.sex, c1=c.pmh[0], rel=c.rel[0])
    vitals(n, c, rng, split)
    exam(n, c, rng, split)
    n.add("A/P: {c1}, continue current regimen. Recheck in {du!duration}.\n", c1=c.pmh[1],
          du=rng.choice(["2 weeks", "3 months"]))
    signature(n, c, rng, split)


def radiology(n, c, rng, split):
    d = lambda x: fmt_date(x, DATE_STYLES[split], rng)
    if split == "dev":
        n.add("RADIOLOGY REPORT\nPatient: {p:NAME.PATIENT}   MR#: {mrn:ID.MRN}\nAccession #: {acc:ID.OTHER}\n"
              "Exam date: {ed:DATE}\nOrdering physician: Dr. {cl:NAME.CLINICIAN}\n",
              p=f"{c.last}, {c.first}", mrn=c.mrn, acc=c.accession, ed=d(c.admit), cl=c.clin[1])
    else:
        n.add("CT CHEST WITH CONTRAST\nName: {p:NAME.PATIENT}   Medical Record Number: {mrn:ID.MRN}\n"
              "Accession No.: {acc:ID.OTHER}   Study date: {ed:DATE}\nReferring MD: {cl:NAME.CLINICIAN}\n",
              p=f"{c.first} {c.last}", mrn=c.mrn, acc=c.accession, ed=d(c.admit),
              cl=f"{c.clin[0]} {c.clin[1]}")
    n.add("\nComparison: prior study from {pd:DATE} at {h:LOCATION.HOSPITAL}.\n",
          pd=d(c.admit - dt.timedelta(days=rng.randint(60, 700))), h=c.hospital2)
    n.add("Findings: {sz!measurement} nodule in the right upper lobe, unchanged. No effusion. "
          "EF {ef!measurement} on prior echo.\n", sz=f"{rng.randint(4, 9)} mm", ef=f"{rng.randint(30, 60)}%")
    n.add("Impression: stable findings. Follow-up CT in {du!duration}.\n", du=rng.choice(["6 months", "12 months"]))
    n.add("\nRead by: {cl:NAME.CLINICIAN}, MD  Pager {pg:CONTACT.PHONE}\n", cl=f"{c.clin2[0]} {c.clin2[1]}", pg=c.pager)


def prescription(n, c, rng, split):
    d = lambda x: fmt_date(x, DATE_STYLES[split], rng)
    n.add("PRESCRIPTION\n{h:LOCATION.HOSPITAL}\n{street:LOCATION.STREET}, {city:LOCATION.CITY}, {st:LOCATION.STATE} {zip:LOCATION.ZIP}\n",
          h=c.hospital, street=f"{rng.randint(100, 999)} Medical Plaza", city=c.city, st=c.state, zip=c.zip)
    if split == "dev":
        n.add("Phone: {ph:CONTACT.PHONE}   Fax: {fx:CONTACT.FAX}\n", ph=c.phone, fx=c.fax)
        n.add("Patient: {p:NAME.PATIENT}   DOB: {dob:DATE}\nMember ID: {mem:ID.HEALTHPLAN}\n",
              p=f"{c.first} {c.last}", dob=d(c.dob), mem=c.member)
    else:
        n.add("Tel {ph:CONTACT.PHONE} | Fax # {fx:CONTACT.FAX}\n", ph=c.phone, fx=c.fax)
        n.add("Pt: {p:NAME.PATIENT}   Date of Birth: {dob:DATE}\nInsurance ID: {mem:ID.HEALTHPLAN}\n",
              p=f"{c.last}, {c.first}", dob=d(c.dob), mem=c.member)
    name, dose, freq = c.meds[0]
    n.add("\nRx: {name} {dose!dose}, take 1 tablet by mouth {freq!frequency}. Dispense #60, refills: 2.\n",
          name=name, dose=dose, freq=freq)
    n.add("Rx: prednisone {d!dose} daily {du!duration}.\n", d="20 mg", du="x5 days")
    n.add("\nPrescriber: {cl:NAME.CLINICIAN}, MD   NPI: {npi:ID.OTHER}   Date: {rd:DATE}\n",
          cl=f"{c.clin[0]} {c.clin[1]}", npi=c.npi, rd=d(c.disch))


def ed_note(n, c, rng, split):
    d = lambda x: fmt_date(x, DATE_STYLES[split], rng)
    if split == "dev":
        n.add("EMERGENCY DEPARTMENT NOTE\nPatient: {p:NAME.PATIENT}   MRN: {mrn:ID.MRN}   Arrival: {ar:DATE} {tm~}\n",
              p=f"{c.first.upper()} {c.last.upper()}", mrn=c.mrn, ar=d(c.admit), tm="03:15")
        n.add("\n{age:AGE} yo {man} brought by EMS from home in {city:LOCATION.CITY} with {comp} {du!duration}. "
              "GCS {g!scale}.\n", age=c.age, man=c.man, city=c.city, comp=c.complaint, du="x2 hours", g="15")
    else:
        n.add("ED PROVIDER NOTE\nPt Name: {p:NAME.PATIENT}   Encounter #: {acct:ID.ACCOUNT}   DOB: {dob:DATE}\n",
              p=f"{c.first} {c.last}", acct=c.acct, dob=d(c.dob))
        n.add("\nPatient is a {age:AGE} year old {man} from {city:LOCATION.CITY} presenting with {comp} that began "
              "{du!duration}. Glasgow coma scale {g!scale}.\n", age=c.age, man=c.man, city=c.city,
              comp=c.complaint, du="3 days ago", g="14")
    vitals(n, c, rng, split)
    n.add("SSN on file: {ssn:ID.SSN}\n", ssn=c.ssn)
    n.add("Emergency contact: {rel:NAME.OTHER} ({relation}) {rph:CONTACT.PHONE}\n",
          rel=f"{c.rel[0]} {c.rel[1]}", relation=c.relation, rph=c.rel_phone)
    n.add("Disposition: admitted to medicine under Dr. {cl:NAME.CLINICIAN}.\n", cl=c.clin[1])


def consult(n, c, rng, split):
    d = lambda x: fmt_date(x, DATE_STYLES[split], rng)
    if split == "dev":
        n.add("{h:LOCATION.HOSPITAL} - Cardiology Consultation\n{cd:DATE}\n\nDear Dr. {cl:NAME.CLINICIAN},\n\n",
              h=c.hospital, cd=d(c.admit), cl=c.clin2[1])
        n.add("Thank you for referring {p:NAME.PATIENT} (DOB {dob:DATE}), a {age:AGE}-year-old {man} with "
              "{ep!eponym} and {c1}.\n", p=f"{c.first} {c.last}", dob=d(c.dob), age=c.age, man=c.man,
              ep=c.eponym, c1=c.pmh[0])
    else:
        n.add("REFERRAL LETTER\nTo: {cl:NAME.CLINICIAN}, MD, {h:LOCATION.HOSPITAL}\nDate: {cd:DATE}\n\n",
              cl=f"{c.clin2[0]} {c.clin2[1]}", h=c.hospital2, cd=d(c.admit))
        n.add("Re: {p:NAME.PATIENT}, {age:AGE} years old, Medical Record Number {mrn:ID.MRN}\n\n",
              p=f"{c.first} {c.last}", age=c.age, mrn=c.mrn)
        n.add("I am referring this {man} with {ep!eponym} diagnosed in {yr:DATE} (ICD-10 {icd!code}).\n",
              man=c.man, ep=c.eponym, yr=c.admit.year - rng.randint(2, 9), icd=rng.choice(["G20", "E05.00", "C81.90"]))
    vitals(n, c, rng, split)
    exam(n, c, rng, split)
    n.add("Please contact my office at {ph:CONTACT.PHONE} or fax {fx:CONTACT.FAX}.\n\nSincerely,\n{cl:NAME.CLINICIAN}, MD\n",
          ph=c.phone, fx=c.fax, cl=f"{c.clin[0]} {c.clin[1]}")


def nursing(n, c, rng, split):
    d = lambda x: fmt_date(x, DATE_STYLES[split], rng)
    if split == "dev":
        n.add("NURSING NOTE {nd:DATE} {tm~}\nPt {p:NAME.PATIENT}, MRN {mrn:ID.MRN}, Rm {rm~}\n",
              nd=d(c.admit), tm="22:40", p=f"{c.last}, {c.first}", mrn=c.mrn, rm=rng.randint(200, 699))
        n.add("Pt resting comfortably. BP {bp!blood_pressure}, HR {hr!measurement}. {ep!eponym} draining clear urine. "
              "Turned {f!frequency}. Family ({rel:NAME.OTHER}) visited.\n", bp=c.bp, hr=rng.randint(60, 100),
              ep="Foley catheter", f="q2h", rel=c.rel[0])
    else:
        n.add("Nursing shift summary - {nd:DATE}\nPatient {p:NAME.PATIENT} (MR {mrn:ID.MRN})\n",
              nd=d(c.admit), p=f"{c.first} {c.last}", mrn=c.mrn)
        n.add("Vitals stable, blood pressure {bp!blood_pressure}. Babinski sign negative. Ambulated {dist!measurement} "
              "with assistance {f!frequency}. Weight {wt!measurement}.\n", bp=c.bp, dist="50 feet",
              f="three times", wt=f"{rng.randint(55, 110)} kg")
    n.add("Charge RN: {cl:NAME.CLINICIAN}, RN  pager {pg:CONTACT.PHONE}\n", cl=f"{c.clin2[0]} {c.clin2[1]}", pg=c.pager)


def pathology(n, c, rng, split):
    d = lambda x: fmt_date(x, DATE_STYLES[split], rng)
    if split == "dev":
        n.add("SURGICAL PATHOLOGY REPORT\nPatient: {p:NAME.PATIENT}   MRN: {mrn:ID.MRN}\n"
              "Accession #: {acc:ID.OTHER}   Collected: {cd:DATE}\n", p=f"{c.last.upper()}, {c.first.upper()}",
              mrn=c.mrn, acc=f"S{c.admit.strftime('%y')}-{rng.randint(10000, 99999)}", cd=d(c.admit))
    else:
        n.add("PATHOLOGY\nName: {p:NAME.PATIENT}   Specimen #: {acc:ID.OTHER}\nReceived: {cd:DATE}   "
              "Submitting physician: Dr. {cl:NAME.CLINICIAN}\n", p=f"{c.first} {c.last}",
              acc=f"SP-{rng.randint(100000, 999999)}", cd=d(c.admit), cl=c.clin[1])
    n.add("\nSpecimen: colon, biopsy. Size {sz!measurement}.\nDiagnosis: tubular adenoma; no evidence of "
          "{ep!eponym}. Ki-67 {ki!measurement}.\n", sz=f"{rng.uniform(0.3, 1.9):.1f} cm", ep="Hodgkin lymphoma",
          ki=f"{rng.randint(5, 40)}%")
    n.add("\nPathologist: {cl:NAME.CLINICIAN}, MD   {h:LOCATION.HOSPITAL}   CPT {cpt!code}\n",
          cl=f"{c.clin2[0]} {c.clin2[1]}", h=c.hospital, cpt="88305")


def operative(n, c, rng, split):
    d = lambda x: fmt_date(x, DATE_STYLES[split], rng)
    n.add("OPERATIVE REPORT\n")
    if split == "dev":
        n.add("Patient: {p:NAME.PATIENT}  MRN: {mrn:ID.MRN}  Date of surgery: {sd:DATE}\n"
              "Surgeon: {cl:NAME.CLINICIAN}, MD   Assistant: {as_:NAME.CLINICIAN}, PA-C\n",
              p=f"{c.first} {c.last}", mrn=c.mrn, sd=d(c.admit), cl=f"{c.clin[0]} {c.clin[1]}",
              as_=f"{c.clin2[0]} {c.clin2[1]}")
    else:
        n.add("Pt Name: {p:NAME.PATIENT}   Medical Record Number: {mrn:ID.MRN}\nProcedure date: {sd:DATE}   "
              "Surgeon: Dr. {cl:NAME.CLINICIAN}\n", p=f"{c.last}, {c.first}", mrn=c.mrn, sd=d(c.admit),
              cl=f"{c.clin[0]} {c.clin[1]}")
    n.add("\nProcedure: laparoscopic cholecystectomy. EBL {ebl!measurement}. Implant serial #: {sn:ID.DEVICE}.\n",
          ebl=f"{rng.randint(10, 150)} mL", sn=f"SN{rng.randint(10000000, 99999999)}")
    n.add("Cefazolin {d!dose} IV given {f!frequency} pre-incision. {he} tolerated the procedure well; "
          "discharge expected POD {pod!duration}.\n", d="2 g", f="once", he=c.he, pod=1)


def telephone(n, c, rng, split):
    d = lambda x: fmt_date(x, DATE_STYLES[split], rng)
    if split == "dev":
        n.add("TELEPHONE ENCOUNTER {td:DATE}\nCaller: {rel:NAME.OTHER} ({relation}) for patient {p:NAME.PATIENT}, "
              "MRN {mrn:ID.MRN}\nCallback: {ph:CONTACT.PHONE}\n", td=d(c.admit), rel=f"{c.rel[0]} {c.rel[1]}",
              relation=c.relation, p=f"{c.first} {c.last}", mrn=c.mrn, ph=c.rel_phone)
    else:
        n.add("Phone note - {td:DATE}\nSpoke with patient {p:NAME.PATIENT} (DOB {dob:DATE}) at {ph:CONTACT.PHONE}.\n",
              td=d(c.admit), p=f"{c.first} {c.last}", dob=d(c.dob), ph=c.phone)
    name, dose, freq = c.meds[1]
    n.add("Reports home BP {bp!blood_pressure} and dizziness {du!duration}. Advised to hold {name} {dose!dose} "
          "and recheck in {du2!duration}.\n", bp=c.bp, du=rng.choice(["x2 days", "for 3 days"]), name=name,
          dose=dose, du2="1 week")
    address_block(n, c, rng, split)
    n.add("Routed to Dr. {cl:NAME.CLINICIAN}; fax results to {fx:CONTACT.FAX}.\n", cl=c.clin[1], fx=c.fax)


NOTE_TYPES = [discharge, progress, radiology, prescription, ed_note, consult, nursing, pathology, operative, telephone]
COUNTS = {"dev": 60, "test": 40}


def generate(split: str):
    rng = random.Random(f"{SEED}-{split}")
    pool = POOLS[split]
    records = []
    for i in range(COUNTS[split]):
        note_type = NOTE_TYPES[i % len(NOTE_TYPES)]
        case = Case(rng, pool, split)
        n = Note()
        note_type(n, case, rng, split)
        text = n.build()
        records.append({
            "doc_id": f"{split}-{i:03d}",
            "note_type": note_type.__name__,
            "text": text,
            "phi": n.phi,
            "hard_negatives": n.neg,
            "ignore": n.ignore,
        })
    return records


def main():
    for split in ("dev", "test"):
        recs = generate(split)
        (OUT_DIR / f"{split}.json").write_text(json.dumps(recs, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        n_phi = sum(len(r["phi"]) for r in recs)
        n_neg = sum(len(r["hard_negatives"]) for r in recs)
        print(f"{split}: {len(recs)} notes, {n_phi} PHI spans, {n_neg} hard negatives")


if __name__ == "__main__":
    main()
