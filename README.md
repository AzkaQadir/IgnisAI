# IgnisAI

IgnisAI is a web dashboard about fire in space. It collects NASA's microgravity combustion
investigations and organises them for fire safety in crewed spacecraft, space stations, and
future bases on the Moon and Mars.

Every value and every answer links back to its NASA source record. When the records do not
have the answer, the app says so.

Made for the 2026 NASA Space Apps Challenge: *Flame in Freefall*.

## What you can do

| Page | What it does |
|---|---|
| **Investigations** | A table of all 24 combustion investigations. Filter by fire-safety pillar, fuel phase, hardware, the kind of fire-safety equipment it informs, oxygen concentration and airflow speed. Download the filtered table as CSV for modelling. Click a name to open its detail page. |
| **Investigation page** | One investigation in detail: test conditions, what changed and what stayed the same between tests, fuel type, shape and size, hardware, measurements, key findings, the fire-safety equipment it informs, related Earth applications, and the source sentence behind each value. |
| **Compare** | Two or three investigations side by side. |
| **Relevance ranking** | Pick an environment (spacecraft, space station, lunar base, Martian base, pressurized rover). Investigations are ranked by five clear rules, and the score for each rule is shown. Below it, an **evidence-gap chart** shows which oxygen and pressure levels have been tested, next to the expected Moon base atmosphere. |
| **Ask the records** | Ask a question. You get the matching text from the NASA records, then a short AI summary that cites a record for every claim. |

## Where the data comes from

All data comes from **NASA Physical Sciences Informatics (PSI)**:
https://psi.nasa.gov/physci/repo/search?q=combustion

The script `fetch_data.py` downloads every investigation in the *Combustion Science* research area
(24 records) and saves them to `data/investigations.json`.

PSI stores most details as normal text, not as separate fields. So the script reads the text with
fixed rules. For example, it finds "21 % oxygen" or "0.5 to 3 atm". It keeps the sentence each value
came from, so you can check it. If the text does not state a value, the app shows
"Not reported in source". It never guesses.

The fire-safety pillar (prevention, detection, suppression) for the investigations named in the
challenge comes from the challenge statement. For other investigations it comes from keyword rules.
Investigations with no direct fire-safety goal are marked "foundational".

The "Informs controls and equipment" field follows the pillar: prevention links to material selection
and flammability limits, detection to smoke and fire detectors, suppression to extinguishers and
suppressants. Cabin ventilation is added when the record reports an airflow speed.

Two values come from the challenge statement because the PSI record text does not state them:
CFI-G tested up to 85 % oxygen, and E-FIELD Flames used an electric field to mimic partial gravity.
The app marks both as coming from the challenge statement.

## How to run it

You need Python 3.10 or newer.

```
git clone <this repo>
cd IgnisAI
python -m venv venv
venv\Scripts\python.exe -m pip install -r requirements.txt
venv\Scripts\python.exe -m streamlit run app.py
```

On macOS or Linux, use `venv/bin/python` instead of `venv\Scripts\python.exe`.

The app opens in your browser at http://localhost:8501.

To download fresh data from PSI: `venv\Scripts\python.exe fetch_data.py`

### Turn on the AI summary (optional)

The app works without it. Only the "AI interpretation" section needs it.

1. Get a free API key from Groq: https://console.groq.com/keys
2. Create the file `.streamlit/secrets.toml` with this line:

   ```toml
   LLM_API_KEY = "your-key-here"
   ```

3. Restart the app.

This file is listed in `.gitignore`, so it is never uploaded to GitHub. On Streamlit Community Cloud,
paste the same line into the app's **Secrets** settings instead.

The default model is `openai/gpt-oss-120b`, an open-weight model. Any service with an
OpenAI-compatible API works. Set `LLM_BASE_URL` and `LLM_MODEL` in the same file to change it.
For a local Ollama model, use `LLM_BASE_URL = "http://localhost:11434/v1"` (no key needed).

## How the ranking works

Each investigation gets five scores from 0 to 1. The final score is their average × 100.

1. **Fire-safety objective**: 1 if it is about prevention, detection or suppression.
2. **Fuel realism**: solid 1, liquid 0.5, gas 0.25. Fires in a cabin burn solid materials.
3. **Atmosphere overlap**: does the tested oxygen and pressure match the chosen environment?
4. **Cabin airflow**: does the tested airflow match ISS cabin ventilation (7.6–20.3 cm/s)?
5. **Gravity relevance**: microgravity counts fully for spacecraft and stations, and half for
   surface bases, because PSI has no partial-gravity data.

Lunar bases and rovers use the expected exploration atmosphere (30 % oxygen at 10.2 psi).
Mars bases use the same values; this is an assumption.

This ranking is a simple rule of thumb to help you choose what to read first. It is not a NASA
assessment and it does not predict fire risk.

## Test results

Ten test questions, run on 15 November 2026 with `openai/gpt-oss-120b`:

| # | Question | Result |
|---|---|---|
| 1 | Which investigations studied flame spread over solid materials? | Answered, cites PSI-25, PSI-62 |
| 2 | What suppressants were tested on droplet flames? | Answered: CO2, helium, SF6 from FLEX (PSI-69) |
| 3 | How does oxygen concentration affect flammability? | Answered, cites PSI-142, PSI-20 and others |
| 4 | Which investigations measured smoke particles? | Answered, cites SAME and SAME-R (PSI-101, PSI-102) |
| 5 | What airflow speeds were used in the Saffire experiments? | Answered: 20 cm/s and 20 or 30 cm/s (PSI-98, PSI-99) |
| 6 | Which investigations studied cool flames? | Answered, cites PSI-39, PSI-69, PSI-117 |
| 7 | What did BASS find about burning in microgravity? | Said "not covered". The BASS text found describes goals, not results. |
| 8 | Which experiments studied soot formation in laminar flames? | Answered, cites PSI-21, PSI-22 |
| 9 | How do flames behave in partial gravity on the Moon? | Correctly said "not covered" (PSI has no partial-gravity data) |
| 10 | What is the best fire extinguisher for a Mars habitat? | Correctly said "not covered" |

Answers depend on the model and can change between runs.

## Limitations

- Only 24 investigations, and only their PSI record text. The detailed test tables in PSI need a
  login, so they are not used.
- Many values are missing because the text does not state them. Only 2 of 24 records report both
  oxygen concentration and pressure. The evidence-gap chart shows this.
- No record states which conditions stayed fixed between tests, so "Fixed conditions" shows
  "Not reported in source" for now. Fuel sizes are found for 6 records.
- Values are found by text rules. They can miss a value or, rarely, pick up a wrong one. Check
  the source sentence on the investigation page.
- The ranking is a rule of thumb, not a scientific measure.
- The AI summary can make mistakes. Always check it against the quoted source text.

## AI use

An AI coding assistant helped write the code. The "AI interpretation" section in the app uses the
open-weight model `openai/gpt-oss-120b`, through Groq.

## Disclaimer

Independent project. Not a NASA product. No NASA endorsement is implied. Data: NASA Physical
Sciences Informatics. AI-generated text is a summary, not fire-safety advice.
