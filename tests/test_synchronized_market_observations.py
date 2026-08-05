from copy import deepcopy

import pytest

from polyedge.synchronized_market_observations import (
    SynchronizedObservationError,
    build_synchronized_market_observation,
)


def bookmaker_row():
    return {
        "output_market_id": "market_1",
        "provider_event_id": "event_1",
        "target_request_time_utc": "2024-10-22T22:30:00Z",
        "observation_time_utc": "2024-10-22T22:25:39Z",
        "provider_snapshot_lag_seconds": "261",
        "provider_commence_time_at_observation_utc": (
            "2024-10-22T23:40:00Z"
        ),
        "provider_home_team": "Boston Celtics",
        "provider_away_team": "New York Knicks",
        "home_fair_prob": "0.6777168234064785",
        "away_fair_prob": "0.32228317659352146",
        "bookmaker_count": "4",
        "oldest_quote_age_seconds": "116",
        "newest_quote_age_seconds": "3",
        "seconds_before_provider_start": "4461",
        "strict_t_minus_60_eligible": "true",
        "status": "eligible",
    }


def identity_row():
    return {
        "output_market_id": "market_1",
        "polymarket_market_id": "510342",
        "condition_id": "condition_1",
        "market_slug": "example-market",
        "home_outcome": "Celtics",
        "away_outcome": "Knicks",
        "home_token_id": "home-token",
        "away_token_id": "away-token",
        "resolved_home_value": "1",
        "resolved_away_value": "0",
        "resolution_source": "legacy_nba_game_result",
        "settlement_time_status": "unknown_not_migrated",
    }


def polymarket_row():
    return {
        "output_market_id": "market_1",
        "observation_time_utc": "2024-10-22T22:25:39Z",
        "home_token_id": "home-token",
        "away_token_id": "away-token",
        "home_status": "eligible",
        "home_price": "0.695000000",
        "home_price_time_utc": "2024-10-22T22:25:02Z",
        "home_price_age_seconds": "37",
        "away_status": "eligible",
        "away_price": "0.305000000",
        "away_price_time_utc": "2024-10-22T22:25:02Z",
        "away_price_age_seconds": "37",
        "pair_status": "eligible",
        "timestamp_gap_seconds": "0",
        "max_price_age_seconds": "37",
        "price_sum": "1.000000000",
        "complementarity_error": "0.000000000",
    }


def build():
    return build_synchronized_market_observation(
        bookmaker_row=bookmaker_row(),
        identity_row=identity_row(),
        polymarket_row=polymarket_row(),
    )


def test_builds_truth_preserving_synchronized_observation():
    result = build()

    assert result.output_market_id == "market_1"
    assert result.history_point_lag_seconds == 37

    assert result.bookmaker_home_fair_probability == (
        pytest.approx(0.6777168234064785)
    )

    assert result.polymarket_home_probability == (
        pytest.approx(0.695)
    )

    assert result.home_probability_edge == pytest.approx(
        -0.0172831765935215
    )

    assert result.away_probability_edge == pytest.approx(
        0.01728317659352146
    )

    assert result.resolved_home_value == 1
    assert result.resolved_away_value == 0

    assert result.source_semantics == (
        "one_minute_sampled_probability_series"
    )

    assert result.execution_semantics == "none"
    assert result.policy_version == "nba_v2_sync_v1"


def test_rejects_future_polymarket_point():
    row = polymarket_row()

    row["home_price_time_utc"] = (
        "2024-10-22T22:26:02Z"
    )

    row["away_price_time_utc"] = (
        "2024-10-22T22:26:02Z"
    )

    with pytest.raises(
        SynchronizedObservationError
    ):
        build_synchronized_market_observation(
            bookmaker_row=bookmaker_row(),
            identity_row=identity_row(),
            polymarket_row=row,
        )


def test_rejects_token_mismatch():
    row = polymarket_row()
    row["home_token_id"] = "wrong-token"

    with pytest.raises(
        SynchronizedObservationError
    ):
        build_synchronized_market_observation(
            bookmaker_row=bookmaker_row(),
            identity_row=identity_row(),
            polymarket_row=row,
        )


def test_rejects_non_binary_resolution():
    row = identity_row()
    row["resolved_home_value"] = "1"
    row["resolved_away_value"] = "1"

    with pytest.raises(
        SynchronizedObservationError
    ):
        build_synchronized_market_observation(
            bookmaker_row=bookmaker_row(),
            identity_row=row,
            polymarket_row=polymarket_row(),
        )


def test_rejects_recorded_lag_that_does_not_reconcile():
    row = deepcopy(polymarket_row())
    row["max_price_age_seconds"] = "36"

    with pytest.raises(
        SynchronizedObservationError
    ):
        build_synchronized_market_observation(
            bookmaker_row=bookmaker_row(),
            identity_row=identity_row(),
            polymarket_row=row,
        )
