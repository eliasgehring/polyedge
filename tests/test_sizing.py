from legacy_models import Signal
from sizing import compute_trade_size


def test_hold_signal_has_zero_size():
    signal = Signal(
        market_id="market_a",
        bookmaker_prob=0.50,
        polymarket_prob=0.50,
        edge=0.00,
        action="HOLD",
    )

    size = compute_trade_size(
        signal=signal,
        max_position_size=30.0,
        edge_size_multiplier=500.0,
    )

    assert size == 0.0


def test_trade_size_scales_with_absolute_edge():
    signal = Signal(
        market_id="market_a",
        bookmaker_prob=0.60,
        polymarket_prob=0.50,
        edge=0.10,
        action="BUY_YES",
    )

    size = compute_trade_size(
        signal=signal,
        max_position_size=100.0,
        edge_size_multiplier=200.0,
    )

    assert size == 20.0


def test_trade_size_uses_absolute_edge_for_buy_no():
    signal = Signal(
        market_id="market_a",
        bookmaker_prob=0.40,
        polymarket_prob=0.50,
        edge=-0.10,
        action="BUY_NO",
    )

    size = compute_trade_size(
        signal=signal,
        max_position_size=100.0,
        edge_size_multiplier=200.0,
    )

    assert size == 20.0


def test_trade_size_is_capped_by_max_position_size():
    signal = Signal(
        market_id="market_a",
        bookmaker_prob=0.90,
        polymarket_prob=0.50,
        edge=0.40,
        action="BUY_YES",
    )

    size = compute_trade_size(
        signal=signal,
        max_position_size=30.0,
        edge_size_multiplier=500.0,
    )

    assert size == 30.0