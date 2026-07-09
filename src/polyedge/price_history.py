from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class PriceHistorySelection:
    price: Optional[float]
    timestamp: Optional[int]
    age_seconds: Optional[int]
    reason: Optional[str]


def select_latest_price_before_snapshot(
    history: List[Dict[str, Any]],
    snapshot_timestamp: int,
    max_staleness_seconds: int,
) -> PriceHistorySelection:
    if not isinstance(history, list) or len(history) == 0:
        return PriceHistorySelection(
            price=None,
            timestamp=None,
            age_seconds=None,
            reason="no_price_history",
        )

    best_price = None
    best_time = None

    for point in history:
        if not isinstance(point, dict):
            continue

        try:
            point_time = int(point["t"])
            point_price = float(point["p"])
        except Exception:
            continue

        if not (0.0 <= point_price <= 1.0):
            continue

        if point_time > snapshot_timestamp:
            continue

        if best_time is None or point_time > best_time:
            best_time = point_time
            best_price = point_price

    if best_time is None or best_price is None:
        return PriceHistorySelection(
            price=None,
            timestamp=None,
            age_seconds=None,
            reason="no_valid_price_before_snapshot",
        )

    age_seconds = snapshot_timestamp - best_time

    if age_seconds > max_staleness_seconds:
        return PriceHistorySelection(
            price=None,
            timestamp=best_time,
            age_seconds=age_seconds,
            reason="price_too_stale",
        )

    return PriceHistorySelection(
        price=best_price,
        timestamp=best_time,
        age_seconds=age_seconds,
        reason=None,
    )
