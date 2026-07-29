import pytest

from polyedge.domain import MarketQuote, Side
from polyedge.signals import generate_signal


def test_positive_edge_buys_yes():
    market = MarketQuote(
        market_id="market_a",
        best_bid=0.49,
        best_ask=0.51,
    )

    signal = generate_signal(
        market=market,
        bookmaker_prob=0.60,
        threshold=0.01,
    )

    assert signal.side is Side.BUY_YES
    assert signal.chosen_edge == pytest.approx(0.09)
    assert signal.signed_edge == pytest.approx(0.09)
    assert signal.action == "BUY_YES"


def test_negative_edge_buys_no():
    market = MarketQuote(
        market_id="market_a",
        best_bid=0.49,
        best_ask=0.51,
    )

    signal = generate_signal(
        market=market,
        bookmaker_prob=0.40,
        threshold=0.01,
    )

    assert signal.side is Side.BUY_NO
    assert signal.chosen_edge == pytest.approx(0.09)
    assert signal.signed_edge == pytest.approx(-0.09)
    assert signal.action == "BUY_NO"


def test_hold_inside_threshold():
    market = MarketQuote(
        market_id="market_a",
        best_bid=0.49,
        best_ask=0.51,
    )

    signal = generate_signal(
        market=market,
        bookmaker_prob=0.505,
        threshold=0.01,
    )

    assert signal.side is None
    assert signal.chosen_edge == 0.0
    assert signal.signed_edge == 0.0
    assert signal.action == "HOLD"


def test_hold_when_market_probability_outside_allowed_band():
    market = MarketQuote(
        market_id="market_a",
        best_bid=0.89,
        best_ask=0.91,
    )

    signal = generate_signal(
        market=market,
        bookmaker_prob=0.99,
        threshold=0.01,
    )

    assert signal.side is None
    assert signal.chosen_edge == 0.0
    assert signal.signed_edge == 0.0
    assert signal.action == "HOLD"
