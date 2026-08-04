from polyedge.bookmaker_policy import (
    APPROVED_BOOKMAKERS,
    DECISION_MINUTES_BEFORE_GAME,
    MAX_BOOKMAKER_STALENESS_SECONDS,
    MIN_BOOKMAKERS,
)


def test_bookmaker_research_policy_is_frozen():
    assert APPROVED_BOOKMAKERS == (
        "betmgm",
        "betrivers",
        "draftkings",
        "fanduel",
    )
    assert MIN_BOOKMAKERS == 3
    assert MAX_BOOKMAKER_STALENESS_SECONDS == 300
    assert DECISION_MINUTES_BEFORE_GAME == 60
