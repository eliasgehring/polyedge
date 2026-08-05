import argparse
import csv
import hashlib
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple


DEFAULT_PLAN_PATH = Path(
    "data/processed/the_odds_api/"
    "historical_odds_request_plan.csv"
)

OUTPUT_DIR = Path(
    "data/raw/the_odds_api/historical"
)

API_ROOT = "https://api.the-odds-api.com"
SPORT_KEY = "basketball_nba"

ENDPOINT = (
    f"/v4/historical/sports/"
    f"{SPORT_KEY}/odds"
)


def parse_utc(value: str) -> datetime:
    text = str(value).strip().replace(
        "Z",
        "+00:00",
    )

    if text.endswith("+00"):
        text += ":00"

    timestamp = datetime.fromisoformat(
        text
    )

    if (
        timestamp.tzinfo is None
        or timestamp.utcoffset() is None
    ):
        raise ValueError(
            f"Timestamp lacks timezone: "
            f"{value!r}"
        )

    return timestamp.astimezone(
        timezone.utc
    )


def format_utc(timestamp: datetime) -> str:
    return (
        timestamp.astimezone(
            timezone.utc
        )
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(
        data
    ).hexdigest()


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


def atomic_write_bytes(
    path: Path,
    data: bytes,
) -> None:
    temporary_path = path.with_suffix(
        path.suffix + ".tmp"
    )

    temporary_path.write_bytes(data)
    temporary_path.replace(path)


def atomic_write_json(
    path: Path,
    payload: Dict[str, object],
) -> None:
    encoded = (
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")

    atomic_write_bytes(
        path,
        encoded,
    )


def capture_paths(
    target_time: datetime,
) -> Tuple[Path, Path]:
    capture_id = target_time.strftime(
        "%Y%m%dT%H%M%SZ"
    )

    raw_path = (
        OUTPUT_DIR
        / f"{SPORT_KEY}_{capture_id}.json"
    )

    metadata_path = (
        OUTPUT_DIR
        / (
            f"{SPORT_KEY}_{capture_id}"
            f".metadata.json"
        )
    )

    return raw_path, metadata_path


def load_plan_groups(
    plan_path: Path,
) -> List[
    Tuple[
        datetime,
        List[Dict[str, str]],
    ]
]:
    with plan_path.open(
        encoding="utf-8",
        newline="",
    ) as file:
        rows = list(
            csv.DictReader(file)
        )

    if not rows:
        raise ValueError(
            f"Plan contains no rows: "
            f"{plan_path}"
        )

    required_columns = {
        "target_request_time_utc",
        "output_market_id",
        "provider_event_id",
    }

    missing_columns = (
        required_columns
        - set(rows[0])
    )

    if missing_columns:
        raise ValueError(
            "Plan is missing columns: "
            f"{sorted(missing_columns)}"
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
                "Plan contains an empty "
                "output_market_id"
            )

        if market_id in seen_market_ids:
            raise ValueError(
                f"Duplicate market ID: "
                f"{market_id}"
            )

        seen_market_ids.add(
            market_id
        )

        target_time = parse_utc(
            row[
                "target_request_time_utc"
            ]
        )

        groups[target_time].append(row)

    return sorted(
        groups.items(),
        key=lambda item: item[0],
    )


def load_capture_payload(
    raw_path: Path,
) -> Dict[str, object]:
    with raw_path.open(
        encoding="utf-8"
    ) as file:
        payload = json.load(file)

    if not isinstance(payload, dict):
        raise RuntimeError(
            f"{raw_path} is not a "
            "JSON object"
        )

    if not isinstance(
        payload.get("data"),
        list,
    ):
        raise RuntimeError(
            f"{raw_path} lacks a "
            "data list"
        )

    if not isinstance(
        payload.get("timestamp"),
        str,
    ):
        raise RuntimeError(
            f"{raw_path} lacks a "
            "provider timestamp"
        )

    return payload


def extract_event_ids(
    payload: Dict[str, object],
) -> set:
    event_ids = set()

    events = payload["data"]

    if not isinstance(events, list):
        raise TypeError(
            "Capture data must be a list"
        )

    for event in events:
        if not isinstance(event, dict):
            continue

        event_id = str(
            event.get("id", "")
        ).strip()

        if event_id:
            event_ids.add(event_id)

    return event_ids


def validate_cached_capture(
    raw_path: Path,
    metadata_path: Path,
    target_time: datetime,
    rows: List[Dict[str, str]],
) -> Dict[str, object]:
    if (
        raw_path.exists()
        != metadata_path.exists()
    ):
        raise RuntimeError(
            "Partial cache detected. "
            "Exactly one file exists:\n"
            f"raw={raw_path}\n"
            f"metadata={metadata_path}"
        )

    if not raw_path.exists():
        raise FileNotFoundError(
            raw_path
        )

    payload = load_capture_payload(
        raw_path
    )

    with metadata_path.open(
        encoding="utf-8"
    ) as file:
        metadata = json.load(file)

    if not isinstance(metadata, dict):
        raise RuntimeError(
            f"{metadata_path} is not "
            "a JSON object"
        )

    expected_target = format_utc(
        target_time
    )

    stored_target = (
        metadata.get(
            "requested_snapshot_utc"
        )
        or metadata.get(
            "requested_date_utc"
        )
        or metadata.get(
            "requested_date"
        )
    )

    if stored_target:
        if parse_utc(
            str(stored_target)
        ) != target_time:
            raise RuntimeError(
                "Cached target mismatch:\n"
                f"stored={stored_target}\n"
                f"expected={expected_target}"
            )

    stored_hash = (
        metadata.get("raw_sha256")
        or metadata.get(
            "response_sha256"
        )
    )

    actual_hash = sha256_file(
        raw_path
    )

    if (
        stored_hash
        and stored_hash != actual_hash
    ):
        raise RuntimeError(
            f"SHA-256 mismatch for "
            f"{raw_path}"
        )

    provider_snapshot = parse_utc(
        str(payload["timestamp"])
    )

    if provider_snapshot > target_time:
        raise RuntimeError(
            "Cached provider snapshot "
            "occurred after requested target:\n"
            f"provider={format_utc(provider_snapshot)}\n"
            f"target={expected_target}"
        )

    requested_event_ids = {
        row["provider_event_id"].strip()
        for row in rows
        if row[
            "provider_event_id"
        ].strip()
    }

    present_event_ids = (
        extract_event_ids(payload)
    )

    missing_event_ids = (
        requested_event_ids
        - present_event_ids
    )

    return {
        "provider_snapshot": (
            provider_snapshot
        ),
        "event_count": len(
            payload["data"]
        ),
        "missing_event_count": len(
            missing_event_ids
        ),
    }


def fetch_capture(
    api_key: str,
    target_time: datetime,
    rows: List[Dict[str, str]],
    raw_path: Path,
    metadata_path: Path,
    plan_path: Path,
) -> Dict[str, object]:
    public_parameters = {
        "date": format_utc(
            target_time
        ),
        "regions": "us",
        "markets": "h2h",
        "oddsFormat": "decimal",
        "dateFormat": "iso",
    }

    request_parameters = {
        **public_parameters,
        "apiKey": api_key,
    }

    url = (
        API_ROOT
        + ENDPOINT
        + "?"
        + urllib.parse.urlencode(
            request_parameters
        )
    )

    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": (
                "polyedge-research/0.1"
            ),
        },
    )

    requested_at = datetime.now(
        timezone.utc
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=45,
        ) as response:
            raw_body = response.read()

            headers = {
                key.lower(): value
                for key, value
                in response.headers.items()
            }

    except urllib.error.HTTPError as exc:
        body = exc.read().decode(
            "utf-8",
            errors="replace",
        )

        raise RuntimeError(
            f"HTTP {exc.code} for "
            f"{format_utc(target_time)}:\n"
            f"{body}"
        ) from exc

    except urllib.error.URLError as exc:
        raise RuntimeError(
            "Connection failed for "
            f"{format_utc(target_time)}: "
            f"{exc}"
        ) from exc

    received_at = datetime.now(
        timezone.utc
    )

    try:
        payload = json.loads(
            raw_body
        )
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "Provider response was not "
            "valid JSON"
        ) from exc

    if not isinstance(payload, dict):
        raise RuntimeError(
            "Historical odds response "
            "must be a JSON object"
        )

    events = payload.get("data")
    provider_timestamp = payload.get(
        "timestamp"
    )

    if not isinstance(events, list):
        raise RuntimeError(
            "Historical odds response "
            "lacks a data list"
        )

    if not isinstance(
        provider_timestamp,
        str,
    ):
        raise RuntimeError(
            "Historical odds response "
            "lacks timestamp"
        )

    provider_snapshot = parse_utc(
        provider_timestamp
    )

    if provider_snapshot > target_time:
        raise RuntimeError(
            "Provider returned a "
            "post-target snapshot"
        )

    requested_event_ids = sorted({
        row["provider_event_id"].strip()
        for row in rows
        if row[
            "provider_event_id"
        ].strip()
    })

    present_event_ids = sorted(
        extract_event_ids(payload)
    )

    missing_event_ids = sorted(
        set(requested_event_ids)
        - set(present_event_ids)
    )

    quota = {
        "requests_last": headers.get(
            "x-requests-last"
        ),
        "requests_used": headers.get(
            "x-requests-used"
        ),
        "requests_remaining": headers.get(
            "x-requests-remaining"
        ),
    }

    metadata: Dict[str, object] = {
        "provider": "the_odds_api",
        "sport_key": SPORT_KEY,
        "endpoint": ENDPOINT,
        "plan_file": str(plan_path),
        "request_parameters": (
            public_parameters
        ),
        "requested_snapshot_utc": (
            format_utc(target_time)
        ),
        "provider_snapshot_utc": (
            format_utc(
                provider_snapshot
            )
        ),
        "provider_snapshot_lag_seconds": int(
            (
                target_time
                - provider_snapshot
            ).total_seconds()
        ),
        "requested_at_utc": format_utc(
            requested_at
        ),
        "received_at_utc": format_utc(
            received_at
        ),
        "output_market_ids": sorted({
            row["output_market_id"]
            for row in rows
        }),
        "requested_provider_event_ids": (
            requested_event_ids
        ),
        "present_provider_event_ids": (
            present_event_ids
        ),
        "missing_provider_event_ids": (
            missing_event_ids
        ),
        "event_count": len(events),
        "raw_file": str(raw_path),
        "raw_sha256": sha256_bytes(
            raw_body
        ),
        "quota": quota,
    }

    atomic_write_bytes(
        raw_path,
        raw_body,
    )

    atomic_write_json(
        metadata_path,
        metadata,
    )

    return {
        "provider_snapshot": (
            provider_snapshot
        ),
        "event_count": len(events),
        "missing_event_count": len(
            missing_event_ids
        ),
        "credits_last": quota[
            "requests_last"
        ],
        "credits_remaining": quota[
            "requests_remaining"
        ],
    }


def parse_optional_int(
    value: Optional[str],
) -> Optional[int]:
    if value is None:
        return None

    try:
        return int(value)
    except ValueError:
        return None


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Cache-first historical NBA "
            "moneyline odds archiver."
        )
    )

    parser.add_argument(
        "--plan",
        type=Path,
        default=DEFAULT_PLAN_PATH,
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help=(
            "Process only the first N "
            "unique target timestamps."
        ),
    )

    parser.add_argument(
        "--offline",
        action="store_true",
        help=(
            "Validate cache without making "
            "network requests."
        ),
    )

    parser.add_argument(
        "--max-new-requests",
        type=int,
        default=5,
        help=(
            "Refuse to start when more than "
            "this many uncached requests "
            "would be needed."
        ),
    )

    parser.add_argument(
        "--minimum-remaining-credits",
        type=int,
        default=1000,
    )

    parser.add_argument(
        "--pause-seconds",
        type=float,
        default=0.25,
    )

    args = parser.parse_args()

    if (
        args.limit is not None
        and args.limit <= 0
    ):
        raise SystemExit(
            "--limit must be positive"
        )

    if args.max_new_requests < 0:
        raise SystemExit(
            "--max-new-requests cannot "
            "be negative"
        )

    if args.pause_seconds < 0:
        raise SystemExit(
            "--pause-seconds cannot "
            "be negative"
        )

    groups = load_plan_groups(
        args.plan
    )

    if args.limit is not None:
        groups = groups[:args.limit]

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    cached_results = {}
    missing_groups = []

    # Validate every existing cache entry before
    # making even one paid request.
    for target_time, rows in groups:
        raw_path, metadata_path = (
            capture_paths(target_time)
        )

        if (
            raw_path.exists()
            or metadata_path.exists()
        ):
            cached_results[
                target_time
            ] = validate_cached_capture(
                raw_path=raw_path,
                metadata_path=metadata_path,
                target_time=target_time,
                rows=rows,
            )
        else:
            missing_groups.append(
                (target_time, rows)
            )

    if (
        not args.offline
        and len(missing_groups)
        > args.max_new_requests
    ):
        raise SystemExit(
            "Safety stop: this run would "
            f"make {len(missing_groups)} new "
            "requests, exceeding "
            f"--max-new-requests="
            f"{args.max_new_requests}"
        )

    api_key = os.environ.get(
        "THE_ODDS_API_KEY"
    )

    if (
        missing_groups
        and not args.offline
        and not api_key
    ):
        raise SystemExit(
            "THE_ODDS_API_KEY is required "
            "for uncached requests"
        )

    cached_count = 0
    fetched_count = 0
    missing_offline_count = 0
    missing_event_total = 0
    latest_remaining = None

    for index, (
        target_time,
        rows,
    ) in enumerate(groups, start=1):
        raw_path, metadata_path = (
            capture_paths(target_time)
        )

        label = (
            f"[{index}/{len(groups)}] "
            f"{format_utc(target_time)}"
        )

        if target_time in cached_results:
            result = cached_results[
                target_time
            ]

            cached_count += 1
            missing_event_total += int(
                result[
                    "missing_event_count"
                ]
            )

            print(
                f"{label} CACHED "
                f"markets={len(rows)} "
                f"events="
                f"{result['event_count']} "
                f"missing_events="
                f"{result['missing_event_count']}"
            )

            continue

        if args.offline:
            missing_offline_count += 1

            print(
                f"{label} MISSING "
                f"markets={len(rows)}"
            )

            continue

        result = fetch_capture(
            api_key=api_key or "",
            target_time=target_time,
            rows=rows,
            raw_path=raw_path,
            metadata_path=metadata_path,
            plan_path=args.plan,
        )

        fetched_count += 1
        missing_event_total += int(
            result[
                "missing_event_count"
            ]
        )

        latest_remaining = (
            parse_optional_int(
                result[
                    "credits_remaining"
                ]
            )
        )

        print(
            f"{label} FETCHED "
            f"markets={len(rows)} "
            f"events="
            f"{result['event_count']} "
            f"missing_events="
            f"{result['missing_event_count']} "
            f"cost="
            f"{result['credits_last']} "
            f"remaining="
            f"{result['credits_remaining']}"
        )

        if (
            latest_remaining is not None
            and latest_remaining
            < args.minimum_remaining_credits
        ):
            raise SystemExit(
                "Credit safety floor reached"
            )

        if index < len(groups):
            time.sleep(
                args.pause_seconds
            )

    print("\nHISTORICAL ODDS ARCHIVE SUMMARY")
    print("=" * 52)
    print(
        f"Snapshots considered : "
        f"{len(groups)}"
    )
    print(
        f"Validated from cache : "
        f"{cached_count}"
    )
    print(
        f"Fetched from API     : "
        f"{fetched_count}"
    )
    print(
        f"Missing offline      : "
        f"{missing_offline_count}"
    )
    print(
        f"Requested events absent: "
        f"{missing_event_total}"
    )

    if latest_remaining is not None:
        print(
            f"Credits remaining    : "
            f"{latest_remaining}"
        )

    if (
        args.offline
        and missing_offline_count
    ):
        raise SystemExit(
            "Offline odds archive is "
            "incomplete"
        )


if __name__ == "__main__":
    main()
