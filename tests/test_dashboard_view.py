import pytest

from polyedge.dashboard_view import (
    build_dashboard_view,
)
from polyedge.research_command import (
    DEMO_DATASET_PATH,
    build_research_summary,
)


def build_demo_view():
    summary = build_research_summary(
        dataset_path=DEMO_DATASET_PATH,
        demo=True,
        resamples=100,
        seed=7,
    )

    return build_dashboard_view(
        summary
    )


def test_demo_view_preserves_claim_boundary():
    view = build_demo_view()

    assert (
        view.dataset_mode
        == "SYNTHETIC_DEMONSTRATION"
    )
    assert (
        view.empirical_claim_status
        == "NONE"
    )
    assert (
        view.execution_semantics
        == "none"
    )
    assert (
        view.tradable_profitability_status
        == "NOT ESTABLISHED"
    )


def test_dashboard_view_uses_canonical_counts():
    view = build_demo_view()

    assert view.row_count == 12
    assert view.strict_row_count == 10
    assert (
        view.at_least_five_points_count
        == 0
    )
    assert (
        view.within_two_points_count
        == 4
    )


def test_dashboard_view_exposes_aggregate_intervals():
    view = build_demo_view()

    assert len(
        view.confidence_intervals
    ) == 2

    labels = {
        interval.metric_label
        for interval
        in view.confidence_intervals
    }

    assert labels == {
        "Brier score",
        "Binary log loss",
    }


def test_dashboard_view_exposes_fixed_probability_bands():
    view = build_demo_view()

    assert [
        band.band_label
        for band in view.probability_bands
    ] == [
        "[0.00, 0.20)",
        "[0.20, 0.35)",
        "[0.35, 0.50)",
        "[0.50, 0.65)",
        "[0.65, 0.80)",
        "[0.80, 1.00]",
    ]

    assert sum(
        band.count
        for band in view.probability_bands
    ) == view.row_count


def test_dashboard_view_converts_probability_units_only_for_display():
    view = build_demo_view()

    assert (
        view.mean_absolute_discrepancy_percentage_points
        == pytest.approx(1.75)
    )
    assert (
        view.bookmaker_less_extreme_percentage
        == (
            view.bookmaker_less_extreme_count
            / view.row_count
            * 100.0
        )
    )
