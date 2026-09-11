"""Curated, local knowledge used by the deterministic Audience Deck Chatbot."""

SLIDE_GUIDE = {
    2: ("Regional Reach", "Estimated BBC audience reach globally and by region."),
    3: ("Competitive Position", "BBC reach compared with the available news competitive set."),
    4: ("BBC.com Pillar Alignment", "Interests aligned with BBC.com content pillars."),
    5: ("Audience Demographics", "Demographic composition and affinity of the selected BBC audience."),
    6: ("Employment Profile", "Firmographics, business titles and role responsibilities."),
    7: ("Platform and Media Consumption", "Regular media and platform consumption habits."),
    8: ("Brand Discovery", "Channels through which the audience discovers brands."),
    9: ("Discovery Attitudes", "Attitudes to advertising, new products and premium options."),
    10: ("AI Attitudes", "Attitudes toward the role and potential benefits of AI."),
}

GWI_CORE_URL = "https://help.globalwebindex.com/en/articles/5880939-understanding-gwi-core"
GWI_WEIGHTING_URL = "https://help.globalwebindex.com/en/articles/5880950-quotas-and-weighting"
GWI_METHOD_URL = "https://www.gwi.com/hubfs/GWI%20Core%20-%20Research%20and%20methodology%202024%20%281%29.pdf"

PURPOSE = (
    "The Audience Deck Chatbot helps users understand the evidence in the audience slides, "
    "compare supported results and find where the information appears in the presentation. "
    "It explains what the data shows without making claims that go beyond the available evidence."
)

DEFINITIONS = {
    "reach": (
        "Reach is the estimated number of people within the selected audience who use BBC "
        "services through the selected platform. It is a survey-weighted estimate, not a count "
        "of individual BBC users. In this deck, reach and reach percentage appear on Slide 2."
    ),
    "reach_percent": (
        "Reach percentage is the proportion of the selected audience estimated to use BBC "
        "services through the selected platform. It helps put the reach volume in context and "
        "appears on Slide 2."
    ),
    "composition": (
        "Composition is the percentage of the selected BBC audience who have a characteristic "
        "or report a behaviour. It describes the make-up of the BBC audience; it does not show "
        "how unusual that characteristic is. Composition appears alongside index on the relevant slide."
    ),
    "responses": (
        "Responses is the number of survey respondents supporting a statistic. It is not the "
        "estimated audience size. When Responses is below 50, the app suppresses the reach or "
        "universe, composition and index together and does not use the result in chatbot claims."
    ),
    "universe": (
        "Universe is the survey-weighted estimate of the number of people represented by a result. "
        "It is different from Responses, which is the number of people who answered the survey."
    ),
    "survey": (
        "These results come from the GWI Core survey of online consumers. Survey answers are "
        "weighted so the results better reflect the online population in each market. Survey data "
        "can show reported patterns and associations, but it does not by itself prove why a pattern exists."
    ),
    "weighting": (
        "GWI uses sampling quotas and respondent weights to make its survey samples more representative "
        "of the online population in each market. Age, gender and education are among the principal "
        "variables used. Weighting improves population estimates, but it does not remove all survey uncertainty."
    ),
}


def index_definition(comparison: str) -> str:
    return (
        f"An affinity index compares the selected BBC audience with {comparison}. An index of 100 "
        "means the characteristic is equally likely in both groups; 123 means it is 23% more likely, "
        "and 85 means it is 15% less likely. It shows relative likelihood, not audience size, and "
        "should be read with composition and response base on the relevant slide."
    )
