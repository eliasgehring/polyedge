from datetime import datetime, timezone

from polyedge.bookmaker_odds import (
    BookmakerMoneylineQuote,
)
from polyedge.historical_bookmaker_observations import (
    build_historical_bookmaker_observation,
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


def event(
    *,
    event_id="event_1",
    home_team="Home Team",
    away_team="Away Team",
    commence_time="2026-08-04T20:00:00Z",
):
    return {
        "id": event_id,
        "sport_key": "basketball_nba",
        "home_team": home_team,
        "away_team": away_team,
        "commence_time": commence_time,
        "bookmakers": [],
    }


def quote(
    bookmaker_key,
    home_prob,
    update_time,
):
    return BookmakerMoneylineQuote(
        event_id="event_1",
        sport_key="basketball_nba",
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


def build(
    *,
    events=None,
    quotes=None,
    observation=timestamp(17, 55, 39),
):
    return build_historical_bookmaker_observation(
        output_market_id="market_1",
        provider_event_id="event_1",
        expected_home_team="Home Team",
        expected_away_team="Away Team",
        target_request_time=timestamp(18),
        observation_time=observation,
        events=events or [event()],
        quotes=quotes or [],
    )


def test_builds_eligible_observation():
    result = build(
        quotes=[
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
        ]
    )

    assert result.status == "eligible"
    assert result.exclusion_reason is None
    assert result.bookmaker_count == 4
    assert result.pregame_at_observation is True
    assert result.strict_t_minus_60_eligible is True
    assert result.provider_snapshot_lag_seconds == 261
    assert result.oldest_quote_age_seconds == 116
    assert result.newest_quote_age_seconds == 3


def test_records_missing_provider_event():
    result = build(
        events=[
            event(event_id="different_event")
        ]
    )

    assert result.status == "excluded"
    assert (
        result.exclusion_reason
        == "provider_event_missing"
    )
    assert result.home_fair_prob is None


def test_rejects_identity_mismatch():
    result = build(
        events=[
            event(home_team="Wrong Team")
        ]
    )

    assert result.status == "excluded"
    assert (
        result.exclusion_reason
        == "provider_identity_mismatch"
    )


def test_rejects_snapshot_after_game_start():
    result = build(
        events=[
            event(
                commence_time=(
                    "2026-08-04T17:50:00Z"
                )
            )
        ]
    )

    assert result.status == "excluded"
    assert (
        result.exclusion_reason
        == "snapshot_not_pregame"
    )
    assert result.pregame_at_observation is False


def test_marks_short_lead_as_non_strict_but_eligible():
    result = build(
        events=[
            event(
                commence_time=(
                    "2026-08-04T18:05:00Z"
                )
            )
        ],
        quotes=[
            quote(
                "betmgm",
                0.58,
                timestamp(17, 55, 36),
            ),
            quote(
                "draftkings",
                0.55,
                timestamp(17, 54, 30),
            ),
            quote(
                "fanduel",
                0.60,
                timestamp(17, 55),
            ),
        ],
    )

    assert result.status == "eligible"
    assert result.pregame_at_observation is True
    assert result.strict_t_minus_60_eligible is False
    assert (
        result.seconds_before_provider_start
        == 561
    )
