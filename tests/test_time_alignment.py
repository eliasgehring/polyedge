from dataclasses import dataclass
from datetime import datetime, timezone

import pytest

from polyedge.time_alignment import (
    DuplicateLatestTimestampError,
    TimeAlignmentError,
    select_latest_at_or_before,
)


UTC = timezone.utc


@dataclass(frozen=True)
class Point:
    timestamp: datetime
    value: float


def utc_time(
    hour: int,
    minute: int,
    second: int = 0,
) -> datetime:
    return datetime(
        2025,
        1,
        1,
        hour,
        minute,
        second,
        tzinfo=UTC,
    )


def select(
    points,
    cutoff,
):
    return select_latest_at_or_before(
        points,
        cutoff=cutoff,
        timestamp_of=(
            lambda point: point.timestamp
        ),
    )


def test_selects_latest_point_before_cutoff():
    points = [
        Point(utc_time(12, 0), 0.40),
        Point(utc_time(12, 4), 0.44),
        Point(utc_time(12, 7), 0.47),
    ]

    result = select(
        points,
        utc_time(12, 5),
    )

    assert result is not None
    assert result.item.value == 0.44
    assert result.observed_at == utc_time(
        12,
        4,
    )
    assert result.age_seconds == 60.0


def test_exact_cutoff_timestamp_is_allowed():
    point = Point(
        utc_time(12, 5),
        0.51,
    )

    result = select(
        [point],
        utc_time(12, 5),
    )

    assert result is not None
    assert result.item == point
    assert result.age_seconds == 0.0


def test_future_points_are_never_selected():
    points = [
        Point(utc_time(12, 4), 0.48),
        Point(utc_time(12, 6), 0.99),
    ]

    result = select(
        points,
        utc_time(12, 5),
    )

    assert result is not None
    assert result.item.value == 0.48


def test_returns_none_when_nothing_existed_by_cutoff():
    points = [
        Point(utc_time(12, 6), 0.55),
    ]

    result = select(
        points,
        utc_time(12, 5),
    )

    assert result is None


def test_duplicate_latest_timestamp_is_rejected():
    points = [
        Point(utc_time(12, 4), 0.48),
        Point(utc_time(12, 4), 0.49),
    ]

    with pytest.raises(
        DuplicateLatestTimestampError
    ):
        select(
            points,
            utc_time(12, 5),
        )


def test_naive_cutoff_is_rejected():
    naive_cutoff = datetime(
        2025,
        1,
        1,
        12,
        5,
    )

    with pytest.raises(
        TimeAlignmentError,
        match="cutoff must be timezone-aware",
    ):
        select(
            [],
            naive_cutoff,
        )


def test_naive_observation_timestamp_is_rejected():
    naive_point = Point(
        datetime(
            2025,
            1,
            1,
            12,
            4,
        ),
        0.48,
    )

    with pytest.raises(
        TimeAlignmentError,
        match=(
            "observation timestamp must be "
            "timezone-aware"
        ),
    ):
        select(
            [naive_point],
            utc_time(12, 5),
        )
