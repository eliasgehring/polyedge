from polyedge.domain import Side, Signal
from polyedge.sizing import compute_trade_size


def test_hold_signal_has_zero_size():
    signal = Signal(
        market_id="market_a",
        side=None,
        model_prob_yes=0.50,
        market_prob_yes=0.50,
        edge_yes=0.00,
        edge_no=0.00,
        chosen_edge=0.00,
    )

    size = compute_trade_size(
        signal=signal,
        max_position_size=30.0,
        edge_size_multiplier=500.0,
    )

    assert size == 0.0


def test_trade_size_scales_with_buy_yes_edge():
    signal = Signal(
        market_id="market_a",
        side=Side.BUY_YES,
        model_prob_yes=0.60,
        market_prob_yes=0.50,
        edge_yes=0.10,
        edge_no=-0.10,
        chosen_edge=0.10,
    )

    size = compute_trade_size(
        signal=signal,
        max_position_size=100.0,
        edge_size_multiplier=200.0,
    )

    assert size == 20.0


def test_trade_size_uses_positive_edge_magnitude_for_buy_no():
    signal = Signal(
        market_id="market_a",
        side=Side.BUY_NO,
        model_prob_yes=0.40,
        market_prob_yes=0.50,
        edge_yes=-0.10,
        edge_no=0.10,
        chosen_edge=0.10,
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
        side=Side.BUY_YES,
        model_prob_yes=0.90,
        market_prob_yes=0.50,
        edge_yes=0.40,
        edge_no=-0.40,
        chosen_edge=0.40,
    )

    size = compute_trade_size(
        signal=signal,
        max_position_size=30.0,
        edge_size_multiplier=500.0,
    )

    assert size == 30.0
