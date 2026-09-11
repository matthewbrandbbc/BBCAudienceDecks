# BBC Audience Size and Profiles — V6.6

A Streamlit application that converts validated regional GWI exports into the September 2026 BBC audience presentation. Total BBC Audience reports contain ten slides; other audience reports omit demographic and employment slides 5 and 6 and contain eight. The on-screen slide viewer and PPTX, ODP and PDF exports all use the same validated source workbooks.

## V6.6 reporting safeguards

Universe, composition percentage and index are reportable only when the matching Responses value is at least 50. Unsupported PowerPoint rows, labels, cards and empty charts are removed completely. The dashboard overview and Audience Deck Chatbot use the same rule, so suppressed figures cannot reappear in an answer or ranking.

The no-API chatbot supports slide-aware definitions, methodology questions, audience profiles, controlled comparisons, typo-tolerant metric matching and contextual follow-ups. It uses neutral language and never sends questions or workbook data to an external AI service. See `CHATBOT_GUIDE.md` for its report map and claim safeguards.

## Security requirement

This repository contains private source workbooks and **must remain private**. Hiding files from the Streamlit interface does not make a public repository secure.

- A temporary public deployment exposes the repository workbooks to anyone who can find the GitHub repository.
- Do not make the GitHub repository public.
- Restrict access to the deployed Streamlit application.
- Do not add workbook download controls or raw-data views.
- Do not place `data/input_workbooks` in a public static directory.
- Generated PPTX files contain only four small chart workbooks used by the editable charts on slides 3 and 8. They do not contain the source exports.

## Project structure

```text
.
├── app.py
├── assets/
│   └── BBC_Insights_Audience_Deck_Tagged_v6_3.pptx
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
2. Filenames must continue to contain the relevant region identifier:
   `All_Markets`, `North_America`, `LATAM` (or `Latin_America`), `Europe`, `Middle_East`, `Africa`, `South_Asia`, or `APAC`.
   The rest of the filename may vary, including download suffixes such as `(1)`, `(2)`, or `(1)(2)`.
   If more than one export for a region is present, the app selects the highest trailing download number.
3. Keep the agreed worksheet, row and column structure.
4. Run:

```bash
python scripts/validate_sources.py
python -m pytest -q
```

5. Commit and redeploy only after both commands pass.

The All Markets workbook is required at launch. Regional files still using the previous row structure are hidden until their matching new exports are uploaded; they then appear automatically.

The present Europe export still lists Russia in B8. Until the source is corrected, the application removes Russia from the displayed market list and appends `(Excl. Russia)`.

## Audience Deck Chatbot

The dashboard places an evidence-based audience overview above the slide preview and an
**Audience Deck Chatbot** question bar beneath the overview.

- It uses no external API and has no per-question cost.
- It reads all eight validated workbooks.
- Every numerical answer can display its source workbook and exact cells.
- It distinguishes composition percentages from indexes and explains both.
- It covers the report slides, reach, competitive position, indexes, affinities, methodology, profiles and controlled comparisons.
- It can rank behaviours, interests and profile qualities across every insight section in the selected audience base.
- Direct characteristics used to define an audience are excluded from rankings where identifiable.
- Its methodology definitions and links are curated locally; it does not browse the internet at runtime.
- It does not make causal, campaign-performance or advertiser-suitability claims.
- Unsupported comparisons are disclosed. For example, the current competitive set does not include the Financial Times.

Example questions:

- `What does an index of 123 mean?`
- `What percentage of the base are male?`
- `Are there any things that BBC audiences are more likely to do?`
- `What are the top indexing qualities for C-Suites?`
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
- Slide 3 retains three native editable charts. Digital is ranked and limited to the top eight results.
- Slide 8 retains a native editable chart and ranks brand-discovery rows by selected-platform index.
- ODP and PDF are created from the completed PPTX using headless LibreOffice.
- Slide 2 always uses the All Markets workbook for its seven-region comparison and the selected platform.
- Slide 2 shows the selected platform's monthly global reach percentage. The self-comparison affinity line is hidden for Total BBC Audience.
- Slide 3 shows the Cross Platform, Digital and TV competitive sets.
- Slide 1 has no footer.
- Slide 2 uses a dedicated bottom-anchored, tightly spaced footer to prevent text collisions.
- Slide 6 ranks rows by reach within Firmographics, Business Title and Role Responsibilities.
- Slides 9 and 10 show index difference with a percentage sign, for example `+43%`.
- Slides 4–10 use the selected platform. Slides 5 and 6 appear only for Total BBC Audience.
- Four unordered source quarters are reduced to the chronologically oldest and newest wave.
- Arial replaces BBC Reith Sans and Georgia replaces BBC Reith Serif.

## Acceptance test

The primary acceptance selection is:

- Region: All Markets
- Audience: C-Suites
- Platform: Cross Platform

Generate the deck and validate it:

```bash
python -c "from pathlib import Path; from src.data_engine import WorkbookRepository; from src.presentation_model import build_model; from src.pptx_service import generate_pptx; r=WorkbookRepository(); generate_pptx(build_model(r,'All Markets','C-Suites','Cross Platform'),Path('outputs/acceptance.pptx'))"
python scripts/validate_export.py outputs/acceptance.pptx
```

For release QA, open both a Total BBC Audience report and a specialist-audience report in Microsoft PowerPoint. Confirm 10 and 8 slides respectively, the four editable charts, BBC-red columns, ranked tables/charts, footer readability, fonts and absence of tagged cell references.
