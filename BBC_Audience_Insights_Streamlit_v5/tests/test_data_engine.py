from src.data_engine import (
    Competitor,
    WorkbookRepository,
    clean_audience_name,
    clean_competitor_name,
    footer_lines,
    format_compact,
    format_index,
    format_index_difference,
    ordinal,
    sort_competitors,
)


def test_audience_cleanup():
    assert clean_audience_name("AD - C-suites") == "C-Suites"
    assert clean_audience_name("AD - Business Decision Makers (BDMs)") == "Business Decision Makers (BDMs)"
    assert clean_audience_name("Totals") == "All Audiences"
    assert clean_audience_name("All Internet Users (Audience Size)") == "All Audiences"


def test_number_formats():
    assert format_compact(123_123_123.12) == "123M"
    assert format_compact(123_123.12) == "123K"
    assert format_index(123.4) == "123"
    assert format_index_difference(123) == "+23"
    assert format_index_difference(100) == "0"
    assert format_index_difference(87) == "-13"


def test_competitors_and_rank():
    assert clean_competitor_name("2.0 Cross Platform CNN Engagement") == "CNN"
    items = sort_competitors([Competitor("BBC", 10), Competitor("CNN", 10), Competitor("CNBC", 8)])
    assert [item.name for item in items] == ["BBC", "CNN", "CNBC"]
    assert ordinal(1) == "1st"
    assert ordinal(2) == "2nd"
    assert ordinal(13) == "13th"


def test_repository_and_footers():
    repo = WorkbookRepository()
    assert len(repo.paths) == 8
    assert repo.slide2_affinity("APAC", "C-Suites") > 0
    assert repo.markets_footer("All Markets") == "Markets: 51 Global Markets (Excl. China, Russia, UK)"
    assert repo.markets_footer("Europe").endswith("(Excl. Russia)")
    lines = footer_lines(repo, "APAC", "C-Suites", "Cross Platform")
    assert len(lines) == 4
    assert lines[0].startswith("Base: C-Suites (")
