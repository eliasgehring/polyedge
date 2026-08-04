from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from polyedge.time_alignment import (
    DuplicateLatestTimestampError,
    TimeAlignmentError,
    select_latest_at_or_before,
)


@dataclass(frozen=True)
class PriceHistorySelection:
    price: Optional[float]
    timestamp: Optional[int]
    age_seconds: Optional[int]
    reason: Optional[str]


@dataclass(frozen=True)
class _ValidPricePoint:
    timestamp: int
    price: float


def _unix_utc(timestamp: int) -> datetime:
    return datetime.fromtimestamp(
        timestamp,
        tz=timezone.utc,
    )


def select_latest_price_before_snapshot(
    history: List[Dict[str, Any]],
    snapshot_timestamp: int,
    max_staleness_seconds: int,
) -> PriceHistorySelection:
    """
    Select the latest valid Polymarket price available at or before
    the common observation cutoff.

    Identical duplicate points are collapsed. Conflicting prices at
    the same latest timestamp are rejected as ambiguous.
    """
    if not isinstance(history, list) or not history:
        return PriceHistorySelection(
            price=None,
            timestamp=None,
            age_seconds=None,
            reason="no_price_history",
        )

    valid_points_by_value = {}

    for point in history:
        if not isinstance(point, dict):
            continue

        try:
            point_time = int(point["t"])
            point_price = float(point["p"])
        except (KeyError, TypeError, ValueError):
            continue

        if point_time < 0:
            continue

        if not 0.0 <= point_price <= 1.0:
            continue

        key = (
            point_time,
            point_price,
        )

        valid_points_by_value[key] = (
            _ValidPricePoint(
                timestamp=point_time,
                price=point_price,
            )
        )

    valid_points = list(
        valid_points_by_value.values()
    )

    if not valid_points:
        return PriceHistorySelection(
            price=None,
            timestamp=None,
            age_seconds=None,
            reason="no_valid_price_before_snapshot",
        )

    try:
        selection = select_latest_at_or_before(
            valid_points,
            cutoff=_unix_utc(
                snapshot_timestamp
            ),
            timestamp_of=lambda point: _unix_utc(
                point.timestamp
            ),
        )
    except DuplicateLatestTimestampError:
        return PriceHistorySelection(
            price=None,
            timestamp=None,
            age_seconds=None,
            reason=(
                "conflicting_prices_at_latest_timestamp"
            ),
        )
    except (
        TimeAlignmentError,
        OverflowError,
        OSError,
        ValueError,
    ):
        return PriceHistorySelection(
            price=None,
            timestamp=None,
            age_seconds=None,
            reason="invalid_snapshot_timestamp",
        )

    if selection is None:
        return PriceHistorySelection(
            price=None,
            timestamp=None,
            age_seconds=None,
            reason="no_valid_price_before_snapshot",
        )

    point = selection.item
    age_seconds = int(
        selection.age_seconds
    )

    if age_seconds > max_staleness_seconds:
        return PriceHistorySelection(
            price=None,
            timestamp=point.timestamp,
            age_seconds=age_seconds,
            reason="price_too_stale",
        )

    return PriceHistorySelection(
        price=point.price,
        timestamp=point.timestamp,
        age_seconds=age_seconds,
        reason=None,
    )
