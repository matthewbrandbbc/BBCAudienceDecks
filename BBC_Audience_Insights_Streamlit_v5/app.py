from __future__ import annotations

from io import BytesIO
from pathlib import Path
import tempfile

import streamlit as st

from src.audience_ai import GroundedAudienceEngine
from src.data_engine import ValidationError, WorkbookRepository
from src.export_service import ConversionError, convert_with_libreoffice, render_pdf_pages
from src.presentation_model import build_model
from src.pptx_service import generate_pptx

st.set_page_config(page_title="BBC Audience Insights", page_icon="📊", layout="wide")

st.markdown(
    """
    <style>
      .stApp { background:#f4f4f4; color:#121212; }
      [data-testid="stHeader"] { background:#000; }
      .bbc-head {background:#000;color:#fff;padding:18px 24px;margin:-1rem -1rem 1.2rem;}
      .bbc-blocks span {background:#fff;color:#000;font:700 18px Arial;margin-right:3px;padding:3px 6px;}
      .bbc-head h1 {font:700 26px Arial;margin:14px 0 2px;}
      .bbc-head p {font:15px Arial;margin:0;color:#d6d6d6;}
      .slide-shell {background:#202020;border-radius:6px;padding:12px;box-shadow:0 10px 32px rgba(0,0,0,.18);}
      .slide-meta {font:600 13px Arial;color:#555;padding:8px 0;}
      .ai-kicker {font:700 12px Arial;color:#b80000;text-transform:uppercase;letter-spacing:.08em;margin-bottom:4px;}
      .ai-title {font:700 22px Arial;color:#121212;margin:0 0 10px;}
      .ai-card {background:#fff;border-left:5px solid #b80000;padding:18px 20px;margin:12px 0 10px;}
      .ai-card ul {margin:8px 0 0 20px;padding:0;}
      .ai-card li {margin:0 0 8px;line-height:1.45;}
      .sales-takeout {background:#ececec;border-radius:4px;padding:12px 14px;margin-top:12px;font:600 15px Arial;line-height:1.45;}
      .ask-label {font:700 18px Arial;margin:18px 0 4px;}
      .grounded-note {font:12px Arial;color:#666;margin-bottom:8px;}
      div[data-testid="stDownloadButton"] button {background:#b80000;color:white;border:0;}
      div[data-testid="stDownloadButton"] button:hover {background:#8d0000;color:white;}
      div[data-testid="stButton"] button {
        background:#fff !important;color:#121212 !important;border:1px solid #555 !important;
        font-weight:700 !important;
      }
      div[data-testid="stButton"] button:hover {
        background:#e6e6e6 !important;color:#000 !important;border-color:#121212 !important;
      }
      div[data-testid="stButton"] button[kind="primary"] {
        background:#b80000 !important;color:#fff !important;border:2px solid #b80000 !important;
        min-height:54px;font-size:26px;font-weight:700;box-shadow:0 3px 10px rgba(0,0,0,.18);
      }
      div[data-testid="stButton"] button[kind="primary"]:hover {
        background:#8d0000 !important;color:#fff !important;border-color:#8d0000 !important;
      }
      div[data-testid="stButton"] button:disabled {
        background:#d7d7d7 !important;color:#777 !important;border-color:#d7d7d7 !important;
      }
    </style>
    <div class="bbc-head">
      <div class="bbc-blocks"><span>B</span><span>B</span><span>C</span></div>
      <h1>BBC Audience Size and Profiles</h1>
      <p>BBC Audience Insights slides - filters for 16 core audiences, region and platform of choice</p>
    </div>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource
def repository():
    return WorkbookRepository()


@st.cache_resource
def audience_engine():
    return GroundedAudienceEngine(repository())


@st.cache_data(show_spinner=False)
def make_exports(region: str, audience: str, platform: str):
    repo = repository()
    model = build_model(repo, region, audience, platform)
    with tempfile.TemporaryDirectory(prefix="bbc-deck-") as temp:
        temp_dir = Path(temp)
        pptx_path = generate_pptx(model, temp_dir / "BBC_Audience_Deck.pptx")
        pptx_bytes = pptx_path.read_bytes()
        odp_bytes = pdf_bytes = None
        page_bytes = []
        conversion_error = None
        try:
            odp_path = convert_with_libreoffice(pptx_path, "odp", temp_dir)
            pdf_path = convert_with_libreoffice(pptx_path, "pdf", temp_dir)
            odp_bytes = odp_path.read_bytes()
            pdf_bytes = pdf_path.read_bytes()
            for page in render_pdf_pages(pdf_path, temp_dir / "pages"):
                page_bytes.append(page.read_bytes())
        except ConversionError as exc:
            conversion_error = str(exc)
    return pptx_bytes, odp_bytes, pdf_bytes, page_bytes, conversion_error, model


def previous_slide():
    st.session_state.slide_number = max(1, int(st.session_state.get("slide_number", 1)) - 1)


def next_slide(max_slides: int):
    st.session_state.slide_number = min(
        max_slides, int(st.session_state.get("slide_number", 1)) + 1
    )


try:
    repo = repository()
    errors = repo.validate_all()
    if errors:
        with st.expander("Source validation failed", expanded=True):
            for error in errors:
                st.error(error)
        st.stop()

    audiences = list(repo.audience_map("All Markets"))
    control_1, control_2, control_3 = st.columns(3)
    with control_1:
        audience = st.selectbox("Audience", audiences, index=audiences.index("All Audiences"))
    with control_2:
        regions = list(repo.paths)
        region = st.selectbox("Region / market", regions, index=regions.index("All Markets"))
    with control_3:
        platform = st.selectbox("Platform", ["Cross Platform", "Digital", "TV"])

    engine = audience_engine()
    overview = engine.overview(region, audience, platform)
    overview_items = "".join(f"<li>{bullet}</li>" for bullet in overview.bullets)
    st.markdown(
        f"""
        <div class="ai-card">
          <div class="ai-kicker">AI Overview</div>
          <div class="ai-title">{overview.headline}</div>
          <ul>{overview_items}</ul>
          <div class="sales-takeout"><strong>Sales takeout:</strong> {overview.sales_takeout}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    with st.expander("View overview evidence"):
        st.dataframe(
            [
                {
                    "Claim": item.statement,
                    "Evidence": item.value,
                    "Source": item.source_label,
                    "Workbook cells": item.cells,
                }
                for item in overview.evidence
            ],
            hide_index=True,
            use_container_width=True,
        )

    st.markdown(
        '<div class="ask-label">Audience Deck Chatbot</div>'
        '<div class="grounded-note">Answers use the eight validated GWI workbooks only. '
        "It understands reach, composition percentages, indexes, rankings and comparisons. "
        "No external AI service is used.</div>",
        unsafe_allow_html=True,
    )
    with st.form("audience_ai_form", clear_on_submit=True):
        ask_col, ask_button_col = st.columns([8.5, 1.5], vertical_alignment="bottom")
        with ask_col:
            question = st.text_input(
                "Question",
                placeholder='Try: "What percentage of the base are male?"',
                label_visibility="collapsed",
            )
        with ask_button_col:
            ask_submitted = st.form_submit_button(
                "Ask",
                type="primary",
                use_container_width=True,
            )

    if "audience_ai_history" not in st.session_state:
        st.session_state.audience_ai_history = []
    filter_key = (audience, region, platform)
    if st.session_state.get("audience_ai_filter_key") != filter_key:
        st.session_state.audience_ai_history = []
        st.session_state.audience_ai_filter_key = filter_key

    submitted_question = question.strip() if ask_submitted else None
    if submitted_question:
        previous_question = previous_scope = None
        if st.session_state.audience_ai_history:
            previous_question, previous_answer = st.session_state.audience_ai_history[-1]
            if previous_answer.resolved_scope:
                parts = previous_answer.resolved_scope.split(" · ")
                if len(parts) == 3:
                    previous_scope = (parts[0], parts[1], parts[2])
        answer = engine.answer(
            submitted_question, region, audience, platform,
            previous_question=previous_question,
            previous_scope=previous_scope,
        )
        st.session_state.audience_ai_history.append((submitted_question, answer))
        st.session_state.audience_ai_history = st.session_state.audience_ai_history[-5:]

    for previous_question, answer in reversed(st.session_state.audience_ai_history):
        with st.container(border=True):
            st.markdown(f"**You:** {previous_question}")
            st.markdown(answer.answer)
            if answer.resolved_scope:
                st.caption(f"Resolved scope: {answer.resolved_scope}")
            if answer.evidence:
                with st.expander("View answer evidence"):
                    st.dataframe(
                        [
                            {
                                "Claim": item.statement,
                                "Evidence": item.value,
                                "Source": item.source_label,
                                "Workbook cells": item.cells,
                            }
                            for item in answer.evidence
                        ],
                        hide_index=True,
                        use_container_width=True,
                    )

    with st.spinner("Preparing the selected presentation…"):
        pptx_bytes, odp_bytes, pdf_bytes, pages, conversion_error, model = make_exports(
            region, audience, platform
        )

    base_name = f"BBC_Audience_Deck_{audience}_{region}_{platform}".replace(" ", "_")
    with st.popover("Download ▾"):
        export_format = st.selectbox(
            "Format",
            ["PowerPoint (.pptx)", "OpenDocument (.odp)", "PDF (.pdf)"],
            label_visibility="collapsed",
        )
        export_options = {
            "PowerPoint (.pptx)": (
                pptx_bytes,
                f"{base_name}.pptx",
                "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            ),
            "OpenDocument (.odp)": (
                odp_bytes,
                f"{base_name}.odp",
                "application/vnd.oasis.opendocument.presentation",
            ),
            "PDF (.pdf)": (pdf_bytes, f"{base_name}.pdf", "application/pdf"),
        }
        export_data, export_name, export_mime = export_options[export_format]
        st.download_button(
            "Download selected format",
            export_data or b"",
            export_name,
            mime=export_mime,
            disabled=export_data is None,
            use_container_width=True,
        )

    if conversion_error:
        st.warning(conversion_error)

    if pages:
        max_slides = min(len(pages), len(model.slides), 9)
        if "slide_number" not in st.session_state:
            st.session_state.slide_number = 1
        # Guard against stale or double-clicked navigation state.
        st.session_state.slide_number = max(
            1, min(int(st.session_state.slide_number), max_slides)
        )
        nav_left, nav_mid, nav_right = st.columns(
            [1.2, 7.6, 1.2], vertical_alignment="center"
        )
        with nav_left:
            st.button(
                "◀",
                key="previous_slide",
                help="Previous slide",
                type="primary",
                disabled=st.session_state.slide_number <= 1,
                on_click=previous_slide,
                use_container_width=True,
            )
        with nav_mid:
            with st.container(border=True):
                st.image(
                    BytesIO(pages[st.session_state.slide_number - 1]),
                    use_container_width=True,
                )
        with nav_right:
            st.button(
                "▶",
                key="next_slide",
                help="Next slide",
                type="primary",
                disabled=st.session_state.slide_number >= max_slides,
                on_click=next_slide,
                args=(max_slides,),
                use_container_width=True,
            )
        st.markdown(
            f'<div class="slide-meta" style="text-align:center">Slide {st.session_state.slide_number} of {max_slides} · '
            f'{audience} · {region} · {platform}</div>',
            unsafe_allow_html=True,
        )
    else:
        st.info("The PPTX export is ready. Install LibreOffice and Poppler to enable slide previews, ODP and PDF.")
except ValidationError as exc:
    st.error(str(exc))
    st.stop()
