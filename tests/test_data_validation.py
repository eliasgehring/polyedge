from polyedge.data_validation import build_diagnostics


def valid_rows():
    return [
        {
            "timestamp": "2024-10-22T21:30:00",
            "market_id": "market_a",
            "best_bid": "0.49",
            "best_ask": "0.51",
            "bookmaker_prob": "0.55",
            "row_type": "PREGAME"
        },
        {
            "timestamp": "2024-10-23T12:00:00",
            "market_id": "market_a",
            "best_bid": "1.0",
            "best_ask": "1.0",
            "bookmaker_prob": "1.0",
            "row_type": "SETTLEMENT"
        },
    ]


def test_valid_dataset_does_not_hard_fail():
    diagnostics = build_diagnostics(valid_rows())

    assert diagnostics["rows"] == 2
    assert diagnostics["markets"] == 1
    assert diagnostics["pregame_rows"] == 1
    assert diagnostics["settlement_rows"] == 1
    assert diagnostics["hard_fail"] is False


def test_missing_settlement_hard_fails():
    rows = [
        {
            "timestamp": "2024-10-22T21:30:00",
            "market_id": "market_a",
            "best_bid": "0.49",
            "best_ask": "0.51",
            "bookmaker_prob": "0.55",
        },
    ]

    diagnostics = build_diagnostics(rows)

    assert diagnostics["missing_settlements"] == 1
    assert diagnostics["hard_fail"] is True


def test_duplicate_pregame_hard_fails():
    rows = valid_rows()
    rows.insert(
        1,
        {
            "timestamp": "2024-10-22T22:00:00",
            "market_id": "market_a",
            "best_bid": "0.50",
            "best_ask": "0.52",
            "bookmaker_prob": "0.56",
            "row_type": "PREGAME",
        },
    )

    diagnostics = build_diagnostics(rows)

    assert diagnostics["duplicate_pregame_markets"] == 1
    assert diagnostics["hard_fail"] is True


def test_bid_greater_than_ask_hard_fails():
    rows = valid_rows()
    rows[0]["best_bid"] = "0.60"
    rows[0]["best_ask"] = "0.50"

    diagnostics = build_diagnostics(rows)

    assert diagnostics["bid_greater_than_ask"] == 1
    assert diagnostics["hard_fail"] is True


def test_probability_out_of_bounds_hard_fails():
    rows = valid_rows()
    rows[0]["bookmaker_prob"] = "1.20"

    diagnostics = build_diagnostics(rows)

    assert diagnostics["probability_out_of_bounds"] == 1
    assert diagnostics["hard_fail"] is True

def test_invalid_row_type_hard_fails():
    rows = valid_rows()
    rows[0]["row_type"] = "QUOTE"

    diagnostics = build_diagnostics(rows)

    assert diagnostics["invalid_row_type"] == 1
    assert diagnostics["hard_fail"] is True

def test_settlement_must_be_after_pregame():
    rows = [
        {
            "timestamp": "2024-10-23T12:00:00",
            "market_id": "market_a",
            "best_bid": "0.49",
            "best_ask": "0.51",
            "bookmaker_prob": "0.55",
            "row_type": "PREGAME",
        },
        {
            "timestamp": "2024-10-23T12:00:00",
            "market_id": "market_a",
            "best_bid": "1.0",
            "best_ask": "1.0",
            "bookmaker_prob": "1.0",
            "row_type": "SETTLEMENT",
        },
    ]

    diagnostics = build_diagnostics(rows)

    assert diagnostics["settlement_not_after_pregame"] == 1
    assert diagnostics["hard_fail"] is True

def test_settlement_before_pregame_hard_fails():
    rows = [
        {
            "timestamp": "2024-10-23T12:00:00",
            "market_id": "market_a",
            "best_bid": "0.49",
            "best_ask": "0.51",
            "bookmaker_prob": "0.55",
            "row_type": "PREGAME",
        },
        {
            "timestamp": "2024-10-22T12:00:00",
            "market_id": "market_a",
            "best_bid": "1.0",
            "best_ask": "1.0",
            "bookmaker_prob": "1.0",
            "row_type": "SETTLEMENT",
        },
    ]

    diagnostics = build_diagnostics(rows)

    assert diagnostics["settlement_not_after_pregame"] == 1
    assert diagnostics["hard_fail"] is True

def test_missing_pregame_hard_fails():
    rows = [
        {
            "timestamp": "2025-01-02T12:00:00",
            "market_id": "market_1",
            "best_bid": "1.0",
            "best_ask": "1.0",
            "bookmaker_prob": "1.0",
            "row_type": "SETTLEMENT",
        }
    ]

    diagnostics = build_diagnostics(rows)

    assert diagnostics["missing_pregames"] == 1
    assert diagnostics["hard_fail"] is True


def test_unresolved_settlement_price_hard_fails():
    rows = [
        {
            "timestamp": "2025-01-01T12:00:00",
            "market_id": "market_1",
            "best_bid": "0.49",
            "best_ask": "0.51",
            "bookmaker_prob": "0.60",
            "row_type": "PREGAME",
        },
        {
            "timestamp": "2025-01-02T12:00:00",
            "market_id": "market_1",
            "best_bid": "0.45",
            "best_ask": "0.55",
            "bookmaker_prob": "1.0",
            "row_type": "SETTLEMENT",
        },
    ]

    diagnostics = build_diagnostics(rows)

    assert diagnostics["invalid_settlement_prices"] == 1
    assert diagnostics["hard_fail"] is True


def test_resolved_yes_settlement_passes():
    rows = [
        {
            "timestamp": "2025-01-01T12:00:00",
            "market_id": "market_1",
            "best_bid": "0.49",
            "best_ask": "0.51",
            "bookmaker_prob": "0.60",
            "row_type": "PREGAME",
        },
        {
            "timestamp": "2025-01-02T12:00:00",
            "market_id": "market_1",
            "best_bid": "1.0",
            "best_ask": "1.0",
            "bookmaker_prob": "1.0",
            "row_type": "SETTLEMENT",
        },
    ]

    diagnostics = build_diagnostics(rows)

    assert diagnostics["invalid_settlement_prices"] == 0
    assert diagnostics["hard_fail"] is False


def test_resolved_no_settlement_passes():
    rows = [
        {
            "timestamp": "2025-01-01T12:00:00",
            "market_id": "market_1",
            "best_bid": "0.49",
            "best_ask": "0.51",
            "bookmaker_prob": "0.60",
            "row_type": "PREGAME",
        },
        {
            "timestamp": "2025-01-02T12:00:00",
            "market_id": "market_1",
            "best_bid": "0.0",
            "best_ask": "0.0",
            "bookmaker_prob": "0.0",
            "row_type": "SETTLEMENT",
        },
    ]

    diagnostics = build_diagnostics(rows)

    assert diagnostics["invalid_settlement_prices"] == 0
    assert diagnostics["hard_fail"] is False

def test_missing_row_type_hard_fails():
    rows = valid_rows()
    rows[0].pop("row_type")

    diagnostics = build_diagnostics(rows)

    assert diagnostics["invalid_row_type"] == 1
    assert diagnostics["hard_fail"] is True