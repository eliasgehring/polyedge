from datetime import datetime, timezone

import pytest

from polyedge.bookmaker_consensus import (
    select_bookmaker_consensus,
)
from polyedge.bookmaker_odds import (
    BookmakerMoneylineQuote,
)


UTC = timezone.utc


def timestamp(
    hour,
    minute=0,
    second=0,
):
    return datetime(
        2026,
        8,
        4,
        hour,
        minute,
        second,
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


def select(
    quotes,
    target=timestamp(18),
    observation=timestamp(17, 55, 39),
    min_bookmakers=3,
):
    return select_bookmaker_consensus(
        quotes=quotes,
        event_id="event_1",
        target_decision_time=target,
        observation_time=observation,
        approved_bookmakers={
            "fanduel",
            "draftkings",
            "betmgm",
            "betrivers",
        },
        max_snapshot_lag_seconds=300,
        max_staleness_seconds=300,
        min_bookmakers=min_bookmakers,
    )


def test_measures_quote_age_from_provider_snapshot():
    quotes = [
        quote(
            "draftkings",
            0.55,
            timestamp(17, 53, 43),
        ),
        quote(
            "fanduel",
            0.60,
            timestamp(17, 54, 56),
        ),
        quote(
            "betmgm",
            0.58,
            timestamp(17, 55, 36),
        ),
        quote(
            "betrivers",
            0.57,
            timestamp(17, 54, 24),
        ),
    ]

    result = select(quotes)

    assert result.reason is None
    assert result.eligible_quote_count == 4
    assert result.consensus is not None

    consensus = result.consensus

    assert consensus.home_fair_prob == pytest.approx(
        0.575
    )
    assert (
        consensus.provider_snapshot_lag_seconds
        == 261
    )
    assert consensus.newest_quote_age_seconds == 3
    assert consensus.oldest_quote_age_seconds == 116


def test_rejects_quote_after_provider_snapshot():
    quotes = [
        quote(
            "fanduel",
            0.60,
            timestamp(17, 56),
        ),
        quote(
            "draftkings",
            0.55,
            timestamp(17, 54),
        ),
        quote(
            "betmgm",
            0.58,
            timestamp(17, 53),
        ),
    ]

    result = select(quotes)

    assert result.consensus is None
    assert result.reason == (
        "insufficient_fresh_bookmakers"
    )
    assert result.eligible_quote_count == 2


def test_rejects_quote_stale_at_snapshot_time():
    quotes = [
        quote(
            "fanduel",
            0.60,
            timestamp(17, 55),
        ),
        quote(
            "draftkings",
            0.55,
            timestamp(17, 54),
        ),
        quote(
            "betmgm",
            0.58,
            timestamp(17, 50),
        ),
    ]

    result = select(quotes)

    assert result.consensus is None
    assert result.reason == (
        "insufficient_fresh_bookmakers"
    )
    assert result.eligible_quote_count == 2


def test_rejects_provider_snapshot_over_five_minutes_old():
    result = select(
        quotes=[],
        target=timestamp(18),
        observation=timestamp(17, 54, 59),
    )

    assert result.consensus is None
    assert result.reason == (
        "provider_snapshot_too_old"
    )
    assert result.eligible_quote_count == 0


def test_rejects_snapshot_after_target_time():
    with pytest.raises(ValueError):
        select(
            quotes=[],
            target=timestamp(18),
            observation=timestamp(18, 0, 1),
        )


def test_uses_latest_quote_per_bookmaker():
    quotes = [
        quote(
            "fanduel",
            0.51,
            timestamp(17, 53),
        ),
        quote(
            "fanduel",
            0.61,
            timestamp(17, 55),
        ),
        quote(
            "draftkings",
            0.57,
            timestamp(17, 54),
        ),
        quote(
            "betmgm",
            0.59,
            timestamp(17, 55, 10),
        ),
    ]

    result = select(quotes)

    assert result.consensus is not None
    assert result.consensus.home_fair_prob == pytest.approx(
        0.59
    )


def test_does_not_mix_events():
    quotes = [
        quote(
            "fanduel",
            0.60,
            timestamp(17, 55),
        ),
        quote(
            "draftkings",
            0.55,
            timestamp(17, 54),
            event_id="event_2",
        ),
    ]

    result = select(
        quotes,
        min_bookmakers=2,
    )

    assert result.consensus is None
    assert result.reason == (
        "insufficient_fresh_bookmakers"
    )
    assert result.eligible_quote_count == 1


def test_requires_timezone_aware_target():
    with pytest.raises(ValueError):
        select_bookmaker_consensus(
            quotes=[],
            event_id="event_1",
            target_decision_time=datetime(
                2026,
                8,
                4,
                18,
            ),
            observation_time=timestamp(17, 55),
            approved_bookmakers={"fanduel"},
            max_snapshot_lag_seconds=300,
            max_staleness_seconds=300,
        )
