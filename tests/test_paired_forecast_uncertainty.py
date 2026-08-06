import math

import pytest

from polyedge.forecast_audit import (
    ForecastAuditRow,
)
from polyedge.paired_forecast_uncertainty import (
    audit_paired_uncertainty,
    build_paired_loss_difference,
    game_date_clustered_bootstrap_interval,
    game_date_from_market_id,
    ordinary_paired_bootstrap_interval,
)


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
        bookmaker_home_probability=(
            bookmaker_home
        ),
        polymarket_home_probability=(
            polymarket_home
        ),
        resolved_home_value=outcome,
    )


def test_extracts_canonical_game_date():
    assert game_date_from_market_id(
        "nba_20241022_boston_vs_new_york_home_win"
    ) == "2024-10-22"


def test_builds_per_game_loss_differences():
    result = build_paired_loss_difference(
        forecast_row(
            market_id=(
                "nba_20241022_boston_vs_new_york_home_win"
            ),
            bookmaker_home=0.8,
            polymarket_home=0.6,
            outcome=1,
        )
    )

    assert (
        result
        .brier_difference_polymarket_minus_bookmaker
    ) == pytest.approx(
        0.12
    )

    assert (
        result
        .log_loss_difference_polymarket_minus_bookmaker
    ) == pytest.approx(
        math.log(0.8 / 0.6)
    )


def test_identical_values_produce_exact_bootstrap_interval():
    interval = ordinary_paired_bootstrap_interval(
        [0.25, 0.25, 0.25],
        resamples=100,
        seed=7,
    )

    assert interval.lower == pytest.approx(
        0.25
    )

    assert interval.upper == pytest.approx(
        0.25
    )


def test_clustered_bootstrap_is_deterministic():
    values_and_dates = [
        (0.1, "2024-01-01"),
        (0.2, "2024-01-01"),
        (-0.1, "2024-01-02"),
    ]

    first = game_date_clustered_bootstrap_interval(
        values_and_dates,
        resamples=200,
        seed=11,
    )

    second = game_date_clustered_bootstrap_interval(
        values_and_dates,
        resamples=200,
        seed=11,
    )

    assert first == second


def test_audits_brier_and_log_loss():
    rows = [
        build_paired_loss_difference(
            forecast_row(
                market_id=(
                    "nba_20241022_a_vs_b_home_win"
                ),
                bookmaker_home=0.8,
                polymarket_home=0.6,
                outcome=1,
            )
        ),
        build_paired_loss_difference(
            forecast_row(
                market_id=(
                    "nba_20241022_c_vs_d_home_win"
                ),
                bookmaker_home=0.2,
                polymarket_home=0.4,
                outcome=0,
            )
        ),
        build_paired_loss_difference(
            forecast_row(
                market_id=(
                    "nba_20241023_e_vs_f_home_win"
                ),
                bookmaker_home=0.7,
                polymarket_home=0.55,
                outcome=1,
            )
        ),
    ]

    audits = audit_paired_uncertainty(
        rows,
        population_name="all_synchronized",
        resamples=100,
        seed=5,
    )

    assert [
        audit.metric_name
        for audit in audits
    ] == [
        "brier_score",
        "binary_log_loss",
    ]

    assert all(
        audit.count == 3
        for audit in audits
    )

    assert all(
        audit.cluster_count == 2
        for audit in audits
    )

    assert all(
        audit
        .mean_difference_polymarket_minus_bookmaker
        > 0
        for audit in audits
    )
