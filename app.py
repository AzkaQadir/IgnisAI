"""IgnisAI: microgravity combustion investigations from NASA PSI, organised for fire safety.

Run: streamlit run app.py   (data: python fetch_data.py)
"""

import html
import json
import math
import os
import re
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

DATA = Path(__file__).parent / "data" / "investigations.json"
NR = "Not reported in source"
SUBTITLE = "Microgravity combustion investigations from NASA PSI, organised for fire safety."
FOOTER = "Independent project. Not a NASA product. Data: NASA Physical Sciences Informatics."

# Exact display labels for schema fields.
L_OXYGEN = "Oxygen concentration (%)"
L_PRESSURE = "Pressure (psi)"
L_AIRFLOW = "Airflow speed (cm/s)"
L_FUEL = "Fuel"
L_PHASE = "Fuel phase (solid / liquid / gas)"
L_GEOMETRY = "Fuel geometry"
L_HARDWARE = "Hardware"
L_MEASUREMENTS = "Measurements"
L_PILLAR = "Fire-safety pillar (prevention / detection / suppression)"
L_VARIABLES = "Test variables"
L_FINDINGS = "Key findings"
L_DILUENTS = "Diluents"
L_GRAVITY = "Gravity"
L_SIZE = "Fuel size"
L_FIXED = "Fixed conditions"
L_EQUIPMENT = "Informs controls and equipment"
ACCENT = "#F2711C"
NEUTRAL = "#8A919C"

# Earth uses of NASA fire-safety work, as listed in the challenge statement.
EARTH_APPLICATIONS = {
    "Extinguishers and suppressants": "Fine-water-mist extinguishers developed for the ISS are used on Earth.",
    "Smoke and fire detectors": "NASA technology has led to improvements in smoke detection on Earth.",
    "Material selection and flammability limits": (
        "NASA technology has led to improved firefighter gear, including protective clothing and air tanks."
    ),
}

st.set_page_config(page_title="IgnisAI", layout="wide")

st.markdown(
    """
<style>
button[kind="primary"], [data-testid="stBaseButton-primary"],
[data-testid="stBaseButton-primaryFormSubmit"] { color: #14171C; }
table.ig-compare { width: 100%; border-collapse: collapse; }
table.ig-compare th, table.ig-compare td {
  border-bottom: 1px solid #2E3540; padding: 0.5rem 0.75rem;
  text-align: left; vertical-align: top;
}
table.ig-compare th:first-child, table.ig-compare td:first-child { color: #9AA1AB; width: 18%; }
.ig-mono { font-family: 'IBM Plex Mono', monospace; }
.ig-muted { color: #9AA1AB; }
.ig-notice { border: 1px solid #2E3540; background: #1E232B; padding: 0.75rem 1rem; border-radius: 0.5rem; }
</style>
""",
    unsafe_allow_html=True,
)


@st.cache_data
def load_records():
    return json.loads(DATA.read_text(encoding="utf-8"))


RECORDS = load_records()
BY_ID = {r["id"]: r for r in RECORDS}


def detail_url(rec):
    return f"/?id={rec['id']}"


def num(x):
    return f"{x:g}"


def fmt_range(value, unit):
    if not value:
        return NR
    lo, hi = value["min"], value["max"]
    if lo is None:
        return f"up to {num(hi)} {unit}"
    span = num(lo) if lo == hi else f"{num(lo)}–{num(hi)}"
    return f"{span} {unit}"


def fmt_size(value):
    return ", ".join(value["values"]) if value else NR


def fmt_list(values):
    return ", ".join(values) if values else NR


def fmt_text(value):
    return value.strip() if value and value.strip() else NR


def header(page_heading):
    st.title("IgnisAI")
    st.caption(SUBTITLE)
    st.header(page_heading)


def notice(text):
    """Neutral notice box; st.info/st.warning would add a second accent colour."""
    st.markdown(f'<div class="ig-notice">{html.escape(text)}</div>', unsafe_allow_html=True)


def footer():
    st.divider()
    st.caption(FOOTER)


def record_link(rec, label=None):
    st.page_link(PAGES["investigations"], label=label or rec["name"], query_params={"id": rec["id"]})


def schema_values(rec):
    return {
        L_FUEL: fmt_list(rec["fuel"]),
        L_PHASE: fmt_list(rec["fuel_phase"]),
        L_GEOMETRY: fmt_list(rec["fuel_geometry"]),
        L_SIZE: fmt_size(rec["fuel_size"]),
        L_OXYGEN: fmt_range(rec["oxygen_pct"], "%"),
        L_PRESSURE: fmt_range(rec["pressure_psi"], "psi"),
        L_AIRFLOW: fmt_range(rec["airflow_cms"], "cm/s"),
        L_DILUENTS: fmt_list(rec["diluents"]),
        L_GRAVITY: fmt_text(rec["gravity"]),
        L_HARDWARE: fmt_text(rec["hardware"]),
        L_MEASUREMENTS: fmt_list(rec["measurements"]),
        L_PILLAR: fmt_list(rec["pillar"]),
        L_EQUIPMENT: fmt_list(rec["equipment"]),
        L_VARIABLES: fmt_list(rec["test_variables"]),
    }


# ---------------------------------------------------------------- Investigations


def investigation_detail(rec):
    st.title("IgnisAI")
    st.caption(SUBTITLE)
    st.page_link(PAGES["investigations"], label="All investigations")
    st.header(rec["name"])
    if rec["acronym"]:
        st.write(rec["title"])
    st.markdown(
        f"`{rec['id']}` · [PSI record]({rec['psi_url']})"
        + (f" · DOI `{rec['doi']}`" if rec["doi"] else "")
    )

    left, right = st.columns(2, gap="large")
    with left:
        st.subheader("Test conditions")
        for label, key, unit in (
            (L_OXYGEN, "oxygen_pct", "%"),
            (L_PRESSURE, "pressure_psi", "psi"),
            (L_AIRFLOW, "airflow_cms", "cm/s"),
        ):
            value = rec[key]
            st.markdown(f"**{label}**  \n" + (f"`{fmt_range(value, unit)}`" if value else NR))
            if value:
                with st.expander("Source text"):
                    for sentence in value["evidence"]:
                        st.markdown(f"> {sentence}")
        for label in (L_DILUENTS, L_GRAVITY):
            st.markdown(f"**{label}**  \n{schema_values(rec)[label]}")
        st.markdown(f"**{L_VARIABLES}** (what differed between tests)  \n{fmt_list(rec['test_variables'])}")
        st.markdown(f"**{L_FIXED}** (what stayed the same)")
        if rec["fixed_conditions"]:
            for sentence in rec["fixed_conditions"]:
                st.markdown(f"> {sentence}")
        else:
            st.write(NR)
    with right:
        st.subheader("Fuel and hardware")
        for label in (L_FUEL, L_PHASE, L_GEOMETRY):
            st.markdown(f"**{label}**  \n{schema_values(rec)[label]}")
        st.markdown(f"**{L_SIZE}**  \n" + (f"`{fmt_size(rec['fuel_size'])}`" if rec["fuel_size"] else NR))
        if rec["fuel_size"]:
            with st.expander("Source text"):
                for sentence in rec["fuel_size"]["evidence"]:
                    st.markdown(f"> {sentence}")
        for label in (L_HARDWARE, L_MEASUREMENTS):
            st.markdown(f"**{label}**  \n{schema_values(rec)[label]}")
        st.markdown(f"**{L_PILLAR}**  \n{fmt_list(rec['pillar'])}  \n"
                    f"<span class='ig-muted'>Source: {rec['pillar_source']}</span>", unsafe_allow_html=True)

    st.subheader("Fire-safety controls and equipment")
    if rec["equipment"]:
        for item in rec["equipment"]:
            st.markdown(f"- {item}")
        earth = [EARTH_APPLICATIONS[e] for e in rec["equipment"] if e in EARTH_APPLICATIONS]
        if earth:
            st.markdown("**Related Earth applications of NASA fire-safety work** (challenge statement)")
            for line in earth:
                st.markdown(f"- {line}")
    else:
        st.write("Foundational combustion research; no direct link to fire-safety equipment in the record.")

    st.subheader(L_FINDINGS)
    if rec["key_findings"]:
        for finding in rec["key_findings"]:
            st.markdown(f"- {finding}")
    else:
        st.write(NR)

    st.subheader("Source record")
    meta = {
        "Platform": fmt_text(rec["platform"]),
        "Project type": fmt_text(rec["project_type"]),
        "Sub-research area": fmt_text(rec["sub_area"]),
        "Principal investigator": fmt_text(rec["principal_investigator"]),
        "Investigation dates": (
            f"`{rec['start_date']}` to `{rec['end_date']}`"
            if rec["start_date"] and rec["end_date"] else NR
        ),
    }
    st.markdown("  \n".join(f"**{k}:** {v}" for k, v in meta.items()))
    for label, key in (
        ("Objective", "objective"),
        ("Hypothesis", "hypothesis"),
        ("Approach", "approach"),
        ("Research impacts", "research_impacts"),
    ):
        with st.expander(label):
            st.write(fmt_text(rec[key]))
    with st.expander("Publications"):
        if rec["publications"]:
            for title in rec["publications"]:
                st.markdown(f"- {title}")
        else:
            st.write(NR)
    st.caption(
        f"Extraction method: {rec['extraction_method']} "
        "Pressures stated in atm or kPa are converted to psi; mole fractions are converted to %."
    )
    footer()


def investigations_page():
    rec = BY_ID.get(st.query_params.get("id", ""))
    if rec:
        investigation_detail(rec)
        return

    header("Investigations")

    with st.sidebar:
        st.subheader("Filters")
        search = st.text_input("Name or keyword")
        pillars = st.multiselect(
            L_PILLAR, ["prevention", "detection", "suppression", "foundational"]
        )
        phases = st.multiselect(L_PHASE, ["solid", "liquid", "gas"])
        hardware = st.multiselect(
            L_HARDWARE, sorted({g for r in RECORDS for g in r["hardware_group"]})
        )
        equipment = st.multiselect(
            L_EQUIPMENT, sorted({e for r in RECORDS for e in r["equipment"]})
        )
        o2_range = st.slider(L_OXYGEN, 0, 100, (0, 100))
        flow_range = st.slider(L_AIRFLOW, 0, 100, (0, 100))
        st.caption("Narrowing a range hides records that do not report that value.")

    def keep(r):
        if search:
            hay = " ".join([r["name"], r["title"], r["keywords"], r["id"]]).lower()
            if search.lower() not in hay:
                return False
        if pillars and not set(pillars) & set(r["pillar"]):
            return False
        if phases and not set(phases) & set(r["fuel_phase"]):
            return False
        if hardware and not set(hardware) & set(r["hardware_group"]):
            return False
        if equipment and not set(equipment) & set(r["equipment"]):
            return False
        for key, (lo, hi) in (("oxygen_pct", o2_range), ("airflow_cms", flow_range)):
            if (lo, hi) != (0, 100):
                value = r[key]
                if not value or value["max"] < lo or (value["min"] or 0) > hi:
                    return False
        return True

    shown = [r for r in RECORDS if keep(r)]
    st.write(f"{len(shown)} investigations, {len(RECORDS) - len(shown)} filtered out")

    rows = [
        {"Investigation": r["name"], "PSI id": r["id"], **schema_values(r), "PSI record": r["psi_url"]}
        for r in shown
    ]
    table = pd.DataFrame(rows, columns=["Investigation", "PSI id", *schema_values(RECORDS[0]), "PSI record"])
    display = table.copy()
    # The link target carries the name after '#' so the cell can display it.
    display["Investigation"] = [f"{detail_url(r)}#{r['name']}" for r in shown]

    st.dataframe(
        display,
        hide_index=True,
        width="stretch",
        column_config={
            "Investigation": st.column_config.LinkColumn(display_text=r"#(.*)$"),
            "PSI record": st.column_config.LinkColumn(display_text="Open in PSI"),
        },
    )
    st.download_button(
        "Download CSV",
        table.to_csv(index=False).encode("utf-8"),
        file_name="ignisai_investigations.csv",
        mime="text/csv",
    )
    footer()


# ---------------------------------------------------------------- Compare


def compare_page():
    header("Compare")
    picked = st.multiselect(
        "Investigations (two or three)",
        [r["id"] for r in RECORDS],
        default=["PSI-68", "PSI-69"],
        max_selections=3,
        format_func=lambda i: f"{BY_ID[i]['name']} ({i})",
    )
    if len(picked) < 2:
        notice("Select at least two investigations.")
        footer()
        return

    recs = [BY_ID[i] for i in picked]
    esc = html.escape
    head = "".join(
        f'<th><a href="{detail_url(r)}" target="_self">{esc(r["name"])}</a>'
        f'<br><span class="ig-mono ig-muted">{r["id"]}</span></th>'
        for r in recs
    )
    numeric_labels = {L_OXYGEN, L_PRESSURE, L_AIRFLOW}
    body = ""
    for label in schema_values(recs[0]):
        cells = ""
        for r in recs:
            value = schema_values(r)[label]
            cls = ' class="ig-mono"' if label in numeric_labels and value != NR else ""
            cells += f"<td{cls}>{esc(value)}</td>"
        body += f"<tr><td>{esc(label)}</td>{cells}</tr>"
    findings = "".join(
        "<td>" + (esc(r["key_findings"][0]) if r["key_findings"] else NR) + "</td>" for r in recs
    )
    body += f"<tr><td>{L_FINDINGS}</td>{findings}</tr>"
    st.markdown(
        f'<table class="ig-compare"><thead><tr><th></th>{head}</tr></thead><tbody>{body}</tbody></table>',
        unsafe_allow_html=True,
    )
    st.caption(f"{L_FINDINGS} shows the first finding sentence in each record; open an investigation for all of them.")
    footer()


# ---------------------------------------------------------------- Relevance ranking

# Atmospheres: ISS cabin values, and the exploration atmosphere expected for lunar bases and
# pressurized rovers (30 % oxygen or more at 10.2 psi or less). Mars uses the same assumption.
ENVIRONMENTS = {
    "Spacecraft cabin": {"o2": 21.0, "p": 14.7, "surface": False},
    "Space station": {"o2": 21.0, "p": 14.7, "surface": False},
    "Lunar surface base": {"o2": 30.0, "p": 10.2, "surface": True},
    "Martian surface base": {"o2": 30.0, "p": 10.2, "surface": True},
    "Pressurized rover": {"o2": 30.0, "p": 10.2, "surface": True},
}
CABIN_AIRFLOW = (7.6, 20.3)  # cm/s, ISS cabin ventilation requirement (0.076–0.203 m/s)
FUEL_REALISM = {"solid": 1.0, "liquid": 0.5, "gas": 0.25}
# Distance (in field units) at which an atmosphere or flow score falls to zero.
SCALES = {"oxygen_pct": 10.0, "pressure_psi": 5.0, "airflow_cms": 20.0}
CRITERIA = ("Fire-safety objective", "Fuel realism", "Atmosphere overlap", "Cabin airflow", "Gravity relevance")


def range_score(value, lo_target, hi_target, scale):
    """1 when the reported range overlaps the target range, falling linearly with distance."""
    if not value:
        return 0.0
    lo, hi = value["min"], value["max"]
    if lo is None:  # "up to" values: only the upper bound is known
        lo = hi if hi < lo_target else lo_target
    if hi >= lo_target and lo <= hi_target:
        return 1.0
    distance = lo - hi_target if lo > hi_target else lo_target - hi
    return max(0.0, 1.0 - distance / scale)


def score_record(r, env):
    pillars = set(r["pillar"]) & {"prevention", "detection", "suppression"}
    o2 = range_score(r["oxygen_pct"], env["o2"], env["o2"], SCALES["oxygen_pct"])
    p = range_score(r["pressure_psi"], env["p"], env["p"], SCALES["pressure_psi"])
    microgravity = r["gravity"].startswith("Microgravity")
    if env["surface"]:
        gravity = 0.75 if "partial gravity" in r["gravity"] else 0.5 if microgravity else 0.0
    else:
        gravity = 1.0 if microgravity else 0.0
    scores = {
        "Fire-safety objective": 1.0 if pillars else 0.0,
        "Fuel realism": max((FUEL_REALISM[ph] for ph in r["fuel_phase"]), default=0.0),
        "Atmosphere overlap": (o2 + p) / 2,
        "Cabin airflow": range_score(r["airflow_cms"], *CABIN_AIRFLOW, SCALES["airflow_cms"]),
        "Gravity relevance": gravity,
    }
    basis = {
        "Fire-safety objective": f"{fmt_list(r['pillar'])} ({r['pillar_source'].lower()})",
        "Fuel realism": fmt_list(r["fuel_phase"]),
        "Atmosphere overlap": f"{fmt_range(r['oxygen_pct'], '%')}; {fmt_range(r['pressure_psi'], 'psi')}",
        "Cabin airflow": fmt_range(r["airflow_cms"], "cm/s"),
        "Gravity relevance": fmt_text(r["gravity"]),
    }
    return 100 * sum(scores.values()) / len(scores), scores, basis


def ranking_page():
    header("Relevance ranking")
    st.subheader("Heuristic ranking")

    name = st.selectbox("Environment", list(ENVIRONMENTS))
    env = ENVIRONMENTS[name]
    st.markdown(
        f"Atmosphere used: `{num(env['o2'])} %` oxygen at `{num(env['p'])} psi`; "
        f"{'surface gravity (partial gravity)' if env['surface'] else 'microgravity'}."
    )
    if env["surface"]:
        notice(
            "PSI has no partial-gravity combustion data. For surface bases, microgravity results "
            "bound the expected behaviour only together with normal-gravity results."
        )

    with st.expander("How the score is calculated", expanded=True):
        st.markdown(
            f"""
Each investigation gets five criterion scores between `0` and `1`. Score = mean × `100`.

- **Fire-safety objective**: `1` if the record has a prevention, detection or suppression pillar; `0` if foundational.
- **Fuel realism**: solid `1`, liquid `0.5`, gas `0.25` (cabin fires burn solid materials). Best phase tested counts.
- **Atmosphere overlap**: mean of the oxygen and pressure scores. Each is `1` when the reported range
  includes the environment value and falls to `0` at `{num(SCALES['oxygen_pct'])} %` or
  `{num(SCALES['pressure_psi'])} psi` away.
- **Cabin airflow**: `1` when the reported airflow overlaps `{num(CABIN_AIRFLOW[0])}–{num(CABIN_AIRFLOW[1])} cm/s`
  (ISS cabin ventilation), falling to `0` at `{num(SCALES['airflow_cms'])} cm/s` away.
- **Gravity relevance**: spacecraft and station: microgravity `1`. Surface bases: microgravity `0.5`,
  partial-gravity mimic `0.75`, because microgravity only bounds partial-gravity behaviour.
- A field marked "{NR}" scores `0`. A value given as "up to" a maximum counts as covering everything below it.

Lunar and Martian bases and rovers use the expected exploration atmosphere (`30 %` oxygen or more at
`10.2 psi` or less); the Martian value is an assumption. This ranking is a heuristic for choosing what to
read first. It is not a NASA assessment or a measure of fire risk.
"""
        )

    ranked = sorted(
        ((*score_record(r, env), r) for r in RECORDS),
        key=lambda x: (-x[0], x[3]["id"]),
    )
    rows = []
    for i, (score, scores, basis, r) in enumerate(ranked):
        row = {"Rank": i + 1, "Investigation": f"{detail_url(r)}#{r['name']}", "Score (0–100)": round(score, 1)}
        for c in CRITERIA:
            row[f"{c} (0–1)"] = round(scores[c], 2)
            row[f"{c}: basis"] = basis[c]
        row["PSI record"] = r["psi_url"]
        rows.append(row)

    st.dataframe(
        pd.DataFrame(rows),
        hide_index=True,
        width="stretch",
        column_config={
            "Investigation": st.column_config.LinkColumn(display_text=r"#(.*)$"),
            "PSI record": st.column_config.LinkColumn(display_text="Open in PSI"),
        },
    )
    st.caption("Open an investigation to see the source sentence behind each value.")
    evidence_gap(name, env)
    footer()


def evidence_gap(env_name, env):
    st.subheader("Evidence gap: tested oxygen and pressure")
    both = [r for r in RECORDS if r["oxygen_pct"] and r["pressure_psi"]]
    o2_only = [r for r in RECORDS if r["oxygen_pct"] and not r["pressure_psi"]]
    p_only = [r for r in RECORDS if r["pressure_psi"] and not r["oxygen_pct"]]
    st.markdown(
        f"Of {len(RECORDS)} investigations, `{len(both)}` report both oxygen concentration and pressure, "
        f"`{len(o2_only)}` report oxygen only and `{len(p_only)}` report pressure only. "
        "Boxes show the tested ranges; points show reference atmospheres."
    )
    boxes = pd.DataFrame([
        {
            "Investigation": r["name"],
            "o2_lo": r["oxygen_pct"]["min"] if r["oxygen_pct"]["min"] is not None else 0,
            "o2_hi": r["oxygen_pct"]["max"],
            "p_lo": r["pressure_psi"]["min"], "p_hi": r["pressure_psi"]["max"],
            "Oxygen": fmt_range(r["oxygen_pct"], "%"), "Pressure": fmt_range(r["pressure_psi"], "psi"),
        }
        for r in both
    ])
    refs = pd.DataFrame([
        {"Atmosphere": "Earth sea level and ISS", "o2": 21.0, "p": 14.7},
        {"Atmosphere": "Moon base and rovers (expected)", "o2": 30.0, "p": 10.2},
        {"Atmosphere": "Spacesuit", "o2": 100.0, "p": 4.3},
    ])
    refs["Selected"] = (refs["o2"] == env["o2"]) & (refs["p"] == env["p"])
    x = alt.Scale(domain=[0, 100])
    y = alt.Scale(domain=[0, 50])
    layers = []
    if not boxes.empty:
        layers.append(
            alt.Chart(boxes).mark_rect(opacity=0.35, color=NEUTRAL, stroke=NEUTRAL, strokeWidth=1.5).encode(
                x=alt.X("o2_lo:Q", scale=x, title="Oxygen concentration (%)"), x2="o2_hi:Q",
                y=alt.Y("p_lo:Q", scale=y, title="Pressure (psi)"), y2="p_hi:Q",
                tooltip=["Investigation", "Oxygen", "Pressure"],
            )
        )
    layers.append(
        alt.Chart(refs).mark_point(filled=True, size=140).encode(
            x=alt.X("o2:Q", scale=x, title="Oxygen concentration (%)"),
            y=alt.Y("p:Q", scale=y, title="Pressure (psi)"),
            color=alt.condition(alt.datum.Selected, alt.value(ACCENT), alt.value("#E6E8EB")),
            tooltip=["Atmosphere", alt.Tooltip("o2:Q", title="Oxygen (%)"), alt.Tooltip("p:Q", title="Pressure (psi)")],
        )
    )
    layers.append(
        alt.Chart(refs).mark_text(align="left", dx=10, color="#9AA1AB").encode(
            x=alt.X("o2:Q", scale=x), y=alt.Y("p:Q", scale=y), text="Atmosphere"
        )
    )
    st.altair_chart(alt.layer(*layers).properties(height=380), width="stretch")
    st.caption(
        f"Orange point: the atmosphere of the selected environment ({env_name}). Pressures above 50 psi are "
        "outside the plotted area. Oxygen given as \"up to\" a value is drawn from 0 %."
    )
    if both:
        st.markdown("Plotted investigations:")
        for r in both:
            record_link(r, label=f"{r['name']} ({r['id']})")
    if o2_only or p_only:
        st.markdown("Not plotted (only one of the two values reported):")
        for r in o2_only + p_only:
            record_link(r, label=f"{r['name']} ({r['id']}): {fmt_range(r['oxygen_pct'], '%')}; "
                                 f"{fmt_range(r['pressure_psi'], 'psi')}")


# ---------------------------------------------------------------- Ask the records

STOPWORDS = set(
    """a an the and or of to in on for with by at from is are was were be been being what which who
    whom how why when where does do did can could would should will this that these those it its as
    about into than then there their they them any all some such not no nor between under over during
    microgravity investigation investigations experiment experiments record records""".split()
)
TEXT_SECTIONS = (
    ("Objective", "objective"),
    ("Hypothesis", "hypothesis"),
    ("Approach", "approach"),
    ("Research impacts", "research_impacts"),
)


def terms(text):
    return {w.rstrip("s") if len(w) > 4 else w for w in re.findall(r"[a-z0-9]+", text.lower().replace("air flow", "airflow"))
            if len(w) > 2 and w not in STOPWORDS}


@st.cache_data
def passage_index():
    passages = []
    for r in RECORDS:
        for label, key in TEXT_SECTIONS:
            for s in re.split(r"(?<=[.!?])\s+|\n+", r[key] or ""):
                if len(s.strip()) > 30:
                    passages.append({"id": r["id"], "section": label, "text": s.strip(), "terms": terms(s) | terms(r["acronym"])})
    df = Counter(t for p in passages for t in p["terms"])
    idf = {t: math.log(len(passages) / n) for t, n in df.items()}
    return passages, idf


def retrieve(question, limit=6, per_record=2):
    passages, idf = passage_index()
    q = terms(question)
    if not q:
        return []
    scored = []
    for p in passages:
        hit = q & p["terms"]
        if len(hit) / len(q) >= 0.5:
            scored.append((sum(idf.get(t, 0) for t in hit), p))
    scored.sort(key=lambda x: -x[0])
    out, per = [], Counter()
    for _, p in scored:
        if per[p["id"]] < per_record:
            out.append(p)
            per[p["id"]] += 1
        if len(out) == limit:
            break
    return out


def setting(name, default=""):
    """Read a setting from the environment, then from .streamlit/secrets.toml."""
    if os.environ.get(name):
        return os.environ[name]
    try:
        return st.secrets.get(name, default)
    except Exception:  # no secrets file
        return default


def interpret(question, passages):
    """Return (text, reason). Calls any OpenAI-compatible chat endpoint serving an open-weight model.

    Settings (environment variable or .streamlit/secrets.toml):
      LLM_API_KEY   key for the provider (not needed for a local Ollama)
      LLM_BASE_URL  default https://api.groq.com/openai/v1
      LLM_MODEL     default openai/gpt-oss-120b
    """
    base_url = setting("LLM_BASE_URL", "https://api.groq.com/openai/v1").rstrip("/")
    api_key = setting("LLM_API_KEY")
    model = setting("LLM_MODEL", "openai/gpt-oss-120b")
    if not api_key and "localhost" not in base_url and "127.0.0.1" not in base_url:
        return None, "Not generated. Set LLM_API_KEY to enable this section."

    context = "\n".join(f"[{p['id']}] ({p['section']}) {p['text']}" for p in passages)
    system = (
        "You answer questions about NASA microgravity combustion investigations using only the "
        "numbered passages supplied. Cite the record id in square brackets, e.g. [PSI-69], after "
        "every claim. Never fill in experimental values the passages do not state. If passages "
        "disagree, report both findings with their ids; do not average them. If the passages do not "
        "answer the question, reply exactly: \"The PSI records do not cover this question.\" "
        "Keep the answer under 150 words, plain prose."
    )
    body = json.dumps({
        "model": model,
        "max_tokens": 2048,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": f"Passages:\n{context}\n\nQuestion: {question}"},
        ],
    }).encode("utf-8")
    headers = {"Content-Type": "application/json", "User-Agent": "IgnisAI"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    request = urllib.request.Request(f"{base_url}/chat/completions", data=body, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=60) as r:
            response = json.load(r)
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            return None, "Not generated. The provider rejected LLM_API_KEY."
        return None, f"Not generated. The model provider returned an error ({e.code})."
    except (urllib.error.URLError, TimeoutError):
        return None, "Not generated. The model provider could not be reached."
    try:
        text = (response["choices"][0]["message"]["content"] or "").strip()
        text = text.replace("【", "[").replace("】", "]")  # some models use CJK brackets for citations
    except (KeyError, IndexError, TypeError):
        text = ""
    return text or None, None if text else "Not generated. The model returned no text."


def ask_page():
    header("Ask the records")
    with st.form("ask"):
        question = st.text_input("Question", placeholder="Which investigations varied oxygen concentration?")
        submitted = st.form_submit_button("Search the records", type="primary")
    if not (submitted and question.strip()):
        footer()
        return

    passages = retrieve(question)
    if not passages:
        notice("The PSI records do not cover this question.")
        footer()
        return

    st.subheader("Source finding")
    st.caption("Passages from PSI records that match the question, quoted as written.")
    for p in passages:
        rec = BY_ID[p["id"]]
        record_link(rec, label=f"{rec['name']} · {rec['id']} · {p['section']}")
        st.markdown(f"> {p['text']}")

    st.subheader("AI interpretation")
    st.caption(
        f"Generated by {setting('LLM_MODEL', 'openai/gpt-oss-120b')} (open-weight model) "
        "from the passages above. Check each claim against its source."
    )
    text, reason = interpret(question, passages)
    if text:
        valid = {p["id"] for p in passages}
        cited = set(re.findall(r"\[(PSI-\d+)\]", text))
        st.write(text)
        if cited - valid:
            notice("The interpretation cites records outside the passages above: " + ", ".join(sorted(cited - valid)))
    else:
        st.write(reason)

    st.subheader("Sources")
    for rid in dict.fromkeys(p["id"] for p in passages):
        rec = BY_ID[rid]
        col1, col2 = st.columns([3, 1])
        with col1:
            record_link(rec, label=f"{rid} · {rec['name']}")
        with col2:
            st.markdown(f"[PSI record]({rec['psi_url']})")
    footer()


PAGES = {
    "investigations": st.Page(investigations_page, title="Investigations", default=True),
    "compare": st.Page(compare_page, title="Compare", url_path="compare"),
    "ranking": st.Page(ranking_page, title="Relevance ranking", url_path="relevance-ranking"),
    "ask": st.Page(ask_page, title="Ask the records", url_path="ask-the-records"),
}

st.navigation(list(PAGES.values())).run()
