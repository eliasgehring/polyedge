from dataclasses import dataclass
import math
import random
import re
from typing import Dict, Iterable, List, Sequence, Tuple

from polyedge.forecast_audit import (
    ForecastAuditError,
    ForecastAuditRow,
    parse_forecast_audit_row,
)


MARKET_DATE_PATTERN = re.compile(
    r"^nba_(\d{8})_"
)

DEFAULT_CONFIDENCE_LEVEL = 0.95
DEFAULT_RESAMPLES = 10000
DEFAULT_SEED = 20260805


@dataclass(frozen=True)
class PairedLossDifference:
    output_market_id: str
    game_date: str
    strict_t_minus_60_eligible: bool
    brier_difference_polymarket_minus_bookmaker: float
    log_loss_difference_polymarket_minus_bookmaker: float


@dataclass(frozen=True)
class BootstrapInterval:
    confidence_level: float
    lower: float
    upper: float
    resamples: int
    seed: int


@dataclass(frozen=True)
class MetricUncertaintyAudit:
    population_name: str
    metric_name: str
    count: int
    cluster_count: int
    mean_difference_polymarket_minus_bookmaker: float
    ordinary_paired_bootstrap: BootstrapInterval
    game_date_clustered_bootstrap: BootstrapInterval


def _binary_log_loss_value(
    probability: float,
    outcome: int,
) -> float:
    if outcome == 1:
        if probability == 0.0:
            return math.inf

        return -math.log(
            probability
        )

    if probability == 1.0:
        return math.inf

    return -math.log1p(
        -probability
    )


def _brier_loss_value(
    probability: float,
    outcome: int,
) -> float:
    return (
        probability
        - outcome
    ) ** 2


def game_date_from_market_id(
    output_market_id: str,
) -> str:
    match = MARKET_DATE_PATTERN.match(
        output_market_id
    )

    if match is None:
        raise ForecastAuditError(
            "Cannot extract canonical NBA game date from "
            + output_market_id
        )

    compact_date = match.group(1)

    return (
        compact_date[:4]
        + "-"
        + compact_date[4:6]
        + "-"
        + compact_date[6:8]
    )


def build_paired_loss_difference(
    row: ForecastAuditRow,
) -> PairedLossDifference:
    bookmaker_brier = _brier_loss_value(
        row.bookmaker_home_probability,
        row.resolved_home_value,
    )

    polymarket_brier = _brier_loss_value(
        row.polymarket_home_probability,
        row.resolved_home_value,
    )

    bookmaker_log_loss = (
        _binary_log_loss_value(
            row.bookmaker_home_probability,
            row.resolved_home_value,
        )
    )

    polymarket_log_loss = (
        _binary_log_loss_value(
            row.polymarket_home_probability,
            row.resolved_home_value,
        )
    )

    return PairedLossDifference(
        output_market_id=(
            row.output_market_id
        ),
        game_date=game_date_from_market_id(
            row.output_market_id
        ),
        strict_t_minus_60_eligible=(
            row.strict_t_minus_60_eligible
        ),
        brier_difference_polymarket_minus_bookmaker=(
            polymarket_brier
            - bookmaker_brier
        ),
        log_loss_difference_polymarket_minus_bookmaker=(
            polymarket_log_loss
            - bookmaker_log_loss
        ),
    )


def parse_paired_loss_differences(
    rows: Iterable[Dict[str, str]],
) -> List[PairedLossDifference]:
    result = []
    seen_market_ids = set()

    for raw_row in rows:
        parsed = parse_forecast_audit_row(
            raw_row
        )

        if parsed.output_market_id in seen_market_ids:
            raise ForecastAuditError(
                "Duplicate output_market_id: "
                + parsed.output_market_id
            )

        seen_market_ids.add(
            parsed.output_market_id
        )

        result.append(
            build_paired_loss_difference(
                parsed
            )
        )

    if not result:
        raise ForecastAuditError(
            "Cannot estimate uncertainty from an empty dataset"
        )

    return result


def mean(
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
            "Bootstrap inputs must be finite"
        )

    return sum(values) / len(values)


def _linear_quantile(
    sorted_values: Sequence[float],
    probability: float,
) -> float:
    if not sorted_values:
        raise ValueError(
            "Cannot compute a quantile from empty values"
        )

    if not 0.0 <= probability <= 1.0:
        raise ValueError(
            "Quantile probability must be between zero and one"
        )

    if len(sorted_values) == 1:
        return sorted_values[0]

    position = (
        len(sorted_values) - 1
    ) * probability

    lower_index = int(
        math.floor(position)
    )

    upper_index = int(
        math.ceil(position)
    )

    lower_value = sorted_values[
        lower_index
    ]

    upper_value = sorted_values[
        upper_index
    ]

    if lower_index == upper_index:
        return lower_value

    weight = position - lower_index

    return (
        lower_value
        + weight
        * (
            upper_value
            - lower_value
        )
    )


def _interval_from_bootstrap_means(
    bootstrap_means: Sequence[float],
    *,
    confidence_level: float,
    resamples: int,
    seed: int,
) -> BootstrapInterval:
    if not 0.0 < confidence_level < 1.0:
        raise ValueError(
            "Confidence level must be between zero and one"
        )

    sorted_means = sorted(
        bootstrap_means
    )

    tail_probability = (
        1.0
        - confidence_level
    ) / 2.0

    return BootstrapInterval(
        confidence_level=confidence_level,
        lower=_linear_quantile(
            sorted_means,
            tail_probability,
        ),
        upper=_linear_quantile(
            sorted_means,
            1.0 - tail_probability,
        ),
        resamples=resamples,
        seed=seed,
    )


def ordinary_paired_bootstrap_interval(
    values: Sequence[float],
    *,
    confidence_level: float = (
        DEFAULT_CONFIDENCE_LEVEL
    ),
    resamples: int = DEFAULT_RESAMPLES,
    seed: int = DEFAULT_SEED,
) -> BootstrapInterval:
    if not values:
        raise ValueError(
            "Cannot bootstrap empty values"
        )

    if resamples <= 0:
        raise ValueError(
            "Bootstrap resamples must be positive"
        )

    values = list(values)
    mean(values)

    random_generator = random.Random(
        seed
    )

    sample_size = len(values)
    bootstrap_means = []

    for _ in range(resamples):
        sample_total = 0.0

        for _ in range(sample_size):
            sample_total += values[
                random_generator.randrange(
                    sample_size
                )
            ]

        bootstrap_means.append(
            sample_total
            / sample_size
        )

    return _interval_from_bootstrap_means(
        bootstrap_means,
        confidence_level=confidence_level,
        resamples=resamples,
        seed=seed,
    )


def game_date_clustered_bootstrap_interval(
    values_and_dates: Sequence[
        Tuple[float, str]
    ],
    *,
    confidence_level: float = (
        DEFAULT_CONFIDENCE_LEVEL
    ),
    resamples: int = DEFAULT_RESAMPLES,
    seed: int = DEFAULT_SEED,
) -> BootstrapInterval:
    if not values_and_dates:
        raise ValueError(
            "Cannot bootstrap empty clustered values"
        )

    if resamples <= 0:
        raise ValueError(
            "Bootstrap resamples must be positive"
        )

    clusters = {}

    for value, game_date in values_and_dates:
        if not math.isfinite(value):
            raise ValueError(
                "Bootstrap inputs must be finite"
            )

        clusters.setdefault(
            game_date,
            [],
        ).append(
            value
        )

    cluster_dates = sorted(
        clusters
    )

    cluster_count = len(
        cluster_dates
    )

    random_generator = random.Random(
        seed
    )

    bootstrap_means = []

    for _ in range(resamples):
        sample_total = 0.0
        sample_count = 0

        for _ in range(cluster_count):
            sampled_date = cluster_dates[
                random_generator.randrange(
                    cluster_count
                )
            ]

            sampled_values = clusters[
                sampled_date
            ]

            sample_total += sum(
                sampled_values
            )

            sample_count += len(
                sampled_values
            )

        bootstrap_means.append(
            sample_total
            / sample_count
        )

    return _interval_from_bootstrap_means(
        bootstrap_means,
        confidence_level=confidence_level,
        resamples=resamples,
        seed=seed,
    )


def _metric_values(
    rows: Sequence[PairedLossDifference],
    metric_name: str,
) -> List[float]:
    if metric_name == "brier_score":
        return [
            row
            .brier_difference_polymarket_minus_bookmaker
            for row in rows
        ]

    if metric_name == "binary_log_loss":
        return [
            row
            .log_loss_difference_polymarket_minus_bookmaker
            for row in rows
        ]

    raise ValueError(
        "Unknown metric: "
        + metric_name
    )


def audit_paired_uncertainty(
    rows: Sequence[PairedLossDifference],
    *,
    population_name: str,
    confidence_level: float = (
        DEFAULT_CONFIDENCE_LEVEL
    ),
    resamples: int = DEFAULT_RESAMPLES,
    seed: int = DEFAULT_SEED,
) -> List[MetricUncertaintyAudit]:
    if not rows:
        raise ValueError(
            f"{population_name} population is empty"
        )

    cluster_count = len({
        row.game_date
        for row in rows
    })

    result = []

    for metric_name in (
        "brier_score",
        "binary_log_loss",
    ):
        values = _metric_values(
            rows,
            metric_name,
        )

        values_and_dates = [
            (
                value,
                row.game_date,
            )
            for value, row in zip(
                values,
                rows,
            )
        ]

        result.append(
            MetricUncertaintyAudit(
                population_name=(
                    population_name
                ),
                metric_name=metric_name,
                count=len(rows),
                cluster_count=(
                    cluster_count
                ),
                mean_difference_polymarket_minus_bookmaker=(
                    mean(values)
                ),
                ordinary_paired_bootstrap=(
                    ordinary_paired_bootstrap_interval(
                        values,
                        confidence_level=(
                            confidence_level
                        ),
                        resamples=resamples,
                        seed=seed,
                    )
                ),
                game_date_clustered_bootstrap=(
                    game_date_clustered_bootstrap_interval(
                        values_and_dates,
                        confidence_level=(
                            confidence_level
                        ),
                        resamples=resamples,
                        seed=seed,
                    )
                ),
            )
        )

    return result
