from polyedge.domain import Side, Signal
from polyedge.domain import Portfolio
from polyedge.risk import get_trade_decision


def test_rejects_trade_when_market_already_has_open_position():
    portfolio = Portfolio(
        cash=1000.0,
        positions={
            "market_a": {
                "YES": {"size": 10.0, "avg_price": 0.40},
                "NO": {"size": 0.0, "avg_price": 0.0},
            },
        },
    )

    signal = Signal(
        market_id="market_a",
        side=Side.BUY_NO,
        model_prob_yes=0.40,
        market_prob_yes=0.50,
        edge_yes=-0.10,
        edge_no=0.10,
        chosen_edge=0.10,
    )

    approved, reason = get_trade_decision(
        signal=signal,
        portfolio=portfolio,
        max_position_size=30,
    )

    assert approved is False
    assert reason == "already in market"


def test_rejects_hold_signal():
    portfolio = Portfolio(
        cash=1000.0,
        positions={},
    )

    signal = Signal(
        market_id="market_a",
        side=None,
        model_prob_yes=0.50,
        market_prob_yes=0.50,
        edge_yes=0.00,
        edge_no=0.00,
        chosen_edge=0.00,
    )

    approved, reason = get_trade_decision(
        signal=signal,
        portfolio=portfolio,
        max_position_size=30,
    )

    assert approved is False
    assert reason == "HOLD signal"


def test_approves_trade_when_market_has_no_open_position():
    portfolio = Portfolio(
        cash=1000.0,
        positions={},
    )

    signal = Signal(
        market_id="market_a",
        side=Side.BUY_YES,
        model_prob_yes=0.60,
        market_prob_yes=0.50,
        edge_yes=0.10,
        edge_no=-0.10,
        chosen_edge=0.10,
    )

    approved, reason = get_trade_decision(
        signal=signal,
        portfolio=portfolio,
        max_position_size=30,
    )

    assert approved is True
    assert reason == "approved"
