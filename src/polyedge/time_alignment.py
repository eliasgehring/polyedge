from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Generic, Iterable, Optional, TypeVar


T = TypeVar("T")


class TimeAlignmentError(ValueError):
    """Raised when observations cannot be aligned safely."""


class DuplicateLatestTimestampError(
    TimeAlignmentError
):
    """Raised when the latest eligible timestamp is ambiguous."""


@dataclass(frozen=True)
class TimedSelection(Generic[T]):
    item: T
    cutoff: datetime
    observed_at: datetime
    age_seconds: float


def _require_aware_datetime(
    value: datetime,
    *,
    label: str,
) -> None:
    if (
        value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise TimeAlignmentError(
            f"{label} must be timezone-aware"
        )


def select_latest_at_or_before(
    items: Iterable[T],
    *,
    cutoff: datetime,
    timestamp_of: Callable[[T], datetime],
) -> Optional[TimedSelection[T]]:
    """
    Select the unique latest observation available at cutoff.

    Future observations are never eligible. None is returned when
    no observation existed by the cutoff.
    """
    _require_aware_datetime(
        cutoff,
        label="cutoff",
    )

    eligible = []

    for item in items:
        observed_at = timestamp_of(item)

        _require_aware_datetime(
            observed_at,
            label="observation timestamp",
        )

        if observed_at <= cutoff:
            eligible.append(
                (observed_at, item)
            )

    if not eligible:
        return None

    latest_timestamp = max(
        observed_at
        for observed_at, _ in eligible
    )

    latest_items = [
        item
        for observed_at, item in eligible
        if observed_at == latest_timestamp
    ]

    if len(latest_items) != 1:
        raise DuplicateLatestTimestampError(
            "Multiple observations share the "
            f"latest eligible timestamp: "
            f"{latest_timestamp.isoformat()}"
        )

    age_seconds = (
        cutoff - latest_timestamp
    ).total_seconds()

    if age_seconds < 0:
        raise AssertionError(
            "Selected observation occurred "
            "after the cutoff"
        )

    return TimedSelection(
        item=latest_items[0],
        cutoff=cutoff,
        observed_at=latest_timestamp,
        age_seconds=age_seconds,
    )
