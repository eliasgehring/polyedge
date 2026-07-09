from polyedge.price_history import (
    select_latest_price_before_snapshot,
)


def test_selects_latest_price_before_snapshot():
    result = select_latest_price_before_snapshot(
        history=[
            {"t": 100, "p": 0.40},
            {"t": 150, "p": 0.45},
            {"t": 210, "p": 0.99},
        ],
        snapshot_timestamp=200,
        max_staleness_seconds=100,
    )

    assert result.reason is None
    assert result.price == 0.45
    assert result.timestamp == 150
    assert result.age_seconds == 50


def test_ignores_future_prices():
    result = select_latest_price_before_snapshot(
        history=[
            {"t": 100, "p": 0.40},
            {"t": 250, "p": 0.80},
        ],
        snapshot_timestamp=200,
        max_staleness_seconds=200,
    )

    assert result.reason is None
    assert result.price == 0.40
    assert result.timestamp == 100


def test_rejects_stale_price():
    result = select_latest_price_before_snapshot(
        history=[
            {"t": 100, "p": 0.40},
        ],
        snapshot_timestamp=1000,
        max_staleness_seconds=300,
    )

    assert result.price is None
    assert result.timestamp == 100
    assert result.age_seconds == 900
    assert result.reason == "price_too_stale"


def test_rejects_empty_history():
    result = select_latest_price_before_snapshot(
        history=[],
        snapshot_timestamp=1000,
        max_staleness_seconds=300,
    )

    assert result.price is None
    assert result.reason == "no_price_history"


def test_invalid_points_do_not_create_price():
    result = select_latest_price_before_snapshot(
        history=[
            {"t": "bad", "p": 0.40},
            {"t": 100, "p": 1.50},
            {"t": 200, "p": -0.10},
        ],
        snapshot_timestamp=300,
        max_staleness_seconds=300,
    )

    assert result.price is None
    assert result.reason == "no_valid_price_before_snapshot"
