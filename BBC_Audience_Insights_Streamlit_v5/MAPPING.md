# Auditable presentation mapping

| Slide | Content | Data rule |
|---:|---|---|
| 1 | Title | Cleaned audience name; no footer |
| 2 | Total reach | Selected regional workbook and audience; `I/L`, `N/Q`, `S/V` row 16; affinity from the All Audiences sheet `M16:M32` label lookup |
| 3 | Global regional comparison | Always All Markets workbook; rows 33–39; all three platform blocks |
| 4 | Competitor reach | Selected workbook/audience; `C40:D45`, `C46:D51`, `C52:D57`; descending sort and deterministic ties |
| 5 | Pillar alignment | Rows 58–69; selected platform percent column |
| 6 | Platform consumption | Rows 70–76; selected platform percent and index columns |
| 7 | Demographics | Rows 77–86; selected platform universe, percent and index columns |
| 8 | Employment | Rows 87–96; selected platform percent and index columns |
| 9 | AI attitudes | Rows 97–100; selected platform index minus 100 |

## Platform shifts

| Metric | Cross Platform | Digital | TV |
|---|---|---|---|
| Universe | I | N | S |
| Percentage | K | P | U |
| Row/reach percentage | L | Q | V |
| Index | M | R | W |

The mapping is implemented once in `src/config.py` and resolved through `src/presentation_model.py`. The Streamlit viewer and all exports consume that same model.

