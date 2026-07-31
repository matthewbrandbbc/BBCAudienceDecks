from src.audience_ai import GroundedAudienceEngine
from src.data_engine import WorkbookRepository


def engine():
    return GroundedAudienceEngine(WorkbookRepository())


def test_overview_is_grounded_and_uses_selected_scope():
    overview = engine().overview("Latin America", "C-Suites", "Cross Platform")
    assert overview.headline == "C-Suites in Latin America — grounded sales overview"
    assert len(overview.bullets) == 4
    assert "BBC reaches" in overview.bullets[0]
    assert "Index" in overview.bullets[2]
    assert all(item.source_label == "GWI Latin America — C-Suites" for item in overview.evidence)
    assert all(item.cells for item in overview.evidence)


def test_index_explanation_is_fixed_and_not_generated():
    answer = engine().answer(
        "What does an index of 123 mean?",
        "All Markets",
        "All Audiences",
        "Cross Platform",
    )
    assert "23% more likely" in answer.answer
    assert "not audience size" in answer.answer


def test_question_can_override_current_filters():
    answer = engine().answer(
        "What is the strongest argument for C-Suites in Latin America on digital?",
        "All Markets",
        "All Audiences",
        "Cross Platform",
    )
    assert answer.resolved_scope == "C-Suites · Latin America · Digital"
    assert "Sales takeout:" in answer.answer
    assert answer.evidence


def test_cross_workbook_audience_leaderboard():
    answer = engine().answer(
        "Which audience has the strongest digital media affinity in Europe?",
        "All Markets",
        "All Audiences",
        "Cross Platform",
    )
    assert answer.resolved_scope.endswith("Europe · Digital")
    assert "media behaviour signal" in answer.answer
    assert answer.evidence[0].source_label.startswith("GWI Europe")


def test_unsupported_competitor_is_disclosed():
    answer = engine().answer(
        "How does BBC compare with the FT for business audiences in Europe?",
        "All Markets",
        "All Audiences",
        "Cross Platform",
    )
    assert "does not contain the Financial Times" in answer.answer
    assert answer.resolved_scope.startswith("Business Decision Makers (BDMs)")


def test_plural_affinities_question_is_understood():
    answer = engine().answer(
        "What are the top affinities for HNWIs in North America on TV?",
        "All Markets",
        "All Audiences",
        "Cross Platform",
    )
    assert answer.resolved_scope == "HNWIs · North America · TV"
    assert "highest-indexing qualities" in answer.answer
    assert len(answer.evidence) == 5


def test_composition_question_returns_percentage_and_index():
    answer = engine().answer(
        "What percentage of the base are male?",
        "Latin America",
        "C-Suites",
        "Cross Platform",
    )
    assert "composition percentage" in answer.answer
    assert "%" in answer.answer
    assert "index" in answer.answer.casefold()
    assert answer.evidence[0].cells == "K77, M77, J77"


def test_more_likely_to_do_ranks_behavioural_rows():
    answer = engine().answer(
        "Are there any things that BBC audiences are more likely to do?",
        "Europe",
        "All Audiences",
        "Digital",
    )
    assert "highest-indexing behaviours and interests" in answer.answer
    assert "composition" in answer.answer
    assert len(answer.evidence) == 5
    assert all(int(item.cells.split(",")[0][1:]) <= 76 for item in answer.evidence)


def test_top_indexing_qualities_searches_all_profile_sections():
    answer = engine().answer(
        "What are the top indexing qualities for C-Suites?",
        "All Markets",
        "C-Suites",
        "Cross Platform",
    )
    assert "highest-indexing qualities" in answer.answer
    assert len(answer.evidence) == 5
    assert all("M93" not in item.cells for item in answer.evidence)


def test_low_base_suppresses_composition_and_all_numeric_fields():
    answer = engine().answer(
        "What percentage of the base are male?",
        "Africa",
        "FBDMs – Finance Business Decision Makers",
        "Digital",
    )
    assert "below 50" in answer.answer
    assert not answer.evidence
    assert "%" not in answer.answer


def test_follow_up_retains_intent_and_changes_region():
    first = engine().answer(
        "What are the top indexing qualities for C-Suites in Latin America?",
        "All Markets", "All Audiences", "Cross Platform",
    )
    second = engine().answer(
        "What about Europe?", "All Markets", "All Audiences", "Cross Platform",
        previous_question="What are the top indexing qualities for C-Suites in Latin America?",
        previous_scope=("C-Suites", "Latin America", "Cross Platform"),
    )
    assert first.evidence and second.evidence
    assert second.resolved_scope == "C-Suites · Europe · Cross Platform"
    assert "highest-indexing qualities" in second.answer


def test_fuzzy_metric_matching_and_two_way_comparison():
    fuzzy = engine().answer(
        "What percentage are afluent?", "Europe", "All Audiences", "Digital"
    )
    comparison = engine().answer(
        "Compare C-Suites vs HNWIs", "Europe", "All Audiences", "Digital"
    )
    assert "high-income consumers" in fuzzy.answer
    assert "C-Suites in Europe" in comparison.answer
    assert "HNWIs in Europe" in comparison.answer
