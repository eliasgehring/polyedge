import argparse
import csv
import hashlib
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple


BOOKMAKER_PATH = Path(
    "data/processed/the_odds_api/"
    "historical_bookmaker_observations.csv"
)

IDENTITY_PATH = Path(
    "data/processed/polymarket/"
    "polymarket_market_identity.csv"
)

ARCHIVE_DIR = Path(
    "data/raw/polymarket/price_history"
)

CLOB_BASE = "https://clob.polymarket.com"
ENDPOINT = "/prices-history"

LOOKBACK_SECONDS = 6 * 60 * 60
FIDELITY_MINUTES = 1


def parse_utc(value: str) -> datetime:
    text = value.strip().replace(
        "Z",
        "+00:00",
    )

    timestamp = datetime.fromisoformat(text)

    if (
        timestamp.tzinfo is None
        or timestamp.utcoffset() is None
    ):
        raise ValueError(
            f"Timestamp lacks timezone: {value!r}"
        )

    return timestamp.astimezone(
        timezone.utc
    )


def format_utc(value: datetime) -> str:
    return (
        value.astimezone(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def read_rows(
    path: Path,
) -> List[Dict[str, str]]:
    with path.open(
        encoding="utf-8",
        newline="",
    ) as file:
        return list(csv.DictReader(file))


def unique_index(
    rows: List[Dict[str, str]],
    field_name: str,
) -> Dict[str, Dict[str, str]]:
    result: Dict[
        str,
        Dict[str, str],
    ] = {}

    for row in rows:
        value = row[field_name]

        if value in result:
            raise ValueError(
                f"Duplicate {field_name}: "
                f"{value}"
            )

        result[value] = row

    return result


def build_plan() -> List[Dict[str, str]]:
    bookmaker_rows = read_rows(
        BOOKMAKER_PATH
    )

    identity_rows = read_rows(
        IDENTITY_PATH
    )

    identity_by_market = unique_index(
        identity_rows,
        "output_market_id",
    )

    eligible_bookmakers = [
        row
        for row in bookmaker_rows
        if row["status"] == "eligible"
    ]

    bookmaker_by_market = unique_index(
        eligible_bookmakers,
        "output_market_id",
    )

    missing_identity = (
        set(bookmaker_by_market)
        - set(identity_by_market)
    )

    if missing_identity:
        raise ValueError(
            "Eligible bookmaker markets lack "
            "Polymarket identity rows: "
            f"{sorted(missing_identity)[:10]}"
        )

    plan = []

    for market_id, bookmaker in (
        bookmaker_by_market.items()
    ):
        identity = identity_by_market[
            market_id
        ]

        plan.append({
            "output_market_id": market_id,
            "observation_time_utc": (
                bookmaker[
                    "observation_time_utc"
                ]
            ),
            "home_token_id": (
                identity["home_token_id"]
            ),
            "away_token_id": (
                identity["away_token_id"]
            ),
        })

    plan.sort(
        key=lambda row: (
            row["observation_time_utc"],
            row["output_market_id"],
        )
    )

    return plan


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
    *,
    market_id: str,
    side: str,
    cutoff_timestamp: int,
) -> Tuple[Path, Path]:
    stem = (
        f"{market_id}_"
        f"{side.lower()}_"
        f"{cutoff_timestamp}"
    )

    raw_path = (
        ARCHIVE_DIR
        / f"{stem}.json"
    )

    metadata_path = (
        ARCHIVE_DIR
        / f"{stem}.metadata.json"
    )

    return raw_path, metadata_path


def validate_payload(
    payload: object,
) -> Dict[str, object]:
    if not isinstance(payload, dict):
        raise ValueError(
            "Price-history response must "
            "be a JSON object"
        )

    history = payload.get("history")

    if not isinstance(history, list):
        raise ValueError(
            "Price-history response must "
            "contain a history list"
        )

    return payload


def validate_cached_capture(
    *,
    raw_path: Path,
    metadata_path: Path,
    expected_parameters: Dict[str, object],
) -> int:
    if (
        raw_path.exists()
        != metadata_path.exists()
    ):
        raise RuntimeError(
            "Partial cache detected:\n"
            f"raw={raw_path}\n"
            f"metadata={metadata_path}"
        )

    with raw_path.open(
        encoding="utf-8"
    ) as file:
        payload = validate_payload(
            json.load(file)
        )

    with metadata_path.open(
        encoding="utf-8"
    ) as file:
        metadata = json.load(file)

    if (
        metadata.get("request_parameters")
        != expected_parameters
    ):
        raise RuntimeError(
            "Cached request parameters "
            f"do not match: {raw_path}"
        )

    if (
        metadata.get("raw_sha256")
        != sha256_file(raw_path)
    ):
        raise RuntimeError(
            f"SHA-256 mismatch: {raw_path}"
        )

    return len(payload["history"])


def fetch_capture(
    *,
    market_id: str,
    side: str,
    token_id: str,
    cutoff: datetime,
    parameters: Dict[str, object],
    raw_path: Path,
    metadata_path: Path,
) -> int:
    url = (
        CLOB_BASE
        + ENDPOINT
        + "?"
        + urllib.parse.urlencode(
            parameters
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
            status_code = response.status

    except urllib.error.HTTPError as exc:
        body = exc.read().decode(
            "utf-8",
            errors="replace",
        )

        raise RuntimeError(
            f"HTTP {exc.code} for "
            f"{market_id}/{side}:\n"
            f"{body}"
        ) from exc

    except urllib.error.URLError as exc:
        raise RuntimeError(
            f"Request failed for "
            f"{market_id}/{side}: {exc}"
        ) from exc

    received_at = datetime.now(
        timezone.utc
    )

    try:
        payload = validate_payload(
            json.loads(raw_body)
        )
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "Polymarket response was not "
            "valid JSON"
        ) from exc

    metadata: Dict[str, object] = {
        "provider": "polymarket_clob",
        "endpoint": ENDPOINT,
        "output_market_id": market_id,
        "side": side,
        "token_id": token_id,
        "common_cutoff_utc": format_utc(
            cutoff
        ),
        "lookback_seconds": (
            LOOKBACK_SECONDS
        ),
        "fidelity_minutes": (
            FIDELITY_MINUTES
        ),
        "request_parameters": parameters,
        "requested_at_utc": format_utc(
            requested_at
        ),
        "received_at_utc": format_utc(
            received_at
        ),
        "http_status": status_code,
        "history_point_count": len(
            payload["history"]
        ),
        "raw_file": str(raw_path),
        "raw_sha256": sha256_bytes(
            raw_body
        ),
    }

    atomic_write_bytes(
        raw_path,
        raw_body,
    )

    atomic_write_json(
        metadata_path,
        metadata,
    )

    return len(payload["history"])


def capture_spec(
    *,
    plan_row: Dict[str, str],
    side: str,
) -> Dict[str, object]:
    cutoff = parse_utc(
        plan_row[
            "observation_time_utc"
        ]
    )

    cutoff_timestamp = int(
        cutoff.timestamp()
    )

    if side == "HOME":
        token_id = plan_row[
            "home_token_id"
        ]
    elif side == "AWAY":
        token_id = plan_row[
            "away_token_id"
        ]
    else:
        raise ValueError(
            f"Unknown side: {side}"
        )

    parameters: Dict[str, object] = {
        "market": token_id,
        "startTs": (
            cutoff_timestamp
            - LOOKBACK_SECONDS
        ),
        "endTs": cutoff_timestamp,
        "fidelity": FIDELITY_MINUTES,
    }

    raw_path, metadata_path = (
        capture_paths(
            market_id=plan_row[
                "output_market_id"
            ],
            side=side,
            cutoff_timestamp=(
                cutoff_timestamp
            ),
        )
    )

    return {
        "market_id": plan_row[
            "output_market_id"
        ],
        "side": side,
        "token_id": token_id,
        "cutoff": cutoff,
        "parameters": parameters,
        "raw_path": raw_path,
        "metadata_path": metadata_path,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Cache-first Polymarket price-"
            "history archiver."
        )
    )

    parser.add_argument(
        "--market-id",
        default=None,
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
    )

    parser.add_argument(
        "--offline",
        action="store_true",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
    )

    parser.add_argument(
        "--max-new-requests",
        type=int,
        default=10,
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

    plan = build_plan()

    if args.market_id is not None:
        plan = [
            row
            for row in plan
            if row["output_market_id"]
            == args.market_id
        ]

        if not plan:
            raise SystemExit(
                "Requested market ID was "
                "not found"
            )

    if args.limit is not None:
        plan = plan[:args.limit]

    ARCHIVE_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    specs = []

    for plan_row in plan:
        specs.append(
            capture_spec(
                plan_row=plan_row,
                side="HOME",
            )
        )

        specs.append(
            capture_spec(
                plan_row=plan_row,
                side="AWAY",
            )
        )

    cached_keys = set()
    missing_specs = []
    cached_point_total = 0

    # Validate all existing cache files before
    # making even one network request.
    for spec in specs:
        raw_path = spec["raw_path"]
        metadata_path = spec[
            "metadata_path"
        ]

        if (
            not isinstance(raw_path, Path)
            or not isinstance(
                metadata_path,
                Path,
            )
        ):
            raise TypeError(
                "Capture paths must be Path "
                "objects"
            )

        key = (
            spec["market_id"],
            spec["side"],
        )

        if (
            raw_path.exists()
            or metadata_path.exists()
        ):
            point_count = (
                validate_cached_capture(
                    raw_path=raw_path,
                    metadata_path=(
                        metadata_path
                    ),
                    expected_parameters=(
                        spec["parameters"]
                    ),
                )
            )

            cached_keys.add(key)
            cached_point_total += (
                point_count
            )
        else:
            missing_specs.append(spec)

    print(
        "POLYMARKET PRICE-HISTORY PLAN"
    )
    print("=" * 60)
    print(
        f"Markets selected      : "
        f"{len(plan)}"
    )
    print(
        f"Token captures        : "
        f"{len(specs)}"
    )
    print(
        f"Validated from cache  : "
        f"{len(cached_keys)}"
    )
    print(
        f"New requests required : "
        f"{len(missing_specs)}"
    )
    print(
        f"Cached history points : "
        f"{cached_point_total}"
    )

    if args.dry_run:
        return

    if (
        not args.offline
        and len(missing_specs)
        > args.max_new_requests
    ):
        raise SystemExit(
            "Safety stop: this run would "
            f"make {len(missing_specs)} "
            "new requests, exceeding "
            f"--max-new-requests="
            f"{args.max_new_requests}"
        )

    fetched_count = 0
    cached_count = 0
    missing_offline_count = 0
    history_point_total = 0

    for market_index, plan_row in enumerate(
        plan,
        start=1,
    ):
        for side in ("HOME", "AWAY"):
            spec = capture_spec(
                plan_row=plan_row,
                side=side,
            )

            key = (
                spec["market_id"],
                spec["side"],
            )

            if key in cached_keys:
                cached_count += 1
                continue

            if args.offline:
                missing_offline_count += 1
                continue

            raw_path = spec["raw_path"]
            metadata_path = spec[
                "metadata_path"
            ]
            cutoff = spec["cutoff"]

            if (
                not isinstance(raw_path, Path)
                or not isinstance(
                    metadata_path,
                    Path,
                )
                or not isinstance(
                    cutoff,
                    datetime,
                )
            ):
                raise TypeError(
                    "Invalid capture specification"
                )

            point_count = fetch_capture(
                market_id=str(
                    spec["market_id"]
                ),
                side=str(spec["side"]),
                token_id=str(
                    spec["token_id"]
                ),
                cutoff=cutoff,
                parameters=spec[
                    "parameters"
                ],
                raw_path=raw_path,
                metadata_path=(
                    metadata_path
                ),
            )

            fetched_count += 1
            history_point_total += (
                point_count
            )

            time.sleep(
                args.pause_seconds
            )

        if (
            market_index == 1
            or market_index % 25 == 0
            or market_index == len(plan)
        ):
            completed_captures = (
                cached_count
                + fetched_count
            )

            remaining_captures = (
                len(specs)
                - completed_captures
                - missing_offline_count
            )

            print(
                f"[{market_index}/"
                f"{len(plan)}] markets | "
                f"cached={cached_count} "
                f"fetched={fetched_count} "
                f"remaining="
                f"{remaining_captures}"
            )

    print()
    print(
        "POLYMARKET PRICE-HISTORY ARCHIVE"
    )
    print("=" * 60)
    print(
        f"Markets processed     : "
        f"{len(plan)}"
    )
    print(
        f"Validated from cache  : "
        f"{cached_count}"
    )
    print(
        f"Fetched from network  : "
        f"{fetched_count}"
    )
    print(
        f"Missing offline       : "
        f"{missing_offline_count}"
    )
    print(
        f"New history points    : "
        f"{history_point_total}"
    )
    print(
        f"Archive directory     : "
        f"{ARCHIVE_DIR}"
    )

    if (
        args.offline
        and missing_offline_count
    ):
        raise SystemExit(
            "Offline archive is incomplete"
        )


if __name__ == "__main__":
    main()
