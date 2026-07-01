import csv
import os
import re
from datetime import datetime, timedelta

from paths import (
    NBA_RAW_DIR,
    BOOKMAKER_SOURCE_DIR,
    ensure_dir,
    ensure_parent_dir,
)

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from run_backtest import run_simulation

RAW_DIR = NBA_RAW_DIR
OUTPUT_DIR = BOOKMAKER_SOURCE_DIR
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "nba_source.csv")

TOTAL_SYNTHETIC_SPREAD = 0.02

# Restrict to 2024/25 NBA season:
# regular season + playoffs / finals window
MIN_GAME_DATE = datetime(2024, 10, 22)
MAX_GAME_DATE = datetime(2025, 6, 22)


def ensure_dirs() -> None:
    if not os.path.isdir(RAW_DIR):
        raise FileNotFoundError(f"Input folder does not exist: {RAW_DIR}")

    ensure_dir(OUTPUT_DIR)


def get_raw_csv_path() -> str:
    files = [f for f in os.listdir(RAW_DIR) if f.endswith(".csv")]

    if not files:
        raise FileNotFoundError(
            f"No NBA raw CSV found. Put nba_new.csv into: {RAW_DIR}"
        )

    if "nba_new.csv" in files:
        return os.path.join(RAW_DIR, "nba_new.csv")

    return os.path.join(RAW_DIR, files[0])


def parse_date(date_str: str) -> datetime:
    value = str(date_str).strip()

    formats = [
        "%Y-%m-%d",
        "%Y-%m-%d %H:%M:%S",
        "%m/%d/%Y",
        "%m/%d/%y",
        "%d/%m/%Y",
        "%d/%m/%y",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            pass

    try:
        return datetime.fromisoformat(value)
    except ValueError:
        raise ValueError(f"Could not parse game_date: {value}")


def safe_float(value):
    if value is None:
        return None

    value = str(value).strip().replace(",", "")
    if value == "":
        return None

    try:
        return float(value)
    except ValueError:
        return None


def safe_bool_won(value):
    """
    Converts likely dataset values for money_home_won into:
    - True  = home team won
    - False = away team won
    - None  = unclear / missing
    """
    if value is None:
        return None

    v = str(value).strip().lower()

    if v in {"1", "1.0", "true", "t", "yes", "y", "won", "win"}:
        return True

    if v in {"0", "0.0", "false", "f", "no", "n", "lost", "loss"}:
        return False

    return None


def fair_two_way_probs_from_decimal_odds(home_odds: float, away_odds: float):
    """
    Remove bookmaker vig from two-way moneyline odds.
    """
    if home_odds <= 1.0 or away_odds <= 1.0:
        return None, None

    raw_home = 1.0 / home_odds
    raw_away = 1.0 / away_odds

    total = raw_home + raw_away
    if total <= 0:
        return None, None

    return raw_home / total, raw_away / total


def clipped_bid_ask(prob: float, total_spread: float):
    half = total_spread / 2.0

    best_bid = max(0.0, prob - half)
    best_ask = min(1.0, prob + half)

    if best_bid > best_ask:
        best_bid = prob
        best_ask = prob

    return best_bid, best_ask


def slugify_team(team: str) -> str:
    s = team.lower().strip()
    s = s.replace("&", "and")
    s = re.sub(r"[^a-z0-9\s]", "", s)
    s = re.sub(r"\s+", "_", s)
    return s


def build_market_id(match_date: datetime, home_team: str, away_team: str) -> str:
    return (
        f"nba_{match_date.strftime('%Y%m%d')}_"
        f"{slugify_team(home_team)}_vs_{slugify_team(away_team)}_home_win"
    )


def convert() -> None:
    ensure_dirs()
    input_path = get_raw_csv_path()

    rows_out = []

    total_input_rows = 0
    in_date_window = 0
    valid_pregame_rows = 0
    valid_settlement_rows = 0
    skipped_outside_date_window = 0
    skipped_missing_core = 0
    skipped_bad_odds = 0
    skipped_no_result = 0

    with open(input_path, mode="r", newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)

        print(f"Reading: {input_path}")
        print(f"Columns: {reader.fieldnames}")

        required_columns = [
            "game_date",
            "away_team",
            "home_team",
            "money_away_decimal_odds",
            "money_home_decimal_odds",
            "money_home_won",
        ]

        missing_columns = [col for col in required_columns if col not in reader.fieldnames]
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")

        for row in reader:
            total_input_rows += 1

            game_date_raw = row.get("game_date")
            away_team = str(row.get("away_team", "")).strip()
            home_team = str(row.get("home_team", "")).strip()

            home_decimal_odds = safe_float(row.get("money_home_decimal_odds"))
            away_decimal_odds = safe_float(row.get("money_away_decimal_odds"))
            home_won = safe_bool_won(row.get("money_home_won"))

            if not game_date_raw or not away_team or not home_team:
                skipped_missing_core += 1
                continue

            match_date = parse_date(game_date_raw)

            if not (MIN_GAME_DATE <= match_date <= MAX_GAME_DATE):
                skipped_outside_date_window += 1
                continue

            in_date_window += 1

            if home_decimal_odds is None or away_decimal_odds is None:
                skipped_bad_odds += 1
                continue

            home_prob, away_prob = fair_two_way_probs_from_decimal_odds(
                home_decimal_odds,
                away_decimal_odds,
            )

            if home_prob is None or not (0.0 < home_prob < 1.0):
                skipped_bad_odds += 1
                continue

            market_id = build_market_id(match_date, home_team, away_team)

            # Temporary bid/ask placeholders.
            # These will be replaced by real Polymarket historical prices
            # Later pipeline stages match this market_id to the corresponding Polymarket event.            
        

            pre_bid, pre_ask = clipped_bid_ask(home_prob, TOTAL_SYNTHETIC_SPREAD)

            pre_timestamp = match_date.replace(
                hour=12,
                minute=0,
                second=0,
                microsecond=0,
            ).isoformat()

            rows_out.append({
                "timestamp": pre_timestamp,
                "market_id": market_id,
                "best_bid": f"{pre_bid:.6f}",
                "best_ask": f"{pre_ask:.6f}",
                "bookmaker_prob": f"{home_prob:.6f}",
                "row_type": "PREGAME",
            })
            valid_pregame_rows += 1

            if home_won is None:
                skipped_no_result += 1
                continue

            settled_prob = 1.0 if home_won else 0.0

            settlement_timestamp = (
                match_date + timedelta(days=1)
            ).replace(
                hour=12,
                minute=0,
                second=0,
                microsecond=0,
            ).isoformat()

            rows_out.append({
                "timestamp": settlement_timestamp,
                "market_id": market_id,
                "best_bid": f"{settled_prob:.6f}",
                "best_ask": f"{settled_prob:.6f}",
                "bookmaker_prob": f"{settled_prob:.6f}",
                "row_type": "SETTLEMENT",
            })
            valid_settlement_rows += 1

    rows_out.sort(key=lambda row: (row["timestamp"], row["market_id"]))

    ensure_parent_dir(OUTPUT_FILE)

    with open(OUTPUT_FILE, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "timestamp",
                "market_id",
                "best_bid",
                "best_ask",
                "bookmaker_prob",
                "row_type",
            ],
        )
        writer.writeheader()
        writer.writerows(rows_out)

    print("\n=== NBA SOURCE BUILD SUMMARY ===")
    print(f"Input rows                  : {total_input_rows}")
    print(f"Rows in 2024/25 date window  : {in_date_window}")
    print(f"Pregame rows written        : {valid_pregame_rows}")
    print(f"Settlement rows written     : {valid_settlement_rows}")
    print(f"Total output rows           : {len(rows_out)}")
    print(f"Skipped outside date window : {skipped_outside_date_window}")
    print(f"Skipped missing core        : {skipped_missing_core}")
    print(f"Skipped bad odds            : {skipped_bad_odds}")
    print(f"Skipped no result           : {skipped_no_result}")
    print(f"Saved to                    : {OUTPUT_FILE}")


if __name__ == "__main__":
    convert()