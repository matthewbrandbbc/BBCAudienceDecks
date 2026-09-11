# Audience Deck Chatbot — V6.6

The chatbot is a deterministic, local retrieval system. It does not call an API or host a language model. It identifies the requested audience, region, platform, metric and slide category, retrieves only validated workbook cells, applies the response-base and claim-safety rules, and assembles an answer from controlled language.

## Purpose

The Audience Deck Chatbot helps users understand the evidence in the audience slides, compare supported results and find where the information appears in the presentation. It explains what the data shows without making claims that go beyond the available evidence.

## Report map

| Slide | Category |
|---:|---|
| 2 | Regional Reach |
| 3 | Competitive Position |
| 4 | BBC.com Pillar Alignment |
| 5 | Audience Demographics |
| 6 | Employment Profile |
| 7 | Platform and Media Consumption |
| 8 | Brand Discovery |
| 9 | Discovery Attitudes |
| 10 | AI Attitudes |

Specialist PowerPoint exports omit Slides 5 and 6, but their validated source rows remain available to the chatbot for audience-profile questions.

## Reporting safeguards

- Suppress all statistics with fewer than 50 Responses.
- Read composition, index and response base together.
- Do not add overlapping composition percentages or Digital and TV reach.
- Do not infer causes, campaign outcomes or advertiser suitability.
- Use a leadership claim only when the complete comparable audience set is reportable and the result is genuinely highest.
- Treat tied top results as joint-highest; do not turn rank two into a leadership story.
- Point users to the relevant slide and expose the supporting workbook cells.

## Methodology sources

- GWI Core: https://help.globalwebindex.com/en/articles/5880939-understanding-gwi-core
- GWI quotas and weighting: https://help.globalwebindex.com/en/articles/5880950-quotas-and-weighting
- GWI Core research and methodology: https://www.gwi.com/hubfs/GWI%20Core%20-%20Research%20and%20methodology%202024%20%281%29.pdf

The chatbot distinguishes GWI's overall coverage from the market scope printed in the selected BBC workbook.
