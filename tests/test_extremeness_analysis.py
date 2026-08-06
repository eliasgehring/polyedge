import math

import pytest

from polyedge.extremeness_analysis import (
    PROBABILITY_BANDS,
    analyze_extremeness,
    build_extremeness_observation,
)
from polyedge.forecast_audit import (
    ForecastAuditRow,
)


def forecast_row(
    *,
    market_id: str,
    bookmaker_home: float,
    polymarket_home: float,
    outcome: int,
    strict: bool = True,
) -> ForecastAuditRow:
    return ForecastAuditRow(
        output_market_id=market_id,
        strict_t_minus_60_eligible=strict,
        bookmaker_home_probability=bookmaker_home,
        polymarket_home_probability=polymarket_home,
        resolved_home_value=outcome,
    )


def test_negative_gap_means_bookmaker_is_less_extreme():
    observation = build_extremeness_observation(
        forecast_row(
            market_id="nba_20260101_a_vs_b_home_win",
            bookmaker_home=0.60,
            polymarket_home=0.70,
            outcome=1,
        )
    )

    assert (
        observation
        .extremeness_gap_bookmaker_minus_polymarket
        == pytest.approx(-0.10)
    )
    assert (
        observation.bookmaker_less_extreme
        is True
    )
    assert (
        observation.equal_extremeness
        is False
    )


def test_positive_gap_means_bookmaker_is_more_extreme():
    observation = build_extremeness_observation(
        forecast_row(
            market_id="nba_20260101_a_vs_b_home_win",
            bookmaker_home=0.80,
            polymarket_home=0.70,
            outcome=0,
        )
    )

    assert (
        observation
        .extremeness_gap_bookmaker_minus_polymarket
        == pytest.approx(0.10)
    )
    assert (
        observation.bookmaker_less_extreme
        is False
    )
    assert (
        observation.equal_extremeness
        is False
    )


def test_equal_distance_from_half_is_equal_extremeness():
    observation = build_extremeness_observation(
        forecast_row(
            market_id="nba_20260101_a_vs_b_home_win",
            bookmaker_home=0.40,
            polymarket_home=0.60,
            outcome=1,
        )
    )

    assert (
        observation
        .extremeness_gap_bookmaker_minus_polymarket
        == pytest.approx(0.0)
    )
    assert (
        observation.equal_extremeness
        is True
    )


def test_probability_bands_use_consensus_probability():
    rows = [
        build_extremeness_observation(
            forecast_row(
                market_id="nba_20260101_a_vs_b_home_win",
                bookmaker_home=0.30,
                polymarket_home=0.40,
                outcome=1,
            )
        ),
        build_extremeness_observation(
            forecast_row(
                market_id="nba_20260102_c_vs_d_home_win",
                bookmaker_home=0.65,
                polymarket_home=0.65,
                outcome=0,
            )
        ),
    ]

    result = analyze_extremeness(
        rows,
        population_name="test",
        resamples=20,
        seed=7,
    )

    counts = {
        band.band_label: band.count
        for band in result.probability_bands
    }

    assert counts["[0.35, 0.50)"] == 1
    assert counts["[0.65, 0.80)"] == 1
    assert sum(counts.values()) == 2


def test_probability_band_boundaries_are_lower_inclusive():
    probabilities = [
        0.00,
        0.20,
        0.35,
        0.50,
        0.65,
        0.80,
        1.00,
    ]

    rows = [
        build_extremeness_observation(
            forecast_row(
                market_id=(
                    "nba_2026010"
                    + str(index + 1)
                    + "_a_vs_b_home_win"
                ),
                bookmaker_home=probability,
                polymarket_home=probability,
                outcome=int(
                    probability >= 0.5
                ),
            )
        )
        for index, probability
        in enumerate(probabilities)
    ]

    result = analyze_extremeness(
        rows,
        population_name="test",
        resamples=20,
        seed=7,
    )

    assert [
        band.count
        for band in result.probability_bands
    ] == [
        1,
        1,
        1,
        1,
        1,
        2,
    ]


def test_aggregate_counts_partition_all_observations():
    rows = [
        build_extremeness_observation(
            forecast_row(
                market_id="nba_20260101_a_vs_b_home_win",
                bookmaker_home=0.60,
                polymarket_home=0.70,
                outcome=1,
            )
        ),
        build_extremeness_observation(
            forecast_row(
                market_id="nba_20260102_c_vs_d_home_win",
                bookmaker_home=0.80,
                polymarket_home=0.70,
                outcome=0,
            )
        ),
        build_extremeness_observation(
            forecast_row(
                market_id="nba_20260103_e_vs_f_home_win",
                bookmaker_home=0.40,
                polymarket_home=0.60,
                outcome=1,
            )
        ),
    ]

    result = analyze_extremeness(
        rows,
        population_name="test",
        resamples=20,
        seed=7,
    )

    assert result.count == 3
    assert (
        result.bookmaker_less_extreme_count
        == 1
    )
    assert (
        result.bookmaker_more_extreme_count
        == 1
    )
    assert (
        result.equal_extremeness_count
        == 1
    )
    assert (
        result.bookmaker_less_extreme_fraction
        == pytest.approx(1 / 3)
    )


def test_band_score_difference_scores_home_outcome_once():
    row = build_extremeness_observation(
        forecast_row(
            market_id="nba_20260101_a_vs_b_home_win",
            bookmaker_home=0.80,
            polymarket_home=0.60,
            outcome=1,
        )
    )

    result = analyze_extremeness(
        [row],
        population_name="test",
        resamples=20,
        seed=7,
    )

    band = next(
        item
        for item in result.probability_bands
        if item.count == 1
    )

    expected_brier_difference = (
        (0.60 - 1) ** 2
        - (0.80 - 1) ** 2
    )

    assert (
        band
        .mean_brier_score_difference_polymarket_minus_bookmaker
        == pytest.approx(
            expected_brier_difference
        )
    )


def test_analysis_is_deterministic_for_fixed_seed():
    rows = [
        build_extremeness_observation(
            forecast_row(
                market_id=(
                    "nba_2026010"
                    + str(index + 1)
                    + "_a_vs_b_home_win"
                ),
                bookmaker_home=0.55 + index * 0.01,
                polymarket_home=0.54 + index * 0.01,
                outcome=index % 2,
            )
        )
        for index in range(5)
    ]

    first = analyze_extremeness(
        rows,
        population_name="test",
        resamples=50,
        seed=11,
    )
    second = analyze_extremeness(
        rows,
        population_name="test",
        resamples=50,
        seed=11,
    )

    assert first == second


def test_empty_population_is_rejected():
    with pytest.raises(
        ValueError,
        match="empty",
    ):
        analyze_extremeness(
            [],
            population_name="test",
            resamples=20,
            seed=7,
        )
