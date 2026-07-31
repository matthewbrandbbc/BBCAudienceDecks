from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data" / "input_workbooks"
TEMPLATE_PATH = PROJECT_ROOT / "assets" / "BBC_Insights_Audience_Deck_Tagged.potx"
OUTPUT_DIR = PROJECT_ROOT / "outputs"

REGION_FILE_HINTS = {
    "All Markets": "All_Markets",
    "North America": "North_America",
    "Latin America": "Latin_America",
    "Europe": "Europe",
    "Middle East": "Middle_East",
    "Africa": "Africa",
    "South Asia": "South_Asia",
    "APAC": "APAC",
}

PLATFORM_COLUMNS = {
    "Cross Platform": {"universe": "I", "responses": "J", "percent": "K", "row_percent": "L", "index": "M"},
    "Digital": {"universe": "N", "responses": "O", "percent": "P", "row_percent": "Q", "index": "R"},
    "TV": {"universe": "S", "responses": "T", "percent": "U", "row_percent": "V", "index": "W"},
}

TOTAL_COLUMNS = {"universe": "D", "responses": "E", "percent": "F", "row_percent": "G", "index": "H"}
MIN_RESPONSES = 50

PLATFORM_FOOTERS = {
    "Cross Platform": "Platform: BBC Cross Platform (30 Day Digital + TV Reach)",
    "Digital": "Platform: BBC Digital (30 Day Digital Reach)",
    "TV": "Platform: BBC TV (30 Day TV Reach)",
}

ALL_PLATFORM_FOOTER = "Platform: BBC Cross Platform, Digital + TV (30 Day Reach)"

REQUIRED_ROWS = tuple(range(16, 101))
REQUIRED_NUMERIC_COLUMNS = tuple("DEIJKLMNOPQRSTUVW")
ALL_MARKETS_FOOTER = "Markets: 51 Global Markets (Excl. China, Russia, UK)"
