import csv
from datetime import datetime, timezone
from pathlib import Path
from statistics import median
from typing import Dict, List


AUDIT_PATH = Path(
    "data/processed/the_odds_api/"
    "historical_event_matches.csv"
)

PLAN_PATH = Path(
    "data/processed/the_odds_api/"
    "historical_odds_request_plan.csv"
)

EXCLUSIONS_PATH = Path(
    "data/processed/the_odds_api/"
    "historical_odds_exclusions.csv"
)


PLAN_COLUMNS = [
    "target_request_time_utc",
    "output_market_id",
    "provider_event_id",
    "provider_home_team",
    "provider_away_team",
    "provider_game_start_utc",
    "manifest_game_start_utc",
    "start_difference_seconds",
    "target_lead_seconds",
]


def parse_utc(value: str) -> datetime:
    text = value.strip().replace(
        "Z",
        "+00:00",
    )

    if text.endswith("+00"):
        text += ":00"

    timestamp = datetime.fromisoformat(text)

    if (
        timestamp.tzinfo is None
        or timestamp.utcoffset() is None
    ):
        raise ValueError(
            f"Timestamp lacks timezone: {value!r}"
        )

    return timestamp.astimezone(timezone.utc)


def write_csv(
    path: Path,
    rows: List[Dict[str, object]],
    fieldnames: List[str],
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with path.open(
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
    with AUDIT_PATH.open(
        encoding="utf-8",
        newline="",
    ) as file:
        audit_rows = list(
            csv.DictReader(file)
        )

    if not audit_rows:
        raise SystemExit(
            "Historical event audit is empty"
        )

    plan_rows: List[
        Dict[str, object]
    ] = []

    exclusion_rows: List[
        Dict[str, object]
    ] = []

    seen_market_ids = set()
    seen_event_ids = set()
    lead_seconds = []

    for row in audit_rows:
        market_id = row[
            "output_market_id"
        ].strip()

        if market_id in seen_market_ids:
            raise ValueError(
                f"Duplicate market ID: {market_id}"
            )

        seen_market_ids.add(market_id)

        if row["match_status"] != "exact":
            exclusion_rows.append({
                "output_market_id": market_id,
                "reason": (
                    "event_identity_not_resolved"
                ),
                "manifest_home_team": row[
                    "manifest_home_team"
                ],
                "manifest_away_team": row[
                    "manifest_away_team"
                ],
                "manifest_game_start_utc": row[
                    "manifest_game_start_utc"
                ],
                "target_request_time_utc": row[
                    "requested_snapshot_utc"
                ],
            })
            continue

        event_id = row[
            "provider_event_id"
        ].strip()

        if not event_id:
            raise ValueError(
                f"Exact match lacks event ID: "
                f"{market_id}"
            )

        if event_id in seen_event_ids:
            raise ValueError(
                f"Provider event reused across "
                f"markets: {event_id}"
            )

        seen_event_ids.add(event_id)

        target_time = parse_utc(
            row["requested_snapshot_utc"]
        )
        provider_start = parse_utc(
            row["provider_game_start_utc"]
        )

        target_lead = int(
            (
                provider_start
                - target_time
            ).total_seconds()
        )

        if target_lead <= 0:
            raise ValueError(
                f"Target is not pregame for "
                f"{market_id}: "
                f"{target_lead} seconds"
            )

        lead_seconds.append(target_lead)

        plan_rows.append({
            "target_request_time_utc": row[
                "requested_snapshot_utc"
            ],
            "output_market_id": market_id,
            "provider_event_id": event_id,
            "provider_home_team": row[
                "provider_home_team"
            ],
            "provider_away_team": row[
                "provider_away_team"
            ],
            "provider_game_start_utc": row[
                "provider_game_start_utc"
            ],
            "manifest_game_start_utc": row[
                "manifest_game_start_utc"
            ],
            "start_difference_seconds": row[
                "start_difference_seconds"
            ],
            "target_lead_seconds": target_lead,
        })

    plan_rows.sort(
        key=lambda row: (
            str(row[
                "target_request_time_utc"
            ]),
            str(row["output_market_id"]),
        )
    )

    exclusion_columns = [
        "output_market_id",
        "reason",
        "manifest_home_team",
        "manifest_away_team",
        "manifest_game_start_utc",
        "target_request_time_utc",
    ]

    write_csv(
        PLAN_PATH,
        plan_rows,
        PLAN_COLUMNS,
    )
    write_csv(
        EXCLUSIONS_PATH,
        exclusion_rows,
        exclusion_columns,
    )

    unique_requests = {
        row["target_request_time_utc"]
        for row in plan_rows
    }

    under_30_minutes = sum(
        value < 30 * 60
        for value in lead_seconds
    )
    under_60_minutes = sum(
        value < 60 * 60
        for value in lead_seconds
    )

    print("HISTORICAL ODDS REQUEST PLAN")
    print("=" * 52)
    print(
        f"Audit markets          : "
        f"{len(audit_rows)}"
    )
    print(
        f"Markets planned        : "
        f"{len(plan_rows)}"
    )
    print(
        f"Markets excluded       : "
        f"{len(exclusion_rows)}"
    )
    print(
        f"Unique API requests    : "
        f"{len(unique_requests)}"
    )

    if lead_seconds:
        print(
            f"Lead min/median/max    : "
            f"{min(lead_seconds)}/"
            f"{median(lead_seconds):g}/"
            f"{max(lead_seconds)} seconds"
        )

    print(
        f"Targets under 30 min   : "
        f"{under_30_minutes}"
    )
    print(
        f"Targets under 60 min   : "
        f"{under_60_minutes}"
    )
    print(
        f"Plan CSV               : "
        f"{PLAN_PATH}"
    )
    print(
        f"Exclusions CSV         : "
        f"{EXCLUSIONS_PATH}"
    )

    if len(plan_rows) + len(
        exclusion_rows
    ) != len(audit_rows):
        raise AssertionError(
            "Plan and exclusions do not "
            "reconcile to audit"
        )


if __name__ == "__main__":
    main()
