from datetime import datetime, timezone

from polyedge.time_semantics import (
    choose_aligned_snapshot_time,
)


def test_uses_bookmaker_timestamp_as_snapshot_time():
    result = choose_aligned_snapshot_time(
        bookmaker_timestamp="2024-10-22T12:00:00",
        game_start_time="2024-10-22 23:30:00+00",
    )

    assert result.reason is None
    assert result.snapshot_time == datetime(
        2024,
        10,
        22,
        12,
        0,
        tzinfo=timezone.utc,
    )


def test_snapshot_after_game_is_rejected():
    result = choose_aligned_snapshot_time(
        bookmaker_timestamp="2024-10-23T00:00:00Z",
        game_start_time="2024-10-22T23:30:00Z",
    )

    assert result.snapshot_time is None
    assert (
        result.reason
        == "bookmaker_snapshot_not_before_game"
    )


def test_snapshot_at_game_start_is_rejected():
    result = choose_aligned_snapshot_time(
        bookmaker_timestamp="2024-10-22T23:30:00Z",
        game_start_time="2024-10-22T23:30:00Z",
    )

    assert result.snapshot_time is None
    assert (
        result.reason
        == "bookmaker_snapshot_not_before_game"
    )


def test_invalid_game_start_is_rejected():
    result = choose_aligned_snapshot_time(
        bookmaker_timestamp="2024-10-22T12:00:00Z",
        game_start_time="not-a-time",
    )

    assert result.snapshot_time is None
    assert result.reason == "invalid_game_start_time"
