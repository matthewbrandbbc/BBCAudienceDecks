from __future__ import annotations

from dataclasses import dataclass
from difflib import get_close_matches
import re
from typing import Iterable

from .config import MIN_RESPONSES, PLATFORM_COLUMNS
from .data_engine import WorkbookRepository, clean_audience_name, format_compact


PLATFORM_START_ROWS = {"Cross Platform": 40, "Digital": 46, "TV": 52}

METRIC_LABELS = {
    58: "business",
    59: "economy, finance, entrepreneurship and investments",
    60: "exploring the world",
    61: "international travel",
    62: "following the latest technology trends and news",
    63: "early adoption of new technology",
    64: "interest in other cultures and countries",
    65: "theatre, film and cinema",
    66: "following three or more sports",
    67: "playing or watching sport",
    68: "personal healthcare",
    69: "health food, drinks and nutrition",
    70: "browsing social media most days",
    71: "watching short-form video most days",
    72: "watching online video and how-to content most days",
    73: "reading online press and articles most days",
    74: "watching broadcast TV most days",
    75: "watching streaming services most days",
    76: "listening to podcasts most days",
    77: "men",
    78: "women",
    79: "university graduates",
    80: "Gen Z",
    81: "Millennials",
    82: "Gen X",
    83: "Baby Boomers and the Silent Generation",
    84: "parents",
    85: "high-income consumers",
    86: "international travellers",
    87: "people working in smaller organisations",
    88: "people working in larger organisations",
    89: "business decision-makers",
    90: "finance business decision-makers",
    91: "IT business decision-makers",
    92: "senior management",
    93: "C-Suites",
    94: "company strategy decision-makers",
    95: "recruitment decision-makers",
    96: "sustainability and energy decision-makers",
    97: "believing AI benefits society",
    98: "believing AI enhances daily life",
    99: "believing AI can help solve major global problems",
    100: "believing AI will create more job opportunities",
}

CATEGORY_RANGES = {
    "content and interests": range(58, 70),
    "media behaviour": range(70, 77),
    "demographics": range(77, 87),
    "business profile": range(87, 97),
    "AI attitudes": range(97, 101),
}

METRIC_ALIASES = {
    58: ("business interest", "interested in business"),
    59: ("finance interest", "economy", "finance", "investments", "investing"),
    60: ("explore the world",),
    61: ("international travel", "business travel"),
    62: ("technology trends", "tech trends"),
    63: ("early adopter", "new technology", "new tech"),
    64: ("other cultures", "other countries"),
    65: ("theatre", "cinema", "films"),
    66: ("follow sports", "three sports", "3 sports"),
    67: ("playing sport", "watching sport", "sports"),
    68: ("healthcare", "personal healthcare"),
    69: ("health food", "nutrition"),
    70: ("social media",),
    71: ("short video", "short form video", "reels", "tiktok"),
    72: ("online video", "how to video", "vlogs"),
    73: ("online press", "online articles", "articles"),
    74: ("broadcast tv",),
    75: ("streaming", "streaming services"),
    76: ("podcast", "podcasts"),
    77: ("male", "males", "men", "man"),
    78: ("female", "females", "women", "woman"),
    79: ("graduates", "graduate", "degree", "university educated"),
    80: ("gen z", "generation z"),
    81: ("millennials", "millennial", "gen y"),
    82: ("gen x", "generation x"),
    83: ("baby boomers", "boomers", "silent generation"),
    84: ("parents", "parent", "children", "child"),
    85: ("high income", "affluent", "affluence"),
    86: ("international travellers", "international travelers"),
    87: ("small organisations", "small organizations", "small companies", "smes"),
    88: ("large organisations", "large organizations", "large companies"),
    89: ("business decision makers", "bdms", "bdm"),
    90: ("finance decision makers", "fbdms", "fbdm"),
    91: ("it decision makers", "itbdms", "itbdm"),
    92: ("senior management", "senior managers"),
    93: ("c suites", "c suite", "executives"),
    94: ("company strategy", "strategy decision makers"),
    95: ("recruitment", "recruiting", "hiring"),
    96: ("sustainability decision makers", "energy decision makers"),
    97: ("ai benefits society",),
    98: ("ai enhances daily life",),
    99: ("ai solve global problems", "ai solve world problems"),
    100: ("ai job opportunities", "ai create jobs"),
}

DEFINITION_ROWS = {
    "Business Decision Makers (BDMs)": {89},
    "C-Suites": {93},
    "FBDMs – Finance Business Decision Makers": {90},
    "Gen Z": {80},
    "IT Business Decision Makers (ITBDMs)": {91},
    "Sports Enthusiasts": {67},
}

AUDIENCE_ALIASES = {
    "all": "All Audiences",
    "all audiences": "All Audiences",
    "c suite": "C-Suites",
    "c suites": "C-Suites",
    "hnwi": "HNWIs",
    "hnwis": "HNWIs",
    "sme": "SMEs",
    "smes": "SMEs",
    "bdm": "Business Decision Makers (BDMs)",
    "bdms": "Business Decision Makers (BDMs)",
    "business audience": "Business Decision Makers (BDMs)",
    "business audiences": "Business Decision Makers (BDMs)",
    "fbdm": "FBDMs – Finance Business Decision Makers",
    "fbdms": "FBDMs – Finance Business Decision Makers",
    "itbdm": "IT Business Decision Makers (ITBDMs)",
    "itbdms": "IT Business Decision Makers (ITBDMs)",
}

REGION_ALIASES = {
    "global": "All Markets",
    "worldwide": "All Markets",
    "all markets": "All Markets",
    "north america": "North America",
    "latin america": "Latin America",
    "europe": "Europe",
    "middle east": "Middle East",
    "africa": "Africa",
    "south asia": "South Asia",
    "apac": "APAC",
    "asia pacific": "APAC",
}

PLATFORM_ALIASES = {
    "cross platform": "Cross Platform",
    "cross-platform": "Cross Platform",
    "digital": "Digital",
    "online": "Digital",
    "tv": "TV",
    "television": "TV",
}


@dataclass(frozen=True)
class Evidence:
    statement: str
    value: str
    source_label: str
    cells: str


@dataclass(frozen=True)
class Affinity:
    label: str
    index: float
    percent: float
    category: str
    row: int
    source_label: str
    cells: str
    responses: int


@dataclass(frozen=True)
class AudienceOverview:
    headline: str
    bullets: tuple[str, ...]
    sales_takeout: str
    evidence: tuple[Evidence, ...]


@dataclass(frozen=True)
class GroundedAnswer:
    answer: str
    evidence: tuple[Evidence, ...] = ()
    resolved_scope: str = ""


def _normalise(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


def _index_phrase(index: float) -> str:
    difference = round(index - 100)
    if difference > 0:
        return f"{difference}% more likely than the comparison audience"
    if difference < 0:
        return f"{abs(difference)}% less likely than the comparison audience"
    return "in line with the comparison audience"


def _percent(value: float) -> str:
    return f"{round(float(value) * 100):.0f}%"


def _source_label(region: str, audience: str) -> str:
    return f"GWI {region} — {audience}"


def _platform_phrase(platform: str) -> str:
    return {"Cross Platform": "cross-platform", "Digital": "digital", "TV": "TV"}[platform]


def _audience_phrase(audience: str) -> str:
    if audience == "All Audiences":
        return "BBC audiences"
    if " – " in audience:
        return f"BBC {audience.split(' – ', 1)[0]}"
    acronym = re.search(r"\(([A-Z][A-Z0-9-]{1,}s?)\)\s*$", audience)
    return f"BBC {acronym.group(1) if acronym else audience}"


class GroundedAudienceEngine:
    """Deterministic insight and Q&A layer with no external AI dependency.

    A future LLM adapter should call these methods as tools rather than read
    workbooks directly. This keeps every generated claim tied to validated data.
    """

    def __init__(self, repo: WorkbookRepository):
        self.repo = repo
        self.audiences = tuple(repo.audience_map("All Markets"))
        self.regions = tuple(repo.paths)

    def reach_evidence(self, region: str, audience: str, platform: str) -> Evidence | None:
        ws = self.repo.sheet(region, audience)
        cols = PLATFORM_COLUMNS[platform]
        universe_cell = f"{cols['universe']}16"
        rate_cell = f"{cols['row_percent']}16"
        response_cell = f"{cols['responses']}16"
        responses = int(ws[response_cell].value or 0)
        if responses < MIN_RESPONSES:
            return None
        reach = format_compact(ws[universe_cell].value)
        rate = _percent(ws[rate_cell].value)
        return Evidence(
            statement=f"BBC {_platform_phrase(platform)} monthly reach",
            value=f"{reach} ({rate} of the selected audience)",
            source_label=_source_label(region, audience),
            cells=f"{universe_cell}, {rate_cell}, {response_cell}",
        )

    def competitive_evidence(self, region: str, audience: str, platform: str) -> Evidence | None:
        start = PLATFORM_START_ROWS[platform]
        items = self.repo.supported_competitor_set(region, audience, start)
        if not items or not any(item.name.casefold() == "bbc" for item in items):
            return None
        rank = next(i for i, item in enumerate(items, 1) if item.name.casefold() == "bbc")
        bbc = next(item for item in items if item.name.casefold() == "bbc")
        leader = items[0]
        if rank == 1:
            detail = f"1st of {len(items)}, reaching {format_compact(bbc.value)}"
        else:
            detail = (
                f"{rank}{'nd' if rank == 2 else 'rd' if rank == 3 else 'th'} of {len(items)}, "
                f"reaching {format_compact(bbc.value)}; {leader.name} leads at {format_compact(leader.value)}"
            )
        return Evidence(
            statement=f"BBC competitive position on {_platform_phrase(platform)}",
            value=detail,
            source_label=_source_label(region, audience),
            cells=f"C{start}:E{start + 5}",
        )

    def affinities(
        self,
        region: str,
        audience: str,
        platform: str,
        rows: Iterable[int] = range(58, 101),
    ) -> list[Affinity]:
        ws = self.repo.sheet(region, audience)
        cols = PLATFORM_COLUMNS[platform]
        results = []
        for row in rows:
            category = next(
                (name for name, category_rows in CATEGORY_RANGES.items() if row in category_rows),
                "audience profile",
            )
            responses = int(ws[f"{cols['responses']}{row}"].value or 0)
            if responses < MIN_RESPONSES:
                continue
            results.append(
                Affinity(
                    label=METRIC_LABELS[row],
                    index=float(ws[f"{cols['index']}{row}"].value),
                    percent=float(ws[f"{cols['percent']}{row}"].value),
                    category=category,
                    row=row,
                    source_label=_source_label(region, audience),
                    cells=f"{cols['percent']}{row}, {cols['index']}{row}, {cols['responses']}{row}",
                    responses=responses,
                )
            )
        return sorted(results, key=lambda item: (-item.index, item.row))

    def ranked_affinities(
        self,
        region: str,
        audience: str,
        platform: str,
        rows: Iterable[int],
        limit: int = 5,
        exclude_definition: bool = True,
    ) -> list[Affinity]:
        excluded = DEFINITION_ROWS.get(audience, set()) if exclude_definition else set()
        return [
            item
            for item in self.affinities(region, audience, platform, rows)
            if item.row not in excluded
        ][:limit]

    def _match_metric_row(self, question: str) -> int | None:
        normal = _normalise(question)
        for row, aliases in METRIC_ALIASES.items():
            for alias in sorted(aliases, key=len, reverse=True):
                if re.search(rf"\b{re.escape(_normalise(alias))}\b", normal):
                    return row
        words = [word for word in normal.split() if len(word) >= 5]
        alias_words = {
            word: row
            for row, aliases in METRIC_ALIASES.items()
            for alias in aliases
            for word in _normalise(alias).split()
            if len(word) >= 5
        }
        for word in words:
            match = get_close_matches(word, alias_words, n=1, cutoff=0.82)
            if match:
                return alias_words[match[0]]
        return None

    def metric(self, region: str, audience: str, platform: str, row: int) -> Affinity | None:
        items = self.affinities(region, audience, platform, [row])
        return items[0] if items else None

    @staticmethod
    def claim_strength(item: Affinity) -> str:
        if item.responses >= 100 and item.index >= 120 and item.percent >= .10:
            return "Strong"
        if item.index >= 110 and item.percent >= .05:
            return "Moderate"
        return "Limited"

    def composition_evidence(
        self, region: str, audience: str, platform: str, row: int
    ) -> Evidence:
        item = self.metric(region, audience, platform, row)
        if item is None:
            raise ValueError("Response base below reporting threshold")
        return Evidence(
            statement=f"Composition: {item.label}",
            value=f"{_percent(item.percent)} of the selected BBC audience; Index {round(item.index)}",
            source_label=item.source_label,
            cells=item.cells,
        )

    def top_distinctive_affinity(
        self, region: str, audience: str, platform: str
    ) -> Affinity | None:
        # Interests, media behaviours and AI attitudes are broadly useful sales
        # evidence and avoid circular audience-definition claims.
        rows = (*range(58, 77), *range(97, 101))
        items = self.affinities(region, audience, platform, rows)
        return items[0] if items else None

    def overview(self, region: str, audience: str, platform: str) -> AudienceOverview:
        reach = self.reach_evidence(region, audience, platform)
        competitive = self.competitive_evidence(region, audience, platform)
        affinity = self.top_distinctive_affinity(region, audience, platform)
        audience_phrase = _audience_phrase(audience)

        evidence = []
        bullets = []
        if reach:
            evidence.append(reach)
            bullets.append(f"BBC reaches {reach.value} through {_platform_phrase(platform)} in {region}.")
        if competitive:
            evidence.append(competitive)
            bullets.append(f"BBC ranks {competitive.value} within the available news competitive set.")
        if affinity:
            affinity_evidence = Evidence(
            statement=f"Strongest distinctive signal: {affinity.label}",
            value=f"Index {round(affinity.index)}; {_percent(affinity.percent)} engage",
            source_label=affinity.source_label,
                cells=affinity.cells,
            )
            evidence.append(affinity_evidence)
            bullets.append(
                f"{audience_phrase} stand out for {affinity.label}: Index "
                f"{round(affinity.index)}, or {_index_phrase(affinity.index)}. Claim strength: {self.claim_strength(affinity)}."
            )
        if not bullets:
            bullets = [f"No statistics are shown because the available response bases are below {MIN_RESPONSES}."]
        sales_takeout = (
            "Use the supported reach, competitive and affinity signals together; treat the score as directional, not a forecast."
            if evidence else f"No sales claim should be made from this selection because its available response bases are below {MIN_RESPONSES}."
        )
        return AudienceOverview(
            headline=f"{audience} in {region}",
            bullets=tuple(bullets),
            sales_takeout=sales_takeout,
            evidence=tuple(evidence),
        )

    def _resolve_scope(
        self, question: str, region: str, audience: str, platform: str
    ) -> tuple[str, str, str]:
        normal = _normalise(question)

        for alias, candidate in sorted(REGION_ALIASES.items(), key=lambda item: -len(item[0])):
            if re.search(rf"\b{re.escape(_normalise(alias))}\b", normal):
                region = candidate
                break

        for alias, candidate in sorted(PLATFORM_ALIASES.items(), key=lambda item: -len(item[0])):
            if re.search(rf"\b{re.escape(_normalise(alias))}\b", normal):
                platform = candidate
                break

        audience_candidates = {**AUDIENCE_ALIASES}
        for candidate in self.audiences:
            audience_candidates[_normalise(candidate)] = candidate
            audience_candidates[_normalise(clean_audience_name(candidate))] = candidate
        for alias, candidate in sorted(audience_candidates.items(), key=lambda item: -len(item[0])):
            if alias and re.search(rf"\b{re.escape(alias)}\b", normal):
                audience = candidate
                break
        return region, audience, platform

    def _leaderboard(
        self, region: str, platform: str, category_rows: Iterable[int]
    ) -> tuple[Affinity, str]:
        candidates = []
        for audience in self.audiences:
            if audience == "All Audiences":
                continue
            supported = self.affinities(region, audience, platform, category_rows)
            if not supported:
                continue
            best = supported[0]
            candidates.append((best.index, audience, best))
        _, audience, affinity = max(candidates, key=lambda item: (item[0], item[1]))
        return affinity, audience

    def _mentioned(self, question: str, aliases: dict[str, str], candidates=()) -> list[str]:
        normal = _normalise(question)
        terms = dict(aliases)
        for candidate in candidates:
            terms[_normalise(candidate)] = candidate
            terms[_normalise(clean_audience_name(candidate))] = candidate
        found = []
        for alias, value in sorted(terms.items(), key=lambda item: -len(item[0])):
            match = re.search(rf"\b{re.escape(_normalise(alias))}\b", normal)
            if match and value not in [item[1] for item in found]:
                found.append((match.start(), value))
        return [value for _, value in sorted(found)]

    def _comparison(self, question: str, region: str, audience: str, platform: str):
        audiences = self._mentioned(question, AUDIENCE_ALIASES, self.audiences)
        regions = self._mentioned(question, REGION_ALIASES)
        pairs = []
        if len(audiences) >= 2:
            pairs = [(region, audiences[0]), (region, audiences[1])]
        elif len(regions) >= 2:
            pairs = [(regions[0], audience), (regions[1], audience)]
        if not pairs:
            return None
        lines, evidence = [], []
        for item_region, item_audience in pairs:
            reach = self.reach_evidence(item_region, item_audience, platform)
            affinity = self.top_distinctive_affinity(item_region, item_audience, platform)
            parts = []
            if reach:
                parts.append(f"reach {reach.value}")
                evidence.append(reach)
            if affinity:
                parts.append(f"top signal {affinity.label} (Index {round(affinity.index)}, {self.claim_strength(affinity)} claim)")
                evidence.append(Evidence("Top distinctive signal", f"{affinity.label}; Index {round(affinity.index)}", affinity.source_label, affinity.cells))
            lines.append(f"- {item_audience} in {item_region}: " + ("; ".join(parts) if parts else f"no reportable statistics; base below {MIN_RESPONSES}"))
        return GroundedAnswer("A grounded two-way comparison:\n\n" + "\n".join(lines), tuple(evidence), f"{audience} · {region} · {platform}")

    def answer(
        self, question: str, region: str, audience: str, platform: str,
        previous_question: str | None = None,
        previous_scope: tuple[str, str, str] | None = None,
    ) -> GroundedAnswer:
        if not question.strip():
            return GroundedAnswer("Ask a question about reach, indexes, affinities or competitive position.")

        normal = _normalise(question)
        if previous_scope and re.match(r"^(what|how) about\b|^and\b|^compare with\b", normal):
            audience, region, platform = previous_scope
        region, audience, platform = self._resolve_scope(question, region, audience, platform)
        intent_text = question
        if previous_question and re.match(r"^(what|how) about\b|^and\b|^compare with\b", normal):
            intent_text = f"{previous_question} {question}"
            normal = _normalise(intent_text)
        scope = f"{audience} · {region} · {platform}"
        metric_row = self._match_metric_row(intent_text)

        if any(term in normal for term in ("compare", "versus", " vs ", "difference between")):
            comparison = self._comparison(question, region, audience, platform)
            if comparison:
                return comparison

        if "index" in normal and (
            any(phrase in normal for phrase in ("mean", "explain", "definition", "understand"))
            or bool(re.search(r"\bwhat (?:is|does) (?:an? )?index\b", normal))
        ):
            return GroundedAnswer(
                "An index compares the selected BBC audience with the relevant average audience. "
                "An index of 100 means no difference; 123 means the selected audience is 23% more "
                "likely to display that behaviour; 85 means it is 15% less likely. Indexes describe "
                "relative likelihood, not audience size.",
                resolved_scope=scope,
            )

        if "affinity" in normal and any(
            phrase in normal for phrase in ("what", "mean", "explain", "definition")
        ):
            return GroundedAnswer(
                "Affinity shows how strongly a behaviour or characteristic is associated with the "
                "selected BBC audience compared with the relevant average audience. The index shows "
                "relative likelihood, while the percentage shows how many people in the selected "
                "audience display the behaviour.",
                resolved_scope=scope,
            )

        if metric_row is None and "composition" in normal and any(
            phrase in normal for phrase in ("what", "mean", "explain", "definition")
        ):
            return GroundedAnswer(
                "Composition is the percentage of the selected BBC audience who have a particular "
                "characteristic or behaviour. For example, a male composition of 57% means 57% of "
                "that selected BBC audience are men. Composition describes the audience itself; "
                "the index shows how that percentage compares with the relevant average audience.",
                resolved_scope=scope,
            )

        if "reach" in normal and any(
            phrase in normal for phrase in ("what", "mean", "explain", "definition")
        ):
            return GroundedAnswer(
                "Reach is the estimated number of people in the selected audience who used the BBC "
                "through the chosen platform during the 30-day measurement period. Cross Platform "
                "combines BBC digital and TV reach without simply adding the two figures.",
                resolved_scope=scope,
            )

        composition_terms = ("percentage", "percent", "proportion", "share", "composition")
        if metric_row is not None and any(term in normal for term in composition_terms):
            item = self.metric(region, audience, platform, metric_row)
            if item is None:
                return GroundedAnswer(
                    f"That statistic is not reportable because its response base is below {MIN_RESPONSES}. Universe, composition and index are suppressed together.",
                    resolved_scope=scope,
                )
            evidence = self.composition_evidence(region, audience, platform, metric_row)
            return GroundedAnswer(
                f"{_percent(item.percent)} of the selected BBC {_platform_phrase(platform)} "
                f"audience for {audience} in {region} are {item.label}. This is a composition "
                f"percentage. Their index is {round(item.index)}, meaning they are "
                f"{_index_phrase(item.index)}.",
                (evidence,),
                scope,
            )

        if any(term in normal for term in ("largest composition", "top composition", "biggest composition")):
            top = sorted(
                self.affinities(region, audience, platform),
                key=lambda item: (-item.percent, item.row),
            )[:5]
            evidence = tuple(
                Evidence(
                    statement=f"Composition: {item.label}",
                    value=f"{_percent(item.percent)}; Index {round(item.index)}",
                    source_label=item.source_label,
                    cells=item.cells,
                )
                for item in top
            )
            lines = [
                f"{item.label}: {_percent(item.percent)} composition (Index {round(item.index)})."
                for item in top
            ]
            return GroundedAnswer(
                "The largest composition measures in the selected base are:\n\n"
                + "\n".join(f"- {line}" for line in lines)
                + "\n\nThese measures can overlap, so they should not be added together.",
                evidence,
                scope,
            )

        if "which audience" in normal or "what audience" in normal:
            if any(term in normal for term in ("platform", "media", "podcast", "social", "video")):
                rows = range(70, 77)
                category = "media behaviour"
            elif "ai" in normal:
                rows = range(97, 101)
                category = "AI attitude"
            elif any(term in normal for term in ("business", "senior", "decision")):
                rows = range(87, 97)
                category = "business-profile"
            else:
                rows = (*range(58, 77), *range(97, 101))
                category = "distinctive"
            affinity, winning_audience = self._leaderboard(region, platform, rows)
            evidence = Evidence(
                statement=f"Highest {category} index",
                value=f"{winning_audience}: {affinity.label}, Index {round(affinity.index)}",
                source_label=affinity.source_label,
                cells=affinity.cells,
            )
            return GroundedAnswer(
                f"{winning_audience} has the strongest {category} signal in {region} on "
                f"{_platform_phrase(platform)}: {affinity.label}, with an index of {round(affinity.index)} "
                f"({_index_phrase(affinity.index)}).",
                (evidence,),
                scope,
            )

        if any(term in normal for term in ("strongest argument", "best argument", "sales argument", "sell")):
            overview = self.overview(region, audience, platform)
            return GroundedAnswer(
                "The strongest defensible argument is the combination of these points:\n\n"
                + "\n".join(f"- {bullet}" for bullet in overview.bullets)
                + f"\n\nSales takeout: {overview.sales_takeout}",
                overview.evidence,
                scope,
            )

        if any(term in normal for term in ("competitor", "competitive", "rank", "cnn", "cnbc", "ft")):
            evidence = self.competitive_evidence(region, audience, platform)
            if evidence is None:
                return GroundedAnswer(f"A competitive statistic is not reportable because the BBC response base is below {MIN_RESPONSES}.", resolved_scope=scope)
            note = ""
            if "ft" in normal:
                note = (
                    " The supplied competitive set does not contain the Financial Times, so this "
                    "workspace cannot make a direct BBC-versus-FT claim."
                )
            return GroundedAnswer(
                f"For {audience} in {region}, {evidence.statement.lower()} is {evidence.value}.{note}",
                (evidence,),
                scope,
            )

        if any(term in normal for term in ("reach", "how many", "audience size", "scale")):
            evidence = self.reach_evidence(region, audience, platform)
            if evidence is None:
                return GroundedAnswer(f"The reach statistic is not reportable because its response base is below {MIN_RESPONSES}. Universe, percentage and index are suppressed together.", resolved_scope=scope)
            return GroundedAnswer(
                f"BBC’s estimated {_platform_phrase(platform)} monthly reach among {audience} in {region} "
                f"is {evidence.value}.",
                (evidence,),
                scope,
            )

        behavioural_question = any(
            term in normal
            for term in (
                "more likely to do",
                "most likely to do",
                "behaviour",
                "behavior",
                "activities",
                "habits",
            )
        )
        profile_ranking_question = any(
            term in normal
            for term in (
                "top index",
                "highest index",
                "top indexing",
                "highest indexing",
                "over index",
                "overindex",
                "qualities",
                "characteristics",
            )
        )
        if behavioural_question or profile_ranking_question or any(
            term in normal for term in ("affinit", "likely", "interest")
        ):
            rows = range(58, 77) if behavioural_question else range(58, 101)
            top = self.ranked_affinities(region, audience, platform, rows, limit=5)
            if not top:
                return GroundedAnswer(f"No reportable qualities were found because all relevant response bases are below {MIN_RESPONSES}.", resolved_scope=scope)
            evidence = tuple(
                Evidence(
                    statement=item.label,
                    value=(
                        f"Index {round(item.index)}; composition {_percent(item.percent)}; "
                        f"category {item.category}; claim strength {self.claim_strength(item)}"
                    ),
                    source_label=item.source_label,
                    cells=item.cells,
                )
                for item in top
            )
            lines = [
                f"{item.label} ({item.category}): Index {round(item.index)} "
                f"({_index_phrase(item.index)}); composition {_percent(item.percent)}; {self.claim_strength(item)} claim."
                for item in top
            ]
            return GroundedAnswer(
                f"The highest-indexing {'behaviours and interests' if behavioural_question else 'qualities'} "
                f"for {audience} in {region} on {_platform_phrase(platform)} are:\n\n"
                + "\n".join(f"- {line}" for line in lines)
                + "\n\nDirect characteristics used to define the selected audience base are excluded "
                "from this ranking where identifiable.",
                evidence,
                scope,
            )

        return GroundedAnswer(
            "Sorry, I can’t answer that right now. I can help with audience reach, composition, "
            "indexes, affinities, competitive position and evidence-based sales arguments from "
            "the available audience workbooks.",
            resolved_scope=scope,
        )
