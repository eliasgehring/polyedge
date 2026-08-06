import math

import pytest

from polyedge.discrepancy_analysis import (
    DISCREPANCY_BINS,
    analyze_discrepancy_bins,
    build_discrepancy_observation,
    discrepancy_bin_for_value,
)
from polyedge.forecast_audit import ForecastAuditRow


def forecast_row(
    *,
    market_id,
    bookmaker_home,
    polymarket_home,
    outcome,
    strict=True,
):
    return ForecastAuditRow(
        output_market_id=market_id,
        strict_t_minus_60_eligible=strict,
        bookmaker_home_probability=bookmaker_home,
        polymarket_home_probability=polymarket_home,
        resolved_home_value=outcome,
    )


@pytest.mark.parametrize(
    'value, expected_label',
    [
        (-0.11, '< -0.10'),
        (-0.10, '[-0.10, -0.05)'),
        (-0.05, '[-0.05, -0.02)'),
        (-0.02, '[-0.02, 0.00)'),
        (0.00, '[0.00, 0.02)'),
        (0.02, '[0.02, 0.05)'),
        (0.05, '[0.05, 0.10)'),
        (0.10, '>= 0.10'),
    ],
)
def test_fixed_bin_boundaries_are_deterministic(
    value,
    expected_label,
):
    assert discrepancy_bin_for_value(value).label == expected_label


def test_builds_signed_discrepancy_and_score_differences():
    observation = build_discrepancy_observation(
        forecast_row(
            market_id='m1',
            bookmaker_home=0.8,
            polymarket_home=0.6,
            outcome=1,
        )
    )

    assert observation.home_probability_discrepancy == pytest.approx(0.2)
    assert (
        observation
        .brier_score_difference_polymarket_minus_bookmaker
    ) == pytest.approx(0.12)
    assert (
        observation
        .log_loss_difference_polymarket_minus_bookmaker
    ) == pytest.approx(math.log(0.8 / 0.6))


def test_analysis_returns_all_fixed_bins_and_reconciles_counts():
    observations = [
        build_discrepancy_observation(
            forecast_row(
                market_id='m1',
                bookmaker_home=0.8,
                polymarket_home=0.6,
                outcome=1,
            )
        ),
        build_discrepancy_observation(
            forecast_row(
                market_id='m2',
                bookmaker_home=0.2,
                polymarket_home=0.4,
                outcome=0,
            )
        ),
        build_discrepancy_observation(
            forecast_row(
                market_id='m3',
                bookmaker_home=0.51,
                polymarket_home=0.50,
                outcome=1,
            )
        ),
    ]

    results = analyze_discrepancy_bins(
        observations,
        population_name='all_synchronized',
    )

    assert len(results) == len(DISCREPANCY_BINS)
    assert sum(result.count for result in results) == 3


def test_positive_discrepancy_bin_reports_calibration_gaps():
    observations = [
        build_discrepancy_observation(
            forecast_row(
                market_id='m1',
                bookmaker_home=0.62,
                polymarket_home=0.55,
                outcome=1,
            )
        ),
        build_discrepancy_observation(
            forecast_row(
                market_id='m2',
                bookmaker_home=0.72,
                polymarket_home=0.65,
                outcome=0,
            )
        ),
    ]

    results = analyze_discrepancy_bins(
        observations,
        population_name='all_synchronized',
    )

    target = next(
        result
        for result in results
        if result.bin_label == '[0.05, 0.10)'
    )

    assert target.count == 2
    assert target.mean_bookmaker_home_probability == pytest.approx(0.67)
    assert target.mean_polymarket_home_probability == pytest.approx(0.60)
    assert target.observed_home_win_rate == pytest.approx(0.50)
    assert target.observed_minus_bookmaker_probability == pytest.approx(-0.17)
    assert target.observed_minus_polymarket_probability == pytest.approx(-0.10)


def test_analysis_scores_home_outcome_once():
    observations = [
        build_discrepancy_observation(
            forecast_row(
                market_id='m1',
                bookmaker_home=0.8,
                polymarket_home=0.6,
                outcome=1,
            )
        )
    ]

    results = analyze_discrepancy_bins(
        observations,
        population_name='all_synchronized',
    )

    assert sum(result.count for result in results) == 1
