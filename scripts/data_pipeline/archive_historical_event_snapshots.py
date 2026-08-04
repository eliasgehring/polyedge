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
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple


MANIFEST_PATH = Path(
    "data/diagnostics/polymarket_match_manifest.csv"
)
OUTPUT_DIR = Path(
    "data/raw/the_odds_api/historical_events"
)

API_ROOT = "https://api.the-odds-api.com"
SPORT_KEY = "basketball_nba"
DECISION_MINUTES_BEFORE_GAME = 60
DISCOVERY_WINDOW_HOURS = 3


def parse_utc(value: str) -> datetime:
    text = value.strip().replace("Z", "+00:00")

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


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as file:
        for chunk in iter(
            lambda: file.read(1024 * 1024),
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

    atomic_write_bytes(path, encoded)


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

    for row in rows:
        game_start = parse_utc(
            row["game_start_time"]
        )
        decision_time = game_start - timedelta(
            minutes=DECISION_MINUTES_BEFORE_GAME
        )
        groups[decision_time].append(row)

    return sorted(
        groups.items(),
        key=lambda item: item[0],
    )


def capture_paths(
    decision_time: datetime,
) -> Tuple[Path, Path]:
    capture_id = decision_time.strftime(
        "%Y%m%dT%H%M%SZ"
    )

    raw_path = (
        OUTPUT_DIR
        / f"{SPORT_KEY}_{capture_id}.json"
    )
    metadata_path = (
        OUTPUT_DIR
        / f"{SPORT_KEY}_{capture_id}.metadata.json"
    )

    return raw_path, metadata_path


def validate_cached_capture(
    raw_path: Path,
    metadata_path: Path,
    decision_time: datetime,
) -> None:
    if raw_path.exists() != metadata_path.exists():
        raise RuntimeError(
            "Partial cache detected. Exactly one of "
            f"{raw_path} and {metadata_path} exists."
        )

    if not raw_path.exists():
        raise FileNotFoundError(raw_path)

    with metadata_path.open(
        encoding="utf-8"
    ) as file:
        metadata = json.load(file)

    expected_decision = format_utc(
        decision_time
    )
    stored_decision = metadata.get(
        "requested_snapshot_utc"
    )

    if stored_decision != expected_decision:
        raise RuntimeError(
            f"Cached decision mismatch for {raw_path}: "
            f"{stored_decision!r} != "
            f"{expected_decision!r}"
        )

    expected_hash = metadata.get(
        "raw_sha256"
    )
    actual_hash = sha256_file(raw_path)

    if expected_hash != actual_hash:
        raise RuntimeError(
            f"SHA-256 mismatch for {raw_path}"
        )

    with raw_path.open(
        encoding="utf-8"
    ) as file:
        payload = json.load(file)

    if not isinstance(payload, dict):
        raise RuntimeError(
            f"{raw_path} is not a JSON object"
        )

    if not isinstance(
        payload.get("data"),
        list,
    ):
        raise RuntimeError(
            f"{raw_path} lacks a data list"
        )


def fetch_snapshot(
    api_key: str,
    decision_time: datetime,
    rows: List[Dict[str, str]],
    raw_path: Path,
    metadata_path: Path,
) -> Optional[str]:
    game_starts = [
        parse_utc(row["game_start_time"])
        for row in rows
    ]

    window_start = (
        min(game_starts)
        - timedelta(
            hours=DISCOVERY_WINDOW_HOURS
        )
    )
    window_end = (
        max(game_starts)
        + timedelta(
            hours=DISCOVERY_WINDOW_HOURS
        )
    )

    endpoint = (
        f"/v4/historical/sports/"
        f"{SPORT_KEY}/events"
    )

    public_parameters = {
        "date": format_utc(decision_time),
        "dateFormat": "iso",
        "commenceTimeFrom": format_utc(
            window_start
        ),
        "commenceTimeTo": format_utc(
            window_end
        ),
    }

    request_parameters = {
        **public_parameters,
        "apiKey": api_key,
    }

    url = (
        API_ROOT
        + endpoint
        + "?"
        + urllib.parse.urlencode(
            request_parameters
        )
    )

    requested_at = datetime.now(
        timezone.utc
    )

    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "polyedge-research/0.1",
        },
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=30,
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
            f"{format_utc(decision_time)}:\n{body}"
        ) from exc

    except urllib.error.URLError as exc:
        raise RuntimeError(
            f"Connection failed for "
            f"{format_utc(decision_time)}: {exc}"
        ) from exc

    received_at = datetime.now(
        timezone.utc
    )

    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "Provider response was not valid JSON"
        ) from exc

    if not isinstance(payload, dict):
        raise RuntimeError(
            "Expected historical response wrapper"
        )

    events = payload.get("data")
    snapshot_text = payload.get("timestamp")

    if not isinstance(events, list):
        raise RuntimeError(
            "Historical response data must be a list"
        )

    if not isinstance(snapshot_text, str):
        raise RuntimeError(
            "Historical response lacks timestamp"
        )

    provider_snapshot = parse_utc(
        snapshot_text
    )

    if provider_snapshot > decision_time:
        raise RuntimeError(
            "Provider returned a post-decision "
            "snapshot"
        )

    metadata: Dict[str, object] = {
        "provider": "the_odds_api",
        "sport_key": SPORT_KEY,
        "endpoint": endpoint,
        "request_parameters": public_parameters,
        "requested_snapshot_utc": format_utc(
            decision_time
        ),
        "provider_snapshot_utc": format_utc(
            provider_snapshot
        ),
        "provider_snapshot_lag_seconds": int(
            (
                decision_time
                - provider_snapshot
            ).total_seconds()
        ),
        "requested_at_utc": format_utc(
            requested_at
        ),
        "received_at_utc": format_utc(
            received_at
        ),
        "manifest_market_ids": [
            row["output_market_id"]
            for row in rows
        ],
        "manifest_game_starts_utc": sorted({
            format_utc(
                parse_utc(
                    row["game_start_time"]
                )
            )
            for row in rows
        }),
        "event_count": len(events),
        "raw_file": str(raw_path),
        "raw_sha256": sha256_bytes(
            raw_body
        ),
        "quota": {
            "requests_last": headers.get(
                "x-requests-last"
            ),
            "requests_used": headers.get(
                "x-requests-used"
            ),
            "requests_remaining": headers.get(
                "x-requests-remaining"
            ),
        },
    }

    atomic_write_bytes(
        raw_path,
        raw_body,
    )
    atomic_write_json(
        metadata_path,
        metadata,
    )

    return headers.get(
        "x-requests-remaining"
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Cache-first historical NBA event "
            "snapshot archiver."
        )
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help=(
            "Process only the first N unique "
            "requested snapshots."
        ),
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help=(
            "Validate cached snapshots without "
            "making network requests."
        ),
    )
    parser.add_argument(
        "--pause-seconds",
        type=float,
        default=0.25,
        help=(
            "Pause between network requests."
        ),
    )
    args = parser.parse_args()

    if args.limit is not None and args.limit <= 0:
        raise SystemExit(
            "--limit must be positive"
        )

    if args.pause_seconds < 0:
        raise SystemExit(
            "--pause-seconds must be non-negative"
        )

    groups = load_snapshot_groups()

    if args.limit is not None:
        groups = groups[:args.limit]

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    api_key = os.environ.get(
        "THE_ODDS_API_KEY"
    )

    cached_count = 0
    fetched_count = 0
    missing_count = 0
    latest_remaining = None

    for index, (
        decision_time,
        rows,
    ) in enumerate(groups, start=1):
        raw_path, metadata_path = (
            capture_paths(decision_time)
        )

        label = (
            f"[{index}/{len(groups)}] "
            f"{format_utc(decision_time)}"
        )

        if (
            raw_path.exists()
            or metadata_path.exists()
        ):
            validate_cached_capture(
                raw_path=raw_path,
                metadata_path=metadata_path,
                decision_time=decision_time,
            )
            cached_count += 1
            print(
                f"{label} CACHED "
                f"markets={len(rows)}"
            )
            continue

        if args.offline:
            missing_count += 1
            print(
                f"{label} MISSING "
                f"markets={len(rows)}"
            )
            continue

        if not api_key:
            raise SystemExit(
                "THE_ODDS_API_KEY is required "
                "for uncached snapshots"
            )

        latest_remaining = fetch_snapshot(
            api_key=api_key,
            decision_time=decision_time,
            rows=rows,
            raw_path=raw_path,
            metadata_path=metadata_path,
        )
        fetched_count += 1

        print(
            f"{label} FETCHED "
            f"markets={len(rows)} "
            f"credits_remaining="
            f"{latest_remaining}"
        )

        if index < len(groups):
            time.sleep(
                args.pause_seconds
            )

    print("\nARCHIVE SUMMARY")
    print("=" * 44)
    print(
        f"Snapshots considered : {len(groups)}"
    )
    print(
        f"Validated from cache : {cached_count}"
    )
    print(
        f"Fetched from API     : {fetched_count}"
    )
    print(
        f"Missing offline      : {missing_count}"
    )

    if latest_remaining is not None:
        print(
            f"Credits remaining    : "
            f"{latest_remaining}"
        )

    if args.offline and missing_count:
        raise SystemExit(
            "Offline archive is incomplete"
        )


if __name__ == "__main__":
    main()
