from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from polyedge.price_history import (
    select_latest_price_before_snapshot,
)


class PolymarketObservationError(ValueError):
    """Raised when Polymarket observations are inconsistent."""


@dataclass(frozen=True)
class PolymarketOutcomeObservation:
    output_market_id: str
    side: str
    token_id: str
    common_cutoff: datetime

    price: Optional[float]
    observed_at: Optional[datetime]
    age_seconds: Optional[int]

    status: str
    exclusion_reason: Optional[str]


@dataclass(frozen=True)
class PolymarketPairObservation:
    output_market_id: str
    common_cutoff: datetime

    home: PolymarketOutcomeObservation
    away: PolymarketOutcomeObservation

    status: str
    exclusion_reason: Optional[str]

    timestamp_gap_seconds: Optional[int]
    max_price_age_seconds: Optional[int]
    price_sum: Optional[float]
    complementarity_error: Optional[float]


def _require_aware_datetime(
    value: datetime,
    *,
    label: str,
) -> None:
    if (
        value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise PolymarketObservationError(
            f"{label} must be timezone-aware"
        )


def build_polymarket_outcome_observation(
    *,
    output_market_id: str,
    side: str,
    token_id: str,
    common_cutoff: datetime,
    history: List[Dict[str, Any]],
    max_staleness_seconds: int,
) -> PolymarketOutcomeObservation:
    if not output_market_id:
        raise PolymarketObservationError(
            "output_market_id must be non-empty"
        )

    normalized_side = side.upper()

    if normalized_side not in {
        "HOME",
        "AWAY",
    }:
        raise PolymarketObservationError(
            "side must be HOME or AWAY"
        )

    if not token_id:
        raise PolymarketObservationError(
            "token_id must be non-empty"
        )

    _require_aware_datetime(
        common_cutoff,
        label="common_cutoff",
    )

    if common_cutoff.microsecond != 0:
        raise PolymarketObservationError(
            "common_cutoff must have "
            "whole-second precision"
        )

    if max_staleness_seconds < 0:
        raise PolymarketObservationError(
            "max_staleness_seconds cannot "
            "be negative"
        )

    cutoff_utc = common_cutoff.astimezone(
        timezone.utc
    )

    cutoff_timestamp = int(
        cutoff_utc.timestamp()
    )

    selection = (
        select_latest_price_before_snapshot(
            history=history,
            snapshot_timestamp=(
                cutoff_timestamp
            ),
            max_staleness_seconds=(
                max_staleness_seconds
            ),
        )
    )

    observed_at = None

    if selection.timestamp is not None:
        observed_at = datetime.fromtimestamp(
            selection.timestamp,
            tz=timezone.utc,
        )

    if selection.reason is not None:
        return PolymarketOutcomeObservation(
            output_market_id=output_market_id,
            side=normalized_side,
            token_id=token_id,
            common_cutoff=cutoff_utc,
            price=None,
            observed_at=observed_at,
            age_seconds=selection.age_seconds,
            status="excluded",
            exclusion_reason=selection.reason,
        )

    if (
        selection.price is None
        or observed_at is None
        or selection.age_seconds is None
    ):
        raise AssertionError(
            "Eligible price selection is incomplete"
        )

    if observed_at > cutoff_utc:
        raise AssertionError(
            "Polymarket observation occurred "
            "after the common cutoff"
        )

    return PolymarketOutcomeObservation(
        output_market_id=output_market_id,
        side=normalized_side,
        token_id=token_id,
        common_cutoff=cutoff_utc,
        price=selection.price,
        observed_at=observed_at,
        age_seconds=selection.age_seconds,
        status="eligible",
        exclusion_reason=None,
    )


def combine_polymarket_outcomes(
    *,
    home: PolymarketOutcomeObservation,
    away: PolymarketOutcomeObservation,
) -> PolymarketPairObservation:
    if home.output_market_id != away.output_market_id:
        raise PolymarketObservationError(
            "HOME and AWAY market IDs differ"
        )

    if home.side != "HOME":
        raise PolymarketObservationError(
            "home observation must use side=HOME"
        )

    if away.side != "AWAY":
        raise PolymarketObservationError(
            "away observation must use side=AWAY"
        )

    if home.common_cutoff != away.common_cutoff:
        raise PolymarketObservationError(
            "HOME and AWAY cutoffs differ"
        )

    exclusion_parts = []

    if home.status != "eligible":
        exclusion_parts.append(
            "home:"
            + str(home.exclusion_reason)
        )

    if away.status != "eligible":
        exclusion_parts.append(
            "away:"
            + str(away.exclusion_reason)
        )

    if exclusion_parts:
        return PolymarketPairObservation(
            output_market_id=(
                home.output_market_id
            ),
            common_cutoff=home.common_cutoff,
            home=home,
            away=away,
            status="excluded",
            exclusion_reason="|".join(
                exclusion_parts
            ),
            timestamp_gap_seconds=None,
            max_price_age_seconds=None,
            price_sum=None,
            complementarity_error=None,
        )

    if (
        home.price is None
        or away.price is None
        or home.observed_at is None
        or away.observed_at is None
        or home.age_seconds is None
        or away.age_seconds is None
    ):
        raise AssertionError(
            "Eligible pair has incomplete data"
        )

    timestamp_gap_seconds = int(
        abs(
            (
                home.observed_at
                - away.observed_at
            ).total_seconds()
        )
    )

    price_sum = (
        home.price
        + away.price
    )

    return PolymarketPairObservation(
        output_market_id=(
            home.output_market_id
        ),
        common_cutoff=home.common_cutoff,
        home=home,
        away=away,
        status="eligible",
        exclusion_reason=None,
        timestamp_gap_seconds=(
            timestamp_gap_seconds
        ),
        max_price_age_seconds=max(
            home.age_seconds,
            away.age_seconds,
        ),
        price_sum=price_sum,
        complementarity_error=abs(
            price_sum - 1.0
        ),
    )
