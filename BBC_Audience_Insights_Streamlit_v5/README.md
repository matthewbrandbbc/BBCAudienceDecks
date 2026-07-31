# BBC Audience Size and Profiles

A Streamlit application that converts validated regional GWI exports into a nine-slide BBC audience presentation. It also provides a free, deterministic Audience AI overview and grounded question bar. The on-screen slide viewer and PPTX, ODP and PDF exports all use the same validated source workbooks.

## Version 5 reporting safeguards

Universe, composition percentage and index are reportable only when the matching Responses value is at least 50. Unsupported PowerPoint rows, labels, cards and empty charts are removed completely. The dashboard overview and Audience AI use the same rule, so suppressed figures cannot reappear in an answer or ranking.

The no-API assistant also supports follow-up questions, two-way audience or region comparisons, typo-tolerant metric matching and claim-strength labels.

## Security requirement

This repository contains private source workbooks and **must remain private**. Hiding files from the Streamlit interface does not make a public repository secure.

- A temporary public deployment exposes the repository workbooks to anyone who can find the GitHub repository.
- Do not make the GitHub repository public.
- Restrict access to the deployed Streamlit application.
- Do not add workbook download controls or raw-data views.
- Do not place `data/input_workbooks` in a public static directory.
- Generated PPTX files contain only three small chart workbooks used by the editable slide-4 charts. They do not contain the eight source exports.

## Project structure

```text
.
├── app.py
├── assets/
│   └── BBC_Insights_Audience_Deck_Tagged.potx
├── data/
│   └── input_workbooks/        # Replace these eight files each quarter
├── src/
│   ├── config.py
│   ├── data_engine.py
│   ├── audience_ai.py
│   ├── presentation_model.py
│   ├── pptx_service.py
│   └── export_service.py
├── scripts/
│   ├── validate_sources.py
│   └── validate_export.py
├── tests/
├── requirements.txt
└── packages.txt
```

## Local installation

Python 3.11–3.13 is recommended.

```bash
python -m venv .venv
```

Activate the environment, then install Python packages:

```bash
python -m pip install -r requirements.txt
```

Install LibreOffice and Poppler using the package manager for your operating system. They are required for ODP/PDF conversion and slide previews. PPTX generation works without Microsoft PowerPoint.

Run:

```bash
streamlit run app.py
```

## Quarterly workbook replacement

1. Replace all eight `.xlsx` files in `data/input_workbooks/`.
2. Filenames must continue to contain the same region identifiers:
   `All_Markets`, `North_America`, `Latin_America`, `Europe`, `Middle_East`, `Africa`, `South_Asia`, and `APAC`.
3. Keep the agreed worksheet, row and column structure.
4. Run:

```bash
python scripts/validate_sources.py
python -m pytest -q
```

5. Commit and redeploy only after both commands pass.

Validation fails explicitly when a workbook, audience, required cell, slide-2 lookup, competitive set, or numeric mapping is missing or inconsistent.

The present Europe export still lists Russia in B8. Until the source is corrected, the application removes Russia from the displayed market list and appends `(Excl. Russia)`.

## Audience AI

The dashboard places an evidence-based audience overview above the slide preview and an
**Audience Deck Chatbot** question bar beneath the overview.

- It uses no external API and has no per-question cost.
- It reads all eight validated workbooks.
- Every numerical answer can display its source workbook and exact cells.
- It distinguishes composition percentages from indexes and explains both.
- It covers reach, competitive position, indexes, affinities, audience comparisons and strongest sales arguments.
- It can rank behaviours, interests and profile qualities across every insight section in the selected audience base.
- Direct characteristics used to define an audience are excluded from rankings where identifiable.
- It does not browse the internet or answer from information outside the supplied GWI exports.
- Unsupported comparisons are disclosed. For example, the current competitive set does not include the Financial Times.

Example questions:

- `What does an index of 123 mean?`
- `What percentage of the base are male?`
- `Are there any things that BBC audiences are more likely to do?`
- `What are the top indexing qualities for C-Suites?`
- `What is the strongest argument for BBC audiences in Latin America?`
- `Which audience has the strongest digital media affinity in Europe?`
- `How does BBC compare with CNN for C-Suites in APAC?`
- `What are the top affinities for HNWIs in North America on TV?`

`GroundedAudienceEngine` is intentionally separated from the interface. A future
LLM can call the same evidence methods as controlled tools without being given
permission to invent or recalculate figures.

## Streamlit Community Cloud deployment

1. Create a **private** GitHub repository.
2. Push the complete project, including `assets` and `data/input_workbooks`.
3. In Streamlit Community Cloud, create an app from the private repository.
4. Set the entry point to `app.py`.
5. Confirm that GitHub and Streamlit access is restricted to the intended users.

`packages.txt` installs LibreOffice, Poppler and portable fonts on Streamlit Community Cloud. First-time conversion of a filter combination may take several seconds; Streamlit caches subsequent results.

## Export behaviour

- PPTX remains a genuine editable PowerPoint Open XML presentation.
- Slide 4 retains three native editable charts and embeds only their six-row datasets.
- ODP and PDF are created from the completed PPTX using headless LibreOffice.
- Slides 2–4 always show all three platforms and use the combined-platform footer.
- Slide 3 always uses the All Markets workbook for its seven-region comparison.
- Slide 1 has no footer.
- Slide 2 uses a dedicated bottom-anchored, tightly spaced footer to prevent text collisions.
- Slides 5–9 use the selected platform.
- Arial replaces BBC Reith Sans and Georgia replaces BBC Reith Serif.

## Acceptance test

The primary acceptance selection is:

- Region: APAC
- Audience: C-Suites
- Platform: Cross Platform

Generate the deck and validate it:

```bash
python -c "from pathlib import Path; from src.data_engine import WorkbookRepository; from src.presentation_model import build_model; from src.pptx_service import generate_pptx; r=WorkbookRepository(); generate_pptx(build_model(r,'APAC','C-Suites','Cross Platform'),Path('outputs/acceptance.pptx'))"
python scripts/validate_export.py outputs/acceptance.pptx
```

For release QA, open the PPTX in Microsoft PowerPoint and verify all nine slides, the three editable charts, BBC-red columns, chart ranks, footer readability, fonts and absence of tagged cell references. Also download the ODP and PDF from the deployed application and confirm nine slides/pages.
