import pytest

from polyedge.config import BASE_SLIPPAGE, SIZE_IMPACT
from polyedge.domain import MarketQuote, Side, Signal
from polyedge.execution import simulate_fill


def test_buy_yes_executes_at_yes_ask_plus_slippage():
    market = MarketQuote(
        market_id="market_a",
        best_bid=0.49,
        best_ask=0.51,
    )

    signal = Signal(
        market_id="market_a",
        side=Side.BUY_YES,
        model_prob_yes=0.60,
        market_prob_yes=0.50,
        edge_yes=0.09,
        edge_no=-0.11,
        chosen_edge=0.09,
    )

    size = 10.0
    fill = simulate_fill(signal, market, size)

    expected_slippage = BASE_SLIPPAGE + SIZE_IMPACT * size
    expected_price = market.best_ask + expected_slippage

    assert fill is not None
    assert fill.side is Side.BUY_YES
    assert fill.price == pytest.approx(expected_price)
    assert fill.size == size


def test_buy_no_executes_at_no_ask_plus_slippage():
    market = MarketQuote(
        market_id="market_a",
        best_bid=0.49,
        best_ask=0.51,
    )

    signal = Signal(
        market_id="market_a",
        side=Side.BUY_NO,
        model_prob_yes=0.40,
        market_prob_yes=0.50,
        edge_yes=-0.11,
        edge_no=0.09,
        chosen_edge=0.09,
    )

    size = 10.0
    fill = simulate_fill(signal, market, size)

    expected_slippage = BASE_SLIPPAGE + SIZE_IMPACT * size
    expected_price = (
        1.0 - market.best_bid
    ) + expected_slippage

    assert fill is not None
    assert fill.side is Side.BUY_NO
    assert fill.price == pytest.approx(expected_price)
    assert fill.size == size


def test_hold_signal_does_not_execute():
    market = MarketQuote(
        market_id="market_a",
        best_bid=0.49,
        best_ask=0.51,
    )

    signal = Signal(
        market_id="market_a",
        side=None,
        model_prob_yes=0.50,
        market_prob_yes=0.50,
        edge_yes=-0.01,
        edge_no=-0.01,
        chosen_edge=0.0,
    )

    fill = simulate_fill(
        signal,
        market,
        size=10.0,
    )

    assert fill is None
