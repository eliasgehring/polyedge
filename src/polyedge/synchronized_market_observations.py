from dataclasses import dataclass
from datetime import datetime, timezone
import math
from typing import Mapping

from polyedge.polymarket_policy import (
    COMPLEMENTARITY_TOLERANCE,
    EXECUTION_SEMANTICS,
    MAX_HISTORY_POINT_LAG_SECONDS,
    POLICY_VERSION,
    SOURCE_SEMANTICS,
)


class SynchronizedObservationError(ValueError):
    """Raised when synchronized source rows violate V2 semantics."""


@dataclass(frozen=True)
class SynchronizedMarketObservation:
    output_market_id: str
    observation_time: datetime

    provider_event_id: str
    target_request_time: datetime
    provider_snapshot_lag_seconds: int
    provider_commence_time_at_observation: datetime
    provider_home_team: str
    provider_away_team: str

    bookmaker_home_fair_probability: float
    bookmaker_away_fair_probability: float
    bookmaker_count: int
    oldest_quote_age_seconds: int
    newest_quote_age_seconds: int
    seconds_before_provider_start: int
    strict_t_minus_60_eligible: bool

    polymarket_market_id: str
    condition_id: str
    market_slug: str
    home_outcome: str
    away_outcome: str
    home_token_id: str
    away_token_id: str

    polymarket_history_time: datetime
    history_point_lag_seconds: int
    polymarket_home_probability: float
    polymarket_away_probability: float

    home_probability_edge: float
    away_probability_edge: float

    resolved_home_value: int
    resolved_away_value: int
    resolution_source: str
    settlement_time_status: str

    source_semantics: str
    execution_semantics: str
    policy_version: str


def _required_text(
    row: Mapping[str, str],
    field_name: str,
) -> str:
    value = str(row.get(field_name, "")).strip()

    if not value:
        raise SynchronizedObservationError(
            f"{field_name} must be non-empty"
        )

    return value


def _parse_utc(
    row: Mapping[str, str],
    field_name: str,
) -> datetime:
    value = _required_text(row, field_name)

    try:
        timestamp = datetime.fromisoformat(
            value.replace("Z", "+00:00")
        )
    except ValueError as exc:
        raise SynchronizedObservationError(
            f"{field_name} must be an ISO-8601 timestamp"
        ) from exc

    if (
        timestamp.tzinfo is None
        or timestamp.utcoffset() is None
    ):
        raise SynchronizedObservationError(
            f"{field_name} must be timezone-aware"
        )

    return timestamp.astimezone(timezone.utc)


def _parse_int(
    row: Mapping[str, str],
    field_name: str,
) -> int:
    value = _required_text(row, field_name)

    try:
        return int(value)
    except ValueError as exc:
        raise SynchronizedObservationError(
            f"{field_name} must be an integer"
        ) from exc


def _parse_nonnegative_int(
    row: Mapping[str, str],
    field_name: str,
) -> int:
    value = _parse_int(row, field_name)

    if value < 0:
        raise SynchronizedObservationError(
            f"{field_name} cannot be negative"
        )

    return value


def _parse_probability(
    row: Mapping[str, str],
    field_name: str,
) -> float:
    value = _required_text(row, field_name)

    try:
        probability = float(value)
    except ValueError as exc:
        raise SynchronizedObservationError(
            f"{field_name} must be numeric"
        ) from exc

    if not 0.0 <= probability <= 1.0:
        raise SynchronizedObservationError(
            f"{field_name} must be between zero and one"
        )

    return probability


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

    raise SynchronizedObservationError(
        f"{field_name} must be true or false"
    )


def _require_same_market_id(
    *,
    bookmaker_row: Mapping[str, str],
    identity_row: Mapping[str, str],
    polymarket_row: Mapping[str, str],
) -> str:
    values = {
        _required_text(
            bookmaker_row,
            "output_market_id",
        ),
        _required_text(
            identity_row,
            "output_market_id",
        ),
        _required_text(
            polymarket_row,
            "output_market_id",
        ),
    }

    if len(values) != 1:
        raise SynchronizedObservationError(
            "Source rows have different output_market_id values"
        )

    return values.pop()


def build_synchronized_market_observation(
    *,
    bookmaker_row: Mapping[str, str],
    identity_row: Mapping[str, str],
    polymarket_row: Mapping[str, str],
) -> SynchronizedMarketObservation:
    market_id = _require_same_market_id(
        bookmaker_row=bookmaker_row,
        identity_row=identity_row,
        polymarket_row=polymarket_row,
    )

    if _required_text(bookmaker_row, "status") != "eligible":
        raise SynchronizedObservationError(
            "Bookmaker row must be eligible"
        )

    for field_name in (
        "home_status",
        "away_status",
        "pair_status",
    ):
        if (
            _required_text(
                polymarket_row,
                field_name,
            )
            != "eligible"
        ):
            raise SynchronizedObservationError(
                f"{field_name} must be eligible"
            )

    observation_time = _parse_utc(
        bookmaker_row,
        "observation_time_utc",
    )

    audit_observation_time = _parse_utc(
        polymarket_row,
        "observation_time_utc",
    )

    if observation_time != audit_observation_time:
        raise SynchronizedObservationError(
            "Bookmaker and Polymarket observation times differ"
        )

    target_request_time = _parse_utc(
        bookmaker_row,
        "target_request_time_utc",
    )

    provider_snapshot_lag_seconds = (
        _parse_nonnegative_int(
            bookmaker_row,
            "provider_snapshot_lag_seconds",
        )
    )

    observed_snapshot_lag = int(
        (
            target_request_time
            - observation_time
        ).total_seconds()
    )

    if (
        observed_snapshot_lag
        != provider_snapshot_lag_seconds
    ):
        raise SynchronizedObservationError(
            "Provider snapshot lag does not reconcile"
        )

    provider_commence_time = _parse_utc(
        bookmaker_row,
        "provider_commence_time_at_observation_utc",
    )

    if observation_time >= provider_commence_time:
        raise SynchronizedObservationError(
            "Observation must be pregame"
        )

    home_token_id = _required_text(
        identity_row,
        "home_token_id",
    )

    away_token_id = _required_text(
        identity_row,
        "away_token_id",
    )

    if home_token_id == away_token_id:
        raise SynchronizedObservationError(
            "HOME and AWAY token IDs must differ"
        )

    if (
        _required_text(
            polymarket_row,
            "home_token_id",
        )
        != home_token_id
    ):
        raise SynchronizedObservationError(
            "HOME token ID does not reconcile"
        )

    if (
        _required_text(
            polymarket_row,
            "away_token_id",
        )
        != away_token_id
    ):
        raise SynchronizedObservationError(
            "AWAY token ID does not reconcile"
        )

    home_history_time = _parse_utc(
        polymarket_row,
        "home_price_time_utc",
    )

    away_history_time = _parse_utc(
        polymarket_row,
        "away_price_time_utc",
    )

    if home_history_time != away_history_time:
        raise SynchronizedObservationError(
            "HOME and AWAY history timestamps differ"
        )

    if home_history_time > observation_time:
        raise SynchronizedObservationError(
            "Polymarket history point occurred after cutoff"
        )

    timestamp_gap_seconds = _parse_nonnegative_int(
        polymarket_row,
        "timestamp_gap_seconds",
    )

    if timestamp_gap_seconds != 0:
        raise SynchronizedObservationError(
            "Latest HOME and AWAY timestamps must be identical"
        )

    computed_lag_seconds = int(
        (
            observation_time
            - home_history_time
        ).total_seconds()
    )

    home_lag_seconds = _parse_nonnegative_int(
        polymarket_row,
        "home_price_age_seconds",
    )

    away_lag_seconds = _parse_nonnegative_int(
        polymarket_row,
        "away_price_age_seconds",
    )

    max_lag_seconds = _parse_nonnegative_int(
        polymarket_row,
        "max_price_age_seconds",
    )

    if (
        computed_lag_seconds != home_lag_seconds
        or computed_lag_seconds != away_lag_seconds
        or computed_lag_seconds != max_lag_seconds
    ):
        raise SynchronizedObservationError(
            "History-point lag fields do not reconcile"
        )

    if (
        computed_lag_seconds
        > MAX_HISTORY_POINT_LAG_SECONDS
    ):
        raise SynchronizedObservationError(
            "Polymarket history point exceeds frozen lag policy"
        )

    bookmaker_home = _parse_probability(
        bookmaker_row,
        "home_fair_prob",
    )

    bookmaker_away = _parse_probability(
        bookmaker_row,
        "away_fair_prob",
    )

    if not math.isclose(
        bookmaker_home + bookmaker_away,
        1.0,
        abs_tol=1e-12,
    ):
        raise SynchronizedObservationError(
            "Bookmaker probabilities are not complementary"
        )

    polymarket_home = _parse_probability(
        polymarket_row,
        "home_price",
    )

    polymarket_away = _parse_probability(
        polymarket_row,
        "away_price",
    )

    try:
        recorded_price_sum = float(
            _required_text(
                polymarket_row,
                "price_sum",
            )
        )
        recorded_complementarity_error = float(
            _required_text(
                polymarket_row,
                "complementarity_error",
            )
        )
    except ValueError as exc:
        raise SynchronizedObservationError(
            "Polymarket audit metrics must be numeric"
        ) from exc

    computed_price_sum = (
        polymarket_home
        + polymarket_away
    )

    if not math.isclose(
        recorded_price_sum,
        computed_price_sum,
        abs_tol=1e-12,
    ):
        raise SynchronizedObservationError(
            "Recorded Polymarket price sum does not reconcile"
        )

    computed_complementarity_error = abs(
        computed_price_sum - 1.0
    )

    if not math.isclose(
        recorded_complementarity_error,
        computed_complementarity_error,
        abs_tol=1e-12,
    ):
        raise SynchronizedObservationError(
            "Recorded complementarity error does not reconcile"
        )

    if (
        computed_complementarity_error
        > COMPLEMENTARITY_TOLERANCE
    ):
        raise SynchronizedObservationError(
            "Polymarket probabilities violate frozen policy"
        )

    resolved_home_value = _parse_int(
        identity_row,
        "resolved_home_value",
    )

    resolved_away_value = _parse_int(
        identity_row,
        "resolved_away_value",
    )

    if (
        resolved_home_value not in {0, 1}
        or resolved_away_value not in {0, 1}
        or resolved_home_value
        + resolved_away_value
        != 1
    ):
        raise SynchronizedObservationError(
            "Resolution must be one complementary binary outcome"
        )

    bookmaker_count = _parse_nonnegative_int(
        bookmaker_row,
        "bookmaker_count",
    )

    if bookmaker_count < 3:
        raise SynchronizedObservationError(
            "Eligible observation has fewer than three books"
        )

    oldest_quote_age_seconds = (
        _parse_nonnegative_int(
            bookmaker_row,
            "oldest_quote_age_seconds",
        )
    )

    newest_quote_age_seconds = (
        _parse_nonnegative_int(
            bookmaker_row,
            "newest_quote_age_seconds",
        )
    )

    if (
        newest_quote_age_seconds
        > oldest_quote_age_seconds
    ):
        raise SynchronizedObservationError(
            "Newest quote cannot be older than oldest quote"
        )

    seconds_before_provider_start = (
        _parse_nonnegative_int(
            bookmaker_row,
            "seconds_before_provider_start",
        )
    )

    observed_seconds_before_start = int(
        (
            provider_commence_time
            - observation_time
        ).total_seconds()
    )

    if (
        observed_seconds_before_start
        != seconds_before_provider_start
    ):
        raise SynchronizedObservationError(
            "Seconds-before-start field does not reconcile"
        )

    return SynchronizedMarketObservation(
        output_market_id=market_id,
        observation_time=observation_time,
        provider_event_id=_required_text(
            bookmaker_row,
            "provider_event_id",
        ),
        target_request_time=target_request_time,
        provider_snapshot_lag_seconds=(
            provider_snapshot_lag_seconds
        ),
        provider_commence_time_at_observation=(
            provider_commence_time
        ),
        provider_home_team=_required_text(
            bookmaker_row,
            "provider_home_team",
        ),
        provider_away_team=_required_text(
            bookmaker_row,
            "provider_away_team",
        ),
        bookmaker_home_fair_probability=(
            bookmaker_home
        ),
        bookmaker_away_fair_probability=(
            bookmaker_away
        ),
        bookmaker_count=bookmaker_count,
        oldest_quote_age_seconds=(
            oldest_quote_age_seconds
        ),
        newest_quote_age_seconds=(
            newest_quote_age_seconds
        ),
        seconds_before_provider_start=(
            seconds_before_provider_start
        ),
        strict_t_minus_60_eligible=_parse_bool(
            bookmaker_row,
            "strict_t_minus_60_eligible",
        ),
        polymarket_market_id=_required_text(
            identity_row,
            "polymarket_market_id",
        ),
        condition_id=_required_text(
            identity_row,
            "condition_id",
        ),
        market_slug=_required_text(
            identity_row,
            "market_slug",
        ),
        home_outcome=_required_text(
            identity_row,
            "home_outcome",
        ),
        away_outcome=_required_text(
            identity_row,
            "away_outcome",
        ),
        home_token_id=home_token_id,
        away_token_id=away_token_id,
        polymarket_history_time=(
            home_history_time
        ),
        history_point_lag_seconds=(
            computed_lag_seconds
        ),
        polymarket_home_probability=(
            polymarket_home
        ),
        polymarket_away_probability=(
            polymarket_away
        ),
        home_probability_edge=(
            bookmaker_home
            - polymarket_home
        ),
        away_probability_edge=(
            bookmaker_away
            - polymarket_away
        ),
        resolved_home_value=(
            resolved_home_value
        ),
        resolved_away_value=(
            resolved_away_value
        ),
        resolution_source=_required_text(
            identity_row,
            "resolution_source",
        ),
        settlement_time_status=_required_text(
            identity_row,
            "settlement_time_status",
        ),
        source_semantics=SOURCE_SEMANTICS,
        execution_semantics=EXECUTION_SEMANTICS,
        policy_version=POLICY_VERSION,
    )
