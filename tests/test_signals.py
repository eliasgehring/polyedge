import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from models import MarketState
from signals import generate_signal


def test_positive_edge_buys_yes():
    market = MarketState(
        market_id="market_a",
        best_bid=0.49,
        best_ask=0.51,
    )

    signal = generate_signal(
        market=market,
        bookmaker_prob=0.60,
        threshold=0.01,
    )

    assert signal.edge == pytest.approx(0.09) 
    assert signal.action == "BUY_YES"


def test_negative_edge_buys_no():
    market = MarketState(
        market_id="market_a",
        best_bid=0.49,
        best_ask=0.51,
    )

    signal = generate_signal(
        market=market,
        bookmaker_prob=0.40,
        threshold=0.01,
    )
    
    assert signal.edge == pytest.approx(-0.09)
    assert signal.action == "BUY_NO"


def test_hold_inside_threshold():
    market = MarketState(
        market_id="market_a",
        best_bid=0.49,
        best_ask=0.51,
    )

    signal = generate_signal(
        market=market,
        bookmaker_prob=0.505,
        threshold=0.01,
    )

    assert signal.action == "HOLD"


def test_hold_when_market_probability_outside_allowed_band():
    market = MarketState(
        market_id="market_a",
        best_bid=0.89,
        best_ask=0.91,
    )

    signal = generate_signal(
        market=market,
        bookmaker_prob=0.99,
        threshold=0.01,
    )

    assert signal.action == "HOLD"