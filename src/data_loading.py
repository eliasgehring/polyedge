import csv
from datetime import datetime

from models import MarketState


def parse_timestamp(timestamp_str: str) -> datetime:
    return datetime.fromisoformat(timestamp_str)


def load_historical_data(filepath: str):
    historical_data = []

    with open(filepath, mode="r", newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)

        for row in reader:
            timestamp = row["timestamp"].strip()

            market = MarketState(
                market_id=row["market_id"].strip(),
                best_bid=float(row["best_bid"]),
                best_ask=float(row["best_ask"]),
            )
            row_type = row.get("row_type", "").strip().upper()
            if row_type not in {"PREGAME", "SETTLEMENT"}:
                raise ValueError(f"Invalid row_type: {row_type}")

            # bookmaker fair / normalized probability
            bookmaker_prob = float(row["bookmaker_prob"])


            historical_data.append((timestamp, market, bookmaker_prob, row_type))

    historical_data.sort(key=lambda x: parse_timestamp(x[0]))
    return historical_data