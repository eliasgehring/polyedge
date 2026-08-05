from datetime import datetime, timezone

import pytest

from polyedge.polymarket_observations import (
    PolymarketObservationError,
    build_polymarket_outcome_observation,
    combine_polymarket_outcomes,
)


CUTOFF = datetime(
    2024,
    10,
    22,
    22,
    25,
    39,
    tzinfo=timezone.utc,
)


def build_side(
    *,
    side,
    price,
    timestamp,
):
    return build_polymarket_outcome_observation(
        output_market_id="market_1",
        side=side,
        token_id=side.lower() + "-token",
        common_cutoff=CUTOFF,
        history=[
            {
                "t": timestamp,
                "p": price,
            },
        ],
        max_staleness_seconds=3600,
    )


def test_builds_same_clock_complementary_pair():
    timestamp = int(
        CUTOFF.timestamp()
    ) - 37

    home = build_side(
        side="HOME",
        price=0.695,
        timestamp=timestamp,
    )

    away = build_side(
        side="AWAY",
        price=0.305,
        timestamp=timestamp,
    )

    pair = combine_polymarket_outcomes(
        home=home,
        away=away,
    )

    assert pair.status == "eligible"
    assert pair.timestamp_gap_seconds == 0
    assert pair.max_price_age_seconds == 37
    assert pair.price_sum == pytest.approx(1.0)
    assert pair.complementarity_error == (
        pytest.approx(0.0)
    )


def test_future_price_is_not_selected():
    cutoff_timestamp = int(
        CUTOFF.timestamp()
    )

    result = (
        build_polymarket_outcome_observation(
            output_market_id="market_1",
            side="HOME",
            token_id="home-token",
            common_cutoff=CUTOFF,
            history=[
                {
                    "t": cutoff_timestamp - 20,
                    "p": 0.60,
                },
                {
                    "t": cutoff_timestamp + 20,
                    "p": 0.90,
                },
            ],
            max_staleness_seconds=3600,
        )
    )

    assert result.status == "eligible"
    assert result.price == 0.60
    assert result.age_seconds == 20


def test_stale_price_is_explicitly_excluded():
    cutoff_timestamp = int(
        CUTOFF.timestamp()
    )

    result = (
        build_polymarket_outcome_observation(
            output_market_id="market_1",
            side="HOME",
            token_id="home-token",
            common_cutoff=CUTOFF,
            history=[
                {
                    "t": cutoff_timestamp - 600,
                    "p": 0.60,
                },
            ],
            max_staleness_seconds=300,
        )
    )

    assert result.status == "excluded"
    assert result.price is None
    assert result.age_seconds == 600
    assert (
        result.exclusion_reason
        == "price_too_stale"
    )


def test_pair_preserves_side_exclusion():
    timestamp = int(
        CUTOFF.timestamp()
    )

    home = build_side(
        side="HOME",
        price=0.60,
        timestamp=timestamp,
    )

    away = (
        build_polymarket_outcome_observation(
            output_market_id="market_1",
            side="AWAY",
            token_id="away-token",
            common_cutoff=CUTOFF,
            history=[],
            max_staleness_seconds=3600,
        )
    )

    pair = combine_polymarket_outcomes(
        home=home,
        away=away,
    )

    assert pair.status == "excluded"
    assert pair.price_sum is None
    assert (
        pair.exclusion_reason
        == "away:no_price_history"
    )


def test_rejects_different_market_ids():
    timestamp = int(
        CUTOFF.timestamp()
    )

    home = build_side(
        side="HOME",
        price=0.60,
        timestamp=timestamp,
    )

    away = build_side(
        side="AWAY",
        price=0.40,
        timestamp=timestamp,
    )

    object.__setattr__(
        away,
        "output_market_id",
        "different_market",
    )

    with pytest.raises(
        PolymarketObservationError
    ):
        combine_polymarket_outcomes(
            home=home,
            away=away,
        )
