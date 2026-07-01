import pytest

from polyedge.legacy_models import Fill, MarketState, Portfolio, Signal


def test_market_state_rejects_crossed_bid_ask():
    with pytest.raises(ValueError):
        MarketState(
            market_id="market_1",
            best_bid=0.60,
            best_ask=0.50,
        )


def test_market_state_rejects_invalid_probability():
    with pytest.raises(ValueError):
        MarketState(
            market_id="market_1",
            best_bid=-0.01,
            best_ask=0.50,
        )


def test_signal_rejects_unknown_action():
    with pytest.raises(ValueError):
        Signal(
            market_id="market_1",
            bookmaker_prob=0.60,
            polymarket_prob=0.50,
            edge=0.10,
            action="BUY",
        )


def test_signal_allows_signed_edge_for_buy_no_compatibility():
    signal = Signal(
        market_id="market_1",
        bookmaker_prob=0.40,
        polymarket_prob=0.50,
        edge=-0.09,
        action="BUY_NO",
    )

    assert signal.edge == pytest.approx(-0.09)
    assert signal.action == "BUY_NO"


def test_fill_rejects_unknown_side():
    with pytest.raises(ValueError):
        Fill(
            market_id="market_1",
            side="YES",
            price=0.50,
            size=10.0,
        )


def test_fill_rejects_non_positive_size():
    with pytest.raises(ValueError):
        Fill(
            market_id="market_1",
            side="BUY_YES",
            price=0.50,
            size=0.0,
        )


def test_portfolio_requires_positions_dict():
    with pytest.raises(TypeError):
        Portfolio(
            cash=1000.0,
            positions=[],
        )