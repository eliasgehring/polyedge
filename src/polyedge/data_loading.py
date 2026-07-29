import csv
from collections import defaultdict
from datetime import date, datetime
from typing import Dict, List, Optional

from .domain import MarketQuote


def parse_timestamp(timestamp_str: str) -> datetime:
    return datetime.fromisoformat(timestamp_str)


def parse_date_bound(
    value: Optional[str],
    name: str,
) -> Optional[date]:
    if value is None:
        return None

    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(
            f"{name} must use YYYY-MM-DD format, got {value!r}"
        ) from exc


def filter_rows_by_pregame_date(
    rows: List[Dict[str, str]],
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> List[Dict[str, str]]:
    """
    Select complete markets using the PREGAME calendar date.

    Once a market is selected, all of its rows are retained, including
    settlement rows occurring after the end of the selected window.
    """

    start = parse_date_bound(start_date, "start_date")
    end = parse_date_bound(end_date, "end_date")

    if start is not None and end is not None and start > end:
        raise ValueError(
            f"start_date must be <= end_date, got "
            f"{start_date} > {end_date}"
        )

    if start is None and end is None:
        return list(rows)

    rows_by_market = defaultdict(list)

    for row in rows:
        market_id = row["market_id"].strip()
        rows_by_market[market_id].append(row)

    selected_market_ids = set()

    for market_id, market_rows in rows_by_market.items():
        pregame_rows = [
            row
            for row in market_rows
            if row.get("row_type", "").strip().upper() == "PREGAME"
        ]

        if len(pregame_rows) != 1:
            raise ValueError(
                f"{market_id} must have exactly one PREGAME row "
                f"before date filtering, got {len(pregame_rows)}"
            )

        pregame_date = parse_timestamp(
            pregame_rows[0]["timestamp"].strip()
        ).date()

        if start is not None and pregame_date < start:
            continue

        if end is not None and pregame_date > end:
            continue

        selected_market_ids.add(market_id)

    return [
        row
        for row in rows
        if row["market_id"].strip() in selected_market_ids
    ]


def historical_data_from_rows(rows):
    historical_data = []

    for row in rows:
        timestamp = row["timestamp"].strip()

        market = MarketQuote(
            market_id=row["market_id"].strip(),
            best_bid=float(row["best_bid"]),
            best_ask=float(row["best_ask"]),
        )

        row_type = row.get("row_type", "").strip().upper()

        if row_type not in {"PREGAME", "SETTLEMENT"}:
            raise ValueError(f"Invalid row_type: {row_type}")

        bookmaker_prob = float(row["bookmaker_prob"])

        historical_data.append(
            (
                timestamp,
                market,
                bookmaker_prob,
                row_type,
            )
        )

    historical_data.sort(
        key=lambda item: parse_timestamp(item[0])
    )

    return historical_data


def load_historical_data(
    filepath: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
):
    with open(
        filepath,
        mode="r",
        newline="",
        encoding="utf-8",
    ) as file:
        rows = list(csv.DictReader(file))

    filtered_rows = filter_rows_by_pregame_date(
        rows,
        start_date=start_date,
        end_date=end_date,
    )

    return historical_data_from_rows(filtered_rows)
