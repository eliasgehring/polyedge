from dataclasses import dataclass
import math
from typing import Dict, Iterable, List, Mapping, Sequence

from polyedge.forecast_scoring import (
    CalibrationBin,
    ForecastScore,
    fixed_width_calibration_bins,
    score_binary_forecasts,
)
from polyedge.polymarket_policy import (
    EXECUTION_SEMANTICS,
    POLICY_VERSION,
    SOURCE_SEMANTICS,
)


PROBABILITY_TOLERANCE = 1e-12
EDGE_TOLERANCE = 1e-12


class ForecastAuditError(ValueError):
    """Raised when synchronized forecast rows violate audit semantics."""


@dataclass(frozen=True)
class ForecastAuditRow:
    output_market_id: str
    strict_t_minus_60_eligible: bool
    bookmaker_home_probability: float
    polymarket_home_probability: float
    resolved_home_value: int


@dataclass(frozen=True)
class ForecastSourceAudit:
    source_name: str
    score: ForecastScore
    calibration_bins: List[CalibrationBin]


@dataclass(frozen=True)
class ForecastPopulationAudit:
    population_name: str
    count: int
    bookmaker: ForecastSourceAudit
    polymarket: ForecastSourceAudit
    brier_score_difference_polymarket_minus_bookmaker: float
    log_loss_difference_polymarket_minus_bookmaker: float


def _required_text(
    row: Mapping[str, str],
    field_name: str,
) -> str:
    value = str(row.get(field_name, "")).strip()

    if not value:
        raise ForecastAuditError(
            f"{field_name} must be non-empty"
        )

    return value


def _parse_probability(
    row: Mapping[str, str],
    field_name: str,
) -> float:
    value = _required_text(
        row,
        field_name,
    )

    try:
        probability = float(value)
    except ValueError as exc:
        raise ForecastAuditError(
            f"{field_name} must be numeric"
        ) from exc

    if not math.isfinite(probability):
        raise ForecastAuditError(
            f"{field_name} must be finite"
        )

    if not 0.0 <= probability <= 1.0:
        raise ForecastAuditError(
            f"{field_name} must be between zero and one"
        )

    return probability


def _parse_binary(
    row: Mapping[str, str],
    field_name: str,
) -> int:
    value = _required_text(
        row,
        field_name,
    )

    try:
        parsed = int(value)
    except ValueError as exc:
        raise ForecastAuditError(
            f"{field_name} must be an integer"
        ) from exc

    if parsed not in (0, 1):
        raise ForecastAuditError(
            f"{field_name} must be binary"
        )

    return parsed


def _parse_bool(
    row: Mapping[str, str],
    field_name: str,
) -> bool:
    value = _required_text(
        row,
        field_name,
    ).lower()

    if value == "true":
        return True

    if value == "false":
        return False

    raise ForecastAuditError(
        f"{field_name} must be true or false"
    )


def _assert_close(
    *,
    actual: float,
    expected: float,
    tolerance: float,
    message: str,
) -> None:
    if not math.isclose(
        actual,
        expected,
        rel_tol=0.0,
        abs_tol=tolerance,
    ):
        raise ForecastAuditError(
            message
        )


def parse_forecast_audit_row(
    row: Mapping[str, str],
) -> ForecastAuditRow:
    market_id = _required_text(
        row,
        "output_market_id",
    )

    if (
        _required_text(
            row,
            "source_semantics",
        )
        != SOURCE_SEMANTICS
    ):
        raise ForecastAuditError(
            f"{market_id}: unexpected source semantics"
        )

    if (
        _required_text(
            row,
            "execution_semantics",
        )
        != EXECUTION_SEMANTICS
    ):
        raise ForecastAuditError(
            f"{market_id}: unexpected execution semantics"
        )

    if (
        _required_text(
            row,
            "policy_version",
        )
        != POLICY_VERSION
    ):
        raise ForecastAuditError(
            f"{market_id}: unexpected policy version"
        )

    bookmaker_home = _parse_probability(
        row,
        "bookmaker_home_fair_probability",
    )

    bookmaker_away = _parse_probability(
        row,
        "bookmaker_away_fair_probability",
    )

    polymarket_home = _parse_probability(
        row,
        "polymarket_home_probability",
    )

    polymarket_away = _parse_probability(
        row,
        "polymarket_away_probability",
    )

    _assert_close(
        actual=(
            bookmaker_home
            + bookmaker_away
        ),
        expected=1.0,
        tolerance=PROBABILITY_TOLERANCE,
        message=(
            f"{market_id}: bookmaker probabilities "
            "are not complementary"
        ),
    )

    _assert_close(
        actual=(
            polymarket_home
            + polymarket_away
        ),
        expected=1.0,
        tolerance=PROBABILITY_TOLERANCE,
        message=(
            f"{market_id}: Polymarket probabilities "
            "are not complementary"
        ),
    )

    recorded_home_edge = float(
        _required_text(
            row,
            "home_probability_edge",
        )
    )

    recorded_away_edge = float(
        _required_text(
            row,
            "away_probability_edge",
        )
    )

    expected_home_edge = (
        bookmaker_home
        - polymarket_home
    )

    expected_away_edge = (
        bookmaker_away
        - polymarket_away
    )

    _assert_close(
        actual=recorded_home_edge,
        expected=expected_home_edge,
        tolerance=EDGE_TOLERANCE,
        message=(
            f"{market_id}: HOME edge does not reconcile"
        ),
    )

    _assert_close(
        actual=recorded_away_edge,
        expected=expected_away_edge,
        tolerance=EDGE_TOLERANCE,
        message=(
            f"{market_id}: AWAY edge does not reconcile"
        ),
    )

    _assert_close(
        actual=(
            recorded_home_edge
            + recorded_away_edge
        ),
        expected=0.0,
        tolerance=EDGE_TOLERANCE,
        message=(
            f"{market_id}: HOME and AWAY edges "
            "are not exact opposites"
        ),
    )

    resolved_home = _parse_binary(
        row,
        "resolved_home_value",
    )

    resolved_away = _parse_binary(
        row,
        "resolved_away_value",
    )

    if resolved_home + resolved_away != 1:
        raise ForecastAuditError(
            f"{market_id}: resolution is not complementary"
        )

    return ForecastAuditRow(
        output_market_id=market_id,
        strict_t_minus_60_eligible=(
            _parse_bool(
                row,
                "strict_t_minus_60_eligible",
            )
        ),
        bookmaker_home_probability=(
            bookmaker_home
        ),
        polymarket_home_probability=(
            polymarket_home
        ),
        resolved_home_value=(
            resolved_home
        ),
    )


def _audit_population(
    *,
    population_name: str,
    rows: Sequence[ForecastAuditRow],
) -> ForecastPopulationAudit:
    if not rows:
        raise ForecastAuditError(
            f"{population_name} population is empty"
        )

    outcomes = [
        row.resolved_home_value
        for row in rows
    ]

    bookmaker_probabilities = [
        row.bookmaker_home_probability
        for row in rows
    ]

    polymarket_probabilities = [
        row.polymarket_home_probability
        for row in rows
    ]

    bookmaker_score = (
        score_binary_forecasts(
            bookmaker_probabilities,
            outcomes,
        )
    )

    polymarket_score = (
        score_binary_forecasts(
            polymarket_probabilities,
            outcomes,
        )
    )

    bookmaker_audit = ForecastSourceAudit(
        source_name="bookmaker",
        score=bookmaker_score,
        calibration_bins=(
            fixed_width_calibration_bins(
                bookmaker_probabilities,
                outcomes,
            )
        ),
    )

    polymarket_audit = ForecastSourceAudit(
        source_name="polymarket",
        score=polymarket_score,
        calibration_bins=(
            fixed_width_calibration_bins(
                polymarket_probabilities,
                outcomes,
            )
        ),
    )

    return ForecastPopulationAudit(
        population_name=population_name,
        count=len(rows),
        bookmaker=bookmaker_audit,
        polymarket=polymarket_audit,
        brier_score_difference_polymarket_minus_bookmaker=(
            polymarket_score.brier_score
            - bookmaker_score.brier_score
        ),
        log_loss_difference_polymarket_minus_bookmaker=(
            polymarket_score.binary_log_loss
            - bookmaker_score.binary_log_loss
        ),
    )


def audit_forecast_rows(
    rows: Iterable[Mapping[str, str]],
) -> List[ForecastPopulationAudit]:
    parsed_rows = []
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

        parsed_rows.append(
            parsed
        )

    if not parsed_rows:
        raise ForecastAuditError(
            "Cannot audit an empty synchronized dataset"
        )

    strict_rows = [
        row
        for row in parsed_rows
        if row.strict_t_minus_60_eligible
    ]

    return [
        _audit_population(
            population_name="all_synchronized",
            rows=parsed_rows,
        ),
        _audit_population(
            population_name="strict_t_minus_60",
            rows=strict_rows,
        ),
    ]
