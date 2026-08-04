from datetime import datetime, timezone

import pytest

from polyedge.bookmaker_consensus import (
    select_bookmaker_consensus,
)
from polyedge.bookmaker_odds import (
    BookmakerMoneylineQuote,
)


UTC = timezone.utc


def timestamp(hour, minute=0):
    return datetime(
        2026,
        8,
        4,
        hour,
        minute,
        tzinfo=UTC,
    )


def quote(
    bookmaker_key,
    home_prob,
    update_time,
    event_id="event_1",
):
    return BookmakerMoneylineQuote(
        event_id=event_id,
        sport_key="basketball_wnba",
        commence_time=timestamp(20),
        home_team="Home Team",
        away_team="Away Team",
        bookmaker_key=bookmaker_key,
        bookmaker_title=bookmaker_key.title(),
        bookmaker_last_update=update_time,
        market_last_update=update_time,
        home_decimal_odds=2.0,
        away_decimal_odds=2.0,
        home_fair_prob=home_prob,
        away_fair_prob=1.0 - home_prob,
    )


def test_uses_median_across_approved_fresh_bookmakers():
    quotes = [
        quote("fanduel", 0.60, timestamp(17, 59)),
        quote("draftkings", 0.55, timestamp(17, 58)),
        quote("betmgm", 0.58, timestamp(17, 57)),
        quote("unapproved", 0.99, timestamp(17, 59)),
    ]

    result = select_bookmaker_consensus(
        quotes=quotes,
        event_id="event_1",
        decision_time=timestamp(18),
        approved_bookmakers={
            "fanduel",
            "draftkings",
            "betmgm",
        },
        max_staleness_seconds=300,
        min_bookmakers=3,
    )

    assert result.reason is None
    assert result.eligible_quote_count == 3
    assert result.consensus is not None

    consensus = result.consensus

    assert consensus.home_fair_prob == pytest.approx(
        0.58
    )
    assert consensus.away_fair_prob == pytest.approx(
        0.42
    )
    assert consensus.bookmaker_keys == (
        "betmgm",
        "draftkings",
        "fanduel",
    )


def test_rejects_stale_and_post_decision_quotes():
    quotes = [
        quote("fanduel", 0.60, timestamp(17, 59)),
        quote("draftkings", 0.55, timestamp(17, 40)),
        quote("betmgm", 0.58, timestamp(18, 1)),
    ]

    result = select_bookmaker_consensus(
        quotes=quotes,
        event_id="event_1",
        decision_time=timestamp(18),
        approved_bookmakers={
            "fanduel",
            "draftkings",
            "betmgm",
        },
        max_staleness_seconds=300,
        min_bookmakers=3,
    )

    assert result.consensus is None
    assert result.reason == (
        "insufficient_fresh_bookmakers"
    )
    assert result.eligible_quote_count == 1


def test_uses_latest_quote_per_bookmaker():
    quotes = [
        quote("fanduel", 0.51, timestamp(17, 55)),
        quote("fanduel", 0.61, timestamp(17, 59)),
        quote("draftkings", 0.57, timestamp(17, 58)),
        quote("betmgm", 0.59, timestamp(17, 57)),
    ]

    result = select_bookmaker_consensus(
        quotes=quotes,
        event_id="event_1",
        decision_time=timestamp(18),
        approved_bookmakers={
            "fanduel",
            "draftkings",
            "betmgm",
        },
        max_staleness_seconds=600,
        min_bookmakers=3,
    )

    assert result.consensus is not None
    assert result.consensus.home_fair_prob == pytest.approx(
        0.59
    )


def test_does_not_mix_events():
    quotes = [
        quote("fanduel", 0.60, timestamp(17, 59)),
        quote(
            "draftkings",
            0.55,
            timestamp(17, 58),
            event_id="event_2",
        ),
    ]

    result = select_bookmaker_consensus(
        quotes=quotes,
        event_id="event_1",
        decision_time=timestamp(18),
        approved_bookmakers={
            "fanduel",
            "draftkings",
        },
        max_staleness_seconds=300,
        min_bookmakers=2,
    )

    assert result.consensus is None
    assert result.eligible_quote_count == 1


def test_requires_timezone_aware_decision_time():
    with pytest.raises(ValueError):
        select_bookmaker_consensus(
            quotes=[],
            event_id="event_1",
            decision_time=datetime(
                2026,
                8,
                4,
                18,
                0,
            ),
            approved_bookmakers={"fanduel"},
            max_staleness_seconds=300,
        )
