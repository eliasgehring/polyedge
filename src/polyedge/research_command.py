import csv
from dataclasses import dataclass
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Sequence

from polyedge.discrepancy_analysis import (
    DiscrepancyObservation,
    parse_discrepancy_observations,
)
from polyedge.forecast_audit import (
    ForecastPopulationAudit,
    audit_forecast_rows,
)
from polyedge.paired_forecast_uncertainty import (
    DEFAULT_SEED,
    MetricUncertaintyAudit,
    audit_paired_uncertainty,
    parse_paired_loss_differences,
)
from polyedge.paths import PROJECT_ROOT
from polyedge.polymarket_policy import (
    EXECUTION_SEMANTICS,
    POLICY_VERSION,
    SOURCE_SEMANTICS,
)


DEMO_DATASET_PATH = (
    PROJECT_ROOT
    / "data/demo/nba_v2_research_demo.csv"
)

PINNED_FULL_DATASET_SHA256 = (
    "5a93b2ebd9fd6a1f5ff0583f8f7b1e63"
    "db75bc51548d7804c41dcb1d165a4e80"
)

PINNED_FULL_DATASET_ROWS = 1217
PINNED_STRICT_ROWS = 1214


@dataclass(frozen=True)
class ResearchSummary:
    dataset_mode: str
    dataset_path: str
    dataset_sha256: str
    row_count: int
    strict_row_count: int
    bookmaker_brier_score: float
    polymarket_brier_score: float
    brier_difference_polymarket_minus_bookmaker: float
    brier_clustered_ci_lower: float
    brier_clustered_ci_upper: float
    bookmaker_log_loss: float
    polymarket_log_loss: float
    log_loss_difference_polymarket_minus_bookmaker: float
    log_loss_clustered_ci_lower: float
    log_loss_clustered_ci_upper: float
    within_two_points_count: int
    at_least_five_points_count: int
    mean_absolute_discrepancy: float
    source_semantics: str
    execution_semantics: str
    policy_version: str
    resamples: int
    seed: int


def sha256_file(
    path: Path,
) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as file:
        for chunk in iter(
            lambda: file.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def read_rows(
    path: Path,
) -> List[Dict[str, str]]:
    with path.open(
        encoding="utf-8",
        newline="",
    ) as file:
        return list(
            csv.DictReader(file)
        )


def _population_by_name(
    audits: Sequence[ForecastPopulationAudit],
    population_name: str,
) -> ForecastPopulationAudit:
    matches = [
        audit
        for audit in audits
        if audit.population_name
        == population_name
    ]

    if len(matches) != 1:
        raise ValueError(
            "Expected exactly one forecast population: "
            + population_name
        )

    return matches[0]


def _uncertainty_by_metric(
    audits: Sequence[MetricUncertaintyAudit],
    metric_name: str,
) -> MetricUncertaintyAudit:
    matches = [
        audit
        for audit in audits
        if audit.metric_name
        == metric_name
    ]

    if len(matches) != 1:
        raise ValueError(
            "Expected exactly one uncertainty metric: "
            + metric_name
        )

    return matches[0]


def _dataset_mode(
    *,
    demo: bool,
    dataset_sha256: str,
) -> str:
    if demo:
        return "SYNTHETIC_DEMONSTRATION"

    if (
        dataset_sha256
        == PINNED_FULL_DATASET_SHA256
    ):
        return "PINNED_FULL_RESEARCH_DATASET"

    return "CUSTOM_AUTHORIZED_DATASET"


def build_research_summary(
    *,
    dataset_path: Path,
    demo: bool,
    resamples: int,
    seed: int,
) -> ResearchSummary:
    if resamples <= 0:
        raise ValueError(
            "Bootstrap resamples must be positive"
        )

    rows = read_rows(
        dataset_path
    )

    forecast_audits = audit_forecast_rows(
        rows
    )

    all_forecasts = _population_by_name(
        forecast_audits,
        "all_synchronized",
    )

    strict_forecasts = _population_by_name(
        forecast_audits,
        "strict_t_minus_60",
    )

    paired_rows = parse_paired_loss_differences(
        rows
    )

    all_uncertainty = audit_paired_uncertainty(
        paired_rows,
        population_name="all_synchronized",
        resamples=resamples,
        seed=seed,
    )

    brier_uncertainty = _uncertainty_by_metric(
        all_uncertainty,
        "brier_score",
    )

    log_loss_uncertainty = _uncertainty_by_metric(
        all_uncertainty,
        "binary_log_loss",
    )

    discrepancy_rows = (
        parse_discrepancy_observations(
            rows
        )
    )

    absolute_discrepancies = [
        abs(
            row.home_probability_discrepancy
        )
        for row in discrepancy_rows
    ]

    dataset_sha256 = sha256_file(
        dataset_path
    )

    return ResearchSummary(
        dataset_mode=_dataset_mode(
            demo=demo,
            dataset_sha256=dataset_sha256,
        ),
        dataset_path=str(
            dataset_path
        ),
        dataset_sha256=dataset_sha256,
        row_count=all_forecasts.count,
        strict_row_count=(
            strict_forecasts.count
        ),
        bookmaker_brier_score=(
            all_forecasts
            .bookmaker
            .score
            .brier_score
        ),
        polymarket_brier_score=(
            all_forecasts
            .polymarket
            .score
            .brier_score
        ),
        brier_difference_polymarket_minus_bookmaker=(
            all_forecasts
            .brier_score_difference_polymarket_minus_bookmaker
        ),
        brier_clustered_ci_lower=(
            brier_uncertainty
            .game_date_clustered_bootstrap
            .lower
        ),
        brier_clustered_ci_upper=(
            brier_uncertainty
            .game_date_clustered_bootstrap
            .upper
        ),
        bookmaker_log_loss=(
            all_forecasts
            .bookmaker
            .score
            .binary_log_loss
        ),
        polymarket_log_loss=(
            all_forecasts
            .polymarket
            .score
            .binary_log_loss
        ),
        log_loss_difference_polymarket_minus_bookmaker=(
            all_forecasts
            .log_loss_difference_polymarket_minus_bookmaker
        ),
        log_loss_clustered_ci_lower=(
            log_loss_uncertainty
            .game_date_clustered_bootstrap
            .lower
        ),
        log_loss_clustered_ci_upper=(
            log_loss_uncertainty
            .game_date_clustered_bootstrap
            .upper
        ),
        within_two_points_count=sum(
            discrepancy < 0.02
            for discrepancy
            in absolute_discrepancies
        ),
        at_least_five_points_count=sum(
            discrepancy >= 0.05
            for discrepancy
            in absolute_discrepancies
        ),
        mean_absolute_discrepancy=(
            sum(
                absolute_discrepancies
            )
            / len(
                absolute_discrepancies
            )
        ),
        source_semantics=(
            SOURCE_SEMANTICS
        ),
        execution_semantics=(
            EXECUTION_SEMANTICS
        ),
        policy_version=(
            POLICY_VERSION
        ),
        resamples=resamples,
        seed=seed,
    )


def _format_float(
    value: float,
) -> str:
    return f"{value:.12f}"


def _format_ci(
    lower: float,
    upper: float,
) -> str:
    return (
        "["
        + _format_float(lower)
        + ", "
        + _format_float(upper)
        + "]"
    )


def print_research_summary(
    summary: ResearchSummary,
) -> None:
    print()
    print("POLYEDGE V2 RESEARCH SUMMARY")
    print("=" * 72)
    print(
        f"Dataset mode               : {summary.dataset_mode}"
    )
    print(
        f"Dataset rows               : {summary.row_count}"
    )
    print(
        f"Strict T-60 rows           : {summary.strict_row_count}"
    )
    print(
        f"Dataset SHA-256            : {summary.dataset_sha256}"
    )
    print(
        f"Policy version             : {summary.policy_version}"
    )
    print()
    print("FORECAST QUALITY")
    print("-" * 72)
    print(
        "Bookmaker Brier            : "
        + _format_float(
            summary.bookmaker_brier_score
        )
    )
    print(
        "Polymarket Brier           : "
        + _format_float(
            summary.polymarket_brier_score
        )
    )
    print(
        "PM minus bookmaker Brier   : "
        + _format_float(
            summary
            .brier_difference_polymarket_minus_bookmaker
        )
    )
    print(
        "Date-clustered 95% CI      : "
        + _format_ci(
            summary.brier_clustered_ci_lower,
            summary.brier_clustered_ci_upper,
        )
    )
    print(
        "Bookmaker log loss         : "
        + _format_float(
            summary.bookmaker_log_loss
        )
    )
    print(
        "Polymarket log loss        : "
        + _format_float(
            summary.polymarket_log_loss
        )
    )
    print(
        "PM minus bookmaker log loss: "
        + _format_float(
            summary
            .log_loss_difference_polymarket_minus_bookmaker
        )
    )
    print(
        "Date-clustered 95% CI      : "
        + _format_ci(
            summary.log_loss_clustered_ci_lower,
            summary.log_loss_clustered_ci_upper,
        )
    )
    print()
    print("DISCREPANCY STRUCTURE")
    print("-" * 72)
    print(
        f"Within 2 percentage points : {summary.within_two_points_count}"
    )
    print(
        f"At least 5 points apart    : {summary.at_least_five_points_count}"
    )
    print(
        "Mean absolute discrepancy  : "
        + _format_float(
            summary.mean_absolute_discrepancy
        )
    )
    print()
    print("CLAIM BOUNDARY")
    print("-" * 72)
    print(
        f"Source semantics           : {summary.source_semantics}"
    )
    print(
        f"Execution semantics        : {summary.execution_semantics}"
    )
    print(
        "Tradable profitability     : NOT ESTABLISHED"
    )

    if (
        summary.dataset_mode
        == "SYNTHETIC_DEMONSTRATION"
    ):
        print(
            "Empirical claims           : NONE"
        )
        print()
        print(
            "This command demonstrates the evaluator workflow only."
        )


def build_markdown_report(
    summary: ResearchSummary,
) -> str:
    empirical_status = (
        "None. This is a synthetic demonstration."
        if summary.dataset_mode
        == "SYNTHETIC_DEMONSTRATION"
        else (
            "Results apply only to the dataset identified "
            "by the SHA-256 below."
        )
    )

    lines = [
        "# PolyEdge V2 Research Report",
        "",
        "## Dataset identity",
        "",
        f"- Mode: `{summary.dataset_mode}`",
        f"- Path: `{summary.dataset_path}`",
        f"- SHA-256: `{summary.dataset_sha256}`",
        f"- Rows: `{summary.row_count}`",
        f"- Strict T-60 rows: `{summary.strict_row_count}`",
        f"- Policy: `{summary.policy_version}`",
        "",
        "## Forecast quality",
        "",
        "| Metric | Bookmaker | Polymarket | PM minus bookmaker | Date-clustered 95% CI |",
        "|---|---:|---:|---:|---:|",
        (
            "| Brier score | "
            f"{_format_float(summary.bookmaker_brier_score)} | "
            f"{_format_float(summary.polymarket_brier_score)} | "
            f"{_format_float(summary.brier_difference_polymarket_minus_bookmaker)} | "
            f"{_format_ci(summary.brier_clustered_ci_lower, summary.brier_clustered_ci_upper)} |"
        ),
        (
            "| Binary log loss | "
            f"{_format_float(summary.bookmaker_log_loss)} | "
            f"{_format_float(summary.polymarket_log_loss)} | "
            f"{_format_float(summary.log_loss_difference_polymarket_minus_bookmaker)} | "
            f"{_format_ci(summary.log_loss_clustered_ci_lower, summary.log_loss_clustered_ci_upper)} |"
        ),
        "",
        "Positive score differences mean the bookmaker forecast had lower loss.",
        "",
        "## Discrepancy structure",
        "",
        f"- Within two percentage points: `{summary.within_two_points_count}`",
        f"- At least five percentage points apart: `{summary.at_least_five_points_count}`",
        (
            "- Mean absolute discrepancy: `"
            + _format_float(
                summary.mean_absolute_discrepancy
            )
            + "`"
        ),
        "",
        "## Claim boundary",
        "",
        f"- Source semantics: `{summary.source_semantics}`",
        f"- Execution semantics: `{summary.execution_semantics}`",
        "- Tradable profitability: **not established**",
        f"- Empirical status: {empirical_status}",
        "",
        "The Polymarket input is a sampled historical probability series, not a historical order book, bid, ask, trade, or fill.",
        "",
    ]

    return "\n".join(
        lines
    )


def write_markdown_report(
    *,
    summary: ResearchSummary,
    output_path: Path,
) -> None:
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path.write_text(
        build_markdown_report(
            summary
        ),
        encoding="utf-8",
    )


def run_research_command(
    *,
    dataset_path: Optional[str],
    demo: bool,
    report_path: Optional[str],
    resamples: int,
    seed: int = DEFAULT_SEED,
) -> int:
    if demo and dataset_path is not None:
        raise ValueError(
            "Choose either demo mode or a dataset path"
        )

    if not demo and dataset_path is None:
        raise ValueError(
            "Choose --demo or provide --dataset"
        )

    resolved_dataset_path = (
        DEMO_DATASET_PATH
        if demo
        else Path(
            dataset_path
        )
    )

    summary = build_research_summary(
        dataset_path=(
            resolved_dataset_path
        ),
        demo=demo,
        resamples=resamples,
        seed=seed,
    )

    print_research_summary(
        summary
    )

    if report_path is not None:
        output_path = Path(
            report_path
        )

        write_markdown_report(
            summary=summary,
            output_path=output_path,
        )

        print()
        print(
            "Report saved to             : "
            + str(
                output_path
            )
        )

    return 0
