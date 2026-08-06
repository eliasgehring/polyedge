from dataclasses import dataclass
import math
from typing import Iterable, List, Mapping, Optional, Sequence

from polyedge.forecast_audit import (
    ForecastAuditError,
    ForecastAuditRow,
    parse_forecast_audit_row,
)


@dataclass(frozen=True)
class DiscrepancyBinDefinition:
    label: str
    lower_bound: Optional[float]
    upper_bound: Optional[float]


@dataclass(frozen=True)
class DiscrepancyObservation:
    output_market_id: str
    strict_t_minus_60_eligible: bool
    bookmaker_home_probability: float
    polymarket_home_probability: float
    resolved_home_value: int
    home_probability_discrepancy: float
    brier_score_difference_polymarket_minus_bookmaker: float
    log_loss_difference_polymarket_minus_bookmaker: float


@dataclass(frozen=True)
class DiscrepancyBinResult:
    population_name: str
    bin_label: str
    lower_bound: Optional[float]
    upper_bound: Optional[float]
    count: int
    mean_home_probability_discrepancy: Optional[float]
    mean_bookmaker_home_probability: Optional[float]
    mean_polymarket_home_probability: Optional[float]
    observed_home_win_rate: Optional[float]
    observed_minus_bookmaker_probability: Optional[float]
    observed_minus_polymarket_probability: Optional[float]
    mean_brier_score_difference_polymarket_minus_bookmaker: Optional[float]
    mean_log_loss_difference_polymarket_minus_bookmaker: Optional[float]


DISCREPANCY_BINS = (
    DiscrepancyBinDefinition('< -0.10', None, -0.10),
    DiscrepancyBinDefinition('[-0.10, -0.05)', -0.10, -0.05),
    DiscrepancyBinDefinition('[-0.05, -0.02)', -0.05, -0.02),
    DiscrepancyBinDefinition('[-0.02, 0.00)', -0.02, 0.00),
    DiscrepancyBinDefinition('[0.00, 0.02)', 0.00, 0.02),
    DiscrepancyBinDefinition('[0.02, 0.05)', 0.02, 0.05),
    DiscrepancyBinDefinition('[0.05, 0.10)', 0.05, 0.10),
    DiscrepancyBinDefinition('>= 0.10', 0.10, None),
)


def _binary_log_loss(probability: float, outcome: int) -> float:
    if outcome == 1:
        if probability == 0.0:
            return math.inf
        return -math.log(probability)

    if probability == 1.0:
        return math.inf
    return -math.log1p(-probability)


def _brier_loss(probability: float, outcome: int) -> float:
    return (probability - outcome) ** 2


def build_discrepancy_observation(
    row: ForecastAuditRow,
) -> DiscrepancyObservation:
    discrepancy = (
        row.bookmaker_home_probability
        - row.polymarket_home_probability
    )

    bookmaker_brier = _brier_loss(
        row.bookmaker_home_probability,
        row.resolved_home_value,
    )
    polymarket_brier = _brier_loss(
        row.polymarket_home_probability,
        row.resolved_home_value,
    )

    bookmaker_log_loss = _binary_log_loss(
        row.bookmaker_home_probability,
        row.resolved_home_value,
    )
    polymarket_log_loss = _binary_log_loss(
        row.polymarket_home_probability,
        row.resolved_home_value,
    )
    log_loss_difference = (
        polymarket_log_loss - bookmaker_log_loss
    )

    if not math.isfinite(log_loss_difference):
        raise ForecastAuditError(
            row.output_market_id
            + ': non-finite paired log-loss difference'
        )

    return DiscrepancyObservation(
        output_market_id=row.output_market_id,
        strict_t_minus_60_eligible=(
            row.strict_t_minus_60_eligible
        ),
        bookmaker_home_probability=(
            row.bookmaker_home_probability
        ),
        polymarket_home_probability=(
            row.polymarket_home_probability
        ),
        resolved_home_value=row.resolved_home_value,
        home_probability_discrepancy=discrepancy,
        brier_score_difference_polymarket_minus_bookmaker=(
            polymarket_brier - bookmaker_brier
        ),
        log_loss_difference_polymarket_minus_bookmaker=(
            log_loss_difference
        ),
    )


def parse_discrepancy_observations(
    rows: Iterable[Mapping[str, str]],
) -> List[DiscrepancyObservation]:
    result = []
    seen_market_ids = set()

    for raw_row in rows:
        parsed = parse_forecast_audit_row(raw_row)

        if parsed.output_market_id in seen_market_ids:
            raise ForecastAuditError(
                'Duplicate output_market_id: '
                + parsed.output_market_id
            )

        seen_market_ids.add(parsed.output_market_id)
        result.append(build_discrepancy_observation(parsed))

    if not result:
        raise ForecastAuditError(
            'Cannot analyze an empty synchronized dataset'
        )

    return result


def discrepancy_bin_for_value(
    value: float,
) -> DiscrepancyBinDefinition:
    if not math.isfinite(value):
        raise ValueError('Discrepancy must be finite')

    for definition in DISCREPANCY_BINS:
        lower_ok = (
            definition.lower_bound is None
            or value >= definition.lower_bound
        )
        upper_ok = (
            definition.upper_bound is None
            or value < definition.upper_bound
        )

        if lower_ok and upper_ok:
            return definition

    raise AssertionError(
        'Finite discrepancy did not match a fixed bin'
    )


def _mean(values: Sequence[float]) -> float:
    if not values:
        raise ValueError('Cannot compute a mean from empty values')
    return sum(values) / len(values)


def analyze_discrepancy_bins(
    observations: Sequence[DiscrepancyObservation],
    *,
    population_name: str,
) -> List[DiscrepancyBinResult]:
    if not observations:
        raise ValueError(f'{population_name} population is empty')

    grouped = {
        definition.label: []
        for definition in DISCREPANCY_BINS
    }

    for observation in observations:
        definition = discrepancy_bin_for_value(
            observation.home_probability_discrepancy
        )
        grouped[definition.label].append(observation)

    results = []

    for definition in DISCREPANCY_BINS:
        rows = grouped[definition.label]

        if rows:
            mean_discrepancy = _mean([
                row.home_probability_discrepancy
                for row in rows
            ])
            mean_bookmaker = _mean([
                row.bookmaker_home_probability
                for row in rows
            ])
            mean_polymarket = _mean([
                row.polymarket_home_probability
                for row in rows
            ])
            observed_rate = _mean([
                float(row.resolved_home_value)
                for row in rows
            ])
            mean_brier_difference = _mean([
                row.brier_score_difference_polymarket_minus_bookmaker
                for row in rows
            ])
            mean_log_loss_difference = _mean([
                row.log_loss_difference_polymarket_minus_bookmaker
                for row in rows
            ])
        else:
            mean_discrepancy = None
            mean_bookmaker = None
            mean_polymarket = None
            observed_rate = None
            mean_brier_difference = None
            mean_log_loss_difference = None

        results.append(
            DiscrepancyBinResult(
                population_name=population_name,
                bin_label=definition.label,
                lower_bound=definition.lower_bound,
                upper_bound=definition.upper_bound,
                count=len(rows),
                mean_home_probability_discrepancy=(
                    mean_discrepancy
                ),
                mean_bookmaker_home_probability=mean_bookmaker,
                mean_polymarket_home_probability=mean_polymarket,
                observed_home_win_rate=observed_rate,
                observed_minus_bookmaker_probability=(
                    None
                    if observed_rate is None
                    else observed_rate - mean_bookmaker
                ),
                observed_minus_polymarket_probability=(
                    None
                    if observed_rate is None
                    else observed_rate - mean_polymarket
                ),
                mean_brier_score_difference_polymarket_minus_bookmaker=(
                    mean_brier_difference
                ),
                mean_log_loss_difference_polymarket_minus_bookmaker=(
                    mean_log_loss_difference
                ),
            )
        )

    if sum(result.count for result in results) != len(observations):
        raise AssertionError('Discrepancy bin counts do not reconcile')

    return results
