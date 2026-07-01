import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from legacy_models import MarketState, Signal
from execution import simulate_fill
from config import BASE_SLIPPAGE, SIZE_IMPACT


def test_buy_yes_executes_at_yes_ask_plus_slippage():
    market = MarketState(
        market_id="market_a",
        best_bid=0.49,
        best_ask=0.51,
    )

    signal = Signal(
        market_id="market_a",
        bookmaker_prob=0.60,
        polymarket_prob=0.50,
        edge=0.10,
        action="BUY_YES",
    )

    size = 10.0
    fill = simulate_fill(signal, market, size)

    expected_slippage = BASE_SLIPPAGE + SIZE_IMPACT * size
    expected_price = market.best_ask + expected_slippage

    assert fill is not None
    assert fill.side == "BUY_YES"
    assert fill.price == pytest.approx(expected_price)
    assert fill.size == size


def test_buy_no_executes_at_no_ask_plus_slippage():
    market = MarketState(
        market_id="market_a",
        best_bid=0.49,
        best_ask=0.51,
    )

    signal = Signal(
        market_id="market_a",
        bookmaker_prob=0.40,
        polymarket_prob=0.50,
        edge=-0.10,
        action="BUY_NO",
    )

    size = 10.0
    fill = simulate_fill(signal, market, size)

    expected_slippage = BASE_SLIPPAGE + SIZE_IMPACT * size
    expected_price = (1.0 - market.best_bid) + expected_slippage

    assert fill is not None
    assert fill.side == "BUY_NO"
    assert fill.price == pytest.approx(expected_price)
    assert fill.size == size


def test_hold_signal_does_not_execute():
    market = MarketState(
        market_id="market_a",
        best_bid=0.49,
        best_ask=0.51,
    )

    signal = Signal(
        market_id="market_a",
        bookmaker_prob=0.50,
        polymarket_prob=0.50,
        edge=0.0,
        action="HOLD",
    )

    fill = simulate_fill(signal, market, size=10.0)

    assert fill is None