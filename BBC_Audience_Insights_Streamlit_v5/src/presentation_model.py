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
    if audience == "All Audiences":
        return "Total BBC Audience"
    if " – " in audience:
        return audience.split(" – ", 1)[0]
    acronym = re.search(r"\(([A-Z][A-Z0-9-]{1,}s?)\)\s*$", audience)
    return acronym.group(1) if acronym else audience


def audience_sentence_name(audience: str) -> str:
    """Return a clean audience phrase without duplicated audience wording."""
    display = title_audience_name(audience)
    if audience == "All Audiences":
        return "Total BBC Audience"
    established = {
        "BDMs": "BDM Audiences",
        "C-Suites": "C-Suite Audiences",
        "FBDMs": "FBDM Audiences",
        "HNWIs": "HNWI Audiences",
        "ITBDMs": "ITBDM Audiences",
        "SMEs": "SME Audiences",
        "Auto Intenders": "Auto Intender Audiences",
        "International Leisure Travellers": "International Leisure Traveller Audiences",
        "Investors": "Investor Audiences",
        "Self Improvers": "Self-Improver Audiences",
        "Sports Enthusiasts": "Sports Enthusiast Audiences",
        "Tech Enthusiasts": "Tech Enthusiast Audiences",
    }
    if display in established:
        return established[display]
    base = re.sub(r"\s+audiences?$", "", display, flags=re.I).strip()
    return f"{base} Audiences"


def _template_markers(row: int, columns: str) -> set[str]:
    return {f"({column}{row})" for column in columns}


BRAND_DISCOVERY_LABELS = {
    112: "Ads on Social Media",
    113: "TV Ads",
    114: "Website Ads",
    115: "Ads on CTV / streaming video",
    116: "Email / Newsletters",
    117: "Ads in Podcasts",
    118: "Content in News Articles",
}


def build_model(repo: WorkbookRepository, region: str, audience: str, platform: str) -> PresentationModel:
    ws = repo.sheet(region, audience)
    global_ws = repo.sheet("All Markets", audience)
    cols = PLATFORM_COLUMNS[platform]
    is_total = audience == "All Audiences"
    display_audience = title_audience_name(audience)
    sentence_audience = audience_sentence_name(audience)
    bbc_audience = "Total BBC Audience" if is_total else f"BBC {display_audience}"
    slides: list[SlideModel] = []

    slides.append(SlideModel(1, "Title", {"Total BBC Audience": bbc_audience}))

    s2 = {
        "[AUDIENCE]": display_audience,
        "[PLATFORM]": platform,
        "Reaching global [AUDIENCE] audiences at scale": (
            "Reaching Total BBC Audience at scale"
            if is_total else f"Reaching global {sentence_audience} at scale"
        ),
        "[AUDIENCE] audiences reached globally each month": (
            "Total BBC Audience reached globally each month"
            if is_total else f"{sentence_audience} reached globally each month"
        ),
        "(M16) : BBC Affinity Index to [AUDIENCE] Audiences": (
            "(M16) : BBC Affinity Index to the Total BBC Audience"
            if is_total else f"(M16) : BBC Affinity Index to {sentence_audience}"
        ),
        "(L16)% monthly global reach to [AUDIENCE] audiences": (
            "(L16)% monthly global reach"
            if is_total else f"(L16)% monthly global reach to {sentence_audience}"
        ),
        "(I16)": format_compact(global_ws[f"{cols['universe']}16"].value),
        "(L16)": format_percent(global_ws[f"{cols['row_percent']}16"].value),
        "(M16)": format_index(repo.audience_affinity("All Markets", audience, platform)),
    }
    s2_suppressed: set[str] = set()
    if is_total:
        # Affinity to itself is always 100 and is not an informative comparison.
        s2_suppressed.add("(M16)")
    if not repo.is_supported("All Markets", audience, platform, 16):
        s2_suppressed.update({"(I16)", "(L16)", "(M16)"})
    for row in range(33, 40):
        s2[f"(I{row})"] = format_compact(global_ws[f"{cols['universe']}{row}"].value)
        s2[f"(L{row})"] = format_percent(global_ws[f"{cols['row_percent']}{row}"].value)
        if not repo.is_supported("All Markets", audience, platform, row):
            s2_suppressed.update({f"(I{row})", f"(L{row})"})
    slides.append(SlideModel(2, "Global and Regional Reach", s2, footer_lines(repo, "All Markets", audience, platform), suppressed_markers=s2_suppressed))

    chart_specs = {
        "Cross Platform": (40, 45, None),
        "Digital": (46, 62, 8),
        "TV": (63, 68, None),
    }
    charts: dict[str, Any] = {}
    for name, (start, end, limit) in chart_specs.items():
        items = repo.supported_competitor_set(region, audience, start, end, limit)
        rank = next((i for i, item in enumerate(items, 1) if item.name.casefold() == "bbc"), None)
        charts[name] = {
            "items": [{"name": item.name, "value": item.value, "label": format_compact(item.value)} for item in items],
            "rank": rank,
            "ordinal": ordinal(rank) if rank is not None else None,
            "suppressed_count": end - start + 1 - len(items),
        }
    s3 = {
        "BBC Achieves Strong Competitive Reach to Audiences": (
            "BBC Achieves Strong Competitive Reach to Audiences"
            if is_total else f"BBC Achieves Strong Competitive Reach to {display_audience} Audiences"
        )
    }
    slides.append(SlideModel(3, "Competitive Reach", s3, footer_lines(repo, region, audience, platform, True), charts))

    s4 = {f"(K{row})": format_percent(ws[f"{cols['percent']}{row}"].value) for row in range(69, 81)}
    if not is_total:
        s4["Audiences engage strongly across each of the BBC content pillar areas"] = f"{display_audience} engage strongly across each of the BBC content pillar areas"
    s4_suppressed = {f"(K{row})" for row in range(69, 81) if not repo.is_supported(region, audience, platform, row)}
    slides.append(SlideModel(4, "Pillar Alignment", s4, footer_lines(repo, region, audience, platform), suppressed_markers=s4_suppressed))

    s5: dict[str, str] = {}
    if not is_total:
        s5["BBC Reaches Audiences across a Range of Demographics"] = f"BBC Reaches {display_audience} across a Range of Demographics"
        s5["BBC Audiences span a broad range of demographic groups"] = f"BBC {display_audience} span a broad range of demographic groups"
    s5_suppressed: set[str] = set()
    for row in range(88, 98):
        s5[f"(I{row})"] = format_compact(ws[f"{cols['universe']}{row}"].value)
        s5[f"(K{row})"] = format_percent(ws[f"{cols['percent']}{row}"].value)
        s5[f"(M{row})"] = format_index(ws[f"{cols['index']}{row}"].value)
        if not repo.is_supported(region, audience, platform, row):
            s5_suppressed.update(_template_markers(row, "IKM"))
    slides.append(SlideModel(5, "Demographics", s5, footer_lines(repo, region, audience, platform), suppressed_markers=s5_suppressed))

    s6: dict[str, str] = {}
    if not is_total:
        s6["BBC Audiences Work Across a Range of Organisations"] = f"BBC {display_audience} Work Across a Range of Organisations"
        s6["BBC Audiences include senior decision-makers and business leaders"] = f"BBC {display_audience} include senior decision-makers and business leaders"
    s6_suppressed: set[str] = set()
    for row in range(98, 108):
        s6[f"(I{row})"] = format_compact(ws[f"{cols['universe']}{row}"].value)
        s6[f"(K{row})"] = format_percent(ws[f"{cols['percent']}{row}"].value)
        s6[f"(M{row})"] = format_index(ws[f"{cols['index']}{row}"].value)
        if not repo.is_supported(region, audience, platform, row):
            s6_suppressed.update(_template_markers(row, "IKM"))
    employment_groups = ((98, 99), (100, 101, 102, 103, 104), (105, 106, 107))
    ranked_groups = [
        sorted(
            group,
            key=lambda row: (
                -float(ws[f"{cols['universe']}{row}"].value or 0),
                row,
            ),
        )
        for group in employment_groups
    ]
    slides.append(
        SlideModel(
            6,
            "Employment Profile",
            s6,
            footer_lines(repo, region, audience, platform),
            charts={"row_groups": ranked_groups},
            suppressed_markers=s6_suppressed,
        )
    )

    s7: dict[str, str] = {}
    if not is_total:
        s7["BBC Audiences are more likely to engage across a range of platforms"] = f"BBC {display_audience} are more likely to engage across a range of platforms"
    s7_suppressed: set[str] = set()
    for row in range(81, 88):
        s7[f"(K{row})"] = format_percent(ws[f"{cols['percent']}{row}"].value)
        s7[f"(M{row})"] = format_index(ws[f"{cols['index']}{row}"].value)
        if not repo.is_supported(region, audience, platform, row):
            s7_suppressed.update(_template_markers(row, "KM"))
    slides.append(SlideModel(7, "Platform Consumption", s7, footer_lines(repo, region, audience, platform), suppressed_markers=s7_suppressed))

    brand_items = []
    for row, label in BRAND_DISCOVERY_LABELS.items():
        if repo.is_supported(region, audience, platform, row):
            value = float(ws[f"{cols['index']}{row}"].value)
            brand_items.append({"name": label, "value": value, "label": format_index(value)})
    brand_items.sort(key=lambda item: (-item["value"], item["name"].casefold()))
    s8 = {
        "BBC [AUDIENCE] are more likely to discover brands across a variety of platforms": (
            "The Total BBC Audience is more likely to discover brands across a variety of platforms"
            if is_total else f"BBC {display_audience} are more likely to discover brands across a variety of platforms"
        )
    }
    slides.append(SlideModel(8, "Brand Discovery", s8, footer_lines(repo, region, audience, platform), charts={"Brand Discovery": {"items": brand_items, "suppressed_count": 7 - len(brand_items)}}))

    s9 = {
        "BBC’s [AUDIENCE] are more likely to be influenced by advertising and try new premium options": (
            "The Total BBC Audience is more likely to be influenced by advertising and try new premium options"
            if is_total else f"BBC’s {display_audience} are more likely to be influenced by advertising and try new premium options"
        )
    }
    s9_suppressed: set[str] = set()
    for row in range(119, 122):
        index_value = ws[f"{cols['index']}{row}"].value
        s9[f"(M{row})"] = f"{format_index_difference(index_value)}%"
        if not repo.is_supported(region, audience, platform, row):
            s9_suppressed.add(f"(M{row})")
    slides.append(SlideModel(9, "Impact Audience", s9, footer_lines(repo, region, audience, platform), suppressed_markers=s9_suppressed))

    s10: dict[str, str] = {}
    if not is_total:
        s10["BBC Audiences Hold Positive Attitudes Towards AI"] = f"BBC {display_audience} Hold Positive Attitudes Towards AI"
    s10_suppressed: set[str] = set()
    for row in range(108, 112):
        index_value = ws[f"{cols['index']}{row}"].value
        s10[f"(M{row})"] = f"{format_index_difference(index_value)}%"
        if not repo.is_supported(region, audience, platform, row):
            s10_suppressed.add(f"(M{row})")
    slides.append(SlideModel(10, "AI Attitudes", s10, footer_lines(repo, region, audience, platform), suppressed_markers=s10_suppressed))

    if not is_total:
        slides = [slide for slide in slides if slide.number not in {5, 6}]

    return PresentationModel(audience, region, platform, slides)
