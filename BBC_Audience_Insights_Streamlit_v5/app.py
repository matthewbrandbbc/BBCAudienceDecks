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
      [data-testid="stHeader"] { background:#000; height:0; }
      [data-testid="stAppViewContainer"] > .main .block-container {max-width:1500px;padding:0 1.1rem .5rem;}
      .bbc-head {background:#000;color:#fff;padding:12px 22px;margin:0 -1.1rem 10px;display:flex;align-items:center;gap:18px;min-height:58px;}
      .bbc-blocks {white-space:nowrap;}
      .bbc-blocks span {background:#fff;color:#000;font:700 18px Arial;margin-right:3px;padding:3px 6px;}
      .bbc-head-copy {border-left:1px solid #555;padding-left:18px;}
      .bbc-head h1 {font:700 22px Arial;margin:0 0 1px;}
      .bbc-head p {font:12px Arial;margin:0;color:#d6d6d6;}
      .panel-label {font:700 11px Arial;color:#b80000;text-transform:uppercase;letter-spacing:.08em;margin:0 0 4px;}
      .chat-title {font:700 18px Arial;color:#121212;margin:4px 0 1px;}
      .grounded-note {font:11px Arial;color:#666;line-height:1.3;margin-bottom:5px;}
      .overview-message {background:#ececec;border-left:4px solid #b80000;padding:9px 10px;margin:0 0 8px;font:12px Arial;line-height:1.35;}
      .overview-message strong {display:block;margin-bottom:4px;}
      .slide-meta {font:600 12px Arial;color:#555;padding:4px 0;text-align:center;}
      [data-testid="stImage"] img {max-height:69vh;object-fit:contain;background:#fff;}
      div[data-testid="stVerticalBlockBorderWrapper"] {background:#fff;border-color:#c9c9c9!important;}
      div[data-testid="stSelectbox"] {margin-bottom:-8px;}
      div[data-testid="stForm"] {border:0;padding:0;}
      div[data-testid="stFormSubmitButton"] button {min-height:39px!important;font-size:14px!important;}
      div[data-testid="stDownloadButton"] button {background:#b80000;color:white;border:0;}
      div[data-testid="stDownloadButton"] button:hover {background:#8d0000;color:white;}
      div[data-testid="stPopover"] > button {
        background:#b80000 !important;color:#fff !important;border:2px solid #b80000 !important;
        font-weight:700 !important;min-height:46px;
      }
      div[data-testid="stPopover"] > button:hover {
        background:#8d0000 !important;color:#fff !important;border-color:#8d0000 !important;
      }
      div[data-testid="stButton"] button {
        background:#fff !important;color:#121212 !important;border:1px solid #555 !important;
        font-weight:700 !important;
      }
      div[data-testid="stButton"] button:hover {
        background:#e6e6e6 !important;color:#000 !important;border-color:#121212 !important;
      }
      div[data-testid="stButton"] button[kind="primary"] {
        background:#b80000 !important;color:#fff !important;border:2px solid #b80000 !important;
        min-height:42px;font-size:20px;font-weight:700;box-shadow:0 3px 10px rgba(0,0,0,.18);
      }
      div[data-testid="stButton"] button[kind="primary"]:hover {
        background:#8d0000 !important;color:#fff !important;border-color:#8d0000 !important;
      }
      div[data-testid="stButton"] button:disabled {
        background:#d7d7d7 !important;color:#777 !important;border-color:#d7d7d7 !important;
      }
      .bbc-loader-overlay {position:fixed;inset:0;background:#050505;z-index:999999;display:flex;align-items:center;justify-content:center;animation:loaderAway .45s ease 2.15s forwards;}
      .bbc-loader {display:flex;align-items:center;gap:18px;transform:scale(1.05);}
      .bbc-loader-boxes {display:flex;gap:6px;}
      .bbc-loader-box {width:58px;height:58px;background:#fff;color:#000;display:flex;align-items:center;justify-content:center;font:700 34px Arial;opacity:0;transform:translateY(8px) scale(.96);animation:boxIn .45s ease forwards;}
      .bbc-loader-box:nth-child(1){animation-delay:.15s}.bbc-loader-box:nth-child(2){animation-delay:.35s}.bbc-loader-box:nth-child(3){animation-delay:.55s}
      .news-reveal {overflow:hidden;width:0;animation:revealNews .9s cubic-bezier(.2,.8,.2,1) 1.05s forwards;}
      .news-word {color:#fff;font:700 56px Arial;letter-spacing:3px;white-space:nowrap;}
      @keyframes boxIn{to{opacity:1;transform:translateY(0) scale(1)}}
      @keyframes revealNews{from{width:0}to{width:178px}}
      @keyframes loaderAway{to{opacity:0;visibility:hidden;pointer-events:none}}
      @media(max-width:900px){.bbc-head p{display:none}.bbc-head-copy{padding-left:12px}.bbc-loader{transform:scale(.75)}}
    </style>
    <div class="bbc-head">
      <div class="bbc-blocks"><span>B</span><span>B</span><span>C</span></div>
      <div class="bbc-head-copy"><h1>Audience Size and Profiles</h1><p>Explore BBC audience insights by audience, region and platform</p></div>
    </div>
    """,
    unsafe_allow_html=True,
)

if not st.session_state.get("bbc_loader_seen"):
    st.markdown(
        """
        <div class="bbc-loader-overlay" aria-label="Loading BBC Audience Insights">
          <div class="bbc-loader">
            <div class="bbc-loader-boxes">
              <div class="bbc-loader-box">B</div><div class="bbc-loader-box">B</div><div class="bbc-loader-box">C</div>
            </div>
            <div class="news-reveal"><div class="news-word">NEWS</div></div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.session_state.bbc_loader_seen = True


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
        expected_pages = len(model.slides)
        try:
            odp_path = convert_with_libreoffice(pptx_path, "odp", temp_dir)
            pdf_path = convert_with_libreoffice(
                pptx_path, "pdf", temp_dir, expected_pages=expected_pages
            )
            odp_bytes = odp_path.read_bytes()
            pdf_bytes = pdf_path.read_bytes()
            for page in render_pdf_pages(
                pdf_path, temp_dir / "pages", expected_pages=expected_pages
            ):
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


def request_template_slide(slide_number: int):
    """Request a numbered source slide; resolved after audience-specific omissions."""
    st.session_state.requested_template_slide = slide_number


try:
    repo = repository()
    errors = repo.validate_region("All Markets")
    if errors:
        with st.expander("Source validation failed", expanded=True):
            for error in errors:
                st.error(error)
        st.stop()

    audiences = list(repo.audience_map("All Markets"))
    regions = repo.compatible_regions()
    if "audience_ai_history" not in st.session_state:
        st.session_state.audience_ai_history = []

    left_panel, viewer_panel = st.columns([3.15, 8.85], gap="medium")
    with left_panel:
        st.markdown('<div class="panel-label">Report filters</div>', unsafe_allow_html=True)
        audience = st.selectbox("Audience", audiences, index=audiences.index("All Audiences"), format_func=lambda value: "Total BBC Audience" if value == "All Audiences" else value)
        region = st.selectbox("Region / market", regions, index=regions.index("All Markets"))
        platform = st.selectbox("Platform", ["Cross Platform", "Digital", "TV"])

        unavailable = [name for name in repo.paths if name not in regions]
        if unavailable:
            st.caption("Unavailable workbook regions: " + ", ".join(unavailable))

        filter_key = (audience, region, platform)
        if st.session_state.get("audience_ai_filter_key") != filter_key:
            st.session_state.audience_ai_history = []
            st.session_state.audience_ai_filter_key = filter_key

        engine = audience_engine()
        overview = engine.overview(region, audience, platform)
        st.markdown('<div class="chat-title">Audience Deck Chatbot</div><div class="grounded-note">Ask about the selected report, a slide or GWI methodology. Answers stay within the validated evidence.</div>', unsafe_allow_html=True)

        with st.container(height=292, border=True):
            overview_text = "<br>".join(f"• {item}" for item in overview.bullets)
            st.markdown(f'<div class="overview-message"><strong>Report overview · {overview.headline}</strong>{overview_text}</div>', unsafe_allow_html=True)
            for history_index, (previous_question, answer) in enumerate(st.session_state.audience_ai_history):
                with st.chat_message("user"):
                    st.markdown(previous_question)
                with st.chat_message("assistant"):
                    st.markdown(answer.answer)
                    if answer.resolved_scope:
                        st.caption(answer.resolved_scope)
                    if answer.relevant_slide:
                        st.button(f"View slide {answer.relevant_slide}", key=f"chat_slide_{history_index}_{answer.relevant_slide}", on_click=request_template_slide, args=(answer.relevant_slide,))
                    if answer.evidence:
                        with st.expander("Evidence"):
                            for item in answer.evidence:
                                st.markdown(f"**{item.statement}**  \n{item.value}  \nSlide {item.slide or '—'} · {item.source_label} · Cells {item.cells}")

        with st.form("audience_ai_form", clear_on_submit=True):
            ask_text, ask_action = st.columns([4.5, 1], vertical_alignment="bottom")
            with ask_text:
                question = st.text_input("Question", placeholder="Ask about this audience…", label_visibility="collapsed")
            with ask_action:
                submitted = st.form_submit_button("Ask", type="primary", use_container_width=True)
        if submitted and question.strip():
            previous_question = previous_scope = None
            if st.session_state.audience_ai_history:
                previous_question, previous_answer = st.session_state.audience_ai_history[-1]
                parts = previous_answer.resolved_scope.split(" · ")
                if len(parts) == 3:
                    previous_scope = (parts[0], parts[1], parts[2])
            answer = engine.answer(question.strip(), region, audience, platform, previous_question=previous_question, previous_scope=previous_scope)
            st.session_state.audience_ai_history.append((question.strip(), answer))
            st.session_state.audience_ai_history = st.session_state.audience_ai_history[-8:]
            st.rerun()

    with st.spinner("Preparing the selected presentation…"):
        pptx_bytes, odp_bytes, pdf_bytes, pages, conversion_error, model = make_exports(region, audience, platform)

    with viewer_panel:
        title_left, title_right = st.columns([7, 3], vertical_alignment="center")
        with title_left:
            st.markdown('<div class="panel-label">Presentation preview</div>', unsafe_allow_html=True)
            st.markdown(f"**{'Total BBC Audience' if audience == 'All Audiences' else audience} · {region} · {platform}**")
        base_name = f"BBC_Audience_Deck_{audience}_{region}_{platform}".replace(" ", "_")
        with title_right:
            with st.popover("Download presentation ▾", use_container_width=True):
                export_format = st.selectbox("Format", ["PowerPoint (.pptx)", "OpenDocument (.odp)", "PDF (.pdf)"], label_visibility="collapsed")
                export_options = {
                    "PowerPoint (.pptx)": (pptx_bytes, f"{base_name}.pptx", "application/vnd.openxmlformats-officedocument.presentationml.presentation"),
                    "OpenDocument (.odp)": (odp_bytes, f"{base_name}.odp", "application/vnd.oasis.opendocument.presentation"),
                    "PDF (.pdf)": (pdf_bytes, f"{base_name}.pdf", "application/pdf"),
                }
                export_data, export_name, export_mime = export_options[export_format]
                st.download_button("Download selected format", export_data or b"", export_name, mime=export_mime, disabled=export_data is None, use_container_width=True)

        if conversion_error:
            st.warning(conversion_error)
        if pages:
            max_slides = min(len(pages), len(model.slides))
            requested = st.session_state.pop("requested_template_slide", None)
            if requested is not None:
                matches = [position for position, slide in enumerate(model.slides, 1) if slide.number == requested]
                if matches:
                    st.session_state.slide_number = matches[0]
                else:
                    st.info(f"Slide {requested} is not included in this specialist export, although its source data can still be explained in chat.")
            st.session_state.slide_number = max(1, min(int(st.session_state.get("slide_number", 1)), max_slides))
            with st.container(border=True):
                st.image(BytesIO(pages[st.session_state.slide_number - 1]), use_container_width=True)
            nav_left, nav_middle, nav_right = st.columns([1, 6, 1], vertical_alignment="center")
            with nav_left:
                st.button("◀", key="previous_slide", help="Previous slide", type="primary", disabled=st.session_state.slide_number <= 1, on_click=previous_slide, use_container_width=True)
            with nav_middle:
                source_number = model.slides[st.session_state.slide_number - 1].number
                st.markdown(f'<div class="slide-meta">Slide {source_number} · {st.session_state.slide_number} of {max_slides}</div>', unsafe_allow_html=True)
            with nav_right:
                st.button("▶", key="next_slide", help="Next slide", type="primary", disabled=st.session_state.slide_number >= max_slides, on_click=next_slide, args=(max_slides,), use_container_width=True)
        else:
            st.info("The PowerPoint is ready to download. Slide previews, ODP and PDF require LibreOffice and Poppler.")
except ValidationError as exc:
    st.error(str(exc))
    st.stop()
