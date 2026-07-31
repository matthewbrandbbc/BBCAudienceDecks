from zipfile import ZipFile

from lxml import etree

from src.data_engine import WorkbookRepository
from src.presentation_model import build_model, title_audience_name
from src.pptx_service import NS, generate_pptx, validate_pptx


def test_platform_shifting():
    repo = WorkbookRepository()
    cross = build_model(repo, "APAC", "C-Suites", "Cross Platform")
    digital = build_model(repo, "APAC", "C-Suites", "Digital")
    assert cross.slides[4].replacements["(K59)"] != digital.slides[4].replacements["(K59)"]


def test_long_audience_title_uses_established_acronym():
    assert title_audience_name("FBDMs – Finance Business Decision Makers") == "FBDMs"
    assert title_audience_name("Business Decision Makers (BDMs)") == "BDMs"
    assert title_audience_name("C-Suites") == "C-Suites"


def test_slide6_composition_and_affinity_use_distinct_sources():
    repo = WorkbookRepository()
    model = build_model(repo, "All Markets", "C-Suites", "Cross Platform")
    slide6 = model.slides[5]
    ws = repo.sheet("All Markets", "C-Suites")
    assert slide6.replacements["(K70)%"] == f"{round(ws['K70'].value * 100)}%"
    assert slide6.replacements["(K70)"] == f"{round(ws['M70'].value)}"


def test_slide3_always_uses_global_data():
    repo = WorkbookRepository()
    apac = build_model(repo, "APAC", "C-Suites", "Cross Platform")
    global_deck = build_model(repo, "All Markets", "C-Suites", "Cross Platform")
    assert apac.slides[2].replacements["(I33)"] == global_deck.slides[2].replacements["(I33)"]


def test_export_has_no_placeholders_and_native_charts(tmp_path):
    repo = WorkbookRepository()
    model = build_model(repo, "APAC", "C-Suites", "Cross Platform")
    output = generate_pptx(model, tmp_path / "acceptance.pptx")
    validate_pptx(output)
    with ZipFile(output) as z:
        assert all(f"ppt/charts/chart{i}.xml" in z.namelist() for i in (1, 2, 3))
        slide4 = etree.fromstring(z.read("ppt/slides/slide4.xml"))
        text = " ".join(slide4.xpath(".//a:t/text()", namespaces=NS))
        assert "C-Suites" in text
        assert "ranks #" not in text
        assert "ranks " in text
        # The template positions chart2 on the left and chart1 in the middle.
        chart2 = etree.fromstring(z.read("ppt/charts/chart2.xml"))
        chart1 = etree.fromstring(z.read("ppt/charts/chart1.xml"))
        left_first = float(chart2.xpath(".//c:ser/c:val/c:numRef/c:numCache/c:pt[@idx='0']/c:v/text()", namespaces=NS)[0])
        middle_first = float(chart1.xpath(".//c:ser/c:val/c:numRef/c:numCache/c:pt[@idx='0']/c:v/text()", namespaces=NS)[0])
        assert left_first == model.slides[3].charts["Cross Platform"]["items"][0]["value"]
        assert middle_first == model.slides[3].charts["Digital"]["items"][0]["value"]


def test_slide2_footer_is_bottom_anchored_and_tightly_spaced(tmp_path):
    repo = WorkbookRepository()
    model = build_model(repo, "All Markets", "FBDMs – Finance Business Decision Makers", "Cross Platform")
    output = generate_pptx(model, tmp_path / "footer-test.pptx")
    with ZipFile(output) as z:
        root = etree.fromstring(z.read("ppt/slides/slide2.xml"))
        footer = root.xpath(
            ".//p:sp[starts-with(p:nvSpPr/p:cNvPr/@name, 'Generated Footer')]",
            namespaces=NS,
        )[0]
        body_pr = footer.find("./p:txBody/a:bodyPr", namespaces=NS)
        assert body_pr.get("anchor") == "b"
        assert body_pr.get("tIns") == "0"
        assert body_pr.get("bIns") == "0"
        assert footer.xpath("count(.//a:pPr/a:spcAft/a:spcPts[@val='0'])", namespaces=NS) == 4.0


def test_low_base_export_removes_rows_labels_and_empty_charts(tmp_path):
    repo = WorkbookRepository()
    model = build_model(repo, "Africa", "FBDMs – Finance Business Decision Makers", "Digital")
    output = generate_pptx(model, tmp_path / "low-base.pptx")
    with ZipFile(output) as z:
        slide2 = etree.fromstring(z.read("ppt/slides/slide2.xml"))
        text2 = " ".join(slide2.xpath(".//a:t/text()", namespaces=NS))
        assert "Monthly Digital Reach" not in text2
        assert "(N16)" not in text2
        slide4 = etree.fromstring(z.read("ppt/slides/slide4.xml"))
        text4 = " ".join(slide4.xpath(".//a:t/text()", namespaces=NS))
        assert "Digital Reach" not in text4
        for number in (6, 7, 8):
            slide = etree.fromstring(z.read(f"ppt/slides/slide{number}.xml"))
            assert not slide.xpath(".//a:tbl", namespaces=NS)
