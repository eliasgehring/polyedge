from dataclasses import dataclass
from typing import Optional, Tuple

from polyedge.research_command import (
    ResearchSummary,
)


@dataclass(frozen=True)
class ConfidenceIntervalView:
    metric_label: str
    estimate: float
    lower: float
    upper: float
    crosses_zero: bool


@dataclass(frozen=True)
class ProbabilityBandView:
    band_label: str
    count: int
    bookmaker_less_extreme_percentage: Optional[float]
    mean_extremeness_gap_percentage_points: Optional[float]
    mean_brier_difference: Optional[float]
    brier_ci_lower: Optional[float]
    brier_ci_upper: Optional[float]


@dataclass(frozen=True)
class DashboardView:
    dataset_mode: str
    dataset_status: str
    empirical_claim_status: str
    dataset_sha256: str
    policy_version: str
    row_count: int
    strict_row_count: int
    within_two_points_count: int
    within_two_points_percentage: float
    at_least_five_points_count: int
    mean_absolute_discrepancy_percentage_points: float
    bookmaker_brier_score: float
    polymarket_brier_score: float
    brier_difference_polymarket_minus_bookmaker: float
    bookmaker_log_loss: float
    polymarket_log_loss: float
    log_loss_difference_polymarket_minus_bookmaker: float
    confidence_intervals: Tuple[
        ConfidenceIntervalView,
        ...,
    ]
    bookmaker_less_extreme_count: int
    bookmaker_less_extreme_percentage: float
    mean_extremeness_gap_percentage_points: float
    probability_bands: Tuple[
        ProbabilityBandView,
        ...,
    ]
    source_semantics: str
    execution_semantics: str
    tradable_profitability_status: str
    conclusion: str


def _crosses_zero(
    lower: float,
    upper: float,
) -> bool:
    return lower <= 0.0 <= upper


def build_dashboard_view(
    summary: ResearchSummary,
) -> DashboardView:
    if summary.row_count <= 0:
        raise ValueError(
            "Dashboard requires at least one research row"
        )

    extremeness = (
        summary.extremeness_analysis
    )

    confidence_intervals = (
        ConfidenceIntervalView(
            metric_label="Brier score",
            estimate=(
                summary
                .brier_difference_polymarket_minus_bookmaker
            ),
            lower=(
                summary.brier_clustered_ci_lower
            ),
            upper=(
                summary.brier_clustered_ci_upper
            ),
            crosses_zero=_crosses_zero(
                summary.brier_clustered_ci_lower,
                summary.brier_clustered_ci_upper,
            ),
        ),
        ConfidenceIntervalView(
            metric_label="Binary log loss",
            estimate=(
                summary
                .log_loss_difference_polymarket_minus_bookmaker
            ),
            lower=(
                summary.log_loss_clustered_ci_lower
            ),
            upper=(
                summary.log_loss_clustered_ci_upper
            ),
            crosses_zero=_crosses_zero(
                summary.log_loss_clustered_ci_lower,
                summary.log_loss_clustered_ci_upper,
            ),
        ),
    )

    probability_bands = tuple(
        ProbabilityBandView(
            band_label=band.band_label,
            count=band.count,
            bookmaker_less_extreme_percentage=(
                None
                if (
                    band
                    .bookmaker_less_extreme_fraction
                    is None
                )
                else (
                    band
                    .bookmaker_less_extreme_fraction
                    * 100.0
                )
            ),
            mean_extremeness_gap_percentage_points=(
                None
                if (
                    band
                    .mean_extremeness_gap_bookmaker_minus_polymarket
                    is None
                )
                else (
                    band
                    .mean_extremeness_gap_bookmaker_minus_polymarket
                    * 100.0
                )
            ),
            mean_brier_difference=(
                band
                .mean_brier_score_difference_polymarket_minus_bookmaker
            ),
            brier_ci_lower=(
                None
                if (
                    band.brier_date_clustered_ci
                    is None
                )
                else (
                    band
                    .brier_date_clustered_ci
                    .lower
                )
            ),
            brier_ci_upper=(
                None
                if (
                    band.brier_date_clustered_ci
                    is None
                )
                else (
                    band
                    .brier_date_clustered_ci
                    .upper
                )
            ),
        )
        for band in extremeness.probability_bands
    )

    all_aggregate_intervals_cross_zero = all(
        interval.crosses_zero
        for interval in confidence_intervals
    )

    if (
        all_aggregate_intervals_cross_zero
    ):
        conclusion = (
            "Bookmaker consensus was usually less extreme, "
            "but neither source showed a credible aggregate "
            "accuracy advantage."
        )
    else:
        conclusion = (
            "At least one aggregate interval excludes zero. "
            "Inspect the metric-specific result before drawing "
            "a source-level conclusion."
        )

    if (
        summary.dataset_mode
        == "SYNTHETIC_DEMONSTRATION"
    ):
        dataset_status = (
            "Synthetic evaluator fixture"
        )
        empirical_claim_status = "NONE"
    elif (
        summary.dataset_mode
        == "PINNED_FULL_RESEARCH_DATASET"
    ):
        dataset_status = (
            "Pinned full dataset verified"
        )
        empirical_claim_status = (
            "HASH-PINNED DATASET ONLY"
        )
    else:
        dataset_status = (
            "Custom authorized dataset"
        )
        empirical_claim_status = (
            "INPUT-SPECIFIC"
        )

    return DashboardView(
        dataset_mode=summary.dataset_mode,
        dataset_status=dataset_status,
        empirical_claim_status=(
            empirical_claim_status
        ),
        dataset_sha256=summary.dataset_sha256,
        policy_version=summary.policy_version,
        row_count=summary.row_count,
        strict_row_count=(
            summary.strict_row_count
        ),
        within_two_points_count=(
            summary.within_two_points_count
        ),
        within_two_points_percentage=(
            summary.within_two_points_count
            / summary.row_count
            * 100.0
        ),
        at_least_five_points_count=(
            summary.at_least_five_points_count
        ),
        mean_absolute_discrepancy_percentage_points=(
            summary.mean_absolute_discrepancy
            * 100.0
        ),
        bookmaker_brier_score=(
            summary.bookmaker_brier_score
        ),
        polymarket_brier_score=(
            summary.polymarket_brier_score
        ),
        brier_difference_polymarket_minus_bookmaker=(
            summary
            .brier_difference_polymarket_minus_bookmaker
        ),
        bookmaker_log_loss=(
            summary.bookmaker_log_loss
        ),
        polymarket_log_loss=(
            summary.polymarket_log_loss
        ),
        log_loss_difference_polymarket_minus_bookmaker=(
            summary
            .log_loss_difference_polymarket_minus_bookmaker
        ),
        confidence_intervals=(
            confidence_intervals
        ),
        bookmaker_less_extreme_count=(
            extremeness
            .bookmaker_less_extreme_count
        ),
        bookmaker_less_extreme_percentage=(
            extremeness
            .bookmaker_less_extreme_fraction
            * 100.0
        ),
        mean_extremeness_gap_percentage_points=(
            extremeness
            .mean_extremeness_gap_bookmaker_minus_polymarket
            * 100.0
        ),
        probability_bands=probability_bands,
        source_semantics=(
            summary.source_semantics
        ),
        execution_semantics=(
            summary.execution_semantics
        ),
        tradable_profitability_status=(
            "NOT ESTABLISHED"
        ),
        conclusion=conclusion,
    )
