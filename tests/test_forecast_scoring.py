import math

import pytest

from polyedge.forecast_scoring import (
    binary_log_loss,
    brier_score,
    fixed_width_calibration_bins,
    score_binary_forecasts,
)


def test_brier_score_matches_known_example():
    probabilities = [
        0.0,
        0.5,
        1.0,
    ]

    outcomes = [
        0,
        1,
        1,
    ]

    assert brier_score(
        probabilities,
        outcomes,
    ) == pytest.approx(
        1.0 / 12.0
    )


def test_log_loss_for_half_probability_is_log_two():
    assert binary_log_loss(
        [0.5, 0.5],
        [0, 1],
    ) == pytest.approx(
        math.log(2.0)
    )


def test_log_loss_does_not_silently_clip_impossible_error():
    assert math.isinf(
        binary_log_loss(
            [0.0],
            [1],
        )
    )

    assert math.isinf(
        binary_log_loss(
            [1.0],
            [0],
        )
    )


def test_certain_correct_predictions_have_zero_log_loss():
    assert binary_log_loss(
        [0.0, 1.0],
        [0, 1],
    ) == pytest.approx(
        0.0
    )


def test_fixed_width_bins_handle_boundaries_deterministically():
    bins = fixed_width_calibration_bins(
        [
            0.0,
            0.1,
            0.999,
            1.0,
        ],
        [
            0,
            0,
            1,
            1,
        ],
    )

    assert len(bins) == 10

    assert bins[0].count == 1
    assert bins[1].count == 1
    assert bins[9].count == 2

    assert not (
        bins[0]
        .upper_bound_inclusive
    )

    assert (
        bins[9]
        .upper_bound_inclusive
    )


def test_calibration_gap_is_observed_minus_forecast():
    bins = fixed_width_calibration_bins(
        [0.2, 0.4],
        [1, 1],
    )

    assert (
        bins[2]
        .observed_minus_forecast
    ) == pytest.approx(
        0.8
    )

    assert (
        bins[4]
        .observed_minus_forecast
    ) == pytest.approx(
        0.6
    )


def test_scoring_rejects_mismatched_lengths():
    with pytest.raises(
        ValueError,
        match="equal length",
    ):
        score_binary_forecasts(
            [0.5],
            [0, 1],
        )


def test_scoring_rejects_empty_input():
    with pytest.raises(
        ValueError,
        match="empty",
    ):
        score_binary_forecasts(
            [],
            [],
        )


def test_scoring_rejects_invalid_probability():
    with pytest.raises(
        ValueError,
        match="between zero and one",
    ):
        score_binary_forecasts(
            [1.01],
            [1],
        )


def test_scoring_rejects_non_binary_outcome():
    with pytest.raises(
        ValueError,
        match="binary",
    ):
        score_binary_forecasts(
            [0.5],
            [2],
        )
