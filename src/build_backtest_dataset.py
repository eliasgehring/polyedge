import os
import csv

from paths import (
    HISTORICAL_READY_DIR,
    HISTORICAL_DATA_FILE,
    ensure_parent_dir,
)


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

RAW_DIR = HISTORICAL_READY_DIR
OUTPUT_FILE = HISTORICAL_DATA_FILE

REQUIRED_COLUMNS = [
    "timestamp",
    "market_id",
    "best_bid",
    "best_ask",
    "bookmaker_prob",
    "row_type"
]

SKIP_FILES = {
    "review_needed.csv",
}


def is_settlement_row(row):
    try:
        bid = float(row["best_bid"])
        ask = float(row["best_ask"])
        prob = float(row["bookmaker_prob"])
    except Exception:
        return False

    return (
        bid in (0.0, 1.0)
        and ask in (0.0, 1.0)
        and prob in (0.0, 1.0)
        and bid == ask == prob
    )


def is_valid_pregame_row(row):
    try:
        bid = float(row["best_bid"])
        ask = float(row["best_ask"])
        prob = float(row["bookmaker_prob"])

        if not (0.0 < bid < 1.0):
            return False
        if not (0.0 < ask < 1.0):
            return False
        if not (0.0 < prob < 1.0):
            return False
        if bid > ask:
            return False

        return True
    except Exception:
        return False


def is_valid_row(row):
    return is_settlement_row(row) or is_valid_pregame_row(row)


def load_file(filepath):
    rows = []

    with open(filepath, mode="r", newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)

        if reader.fieldnames is None:
            print("Skipping empty file: {}".format(filepath))
            return rows

        for col in REQUIRED_COLUMNS:
            if col not in reader.fieldnames:
                raise ValueError("{} missing column {}".format(filepath, col))

        for row in reader:
            if is_valid_row(row):
                cleaned_row = {
                    "timestamp": row["timestamp"],
                    "market_id": row["market_id"],
                    "best_bid": row["best_bid"],
                    "best_ask": row["best_ask"],
                    "bookmaker_prob": row["bookmaker_prob"],
                    "row_type": row["row_type"],
                }
                rows.append(cleaned_row)

    return rows


def merge_all_files():
    all_rows = []

    files = [
        f for f in os.listdir(RAW_DIR)
        if f.endswith(".csv") and f not in SKIP_FILES
    ]

    if not files:
        raise ValueError("No usable CSV files found in {}".format(RAW_DIR))

    print("Found {} usable files".format(len(files)))

    for filename in sorted(files):
        path = os.path.join(RAW_DIR, filename)

        try:
            rows = load_file(path)
        except ValueError as e:
            print("Skipping {} because: {}".format(filename, e))
            continue

        print("{}: {} valid rows".format(filename, len(rows)))
        all_rows.extend(rows)

    all_rows.sort(key=lambda x: (x["timestamp"], x["market_id"]))

    print("\nTOTAL ROWS: {}".format(len(all_rows)))
    return all_rows


def save_output(rows):
    ensure_parent_dir(OUTPUT_FILE)

    with open(OUTPUT_FILE, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=REQUIRED_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    print("\nSaved merged file -> {}".format(OUTPUT_FILE))


def main():
    rows = merge_all_files()
    save_output(rows)


if __name__ == "__main__":
    main()