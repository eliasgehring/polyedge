import csv
import json
from collections import Counter, defaultdict
from datetime import datetime

from .paths import (
    HISTORICAL_DATA_FILE,
    DATASET_DIAGNOSTICS_FILE,
    ensure_parent_dir,
)


REQUIRED_COLUMNS = [
    "timestamp",
    "market_id",
    "best_bid",
    "best_ask",
    "bookmaker_prob",
    "row_type"
]


def parse_float(value):
    try:
        return float(value)
    except Exception:
        return None


def parse_timestamp(value):
    try:
        return datetime.fromisoformat(str(value))
    except Exception:
        return None


def is_settlement_row(row):
    return str(row.get("row_type", "")).strip().upper() == "SETTLEMENT"


def load_rows(filepath):
    with open(filepath, mode="r", newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)

        missing_columns = [
            column
            for column in REQUIRED_COLUMNS
            if column not in reader.fieldnames
        ]

        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")

        return list(reader)


def build_diagnostics(rows):
    market_counts = Counter(row["market_id"] for row in rows)
    rows_by_market = defaultdict(list)

    pregame_rows = []
    settlement_rows = []

    bad_timestamps = 0
    malformed_numeric_rows = 0
    bid_greater_than_ask = 0
    probability_out_of_bounds = 0
    invalid_row_type = 0

    timestamps = []

    for row in rows:
        rows_by_market[row["market_id"]].append(row)

        row_type = str(row.get("row_type", "")).strip().upper()

        if row_type not in {"PREGAME", "SETTLEMENT"}:
            invalid_row_type += 1

        timestamp = parse_timestamp(row.get("timestamp"))
        if timestamp is None:
            bad_timestamps += 1
        else:
            timestamps.append(timestamp)

        best_bid = parse_float(row.get("best_bid"))
        best_ask = parse_float(row.get("best_ask"))
        bookmaker_prob = parse_float(row.get("bookmaker_prob"))

        if best_bid is None or best_ask is None or bookmaker_prob is None:
            malformed_numeric_rows += 1
            continue

        if best_bid > best_ask:
            bid_greater_than_ask += 1

        if not (0.0 <= best_bid <= 1.0):
            probability_out_of_bounds += 1

        if not (0.0 <= best_ask <= 1.0):
            probability_out_of_bounds += 1

        if not (0.0 <= bookmaker_prob <= 1.0):
            probability_out_of_bounds += 1

        if row_type == "PREGAME":
            pregame_rows.append(row)
        elif row_type == "SETTLEMENT":
            settlement_rows.append(row)

    missing_pregames = 0
    missing_settlements = 0
    duplicate_pregame_markets = 0
    duplicate_settlement_markets = 0
    settlement_not_after_pregame = 0
    invalid_settlement_prices = 0

    for market_id, market_rows in rows_by_market.items():
        market_pregame_rows = [
            row
            for row in market_rows
            if str(row.get("row_type", "")).strip().upper() == "PREGAME"
        ]
        market_settlement_rows = [
            row
            for row in market_rows
            if str(row.get("row_type", "")).strip().upper() == "SETTLEMENT"
        ]

        if len(market_pregame_rows) == 0:
            missing_pregames += 1

        if len(market_settlement_rows) == 0:
            missing_settlements += 1

        if len(market_pregame_rows) > 1:
            duplicate_pregame_markets += 1

        if len(market_settlement_rows) > 1:
            duplicate_settlement_markets += 1

        if len(market_pregame_rows) == 1 and len(market_settlement_rows) == 1:
            pregame_timestamp = parse_timestamp(
                market_pregame_rows[0].get("timestamp")
            )
            settlement_timestamp = parse_timestamp(
                market_settlement_rows[0].get("timestamp")
            )

            if (
                pregame_timestamp is not None
                and settlement_timestamp is not None
                and settlement_timestamp <= pregame_timestamp
            ):
                settlement_not_after_pregame += 1

        for settlement_row in market_settlement_rows:
            settlement_bid = parse_float(settlement_row.get("best_bid"))
            settlement_ask = parse_float(settlement_row.get("best_ask"))

            if settlement_bid is None or settlement_ask is None:
                continue

            settlement_midpoint = (
                settlement_bid + settlement_ask
            ) / 2.0

            resolved_yes = settlement_midpoint >= 0.99
            resolved_no = settlement_midpoint <= 0.01

            if not (resolved_yes or resolved_no):
                invalid_settlement_prices += 1

    diagnostics = {
        "rows": len(rows),
        "markets": len(market_counts),
        "pregame_rows": len(pregame_rows),
        "settlement_rows": len(settlement_rows),
        "missing_pregames": missing_pregames,
        "missing_settlements": missing_settlements,
        "duplicate_pregame_markets": duplicate_pregame_markets,
        "duplicate_settlement_markets": duplicate_settlement_markets,
        "bad_timestamps": bad_timestamps,
        "malformed_numeric_rows": malformed_numeric_rows,
        "bid_greater_than_ask": bid_greater_than_ask,
        "probability_out_of_bounds": probability_out_of_bounds,
        "invalid_row_type": invalid_row_type,
        "settlement_not_after_pregame": settlement_not_after_pregame,
        "invalid_settlement_prices": invalid_settlement_prices,
        "min_timestamp": min(timestamps).isoformat() if timestamps else None,
        "max_timestamp": max(timestamps).isoformat() if timestamps else None,
        "synthetic_bid_ask": True,
    }

    hard_fail_fields = [
        "missing_pregames",
        "missing_settlements",
        "settlement_not_after_pregame",
        "invalid_settlement_prices",
        "duplicate_pregame_markets",
        "duplicate_settlement_markets",
        "bad_timestamps",
        "malformed_numeric_rows",
        "bid_greater_than_ask",
        "probability_out_of_bounds",
        "invalid_row_type",
    ]

    diagnostics["hard_fail"] = any(
        diagnostics[field] > 0
        for field in hard_fail_fields
    )

    return diagnostics

def save_diagnostics(diagnostics):
    ensure_parent_dir(DATASET_DIAGNOSTICS_FILE)

    with open(DATASET_DIAGNOSTICS_FILE, mode="w", encoding="utf-8") as file:
        json.dump(diagnostics, file, indent=2)


def print_diagnostics(diagnostics):
    print("\n" + "=" * 60)
    print("DATASET DIAGNOSTICS")
    print("=" * 60)

    for key, value in diagnostics.items():
        print(f"{key:<30}: {value}")

    print("=" * 60)


def main():
    rows = load_rows(HISTORICAL_DATA_FILE)
    diagnostics = build_diagnostics(rows)

    save_diagnostics(diagnostics)
    print_diagnostics(diagnostics)

    if diagnostics["hard_fail"]:
        raise ValueError(
            "Dataset diagnostics failed. "
            f"See {DATASET_DIAGNOSTICS_FILE}"
        )


if __name__ == "__main__":
    main()