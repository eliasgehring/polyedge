import pytest

from polyedge.data_loading import (
    filter_rows_by_pregame_date,
)


def row(
    market_id,
    timestamp,
    row_type,
):
    return {
        "market_id": market_id,
        "timestamp": timestamp,
        "row_type": row_type,
        "best_bid": "0.49",
        "best_ask": "0.51",
        "bookmaker_prob": "0.50",
    }


def test_window_uses_pregame_date_and_keeps_settlement():
    rows = [
        row(
            "market_a",
            "2025-02-28T23:00:00",
            "PREGAME",
        ),
        row(
            "market_a",
            "2025-03-01T02:00:00",
            "SETTLEMENT",
        ),
        row(
            "market_b",
            "2025-03-01T12:00:00",
            "PREGAME",
        ),
        row(
            "market_b",
            "2025-03-02T12:00:00",
            "SETTLEMENT",
        ),
    ]

    selected = filter_rows_by_pregame_date(
        rows,
        start_date="2025-02-28",
        end_date="2025-02-28",
    )

    assert len(selected) == 2
    assert {
        item["market_id"]
        for item in selected
    } == {"market_a"}

    assert {
        item["row_type"]
        for item in selected
    } == {"PREGAME", "SETTLEMENT"}


def test_adjacent_windows_do_not_overlap():
    rows = [
        row(
            "market_a",
            "2025-02-28T12:00:00",
            "PREGAME",
        ),
        row(
            "market_a",
            "2025-03-01T12:00:00",
            "SETTLEMENT",
        ),
        row(
            "market_b",
            "2025-03-01T12:00:00",
            "PREGAME",
        ),
        row(
            "market_b",
            "2025-03-02T12:00:00",
            "SETTLEMENT",
        ),
    ]

    development = filter_rows_by_pregame_date(
        rows,
        end_date="2025-02-28",
    )
    evaluation = filter_rows_by_pregame_date(
        rows,
        start_date="2025-03-01",
    )

    development_ids = {
        item["market_id"]
        for item in development
    }
    evaluation_ids = {
        item["market_id"]
        for item in evaluation
    }

    assert development_ids == {"market_a"}
    assert evaluation_ids == {"market_b"}
    assert development_ids.isdisjoint(evaluation_ids)


def test_invalid_window_order_is_rejected():
    with pytest.raises(ValueError):
        filter_rows_by_pregame_date(
            [],
            start_date="2025-03-01",
            end_date="2025-02-28",
        )


def test_invalid_date_format_is_rejected():
    with pytest.raises(ValueError):
        filter_rows_by_pregame_date(
            [],
            start_date="01-03-2025",
        )


def test_market_without_exactly_one_pregame_is_rejected():
    rows = [
        row(
            "market_a",
            "2025-03-01T12:00:00",
            "SETTLEMENT",
        ),
    ]

    with pytest.raises(ValueError):
        filter_rows_by_pregame_date(
            rows,
            start_date="2025-03-01",
        )
