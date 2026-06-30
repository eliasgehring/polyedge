import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from models import Portfolio, Signal
from risk import get_trade_decision


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
        bookmaker_prob=0.40,
        polymarket_prob=0.50,
        edge=-0.10,
        action="BUY_NO",
    )

    approved, reason = get_trade_decision(
        signal=signal,
        portfolio=portfolio,
        max_position_size=30,
    )

    assert approved is False
    assert reason == "already in market"


def test_rejects_hold_signal():
    portfolio = Portfolio(cash=1000.0, positions={})

    signal = Signal(
        market_id="market_a",
        bookmaker_prob=0.50,
        polymarket_prob=0.50,
        edge=0.0,
        action="HOLD",
    )

    approved, reason = get_trade_decision(
        signal=signal,
        portfolio=portfolio,
        max_position_size=30,
    )

    assert approved is False
    assert reason == "HOLD signal"


def test_approves_trade_when_market_has_no_open_position():
    portfolio = Portfolio(cash=1000.0, positions={})

    signal = Signal(
        market_id="market_a",
        bookmaker_prob=0.60,
        polymarket_prob=0.50,
        edge=0.10,
        action="BUY_YES",
    )

    approved, reason = get_trade_decision(
        signal=signal,
        portfolio=portfolio,
        max_position_size=30,
    )

    assert approved is True
    assert reason == "approved"