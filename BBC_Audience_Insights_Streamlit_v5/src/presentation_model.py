from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any

from .config import PLATFORM_COLUMNS
from .data_engine import (
    WorkbookRepository,
    footer_lines,
    format_compact,
    format_index,
    format_index_difference,
    format_percent,
    ordinal,
)


@dataclass
class SlideModel:
    number: int
    title: str
    replacements: dict[str, str] = field(default_factory=dict)
    footer: list[str] = field(default_factory=list)
    charts: dict[str, Any] = field(default_factory=dict)
    suppressed_markers: set[str] = field(default_factory=set)


@dataclass
class PresentationModel:
    audience: str
    region: str
    platform: str
    slides: list[SlideModel]


def title_audience_name(audience: str) -> str:
    """Use established acronyms in titles where the full label would collide."""
    if audience == "All Audiences":
        return audience
    if " – " in audience:
        return audience.split(" – ", 1)[0]
    acronym = re.search(r"\(([A-Z][A-Z0-9-]{1,}s?)\)\s*$", audience)
    return acronym.group(1) if acronym else audience


def _template_markers(row: int, columns: str) -> set[str]:
    return {f"({column}{row})" for column in columns}


def build_model(repo: WorkbookRepository, region: str, audience: str, platform: str) -> PresentationModel:
    ws = repo.sheet(region, audience)
    cols = PLATFORM_COLUMNS[platform]
    slides = []

    is_all = audience == "All Audiences"
    display_audience = title_audience_name(audience)
    audience_tokens = {
        "(All Audiences)": display_audience,
        "(All Audience)": display_audience,
        "All BBC (All Audiences)": f"BBC {display_audience}",
    }

    slides.append(SlideModel(1, "Title", replacements=audience_tokens))

    s2 = dict(audience_tokens)
    s2["BBC News"] = f"BBC News — {display_audience}"
    for cell in ("I16", "N16", "S16"):
        s2[f"({cell})"] = format_compact(ws[cell].value)
    for cell in ("L16", "Q16", "V16"):
        s2[f"({cell})"] = format_percent(ws[cell].value)
    s2["(M16)"] = format_index(repo.slide2_affinity(region, audience))
    s2_suppressed = set()
    for check_platform, marker_columns in {
        "Cross Platform": "IL",
        "Digital": "NQ",
        "TV": "SV",
    }.items():
        if not repo.is_supported(region, audience, check_platform, 16):
            s2_suppressed.update(_template_markers(16, marker_columns))
    slides.append(
        SlideModel(
            2,
            "Audience Reach",
            s2,
            footer_lines(repo, region, audience, platform, True),
            suppressed_markers=s2_suppressed,
        )
    )

    global_ws = repo.sheet("All Markets", audience)
    s3 = dict(audience_tokens)
    if is_all:
        s3["BBC Reach (All Audience)  across Global Regions through Digital and TV Platforms"] = (
            "BBC Reach Audiences across Global Regions through Digital and TV Platforms"
        )
    else:
        s3["BBC Reach (All Audience)  across Global Regions through Digital and TV Platforms"] = (
            f"BBC Reaches {display_audience} Audiences across Global Regions through Digital and TV Platforms"
        )
    s3["__AUDIENCE_BUBBLE__"] = "Audiences" if is_all else display_audience
    for row in range(33, 40):
        for cell in (f"I{row}", f"N{row}", f"S{row}"):
            s3[f"({cell})"] = format_compact(global_ws[cell].value)
        for cell in (f"L{row}", f"Q{row}", f"V{row}"):
            s3[f"({cell})"] = format_percent(global_ws[cell].value)
    for cell in ("I16", "N16", "S16"):
        s3[f"({cell})"] = format_compact(ws[cell].value)
    for cell in ("L16", "Q16", "V16"):
        s3[f"({cell})"] = format_percent(ws[cell].value)
    s3_suppressed = set()
    # The three regional tables share one set of row labels. If any platform
    # has an insufficient base for a region, remove that region from all three
    # tables so the remaining rows stay aligned and interpretable.
    for row in range(33, 40):
        if any(
            not repo.is_supported("All Markets", audience, check_platform, row)
            for check_platform in PLATFORM_COLUMNS
        ):
            s3_suppressed.update(_template_markers(row, "ILNQSV"))
    if not repo.is_supported(region, audience, "Cross Platform", 16):
        s3_suppressed.update(_template_markers(16, "IL"))
    slides.append(
        SlideModel(
            3,
            "Reach by Region",
            s3,
            footer_lines(repo, region, audience, platform, True),
            suppressed_markers=s3_suppressed,
        )
    )

    charts = {}
    for name, start in (("Cross Platform", 40), ("Digital", 46), ("TV", 52)):
        items = repo.supported_competitor_set(region, audience, start)
        rank = next(
            (i for i, item in enumerate(items, 1) if item.name.casefold() == "bbc"),
            None,
        )
        charts[name] = {
            "items": [{"name": item.name, "value": item.value, "label": format_compact(item.value)} for item in items],
            "rank": rank,
            "ordinal": ordinal(rank) if rank is not None else None,
            "suppressed_count": 6 - len(items),
        }
    s4 = dict(audience_tokens)
    s4["BBC Achieves Strong Global reach to (All Audience) Audiences "] = (
        "BBC Achieves Strong Competitive Reach to Audiences"
        if is_all
        else f"BBC Achieves Strong Competitive Reach to {display_audience} Audiences"
    )
    slides.append(SlideModel(4, "Competitive Reach", s4, footer_lines(repo, region, audience, platform, True), charts))

    s5 = dict(audience_tokens)
    if is_all:
        s5["(All Audience)  Audience engage strongly across each of BBC content pillar areas"] = (
            "Audiences engage strongly across each of the BBC content pillar areas"
        )
    for row in range(58, 70):
        source = f"{cols['percent']}{row}"
        s5[f"(K{row})"] = format_percent(ws[source].value)
    s5_suppressed = {
        f"(K{row})" for row in range(58, 70) if not repo.is_supported(region, audience, platform, row)
    }
    if len(s5_suppressed) == 12:
        s5["(All Audience)  Audience engage strongly across each of BBC content pillar areas"] = (
            "No pillar statistics are shown because all response bases are below 50"
        )
    slides.append(
        SlideModel(
            5,
            "Pillar Alignment",
            s5,
            footer_lines(repo, region, audience, platform),
            suppressed_markers=s5_suppressed,
        )
    )

    s6 = dict(audience_tokens)
    s6["BBC’s (All Audience)  Audience regularly engage across a variety of platforms"] = (
        "BBC Audiences are more likely to engage across a range of platforms"
        if is_all
        else f"BBC {display_audience} are more likely to engage across a range of platforms"
    )
    s6["XX Audiences over indexing on a range of platforms vs. avg. BBC audience"] = (
        "BBC Audiences are more likely to engage across a range of platforms"
        if is_all
        else f"BBC {display_audience} are more likely to engage across a range of platforms"
    )
    s6["Audience Affinity = Likelihood of (All Audience)  Audience to regularly consume platform vs. avg. BBC Audience"] = (
        "Audience Affinity – Likelihood of BBC audiences to regularly consume a platform vs. the average audience"
        if is_all
        else f"Audience Affinity – Likelihood of BBC {display_audience} audiences to regularly consume a platform vs. the average {display_audience} audience"
    )
    for row in range(70, 77):
        # Template composition cells contain "(K70)%" while affinity cells
        # contain "(K70)". The longer token must be resolved first.
        percent_cell = f"{cols['percent']}{row}"
        index_cell = f"{cols['index']}{row}"
        s6[f"(K{row})%"] = f"{format_percent(ws[percent_cell].value)}%"
        s6[f"(K{row})"] = format_index(ws[index_cell].value)
    s6_suppressed = {
        f"(K{row})" for row in range(70, 77) if not repo.is_supported(region, audience, platform, row)
    }
    if len(s6_suppressed) == 7:
        no_platform_data = "No platform statistics are shown because all response bases are below 50"
        s6["BBC’s (All Audience)  Audience regularly engage across a variety of platforms"] = no_platform_data
        s6["XX Audiences over indexing on a range of platforms vs. avg. BBC audience"] = no_platform_data
        s6[
            "Audience Affinity = Likelihood of (All Audience)  Audience to regularly consume platform vs. avg. BBC Audience"
        ] = ""
    slides.append(
        SlideModel(
            6,
            "Platform Consumption",
            s6,
            footer_lines(repo, region, audience, platform),
            suppressed_markers=s6_suppressed,
        )
    )

    s7 = dict(audience_tokens)
    if is_all:
        s7["Audience Demographics – (All Audience) Audience"] = "Audience Demographics"
        s7["BBC Reach a number of (All Audience)  Audience across a range of Demographics "] = (
            "BBC Reaches Audiences across a Range of Demographics"
        )
        s7["BBCs (All Audience)  Audience more likely to be younger and affluence vs. avg. online audience"] = (
            "BBC Audiences span a broad range of demographic groups"
        )
    for row in range(77, 87):
        s7[f"(I{row})"] = format_compact(ws[f"{cols['universe']}{row}"].value)
        s7[f"(K{row})"] = format_percent(ws[f"{cols['percent']}{row}"].value)
        s7[f"(M{row})"] = format_index(ws[f"{cols['index']}{row}"].value)
    s7_suppressed = set()
    for row in range(77, 87):
        if not repo.is_supported(region, audience, platform, row):
            s7_suppressed.update(_template_markers(row, "IKM"))
    if len(s7_suppressed) == 30:
        s7["BBC Reach a number of (All Audience)  Audience across a range of Demographics "] = (
            "No demographic statistics are shown because all response bases are below 50"
        )
        s7["BBCs (All Audience)  Audience more likely to be younger and affluence vs. avg. online audience"] = ""
    slides.append(
        SlideModel(
            7,
            "Demographics",
            s7,
            footer_lines(repo, region, audience, platform),
            suppressed_markers=s7_suppressed,
        )
    )

    s8 = dict(audience_tokens)
    if is_all:
        s8["BBC’s (All Audience)  Audience regularly engage across a variety of platforms"] = (
            "BBC Audiences Work Across a Range of Organisations"
        )
        s8["BBC’s (All Audience)  Audiences are more likely to hold a number of senior business positions"] = (
            "BBC Audiences include senior decision-makers and business leaders"
        )
    for row in range(87, 97):
        s8[f"(K{row})"] = format_percent(ws[f"{cols['percent']}{row}"].value)
        s8[f"(M{row})"] = format_index(ws[f"{cols['index']}{row}"].value)
    s8_suppressed = set()
    for row in range(87, 97):
        if not repo.is_supported(region, audience, platform, row):
            s8_suppressed.update(_template_markers(row, "KM"))
    if len(s8_suppressed) == 20:
        s8["BBC’s (All Audience)  Audience regularly engage across a variety of platforms"] = (
            "No employment statistics are shown because all response bases are below 50"
        )
        s8["BBC’s (All Audience)  Audiences are more likely to hold a number of senior business positions"] = ""
    slides.append(
        SlideModel(
            8,
            "Employment Profile",
            s8,
            footer_lines(repo, region, audience, platform),
            suppressed_markers=s8_suppressed,
        )
    )

    s9 = dict(audience_tokens)
    if is_all:
        s9["BBC’s (All Audience)  Audience are more likely to hold positive attitudes towards AI implementation"] = (
            "BBC Audiences Hold Positive Attitudes Towards AI"
        )
        s9["(All Audience)  Audience AI Attitudes"] = "BBC Audience AI Attitudes"
        s9["BBC (All Audience)  Audiences more likely to agree.."] = "BBC Audiences are more likely to agree"
    for row in range(97, 101):
        s9[f"(M{row})"] = format_index_difference(ws[f"{cols['index']}{row}"].value)
    s9_suppressed = {
        f"(M{row})" for row in range(97, 101) if not repo.is_supported(region, audience, platform, row)
    }
    if len(s9_suppressed) == 4:
        s9["BBC’s (All Audience)  Audience are more likely to hold positive attitudes towards AI implementation"] = (
            "No AI attitude statistics are shown because all response bases are below 50"
        )
        s9["BBC (All Audience)  Audiences more likely to agree.."] = ""
    slides.append(
        SlideModel(
            9,
            "AI Attitudes",
            s9,
            footer_lines(repo, region, audience, platform),
            suppressed_markers=s9_suppressed,
        )
    )

    return PresentationModel(audience, region, platform, slides)
