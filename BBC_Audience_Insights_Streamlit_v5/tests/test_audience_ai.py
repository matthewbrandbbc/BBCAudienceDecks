from src.audience_ai import GroundedAudienceEngine
from src.data_engine import WorkbookRepository


def engine():
    return GroundedAudienceEngine(WorkbookRepository())


def test_overview_is_neutral_grounded_and_slide_aware():
    result = engine().overview("All Markets", "C-Suites", "Cross Platform")
    assert result.headline == "C-Suites in All Markets"
    assert len(result.bullets) == 3
    assert "Sales takeout" not in result.interpretation_note
    assert "do not establish causes" in result.interpretation_note
    assert all(item.cells and item.scope and item.reason for item in result.evidence)


def test_contextual_definitions():
    chatbot = engine()
    reach = chatbot.answer("What is reach?", "All Markets", "All Audiences", "Digital")
    index = chatbot.answer("What is an affinity index?", "Europe", "C-Suites", "TV")
    composition = chatbot.answer("Explain composition", "All Markets", "C-Suites", "TV")
    responses = chatbot.answer("What does responses mean?", "All Markets", "C-Suites", "TV")
    assert "estimated number of people" in reach.answer and "measurement period" not in reach.answer
    assert "equivalent C-Suites audience in Europe" in index.answer
    assert "relative likelihood" in index.answer and "audience size" in index.answer
    assert "make-up" in composition.answer
    assert "below 50" in responses.answer


def test_methodology_distinguishes_gwi_and_report_market_scope():
    answer = engine().answer("What markets does the GWI survey run in?", "All Markets", "All Audiences", "Cross Platform")
    assert "53 markets" in answer.answer
    assert "51 Global Markets" in answer.answer
    assert "Excl. China, Russia, UK" in answer.answer


def test_slide_guide_and_correct_slide_nine_name():
    answer = engine().answer("What does slide 9 show?", "All Markets", "All Audiences", "Cross Platform")
    assert "Discovery Attitudes" in answer.answer
    assert answer.relevant_slide == 9


def test_specialist_profile_uses_both_profile_slides_and_excludes_definition():
    answer = engine().answer("What do BBC C-Suites look like?", "All Markets", "All Audiences", "Cross Platform")
    slides = {item.slide for item in answer.evidence}
    assert answer.resolved_scope.startswith("C-Suites")
    assert len(answer.evidence) == 5
    assert {5, 6}.issubset(slides)
    assert all("M104" not in item.cells for item in answer.evidence)
    assert "not everyone in the wider C-Suites group" in answer.answer


def test_ai_question_corrects_scope_and_points_to_slide_ten():
    answer = engine().answer("What do C-Suites think of AI?", "All Markets", "All Audiences", "Digital")
    assert "BBC C-Suites" in answer.answer
    assert "equivalent C-Suites audience" in answer.answer
    assert answer.relevant_slide == 10
    assert all(item.slide == 10 for item in answer.evidence)


def test_two_way_comparison_does_not_treat_audience_name_as_metric():
    answer = engine().answer("Compare C-Suites vs HNWIs", "All Markets", "All Audiences", "Digital")
    assert "reach" in answer.answer
    assert "C-Suites in All Markets" in answer.answer
    assert "HNWIs in All Markets" in answer.answer


def test_fuzzy_metric_matching_and_suppression():
    answer = engine().answer("What percentage are afluent?", "All Markets", "C-Suites", "Digital")
    assert "high-income consumers" in answer.answer
    assert answer.evidence
    low = engine().answer("What percentage are baby boomers?", "All Markets", "FBDMs – Finance Business Decision Makers", "Digital")
    assert "below 50" in low.answer
    assert not low.evidence


def test_follow_up_retains_intent_and_changes_platform():
    chatbot = engine()
    first = chatbot.answer("What do C-Suites think of AI?", "All Markets", "All Audiences", "Cross Platform")
    second = chatbot.answer("What about TV?", "All Markets", "All Audiences", "Cross Platform", previous_question="What do C-Suites think of AI?", previous_scope=("C-Suites", "All Markets", "Cross Platform"))
    assert first.evidence and second.evidence
    assert second.resolved_scope == "C-Suites · All Markets · TV"
    assert second.relevant_slide == 10


def test_ambiguous_comparison_clarifies_and_unsupported_does_not_repeat():
    chatbot = engine()
    vague = chatbot.answer("Compare these audiences", "All Markets", "All Audiences", "Digital")
    unsupported = chatbot.answer("Will this campaign increase sales?", "All Markets", "C-Suites", "Digital", previous_question="What is reach?", previous_scope=("C-Suites", "All Markets", "Digital"))
    assert "name the two audiences" in vague.answer
    assert unsupported.answer.startswith("Sorry, I can’t answer")
    assert "estimated number of people" not in unsupported.answer


def test_leadership_claim_requires_complete_reportable_set():
    answer = engine().answer("Which audience is strongest on AI?", "All Markets", "All Audiences", "Cross Platform")
    assert ("highest" in answer.answer or "can’t make a reliable number-one claim" in answer.answer)
    assert "best audience" not in answer.answer.casefold()


def test_no_overclaim_language_in_representative_answers():
    chatbot = engine()
    for question in ("What do C-Suites think of AI?", "What are the top indexing qualities for HNWIs?", "Compare C-Suites vs HNWIs"):
        text = chatbot.answer(question, "All Markets", "All Audiences", "Cross Platform").answer.casefold()
        assert "will drive" not in text
        assert "caused by" not in text
        assert "guarantee" not in text
        assert "sales takeout" not in text
