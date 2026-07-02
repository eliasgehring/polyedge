from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional


@dataclass(frozen=True)
class SnapshotTimeResult:
    snapshot_time: Optional[datetime]
    game_start_time: Optional[datetime]
    reason: Optional[str]


def parse_utc_timestamp(value: str) -> Optional[datetime]:
    text = str(value).strip()

    if not text:
        return None

    if text.endswith("Z"):
        text = text[:-1] + "+00:00"

    # Polymarket may emit offsets such as "+00".
    # Python 3.9 expects "+00:00".
    elif (
        len(text) >= 3
        and text[-3] in {"+", "-"}
        and text[-2:].isdigit()
    ):
        text = text + ":00"

    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)

    return parsed.astimezone(timezone.utc)


def choose_aligned_snapshot_time(
    bookmaker_timestamp: str,
    game_start_time: str,
) -> SnapshotTimeResult:
    snapshot_time = parse_utc_timestamp(
        bookmaker_timestamp
    )

    if snapshot_time is None:
        return SnapshotTimeResult(
            snapshot_time=None,
            game_start_time=None,
            reason="invalid_bookmaker_timestamp",
        )

    parsed_game_start = parse_utc_timestamp(
        game_start_time
    )

    if parsed_game_start is None:
        return SnapshotTimeResult(
            snapshot_time=None,
            game_start_time=None,
            reason="invalid_game_start_time",
        )

    if snapshot_time >= parsed_game_start:
        return SnapshotTimeResult(
            snapshot_time=None,
            game_start_time=parsed_game_start,
            reason="bookmaker_snapshot_not_before_game",
        )

    return SnapshotTimeResult(
        snapshot_time=snapshot_time,
        game_start_time=parsed_game_start,
        reason=None,
    )
