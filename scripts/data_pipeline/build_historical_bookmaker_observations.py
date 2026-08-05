import csv
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

from polyedge.bookmaker_odds import (
    MoneylineQuoteRejection,
    parse_the_odds_api_moneylines,
)
from polyedge.bookmaker_policy import (
    APPROVED_BOOKMAKERS,
)
from polyedge.historical_bookmaker_observations import (
    HistoricalBookmakerObservation,
    build_historical_bookmaker_observation,
)


PLAN_PATH = Path(
    "data/processed/the_odds_api/"
    "historical_odds_request_plan.csv"
)

ARCHIVE_DIR = Path(
    "data/raw/the_odds_api/historical"
)

OUTPUT_PATH = Path(
    "data/processed/the_odds_api/"
    "historical_bookmaker_observations.csv"
)


OUTPUT_COLUMNS = [
    "output_market_id",
    "provider_event_id",
    "target_request_time_utc",
    "observation_time_utc",
    "provider_snapshot_lag_seconds",
    "provider_commence_time_at_observation_utc",
    "provider_home_team",
    "provider_away_team",
    "home_fair_prob",
    "away_fair_prob",
    "bookmaker_count",
    "invalid_quote_count",
    "invalid_approved_quote_count",
    "invalid_quote_rejections_json",
    "bookmaker_keys_json",
    "quote_timestamps_json",
    "oldest_quote_age_seconds",
    "newest_quote_age_seconds",
    "seconds_before_provider_start",
    "pregame_at_observation",
    "strict_t_minus_60_eligible",
    "status",
    "exclusion_reason",
    "raw_file",
    "raw_sha256",
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


def format_utc(
    timestamp: datetime,
) -> str:
    return (
        timestamp.astimezone(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as file:
        for chunk in iter(
            lambda: file.read(
                1024 * 1024
            ),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def capture_paths(
    target_time: datetime,
) -> Tuple[Path, Path]:
    capture_id = target_time.strftime(
        "%Y%m%dT%H%M%SZ"
    )

    raw_path = (
        ARCHIVE_DIR
        / f"basketball_nba_{capture_id}.json"
    )

    metadata_path = (
        ARCHIVE_DIR
        / (
            f"basketball_nba_{capture_id}"
            f".metadata.json"
        )
    )

    return raw_path, metadata_path


def load_plan_groups() -> List[
    Tuple[
        datetime,
        List[Dict[str, str]],
    ]
]:
    with PLAN_PATH.open(
        encoding="utf-8",
        newline="",
    ) as file:
        rows = list(csv.DictReader(file))

    if not rows:
        raise ValueError(
            "Historical odds request plan is empty"
        )

    groups = defaultdict(list)
    seen_market_ids = set()

    for row in rows:
        market_id = row[
            "output_market_id"
        ].strip()

        if market_id in seen_market_ids:
            raise ValueError(
                f"Duplicate market ID: {market_id}"
            )

        seen_market_ids.add(market_id)

        target_time = parse_utc(
            row["target_request_time_utc"]
        )

        groups[target_time].append(row)

    return sorted(
        groups.items(),
        key=lambda item: item[0],
    )


def serialize_observation(
    observation: HistoricalBookmakerObservation,
    *,
    raw_path: Path,
    raw_sha256: str,
    invalid_quote_rejections: Sequence[
        MoneylineQuoteRejection
    ],
) -> Dict[str, object]:
    ordered_rejections = sorted(
        invalid_quote_rejections,
        key=lambda rejection: (
            rejection.bookmaker_key,
            rejection.market_last_update,
            rejection.reason,
        ),
    )

    rejection_rows = [
        {
            "event_id": rejection.event_id,
            "bookmaker_key": (
                rejection.bookmaker_key
            ),
            "market_last_update_utc": format_utc(
                rejection.market_last_update
            ),
            "home_raw_price": repr(
                rejection.home_raw_price
            ),
            "away_raw_price": repr(
                rejection.away_raw_price
            ),
            "reason": rejection.reason,
            "approved": (
                rejection.bookmaker_key
                in APPROVED_BOOKMAKERS
            ),
        }
        for rejection in ordered_rejections
    ]

    return {
        "output_market_id": (
            observation.output_market_id
        ),
        "provider_event_id": (
            observation.provider_event_id
        ),
        "target_request_time_utc": format_utc(
            observation.target_request_time
        ),
        "observation_time_utc": format_utc(
            observation.observation_time
        ),
        "provider_snapshot_lag_seconds": (
            observation
            .provider_snapshot_lag_seconds
        ),
        (
            "provider_commence_time_"
            "at_observation_utc"
        ): (
            ""
            if observation.provider_commence_time
            is None
            else format_utc(
                observation.provider_commence_time
            )
        ),
        "provider_home_team": (
            observation.provider_home_team
        ),
        "provider_away_team": (
            observation.provider_away_team
        ),
        "home_fair_prob": (
            ""
            if observation.home_fair_prob is None
            else observation.home_fair_prob
        ),
        "away_fair_prob": (
            ""
            if observation.away_fair_prob is None
            else observation.away_fair_prob
        ),
        "bookmaker_count": (
            observation.bookmaker_count
        ),
        "invalid_quote_count": len(
            rejection_rows
        ),
        "invalid_approved_quote_count": sum(
            bool(row["approved"])
            for row in rejection_rows
        ),
        "invalid_quote_rejections_json": (
            json.dumps(
                rejection_rows,
                separators=(",", ":"),
                sort_keys=True,
            )
        ),
        "bookmaker_keys_json": json.dumps(
            list(observation.bookmaker_keys),
            separators=(",", ":"),
        ),
        "quote_timestamps_json": json.dumps(
            [
                format_utc(timestamp)
                for timestamp
                in observation.quote_timestamps
            ],
            separators=(",", ":"),
        ),
        "oldest_quote_age_seconds": (
            ""
            if (
                observation
                .oldest_quote_age_seconds
                is None
            )
            else (
                observation
                .oldest_quote_age_seconds
            )
        ),
        "newest_quote_age_seconds": (
            ""
            if (
                observation
                .newest_quote_age_seconds
                is None
            )
            else (
                observation
                .newest_quote_age_seconds
            )
        ),
        "seconds_before_provider_start": (
            ""
            if (
                observation
                .seconds_before_provider_start
                is None
            )
            else (
                observation
                .seconds_before_provider_start
            )
        ),
        "pregame_at_observation": (
            str(
                observation.pregame_at_observation
            ).lower()
        ),
        "strict_t_minus_60_eligible": (
            str(
                observation
                .strict_t_minus_60_eligible
            ).lower()
        ),
        "status": observation.status,
        "exclusion_reason": (
            observation.exclusion_reason or ""
        ),
        "raw_file": str(raw_path),
        "raw_sha256": raw_sha256,
    }


def write_csv_atomic(
    rows: List[Dict[str, object]],
) -> None:
    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary_path = OUTPUT_PATH.with_suffix(
        OUTPUT_PATH.suffix + ".tmp"
    )

    with temporary_path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=OUTPUT_COLUMNS,
        )
        writer.writeheader()
        writer.writerows(rows)

    temporary_path.replace(OUTPUT_PATH)


def main() -> None:
    groups = load_plan_groups()

    output_rows: List[
        Dict[str, object]
    ] = []

    reason_counts = Counter()
    eligible_count = 0
    strict_count = 0

    for snapshot_index, (
        target_time,
        plan_rows,
    ) in enumerate(groups, start=1):
        raw_path, metadata_path = (
            capture_paths(target_time)
        )

        if not raw_path.exists():
            raise FileNotFoundError(raw_path)

        if not metadata_path.exists():
            raise FileNotFoundError(metadata_path)

        with raw_path.open(
            encoding="utf-8"
        ) as file:
            payload = json.load(file)

        with metadata_path.open(
            encoding="utf-8"
        ) as file:
            metadata = json.load(file)

        if not isinstance(payload, dict):
            raise ValueError(
                f"Raw payload is not an object: "
                f"{raw_path}"
            )

        events = payload.get("data")

        if not isinstance(events, list):
            raise ValueError(
                f"Raw payload lacks data list: "
                f"{raw_path}"
            )

        observation_text = payload.get(
            "timestamp"
        )

        if not isinstance(
            observation_text,
            str,
        ):
            raise ValueError(
                "Raw payload lacks provider "
                f"timestamp: {raw_path}"
            )

        observation_time = parse_utc(
            observation_text
        )

        actual_hash = sha256_file(
            raw_path
        )

        stored_hash = metadata.get(
            "raw_sha256"
        )

        if (
            stored_hash is not None
            and stored_hash != actual_hash
        ):
            raise ValueError(
                f"Raw SHA-256 mismatch: {raw_path}"
            )

        parse_result = (
            parse_the_odds_api_moneylines(
                events
            )
        )

        quotes = parse_result.quotes

        rejections_by_event_id = defaultdict(
            list
        )

        for rejection in (
            parse_result.rejections
        ):
            rejections_by_event_id[
                rejection.event_id
            ].append(rejection)

        for plan_row in plan_rows:
            result = (
                build_historical_bookmaker_observation(
                    output_market_id=plan_row[
                        "output_market_id"
                    ],
                    provider_event_id=plan_row[
                        "provider_event_id"
                    ],
                    expected_home_team=plan_row[
                        "provider_home_team"
                    ],
                    expected_away_team=plan_row[
                        "provider_away_team"
                    ],
                    target_request_time=target_time,
                    observation_time=(
                        observation_time
                    ),
                    events=events,
                    quotes=quotes,
                )
            )

            output_rows.append(
                serialize_observation(
                    result,
                    raw_path=raw_path,
                    raw_sha256=actual_hash,
                    invalid_quote_rejections=(
                        rejections_by_event_id.get(
                            plan_row[
                                "provider_event_id"
                            ],
                            (),
                        )
                    ),
                )
            )

            if result.status == "eligible":
                eligible_count += 1
            else:
                reason_counts[
                    result.exclusion_reason
                    or "unknown"
                ] += 1

            if (
                result.strict_t_minus_60_eligible
            ):
                strict_count += 1

        if (
            snapshot_index == 1
            or snapshot_index % 25 == 0
            or snapshot_index == len(groups)
        ):
            print(
                f"[{snapshot_index}/{len(groups)}] "
                f"processed "
                f"{len(output_rows)} markets"
            )

    expected_market_count = sum(
        len(rows)
        for _, rows in groups
    )

    if len(output_rows) != expected_market_count:
        raise AssertionError(
            "Output rows do not reconcile "
            "to request-plan rows"
        )

    market_ids = [
        str(row["output_market_id"])
        for row in output_rows
    ]

    if len(market_ids) != len(
        set(market_ids)
    ):
        raise AssertionError(
            "Output contains duplicate market IDs"
        )

    write_csv_atomic(output_rows)

    print()
    print(
        "HISTORICAL BOOKMAKER OBSERVATIONS"
    )
    print("=" * 52)
    print(
        f"Snapshots processed    : "
        f"{len(groups)}"
    )
    print(
        f"Markets processed      : "
        f"{len(output_rows)}"
    )
    print(
        f"Eligible synchronized  : "
        f"{eligible_count}"
    )
    print(
        f"Strict T-60 eligible   : "
        f"{strict_count}"
    )
    print(
        f"Excluded               : "
        f"{len(output_rows) - eligible_count}"
    )
    invalid_quote_total = sum(
        int(row["invalid_quote_count"])
        for row in output_rows
    )

    invalid_approved_quote_total = sum(
        int(
            row[
                "invalid_approved_quote_count"
            ]
        )
        for row in output_rows
    )

    print(
        f"Invalid quotes recorded: "
        f"{invalid_quote_total}"
    )
    print(
        f"Invalid approved quotes: "
        f"{invalid_approved_quote_total}"
    )

    if reason_counts:
        print("Exclusion reasons:")

        for reason, count in sorted(
            reason_counts.items()
        ):
            print(
                f"  {reason}: {count}"
            )

    print(
        f"Output CSV             : "
        f"{OUTPUT_PATH}"
    )


if __name__ == "__main__":
    main()
