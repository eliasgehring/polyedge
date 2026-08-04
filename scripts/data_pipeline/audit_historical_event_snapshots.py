import argparse
import csv
import json
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import median
from typing import Dict, List, Tuple

from polyedge.nba_team_identity import (
    nba_matchup_matches,
)


MANIFEST_PATH = Path(
    "data/diagnostics/polymarket_match_manifest.csv"
)
ARCHIVE_DIR = Path(
    "data/raw/the_odds_api/historical_events"
)
OUTPUT_PATH = Path(
    "data/processed/the_odds_api/"
    "historical_event_matches.csv"
)

SPORT_KEY = "basketball_nba"
DECISION_MINUTES_BEFORE_GAME = 60


def parse_utc(value: str) -> datetime:
    text = value.strip().replace(
        "Z",
        "+00:00",
    )

    if text.endswith("+00"):
        text += ":00"

    timestamp = datetime.fromisoformat(text)

    if timestamp.tzinfo is None:
        raise ValueError(
            f"Timestamp lacks timezone: {value!r}"
        )

    return timestamp.astimezone(timezone.utc)


def format_utc(timestamp: datetime) -> str:
    return (
        timestamp.astimezone(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def capture_paths(
    decision_time: datetime,
) -> Tuple[Path, Path]:
    capture_id = decision_time.strftime(
        "%Y%m%dT%H%M%SZ"
    )

    raw_path = (
        ARCHIVE_DIR
        / f"{SPORT_KEY}_{capture_id}.json"
    )
    metadata_path = (
        ARCHIVE_DIR
        / f"{SPORT_KEY}_{capture_id}.metadata.json"
    )

    return raw_path, metadata_path


def load_snapshot_groups() -> List[
    Tuple[datetime, List[Dict[str, str]]]
]:
    with MANIFEST_PATH.open(
        encoding="utf-8",
        newline="",
    ) as file:
        rows = list(csv.DictReader(file))

    if not rows:
        raise ValueError(
            "Manifest contains no rows"
        )

    groups: Dict[
        datetime,
        List[Dict[str, str]],
    ] = defaultdict(list)

    seen_market_ids = set()

    for row in rows:
        market_id = row[
            "output_market_id"
        ].strip()

        if not market_id:
            raise ValueError(
                "Manifest contains an empty "
                "output_market_id"
            )

        if market_id in seen_market_ids:
            raise ValueError(
                f"Duplicate output_market_id: "
                f"{market_id}"
            )

        seen_market_ids.add(market_id)

        manifest_start = parse_utc(
            row["game_start_time"]
        )
        decision_time = (
            manifest_start
            - timedelta(
                minutes=(
                    DECISION_MINUTES_BEFORE_GAME
                )
            )
        )

        groups[decision_time].append(row)

    return sorted(
        groups.items(),
        key=lambda item: item[0],
    )


def load_json(path: Path):
    with path.open(
        encoding="utf-8"
    ) as file:
        return json.load(file)


def write_results(
    rows: List[Dict[str, object]],
) -> None:
    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    fieldnames = [
        "requested_snapshot_utc",
        "provider_snapshot_utc",
        "provider_snapshot_lag_seconds",
        "output_market_id",
        "manifest_home_team",
        "manifest_away_team",
        "manifest_game_start_utc",
        "match_status",
        "provider_event_id",
        "provider_home_team",
        "provider_away_team",
        "provider_game_start_utc",
        "start_difference_seconds",
    ]

    with OUTPUT_PATH.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
        )
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Audit cached historical event "
            "snapshots against the PolyEdge "
            "manifest."
        )
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=5,
        help=(
            "Number of chronological snapshot "
            "groups to audit."
        ),
    )
    args = parser.parse_args()

    if args.limit <= 0:
        raise SystemExit(
            "--limit must be positive"
        )

    groups = load_snapshot_groups()[
        :args.limit
    ]

    output_rows: List[
        Dict[str, object]
    ] = []

    exact_count = 0
    unmatched_count = 0
    ambiguous_count = 0
    reused_event_count = 0

    start_differences: List[int] = []
    snapshot_lags: List[int] = []

    for index, (
        decision_time,
        manifest_rows,
    ) in enumerate(groups, start=1):
        raw_path, metadata_path = (
            capture_paths(decision_time)
        )

        if not raw_path.exists():
            raise SystemExit(
                f"Missing raw capture: {raw_path}"
            )

        if not metadata_path.exists():
            raise SystemExit(
                f"Missing metadata: {metadata_path}"
            )

        payload = load_json(raw_path)
        metadata = load_json(
            metadata_path
        )

        events = payload.get("data")

        if not isinstance(events, list):
            raise ValueError(
                f"{raw_path} lacks a data list"
            )

        requested_snapshot = (
            metadata.get(
                "requested_snapshot_utc"
            )
        )
        expected_snapshot = format_utc(
            decision_time
        )

        if (
            requested_snapshot
            != expected_snapshot
        ):
            raise ValueError(
                f"Snapshot mismatch: "
                f"{requested_snapshot!r} != "
                f"{expected_snapshot!r}"
            )

        provider_snapshot = str(
            metadata.get(
                "provider_snapshot_utc"
            )
        )
        snapshot_lag = int(
            metadata.get(
                "provider_snapshot_lag_seconds"
            )
        )
        snapshot_lags.append(
            snapshot_lag
        )

        used_provider_event_ids = set()

        snapshot_exact = 0
        snapshot_unmatched = 0
        snapshot_ambiguous = 0
        snapshot_reused = 0

        for manifest_row in manifest_rows:
            matches = []

            for event in events:
                if not isinstance(
                    event,
                    dict,
                ):
                    raise TypeError(
                        "Provider event must be "
                        "a dictionary"
                    )

                if nba_matchup_matches(
                    manifest_home=(
                        manifest_row[
                            "home_outcome"
                        ]
                    ),
                    manifest_away=(
                        manifest_row[
                            "away_outcome"
                        ]
                    ),
                    provider_home=str(
                        event.get(
                            "home_team",
                            "",
                        )
                    ),
                    provider_away=str(
                        event.get(
                            "away_team",
                            "",
                        )
                    ),
                ):
                    matches.append(event)

            manifest_start = parse_utc(
                manifest_row[
                    "game_start_time"
                ]
            )

            base_result: Dict[
                str,
                object,
            ] = {
                "requested_snapshot_utc": (
                    expected_snapshot
                ),
                "provider_snapshot_utc": (
                    provider_snapshot
                ),
                "provider_snapshot_lag_seconds": (
                    snapshot_lag
                ),
                "output_market_id": (
                    manifest_row[
                        "output_market_id"
                    ]
                ),
                "manifest_home_team": (
                    manifest_row[
                        "home_outcome"
                    ]
                ),
                "manifest_away_team": (
                    manifest_row[
                        "away_outcome"
                    ]
                ),
                "manifest_game_start_utc": (
                    format_utc(
                        manifest_start
                    )
                ),
                "provider_event_id": "",
                "provider_home_team": "",
                "provider_away_team": "",
                "provider_game_start_utc": "",
                "start_difference_seconds": "",
            }

            if len(matches) == 0:
                unmatched_count += 1
                snapshot_unmatched += 1

                base_result[
                    "match_status"
                ] = "unmatched"

                output_rows.append(
                    base_result
                )
                continue

            if len(matches) > 1:
                ambiguous_count += 1
                snapshot_ambiguous += 1

                base_result[
                    "match_status"
                ] = "ambiguous"

                output_rows.append(
                    base_result
                )
                continue

            event = matches[0]

            event_id = str(
                event.get("id", "")
            ).strip()

            if not event_id:
                raise ValueError(
                    "Matched provider event "
                    "has no event ID"
                )

            if (
                event_id
                in used_provider_event_ids
            ):
                reused_event_count += 1
                snapshot_reused += 1

                base_result[
                    "match_status"
                ] = "provider_event_reused"

                output_rows.append(
                    base_result
                )
                continue

            used_provider_event_ids.add(
                event_id
            )

            provider_start = parse_utc(
                str(
                    event[
                        "commence_time"
                    ]
                )
            )

            start_difference = int(
                (
                    provider_start
                    - manifest_start
                ).total_seconds()
            )

            start_differences.append(
                start_difference
            )

            exact_count += 1
            snapshot_exact += 1

            base_result.update({
                "match_status": "exact",
                "provider_event_id": (
                    event_id
                ),
                "provider_home_team": (
                    event["home_team"]
                ),
                "provider_away_team": (
                    event["away_team"]
                ),
                "provider_game_start_utc": (
                    format_utc(
                        provider_start
                    )
                ),
                "start_difference_seconds": (
                    start_difference
                ),
            })

            output_rows.append(
                base_result
            )

        print(
            f"[{index}/{len(groups)}] "
            f"{expected_snapshot} "
            f"markets={len(manifest_rows)} "
            f"exact={snapshot_exact} "
            f"unmatched={snapshot_unmatched} "
            f"ambiguous={snapshot_ambiguous} "
            f"reused={snapshot_reused}"
        )

    write_results(output_rows)

    print("\nMATCH AUDIT SUMMARY")
    print("=" * 52)
    print(
        f"Snapshots audited       : "
        f"{len(groups)}"
    )
    print(
        f"Manifest markets audited: "
        f"{len(output_rows)}"
    )
    print(
        f"Exact matches           : "
        f"{exact_count}"
    )
    print(
        f"Unmatched               : "
        f"{unmatched_count}"
    )
    print(
        f"Ambiguous               : "
        f"{ambiguous_count}"
    )
    print(
        f"Provider events reused  : "
        f"{reused_event_count}"
    )

    if snapshot_lags:
        print(
            f"Snapshot lag min/median/max: "
            f"{min(snapshot_lags)}/"
            f"{median(snapshot_lags):g}/"
            f"{max(snapshot_lags)} seconds"
        )

    if start_differences:
        print(
            f"Start delta min/median/max : "
            f"{min(start_differences)}/"
            f"{median(start_differences):g}/"
            f"{max(start_differences)} seconds"
        )

        counts = Counter(
            start_differences
        )

        print("\nSTART DELTA COUNTS")

        for difference, count in sorted(
            counts.items()
        ):
            print(
                f"{difference:>6d}s : "
                f"{count}"
            )

    print(
        f"\nAudit CSV               : "
        f"{OUTPUT_PATH}"
    )

    if (
        unmatched_count
        or ambiguous_count
        or reused_event_count
    ):
        raise SystemExit(
            "Historical event matching audit "
            "failed"
        )


if __name__ == "__main__":
    main()
