from dataclasses import dataclass
import math
from typing import (
    Iterable,
    List,
    Mapping,
    Optional,
    Sequence,
    Tuple,
)

from polyedge.forecast_audit import (
    ForecastAuditError,
    ForecastAuditRow,
    parse_forecast_audit_row,
)
from polyedge.paired_forecast_uncertainty import (
    BootstrapInterval,
    DEFAULT_SEED,
    build_paired_loss_difference,
    game_date_clustered_bootstrap_interval,
)


EXTREMENESS_TOLERANCE = 1e-12


@dataclass(frozen=True)
class ProbabilityBandDefinition:
    label: str
    lower_bound: float
    upper_bound: Optional[float]


@dataclass(frozen=True)
class ExtremenessObservation:
    output_market_id: str
    game_date: str
    strict_t_minus_60_eligible: bool
    bookmaker_home_probability: float
    polymarket_home_probability: float
    consensus_home_probability: float
    extremeness_gap_bookmaker_minus_polymarket: float
    bookmaker_less_extreme: bool
    equal_extremeness: bool
    brier_score_difference_polymarket_minus_bookmaker: float
    log_loss_difference_polymarket_minus_bookmaker: float


@dataclass(frozen=True)
class ProbabilityBandResult:
    population_name: str
    band_label: str
    lower_bound: float
    upper_bound: Optional[float]
    count: int
    bookmaker_less_extreme_fraction: Optional[float]
    mean_extremeness_gap_bookmaker_minus_polymarket: Optional[float]
    mean_brier_score_difference_polymarket_minus_bookmaker: Optional[float]
    brier_date_clustered_ci: Optional[BootstrapInterval]
    mean_log_loss_difference_polymarket_minus_bookmaker: Optional[float]
    log_loss_date_clustered_ci: Optional[BootstrapInterval]


@dataclass(frozen=True)
class ExtremenessAnalysisResult:
    population_name: str
    count: int
    bookmaker_less_extreme_count: int
    equal_extremeness_count: int
    bookmaker_more_extreme_count: int
    bookmaker_less_extreme_fraction: float
    equal_extremeness_fraction: float
    bookmaker_more_extreme_fraction: float
    mean_extremeness_gap_bookmaker_minus_polymarket: float
    probability_bands: Tuple[ProbabilityBandResult, ...]


PROBABILITY_BANDS = (
    ProbabilityBandDefinition(
        "[0.00, 0.20)",
        0.00,
        0.20,
    ),
    ProbabilityBandDefinition(
        "[0.20, 0.35)",
        0.20,
        0.35,
    ),
    ProbabilityBandDefinition(
        "[0.35, 0.50)",
        0.35,
        0.50,
    ),
    ProbabilityBandDefinition(
        "[0.50, 0.65)",
        0.50,
        0.65,
    ),
    ProbabilityBandDefinition(
        "[0.65, 0.80)",
        0.65,
        0.80,
    ),
    ProbabilityBandDefinition(
        "[0.80, 1.00]",
        0.80,
        None,
    ),
)


def build_extremeness_observation(
    row: ForecastAuditRow,
) -> ExtremenessObservation:
    bookmaker_extremeness = abs(
        row.bookmaker_home_probability
        - 0.5
    )
    polymarket_extremeness = abs(
        row.polymarket_home_probability
        - 0.5
    )
    extremeness_gap = (
        bookmaker_extremeness
        - polymarket_extremeness
    )

    equal_extremeness = math.isclose(
        extremeness_gap,
        0.0,
        rel_tol=0.0,
        abs_tol=EXTREMENESS_TOLERANCE,
    )

    paired_difference = (
        build_paired_loss_difference(
            row
        )
    )

    if not math.isfinite(
        paired_difference
        .brier_difference_polymarket_minus_bookmaker
    ):
        raise ForecastAuditError(
            row.output_market_id
            + ": non-finite paired Brier-score difference"
        )

    if not math.isfinite(
        paired_difference
        .log_loss_difference_polymarket_minus_bookmaker
    ):
        raise ForecastAuditError(
            row.output_market_id
            + ": non-finite paired log-loss difference"
        )

    return ExtremenessObservation(
        output_market_id=(
            row.output_market_id
        ),
        game_date=(
            paired_difference.game_date
        ),
        strict_t_minus_60_eligible=(
            row.strict_t_minus_60_eligible
        ),
        bookmaker_home_probability=(
            row.bookmaker_home_probability
        ),
        polymarket_home_probability=(
            row.polymarket_home_probability
        ),
        consensus_home_probability=(
            (
                row.bookmaker_home_probability
                + row.polymarket_home_probability
            )
            / 2.0
        ),
        extremeness_gap_bookmaker_minus_polymarket=(
            extremeness_gap
        ),
        bookmaker_less_extreme=(
            extremeness_gap
            < -EXTREMENESS_TOLERANCE
        ),
        equal_extremeness=(
            equal_extremeness
        ),
        brier_score_difference_polymarket_minus_bookmaker=(
            paired_difference
            .brier_difference_polymarket_minus_bookmaker
        ),
        log_loss_difference_polymarket_minus_bookmaker=(
            paired_difference
            .log_loss_difference_polymarket_minus_bookmaker
        ),
    )


def parse_extremeness_observations(
    rows: Iterable[Mapping[str, str]],
) -> List[ExtremenessObservation]:
    result = []
    seen_market_ids = set()

    for raw_row in rows:
        parsed = parse_forecast_audit_row(
            raw_row
        )

        if (
            parsed.output_market_id
            in seen_market_ids
        ):
            raise ForecastAuditError(
                "Duplicate output_market_id: "
                + parsed.output_market_id
            )

        seen_market_ids.add(
            parsed.output_market_id
        )

        result.append(
            build_extremeness_observation(
                parsed
            )
        )

    if not result:
        raise ForecastAuditError(
            "Cannot analyze extremeness from an empty dataset"
        )

    return result


def _mean(
    values: Sequence[float],
) -> float:
    if not values:
        raise ValueError(
            "Cannot compute a mean from empty values"
        )

    if any(
        not math.isfinite(value)
        for value in values
    ):
        raise ValueError(
            "Extremeness-analysis inputs must be finite"
        )

    return sum(values) / len(values)


def _contains_probability(
    definition: ProbabilityBandDefinition,
    probability: float,
) -> bool:
    if probability < definition.lower_bound:
        return False

    if definition.upper_bound is None:
        return probability <= 1.0

    return probability < definition.upper_bound


def _analyze_probability_band(
    *,
    population_name: str,
    definition: ProbabilityBandDefinition,
    rows: Sequence[ExtremenessObservation],
    resamples: int,
    seed: int,
) -> ProbabilityBandResult:
    band_rows = [
        row
        for row in rows
        if _contains_probability(
            definition,
            row.consensus_home_probability,
        )
    ]

    if not band_rows:
        return ProbabilityBandResult(
            population_name=population_name,
            band_label=definition.label,
            lower_bound=definition.lower_bound,
            upper_bound=definition.upper_bound,
            count=0,
            bookmaker_less_extreme_fraction=None,
            mean_extremeness_gap_bookmaker_minus_polymarket=None,
            mean_brier_score_difference_polymarket_minus_bookmaker=None,
            brier_date_clustered_ci=None,
            mean_log_loss_difference_polymarket_minus_bookmaker=None,
            log_loss_date_clustered_ci=None,
        )

    brier_values = [
        (
            row
            .brier_score_difference_polymarket_minus_bookmaker
        )
        for row in band_rows
    ]
    log_loss_values = [
        (
            row
            .log_loss_difference_polymarket_minus_bookmaker
        )
        for row in band_rows
    ]

    brier_values_and_dates = [
        (
            value,
            row.game_date,
        )
        for value, row in zip(
            brier_values,
            band_rows,
        )
    ]
    log_loss_values_and_dates = [
        (
            value,
            row.game_date,
        )
        for value, row in zip(
            log_loss_values,
            band_rows,
        )
    ]

    return ProbabilityBandResult(
        population_name=population_name,
        band_label=definition.label,
        lower_bound=definition.lower_bound,
        upper_bound=definition.upper_bound,
        count=len(band_rows),
        bookmaker_less_extreme_fraction=(
            sum(
                row.bookmaker_less_extreme
                for row in band_rows
            )
            / len(band_rows)
        ),
        mean_extremeness_gap_bookmaker_minus_polymarket=(
            _mean([
                (
                    row
                    .extremeness_gap_bookmaker_minus_polymarket
                )
                for row in band_rows
            ])
        ),
        mean_brier_score_difference_polymarket_minus_bookmaker=(
            _mean(
                brier_values
            )
        ),
        brier_date_clustered_ci=(
            game_date_clustered_bootstrap_interval(
                brier_values_and_dates,
                resamples=resamples,
                seed=seed,
            )
        ),
        mean_log_loss_difference_polymarket_minus_bookmaker=(
            _mean(
                log_loss_values
            )
        ),
        log_loss_date_clustered_ci=(
            game_date_clustered_bootstrap_interval(
                log_loss_values_and_dates,
                resamples=resamples,
                seed=seed,
            )
        ),
    )


def analyze_extremeness(
    observations: Sequence[ExtremenessObservation],
    *,
    population_name: str,
    resamples: int,
    seed: int = DEFAULT_SEED,
) -> ExtremenessAnalysisResult:
    if not observations:
        raise ValueError(
            f"{population_name} population is empty"
        )

    if resamples <= 0:
        raise ValueError(
            "Bootstrap resamples must be positive"
        )

    bookmaker_less_extreme_count = sum(
        row.bookmaker_less_extreme
        for row in observations
    )
    equal_extremeness_count = sum(
        row.equal_extremeness
        for row in observations
    )
    bookmaker_more_extreme_count = (
        len(observations)
        - bookmaker_less_extreme_count
        - equal_extremeness_count
    )

    count = len(
        observations
    )

    probability_bands = tuple(
        _analyze_probability_band(
            population_name=population_name,
            definition=definition,
            rows=observations,
            resamples=resamples,
            seed=seed,
        )
        for definition in PROBABILITY_BANDS
    )

    if sum(
        result.count
        for result in probability_bands
    ) != count:
        raise ValueError(
            "Probability bands do not partition the population"
        )

    return ExtremenessAnalysisResult(
        population_name=population_name,
        count=count,
        bookmaker_less_extreme_count=(
            bookmaker_less_extreme_count
        ),
        equal_extremeness_count=(
            equal_extremeness_count
        ),
        bookmaker_more_extreme_count=(
            bookmaker_more_extreme_count
        ),
        bookmaker_less_extreme_fraction=(
            bookmaker_less_extreme_count
            / count
        ),
        equal_extremeness_fraction=(
            equal_extremeness_count
            / count
        ),
        bookmaker_more_extreme_fraction=(
            bookmaker_more_extreme_count
            / count
        ),
        mean_extremeness_gap_bookmaker_minus_polymarket=(
            _mean([
                (
                    row
                    .extremeness_gap_bookmaker_minus_polymarket
                )
                for row in observations
            ])
        ),
        probability_bands=(
            probability_bands
        ),
    )
