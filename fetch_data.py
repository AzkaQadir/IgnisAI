"""Fetch Combustion Science investigations from NASA PSI and build data/investigations.json.

Schema fields are extracted from the PSI record text with fixed rules. Nothing is
inferred beyond what the text states; a field with no match is left empty and the
app shows "Not reported in source".

Run: python fetch_data.py
"""

import json
import re
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://psi.nasa.gov/geode-py/ws/repo"
PSI_PAGE = "https://psi.nasa.gov/physci/repo/data/investigations/{}"
OUT = Path(__file__).parent / "data" / "investigations.json"

NUM = r"(\d+(?:\.\d+)?)"
RANGE_SEP = r"\s*(?:%\s*)?(?:to|-|–|−|and|or)\s*"
# Sentences about non-test contexts (e.g. "real engines operate at 20-40 atm") are skipped.
OFF_TOPIC = re.compile(r"\bengines?\b", re.I)

# Unit conversions to the units shown in the app.
PRESSURE_TO_PSI = {"psia": 1.0, "psi": 1.0, "atm": 14.696, "kpa": 0.145038, "bar": 14.5038}
SPEED_TO_CMS = {"cm/s": 1.0, "mm/s": 0.1, "m/s": 100.0}

# Fuel name pattern -> (display name, phase)
FUELS = [
    (r"n-?heptane", "n-heptane", "liquid"),
    (r"n-?decane", "n-decane", "liquid"),
    (r"n-?dodecane", "n-dodecane", "liquid"),
    (r"n-?octane", "n-octane", "liquid"),
    (r"iso-?octane", "iso-octane", "liquid"),
    (r"methanol", "methanol", "liquid"),
    (r"ethanol", "ethanol", "liquid"),
    (r"propanol", "propanol", "liquid"),
    (r"hexanol", "hexanol", "liquid"),
    (r"methane", "methane", "gas"),
    (r"\bethane\b", "ethane", "gas"),
    (r"ethylene", "ethylene", "gas"),
    (r"propane", "propane", "gas"),
    (r"propylene", "propylene", "gas"),
    (r"butane", "butane", "gas"),
    (r"hydrogen", "hydrogen", "gas"),
    (r"dimethyl ether|\bDME\b", "dimethyl ether", "gas"),
    (r"\bPMMA\b|polymethyl ?methacrylate|acrylic", "PMMA (acrylic)", "solid"),
    (r"cotton[- ]fiberglass|\bSIBAL\b", "cotton-fiberglass (SIBAL)", "solid"),
    (r"\bNomex\b", "Nomex", "solid"),
    (r"\bDelrin\b", "Delrin", "solid"),
    (r"polyethylene", "polyethylene", "solid"),
    (r"silicone", "silicone", "solid"),
    (r"\bKapton\b", "Kapton", "solid"),
    (r"\bTeflon\b|\bPTFE\b", "Teflon (PTFE)", "solid"),
    (r"\bPyrell\b", "Pyrell foam", "solid"),
    (r"cellulose|lamp wick|filter paper", "cellulose", "solid"),
    (r"polycarbonate|\bLexan\b", "polycarbonate", "solid"),
    (r"\bUltem\b", "Ultem", "solid"),
    (r"wire insulation", "wire insulation", "solid"),
]

GEOMETRY = [
    (r"droplet", "Droplet"),
    (r"\bspher(e|ical)", "Sphere"),
    (r"cylind(er|rical)|\brods?\b", "Cylinder or rod"),
    (r"flat (sheet|sample|plate)|thin sheet|\bslab\b|\bsheets?\b", "Flat sheet"),
    (r"co-?flow", "Coflow burner"),
    (r"counter-?flow", "Counterflow burner"),
    (r"porous", "Porous burner"),
    (r"wire insulation", "Wire"),
]

MEASUREMENTS = [
    (r"\bcameras?\b|video|imag(ing|es)", "Video imaging"),
    (r"infrared|\bIR\b", "Infrared imaging"),
    (r"radiometer", "Radiometry"),
    (r"thermocouple", "Thermocouples"),
    (r"gas (chromatograph|analy[sz]er|sampl)", "Gas sampling"),
    (r"smoke detector", "Smoke detectors"),
    (r"particle (counter|size|sizing)|particulate|aerosol", "Particle measurement"),
    (r"\bsoot\b", "Soot"),
    (r"chemiluminescence|\bOH\*", "Chemiluminescence"),
    (r"flame spread rate|spread rate", "Flame spread rate"),
    (r"burning rate|burn rate|mass loss", "Burning rate"),
    (r"droplet (diameter|size)|burning histor", "Droplet diameter history"),
    (r"flame temperature|temperature (field|profile|measurement)", "Flame temperature"),
]

PILLARS = [
    (r"flammab|flame spread|limiting oxygen|\bLOI\b", "prevention"),
    (r"smoke|aerosol|fire detect", "detection"),
    (r"extingu|suppress", "suppression"),
]

# Pillars the challenge statement assigns to named investigations. These take precedence
# over keyword rules; records matching neither are "foundational".
CHALLENGE_PILLARS = {
    "BASS": "prevention", "BASS-II": "prevention", "SAFFIRE-I": "prevention",
    "SAFFIRE-II": "prevention", "SAFFIRE-III": "prevention", "ACME BRE": "prevention",
    "SAME": "detection", "SAME-R": "detection", "DAFT / DAFT-2": "detection",
    "FLEX": "suppression",
}

HARDWARE_GROUPS = [
    (r"\bACME\b", "ACME insert (CIR)"),
    (r"\bMDCA\b|Droplet Combustion App", "MDCA (CIR)"),
    (r"Glovebox|\bMSG\b", "Microgravity Science Glovebox (MSG)"),
    (r"Saffire|Cygnus", "Saffire (Cygnus)"),
    (r"Soot Diagnostic", "Comparative Soot Diagnostic hardware"),
]

DILUENTS = [
    (r"helium|\bHe\b", "helium"),
    (r"carbon dioxide|\bCO2\b", "carbon dioxide"),
    (r"nitrogen|\bN2\b", "nitrogen"),
    (r"\bSF6\b|sulfur hexafluoride", "sulfur hexafluoride"),
    (r"\bargon\b", "argon"),
    (r"\bxenon\b", "xenon"),
]

DILUENT_CONTEXT = re.compile(r"dilu|suppress|extingu|inert|\badd(ed|ing)\b|balance", re.I)

# Gravity notes the challenge statement gives that are not in the PSI record text.
CHALLENGE_GRAVITY_NOTES = {"PSI-22": "electric field used to mimic partial gravity (challenge statement)"}

# Values the challenge statement gives that are not in the PSI record text.
CHALLENGE_OXYGEN = {
    "PSI-159": {
        "min": None, "max": 85.0,
        "evidence": ["Challenge statement: in CFI-G tests an oxygen-nitrogen mixture of up to 85% oxygen "
                     "flowed from the spherical burner (the chamber held nitrogen and a flammable gas)."],
        "source": "Challenge statement",
    }
}

# Which kind of fire-safety controls and equipment a record informs (challenge objective 3),
# taken from its pillar. Ventilation is added when an airflow speed is reported.
PILLAR_EQUIPMENT = {
    "prevention": "Material selection and flammability limits",
    "detection": "Smoke and fire detectors",
    "suppression": "Extinguishers and suppressants",
}
SIZE_CONTEXT = re.compile(r"sample|droplet|burner|diameter|thick|width|wide|long|length|sheet|rod|sphere", re.I)
SIZE_EXCLUDE = re.compile(r"duct|cross section|chamber|enclosure", re.I)
SIZE = re.compile(r"(\d+(?:\.\d+)?(?:\s*(?:,|and|or|to|-|–)\s*\d+(?:\.\d+)?)*)\s*(mm|cm)\b(?!/)")
FIXED = re.compile(
    r"\b(held|kept|remained|maintained) (constant|fixed|the same|at)\b|\bconstant (pressure|oxygen|flow|temperature)"
    r"|\bat a (fixed|constant)\b|\bfixed (pressure|oxygen|flow|temperature)", re.I)

EXTRACTION_METHOD = (
    "Rule-based extraction from the PSI record text; values link to the sentence they came from. "
    "Pillar for investigations named in the challenge statement is taken from that statement."
)

TEST_VARIABLES = [
    (r"oxygen (concentration|level|mole fraction|content)|O2 concentration", "Oxygen concentration"),
    (r"pressure", "Pressure"),
    (r"flow (velocity|speed|rate)|airflow|air flow|velocit", "Airflow speed"),
    (r"diluent|helium|carbon dioxide|\bCO2\b|nitrogen|\bSF6\b", "Diluent or suppressant"),
    (r"droplet (diameter|size)|initial diameter", "Droplet size"),
    (r"electric field", "Electric field"),
    (r"thickness", "Sample thickness"),
    (r"heat flux", "Heat flux"),
    (r"strain rate|stretch", "Strain rate"),
    (r"fuel (type|composition)|different fuels", "Fuel type"),
]

FINDING_VERBS = re.compile(
    r"\b(showed|shown|found|demonstrated|revealed|observed|discovered|confirmed|"
    r"results (indicate|show|suggest))\b",
    re.I,
)
OXYGEN_WORD = re.compile(r"\b(oxygen|O2|O₂)\b", re.I)


def get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "IgnisAI data fetch"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def sentences(text):
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", text) if len(s.strip()) > 20]


def numeric_field(sents, pattern, convert, accept=None):
    """Return {min, max, evidence} for values matched by pattern, converted to the target unit."""
    values, evidence = [], []
    for s in sents:
        if OFF_TOPIC.search(s):
            continue
        found = False
        for m in re.finditer(pattern, s, re.I):
            if accept and not accept(s, m):
                continue
            unit = m.group(3).lower() if m.lastindex >= 3 and m.group(3) else None
            for g in (m.group(1), m.group(2)):
                if g:
                    values.append(round(float(g) * convert(unit), 2))
                    found = True
        if found:
            evidence.append(s)
    if not values:
        return None
    return {"min": min(values), "max": max(values), "evidence": evidence[:3]}


def oxygen_field(sents):
    pattern = NUM + r"(?:" + RANGE_SEP + NUM + r")?\s*(?:%|percent)()"

    def accept(s, m):
        window = s[max(0, m.start() - 60): m.end() + 40]
        return OXYGEN_WORD.search(window) and 0 < float(m.group(1)) <= 100

    pct = numeric_field(sents, pattern, lambda u: 1.0, accept)

    # Mole fractions (0.1 to 0.4 mole fraction) are converted to percent.
    frac_pattern = r"(0?\.\d+|1\.0)(?:" + RANGE_SEP + r"(0?\.\d+|1\.0))?\s*mole fraction()"
    frac = numeric_field(sents, frac_pattern, lambda u: 100.0,
                         lambda s, m: OXYGEN_WORD.search(s[max(0, m.start() - 60): m.end() + 40]))
    if not (pct and frac):
        return pct or frac
    return {"min": min(pct["min"], frac["min"]), "max": max(pct["max"], frac["max"]),
            "evidence": (pct["evidence"] + frac["evidence"])[:3]}


def pressure_field(sents):
    pattern = NUM + r"(?:" + RANGE_SEP + NUM + r")?\s*(psia|psi|atm|kPa|bar)\b"
    return numeric_field(sents, pattern, lambda u: PRESSURE_TO_PSI[u])


def airflow_field(sents):
    pattern = NUM + r"(?:" + RANGE_SEP + NUM + r")?\s*\b(cm/s|mm/s|m/s)"
    return numeric_field(sents, pattern, lambda u: SPEED_TO_CMS[u])


def keyword_list(text, rules):
    out = []
    for pat, label in rules:
        if re.search(pat, text, re.I) and label not in out:
            out.append(label)
    return out


def build_record(summary):
    acc = summary["Accession"]
    d = get_json(f"{API}/investigations/{acc}")
    title = d.get("title") or summary.get("Title", "")
    acronym = (d.get("investigationAcronym") or "").strip()
    sections = {
        "objective": d.get("objective") or "",
        "hypothesis": d.get("hypothesis") or "",
        "approach": d.get("approach") or "",
        "research_impacts": d.get("researchImpacts") or "",
    }
    keywords = summary.get("Keywords") or ""
    full_text = " ".join([title, keywords, *sections.values()])
    sents = sentences(full_text)

    fuels = [(name, phase) for pat, name, phase in FUELS if re.search(pat, full_text, re.I)]
    pi = next(
        (f"{c.get('firstName', '')} {c.get('lastName', '')}".strip()
         for c in d.get("contacts", [])
         if any("Principal" in r.get("annotationValue", "") for r in c.get("roles", []))),
        "",
    )
    if acronym in CHALLENGE_PILLARS:
        pillar, pillar_source = [CHALLENGE_PILLARS[acronym]], "Challenge statement"
    else:
        pillar = keyword_list(full_text, PILLARS) or ["foundational"]
        pillar_source = "Keyword rules on the PSI record text"
    platform = d.get("flightProgram") or summary.get("Flight Platform") or ""
    gravity = "Microgravity" if re.search(r"Space Station|Cygnus", platform) else ""
    if acc in CHALLENGE_GRAVITY_NOTES:
        gravity += f"; {CHALLENGE_GRAVITY_NOTES[acc]}"
    oxygen = oxygen_field(sents) or CHALLENGE_OXYGEN.get(acc)
    airflow = airflow_field(sents)
    equipment = [PILLAR_EQUIPMENT[p] for p in pillar if p in PILLAR_EQUIPMENT]
    if equipment and airflow:
        equipment.append("Cabin ventilation and airflow control")
    size_sents = [s for s in sents if SIZE_CONTEXT.search(s) and SIZE.search(s) and not SIZE_EXCLUDE.search(s)]
    sizes = list(dict.fromkeys(
        f"{n} {u}" for s in size_sents for v, u in SIZE.findall(s) for n in re.findall(NUM, v)
    ))
    fuel_size = {"values": sizes[:6], "evidence": size_sents[:3]} if sizes else None
    return {
        "id": acc,
        "acronym": acronym,
        "title": title,
        "name": acronym or title,
        "psi_url": PSI_PAGE.format(acc),
        "doi": d.get("doi") or "",
        "platform": d.get("flightProgram") or summary.get("Flight Platform") or "",
        "project_type": d.get("projectType") or "",
        "sub_area": d.get("subResearchArea") or "",
        "start_date": d.get("investigationStartDate") or "",
        "end_date": d.get("investigationEndDate") or "",
        "principal_investigator": pi,
        "hardware": d.get("experimentHardware") or "",
        "keywords": " ".join(keywords.split()),
        **sections,
        "publications": [p.get("title", "") for p in d.get("publications", []) if p.get("title")],
        "oxygen_pct": oxygen,
        "pressure_psi": pressure_field(sents),
        "airflow_cms": airflow,
        "fuel": [f[0] for f in fuels],
        "fuel_phase": sorted({f[1] for f in fuels}),
        "fuel_geometry": keyword_list(full_text, GEOMETRY),
        "fuel_size": fuel_size,
        "measurements": keyword_list(full_text, MEASUREMENTS),
        "pillar": pillar,
        "pillar_source": pillar_source,
        "hardware_group": keyword_list(f"{acronym} {d.get('experimentHardware') or ''}", HARDWARE_GROUPS),
        "diluents": keyword_list(" ".join(s for s in sents if DILUENT_CONTEXT.search(s)), DILUENTS),
        "gravity": gravity,
        "test_variables": keyword_list(full_text, TEST_VARIABLES),
        "fixed_conditions": [s for s in sents if FIXED.search(s)][:3],
        "equipment": equipment,
        "key_findings": [s for s in sents if FINDING_VERBS.search(s)][:3],
        "extraction_method": EXTRACTION_METHOD,
    }


def main():
    query = urllib.parse.urlencode({
        "q": "", "data_source": "psi", "data_type": "investigation", "size": 500,
        "ffield": "Research Area", "fvalue": "Combustion Science",
    })
    hits = get_json(f"{API}/search?{query}")["hits"]["hits"]
    records = []
    for h in hits:
        rec = build_record(h["_source"])
        records.append(rec)
        print(f"{rec['id']:8} {rec['name']}")
    records.sort(key=lambda r: int(r["id"].split("-")[1]))
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(records, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {len(records)} records to {OUT}")


if __name__ == "__main__":
    main()
