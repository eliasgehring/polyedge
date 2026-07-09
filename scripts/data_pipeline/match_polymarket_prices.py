import csv
import json
import os
import re
import time
from collections import defaultdict
from datetime import datetime, timezone
from typing import Optional, Dict
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError


from polyedge.paths import (
    BOOKMAKER_SOURCE_DIR,
    HISTORICAL_READY_DIR,
    POLYMARKET_REVIEW_FILE,
    DIAGNOSTICS_DIR,
    ensure_dir,
    ensure_parent_dir,
)

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from polyedge.backtest import run_simulation
from polyedge.market_matching import select_home_token
from polyedge.match_manifest import MATCH_MANIFEST_COLUMNS, build_match_manifest_row
from polyedge.time_semantics import choose_aligned_snapshot_time
from polyedge.price_history import PriceHistorySelection, select_latest_price_before_snapshot


SOURCE_DIR = BOOKMAKER_SOURCE_DIR
OUTPUT_DIR = HISTORICAL_READY_DIR
REVIEW_FILE = POLYMARKET_REVIEW_FILE
MATCH_MANIFEST_FILE = (
    DIAGNOSTICS_DIR / "polymarket_match_manifest.csv"
)
GAMMA_BASE = "https://gamma-api.polymarket.com"
CLOB_BASE = "https://clob.polymarket.com"

# Polymarket exposes historical prices, not historical order books.
# We treat the historical price as midpoint and synthesize bid/ask.
SYNTHETIC_TOTAL_SPREAD = 0.02

PRICE_LOOKBACK_HOURS = 72
MAX_PRICE_STALENESS_HOURS = 6
MAX_PRICE_STALENESS_SECONDS = MAX_PRICE_STALENESS_HOURS * 3600
REQUEST_SLEEP_SECONDS = 0.20
CHECKPOINT_EVERY = 50


TEAM_TO_SLUG_CODES = {
    "atlanta": ["atl"],
    "boston": ["bos"],
    "brooklyn": ["bkn", "bro"],
    "charlotte": ["cha"],
    "chicago": ["chi"],
    "cleveland": ["cle"],
    "dallas": ["dal"],
    "denver": ["den"],
    "detroit": ["det"],
    "golden state": ["gsw"],
    "houston": ["hou"],
    "indiana": ["ind"],
    "la clippers": ["lac"],
    "la lakers": ["lal"],
    "memphis": ["mem"],
    "miami": ["mia"],
    "milwaukee": ["mil"],
    "minnesota": ["min"],
    "new orleans": ["nor", "nop"],
    "new york": ["nyk"],
    "oklahoma city": ["okc"],
    "orlando": ["orl"],
    "philadelphia": ["phi"],
    "phoenix": ["phx", "pho"],
    "portland": ["por"],
    "sacramento": ["sac"],
    "san antonio": ["sas"],
    "toronto": ["tor"],
    "utah": ["uta", "utah"],
    "washington": ["was"],
}


OUTPUT_COLUMNS = [
    "timestamp",
    "market_id",
    "best_bid",
    "best_ask",
    "bookmaker_prob",
    "row_type"
]

REVIEW_COLUMNS = [
    "market_id",
    "reason",
    "slug",
    "event_title",
    "home_outcome",
    "candidate_count",
    "price_timestamp",
    "price_age_seconds",
]


def ensure_dirs() -> None:
    if not os.path.isdir(SOURCE_DIR):
        raise FileNotFoundError(f"Input folder does not exist: {SOURCE_DIR}")

    ensure_dir(OUTPUT_DIR)


def http_get_json(base_url: str, path: str, params: Optional[Dict] = None):
    
    url = f"{base_url}{path}"

    if params:
        url = f"{url}?{urlencode(params, doseq=True)}"

    req = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json",
        },
    )

    max_attempts = 6
    base_sleep = 0.75

    for attempt in range(1, max_attempts + 1):
        try:
            with urlopen(req, timeout=45) as response:
                payload = response.read().decode("utf-8")
                return json.loads(payload)

        except HTTPError as exc:
            retryable = exc.code in {429, 500, 502, 503, 504}

            if retryable and attempt < max_attempts:
                sleep_time = base_sleep * (2 ** (attempt - 1))
                print(
                    f"    HTTP {exc.code}; retrying in {sleep_time:.1f}s "
                    f"({attempt}/{max_attempts})"
                )
                time.sleep(sleep_time)
                continue

            raise

        except (URLError, ConnectionResetError, TimeoutError) as exc:
            if attempt < max_attempts:
                sleep_time = base_sleep * (2 ** (attempt - 1))
                print(
                    f"    Network reset/timeout; retrying in {sleep_time:.1f}s "
                    f"({attempt}/{max_attempts})"
                )
                time.sleep(sleep_time)
                continue

            raise

    return None


def parse_timestamp(ts: str) -> datetime:
    ts = str(ts).strip()

    if ts.endswith("Z"):
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))

    dt = datetime.fromisoformat(ts)

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    return dt


def dt_to_unix(dt: datetime) -> int:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    return int(dt.timestamp())


def naive_utc_iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    return dt.astimezone(timezone.utc).replace(tzinfo=None).isoformat()


def clipped_bid_ask(mid: float, total_spread: float):
    half = total_spread / 2.0

    best_bid = max(0.0, mid - half)
    best_ask = min(1.0, mid + half)

    if best_bid > best_ask:
        best_bid = mid
        best_ask = mid

    return best_bid, best_ask


def parse_list_field(value):
    if value is None:
        return []

    if isinstance(value, list):
        return value

    if isinstance(value, str):
        value = value.strip()

        if not value:
            return []

        try:
            loaded = json.loads(value)
            if isinstance(loaded, list):
                return loaded
        except Exception:
            pass

        return [x.strip() for x in value.split(",") if x.strip()]

    return []


def is_settlement_row(row: dict) -> bool:
    row_type = str(row.get("row_type", "")).strip().upper()

    if row_type == "SETTLEMENT":
        return True

    if row_type == "PREGAME":
        return False

    try:
        best_bid = float(row["best_bid"])
        best_ask = float(row["best_ask"])
        bookmaker_prob = float(row["bookmaker_prob"])
    except Exception:
        return False

    return (
        best_bid in (0.0, 1.0)
        and best_ask in (0.0, 1.0)
        and bookmaker_prob in (0.0, 1.0)
        and best_bid == best_ask == bookmaker_prob
    )


def parse_market_id(market_id: str):
    """
    Expected format: nba_YYYYMMDD_home_team_vs_away_team_home_win
    """
    pattern = (
        r"^nba_"
        r"(?P<date>\d{8})_"
        r"(?P<home>.+)_vs_"
        r"(?P<away>.+)_home_win$"
    )

    match = re.match(pattern, market_id)

    if not match:
        return None

    game_date = datetime.strptime(match.group("date"), "%Y%m%d").date()
    home_team = match.group("home").replace("_", " ").strip()
    away_team = match.group("away").replace("_", " ").strip()

    return {
        "date": game_date,
        "home_team": home_team,
        "away_team": away_team,
    }


def build_slug_candidates(home_team: str, away_team: str, date_obj):
    """
    Polymarket NBA slug convention: nba-{away}-{home}-{YYYY-MM-DD}
    """
    home_codes = TEAM_TO_SLUG_CODES.get(home_team)
    away_codes = TEAM_TO_SLUG_CODES.get(away_team)

    if not home_codes or not away_codes:
        return []

    date_str = date_obj.strftime("%Y-%m-%d")

    candidates = []

    for away_code in away_codes:
        for home_code in home_codes:
            candidates.append(f"nba-{away_code}-{home_code}-{date_str}")

    return candidates


def fetch_event_by_slug(slug: str):
    payload = http_get_json(
        GAMMA_BASE,
        "/events",
        {"slug": slug},
    )

    time.sleep(REQUEST_SLEEP_SECONDS)

    if isinstance(payload, list):
        if len(payload) == 0:
            return None
        return payload[0]

    if isinstance(payload, dict):
        events = payload.get("events", [])

        if isinstance(events, list) and len(events) > 0:
            return events[0]

        if payload.get("slug") == slug:
            return payload

    return None


def find_event_from_slug_candidates(slug_candidates):
    for slug in slug_candidates:
        try:
            event = fetch_event_by_slug(slug)

            if event is not None:
                return event, slug

        except Exception:
            continue

    return None, None


def fetch_price_before_snapshot(
    token_id: str,
    snapshot_dt: datetime,
) -> PriceHistorySelection:
    """
    Fetch the latest historical token price at or before snapshot_dt.

    Polymarket exposes historical prices, not historical order books.
    The returned price is usable only if it is recent enough relative
    to the aligned bookmaker snapshot.
    """
    snapshot_ts = dt_to_unix(snapshot_dt)
    start_ts = snapshot_ts - PRICE_LOOKBACK_HOURS * 3600

    payload = http_get_json(
        CLOB_BASE,
        "/prices-history",
        {
            "market": token_id,
            "startTs": start_ts,
            "endTs": snapshot_ts,
            "fidelity": 60,
        },
    )

    time.sleep(REQUEST_SLEEP_SECONDS)

    if not isinstance(payload, dict):
        return PriceHistorySelection(
            price=None,
            timestamp=None,
            age_seconds=None,
            reason="invalid_price_history_payload",
        )

    history = payload.get("history", [])

    return select_latest_price_before_snapshot(
        history=history,
        snapshot_timestamp=snapshot_ts,
        max_staleness_seconds=MAX_PRICE_STALENESS_SECONDS,
    )


def load_existing_processed_market_ids(output_path: str):
    """
    Resume support: markets with existing pregame rows are skipped.

    """
    if not os.path.exists(output_path):
        return set()

    processed = set()

    with open(output_path, mode="r", newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)

        for row in reader:
            if not is_settlement_row(row):
                market_id = row.get("market_id")
                if market_id:
                    processed.add(market_id)

    return processed


def load_existing_output_rows(output_path: str):
    if not os.path.exists(output_path):
        return []

    rows = []

    with open(output_path, mode="r", newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)

        for row in reader:
            if all(col in row for col in OUTPUT_COLUMNS):
                rows.append({
                    "timestamp": row["timestamp"],
                    "market_id": row["market_id"],
                    "best_bid": row["best_bid"],
                    "best_ask": row["best_ask"],
                    "bookmaker_prob": row["bookmaker_prob"],
                    "row_type": row.get("row_type", ""),

                })

    return rows


def save_output_rows(output_path: str, output_rows):
    ensure_parent_dir(output_path)
    output_rows.sort(key=lambda row: (row["timestamp"], row["market_id"]))

    with open(output_path, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        writer.writerows(output_rows)


def save_review_rows(review_rows):    
    ensure_parent_dir(REVIEW_FILE)

    with open(REVIEW_FILE, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=REVIEW_COLUMNS)
        writer.writeheader()

        clean_rows = []

        for row in review_rows:
            clean_rows.append({
                "market_id": row.get("market_id", ""),
                "reason": row.get("reason", ""),
                "slug": row.get("slug", ""),
                "event_title": row.get("event_title", ""),
                "home_outcome": row.get("home_outcome", ""),
                "candidate_count": row.get("candidate_count", ""),
                "price_timestamp": row.get("price_timestamp", ""),
                "price_age_seconds": row.get("price_age_seconds", ""),
            })

        writer.writerows(clean_rows)


def load_match_manifest_rows():
    if not MATCH_MANIFEST_FILE.exists():
        return []

    with MATCH_MANIFEST_FILE.open(
        mode="r",
        newline="",
        encoding="utf-8",
    ) as file:
        reader = csv.DictReader(file)

        return [
            row
            for row in reader
            if all(column in row for column in MATCH_MANIFEST_COLUMNS)
        ]


def save_match_manifest_rows(manifest_rows):
    ensure_parent_dir(MATCH_MANIFEST_FILE)

    with MATCH_MANIFEST_FILE.open(
        mode="w",
        newline="",
        encoding="utf-8",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=MATCH_MANIFEST_COLUMNS,
        )
        writer.writeheader()
        writer.writerows(manifest_rows)


def process_source_file(input_path: str, output_path: str, review_rows):
    grouped = defaultdict(list)

    with open(input_path, mode="r", newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)

        for row in reader:
            market_id = row.get("market_id")

            if market_id:
                grouped[market_id].append(row)

    market_ids = list(grouped.keys())
    total_markets = len(market_ids)

    existing_processed = load_existing_processed_market_ids(output_path)
    output_rows = load_existing_output_rows(output_path)
    manifest_rows = load_match_manifest_rows()

    matched_events = 0
    matched_with_price = len(existing_processed)
    skipped_already_done = 0

    print(f"  grouped into {total_markets} markets")
    print(f"  already completed from existing output: {len(existing_processed)}")

    for idx, market_id in enumerate(market_ids, start=1):
        if market_id in existing_processed:
            skipped_already_done += 1
            continue

        if idx == 1 or idx % 25 == 0 or idx == total_markets:
            print(f"  processing market {idx}/{total_markets}: {market_id}")

        rows = grouped[market_id]
        parsed = parse_market_id(market_id)

        if parsed is None:
            review_rows.append({
                "market_id": market_id,
                "reason": "could_not_parse_market_id",
                "slug": "",
                "event_title": "",
                "home_outcome": "",
            })
            continue

        home_team = parsed["home_team"]
        away_team = parsed["away_team"]
        date_obj = parsed["date"]

        pregame_rows = [row for row in rows if not is_settlement_row(row)]
        settlement_rows = [row for row in rows if is_settlement_row(row)]

        if not pregame_rows:
            review_rows.append({
                "market_id": market_id,
                "reason": "no_pregame_row",
                "slug": "",
                "event_title": "",
                "home_outcome": "",
            })
            continue

        slug_candidates = build_slug_candidates(
            home_team=home_team,
            away_team=away_team,
            date_obj=date_obj,
        )

        if not slug_candidates:
            review_rows.append({
                "market_id": market_id,
                "reason": "missing_slug_abbreviation_mapping",
                "slug": "",
                "event_title": "",
                "home_outcome": "",
            })
            continue

        event, winning_slug = find_event_from_slug_candidates(slug_candidates)

        if event is None:
            review_rows.append({
                "market_id": market_id,
                "reason": "no_event_for_slug_candidates",
                "slug": " | ".join(slug_candidates),
                "event_title": "",
                "home_outcome": "",
            })
            continue

        matched_events += 1

        selection_result = select_home_token(
            event=event,
            expected_home_team=home_team,
            expected_away_team=away_team,
        )

        if selection_result.selection is None:
            review_rows.append({
                "market_id": market_id,
                "reason": (
                    selection_result.reason
                    or "home_token_selection_failed"
                ),
                "slug": winning_slug,
                "event_title": event.get("title", ""),
                "home_outcome": "",
                "candidate_count": (
                    selection_result.candidate_count
                ),
            })
            continue

        selection = selection_result.selection
        home_token_id = selection.home_token_id
        home_outcome = selection.home_outcome

        pregame_row = sorted(
            pregame_rows,
            key=lambda row: row["timestamp"],
        )[0]

        snapshot_result = choose_aligned_snapshot_time(
            bookmaker_timestamp=pregame_row["timestamp"],
            game_start_time=selection.game_start_time,
        )

        if snapshot_result.snapshot_time is None:
            review_rows.append({
                "market_id": market_id,
                "reason": (
                    snapshot_result.reason
                    or "snapshot_time_selection_failed"
                ),
                "slug": winning_slug,
                "event_title": event.get("title", ""),
                "home_outcome": home_outcome,
            })
            continue

        snapshot_dt = snapshot_result.snapshot_time

        try:
            price_result = fetch_price_before_snapshot(
                token_id=home_token_id,
                snapshot_dt=snapshot_dt,
            )
        except Exception as exc:
            review_rows.append({
                "market_id": market_id,
                "reason": f"price_history_exception_{type(exc).__name__}",
                "slug": winning_slug,
                "event_title": event.get("title", ""),
                "home_outcome": home_outcome,
            })
            continue

        if price_result.price is None:
            review_rows.append({
                "market_id": market_id,
                "reason": (
                    price_result.reason
                    or "price_history_selection_failed"
                ),
                "slug": winning_slug,
                "event_title": event.get("title", ""),
                "home_outcome": home_outcome,
                "price_timestamp": price_result.timestamp or "",
                "price_age_seconds": (
                    price_result.age_seconds or ""
                ),
            })
            continue

        polymarket_mid = price_result.price

        matched_with_price += 1

        best_bid, best_ask = clipped_bid_ask(
            polymarket_mid,
            SYNTHETIC_TOTAL_SPREAD,
        )

        manifest_rows.append(
            build_match_manifest_row(
                source_market_id=market_id,
                output_market_id=pregame_row["market_id"],
                slug=winning_slug,
                selection=selection,
                snapshot_timestamp=naive_utc_iso(snapshot_dt),
                price_result=price_result,
                polymarket_mid=polymarket_mid,
                synthetic_total_spread=SYNTHETIC_TOTAL_SPREAD,
                best_bid=best_bid,
                best_ask=best_ask,
                bookmaker_prob=pregame_row["bookmaker_prob"],
            )
        )

        output_rows.append({
            "timestamp": naive_utc_iso(snapshot_dt),
            "market_id": pregame_row["market_id"],
            "best_bid": f"{best_bid:.6f}",
            "best_ask": f"{best_ask:.6f}",
            "bookmaker_prob": pregame_row["bookmaker_prob"],
            "row_type": "PREGAME",

        })

        for row in sorted(settlement_rows, key=lambda row: row["timestamp"]):
            output_rows.append({
                "timestamp": row["timestamp"],
                "market_id": row["market_id"],
                "best_bid": row["best_bid"],
                "best_ask": row["best_ask"],
                "bookmaker_prob": row["bookmaker_prob"],
                "row_type": "SETTLEMENT",

            })

        if idx % CHECKPOINT_EVERY == 0:
            save_output_rows(output_path, output_rows)
            save_review_rows(review_rows)
            save_match_manifest_rows(manifest_rows)
            print(
                f"    checkpoint saved at market {idx}: "
                f"{matched_with_price} matched with price history"
            )

    save_output_rows(output_path, output_rows)
    save_match_manifest_rows(manifest_rows)

    print(f"  skipped already completed markets : {skipped_already_done}")
    print(f"  matched Polymarket events         : {matched_events}")
    print(f"  matched events with price history : {matched_with_price}")
    print(f"  wrote {len(output_rows)} rows to {output_path}")
    print(f"  wrote {len(manifest_rows)} manifest rows to {MATCH_MANIFEST_FILE}")


def main():
    ensure_dirs()

    # Start with fresh review rows every run.
    review_rows = []

    source_files = [
        filename
        for filename in os.listdir(SOURCE_DIR)
        if filename.endswith(".csv")
    ]

    if not source_files:
        raise ValueError(f"No source CSV files found in {SOURCE_DIR}")

    print(f"Found {len(source_files)} source files")

    for filename in source_files:
        input_path = os.path.join(SOURCE_DIR, filename)
        output_path = os.path.join(OUTPUT_DIR, filename)

        print(f"Processing {filename} ...")
        process_source_file(input_path, output_path, review_rows)
        print(f"Saved {output_path}")

    save_review_rows(review_rows)

    print(f"Review file saved to {REVIEW_FILE}")
    print(f"Review rows: {len(review_rows)}")


if __name__ == "__main__":
    main()