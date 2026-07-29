import pytest

from polyedge.domain import Fill, MarketQuote, Side, Signal
from polyedge.legacy_models import Portfolio


def test_market_state_rejects_crossed_bid_ask():
    with pytest.raises(ValueError):
        MarketQuote(
            market_id="market_1",
            best_bid=0.60,
            best_ask=0.50,
        )


def test_market_state_rejects_invalid_probability():
    with pytest.raises(ValueError):
        MarketQuote(
            market_id="market_1",
            best_bid=-0.01,
            best_ask=0.50,
        )


def test_signal_rejects_unknown_side_type():
    with pytest.raises(TypeError):
        Signal(
            market_id="market_1",
            side="BUY",
            model_prob_yes=0.60,
            market_prob_yes=0.50,
            edge_yes=0.10,
            edge_no=-0.10,
            chosen_edge=0.10,
        )


def test_signal_exposes_signed_edge_for_buy_no_logs():
    signal = Signal(
        market_id="market_1",
        side=Side.BUY_NO,
        model_prob_yes=0.40,
        market_prob_yes=0.50,
        edge_yes=-0.09,
        edge_no=0.09,
        chosen_edge=0.09,
    )

    assert signal.signed_edge == pytest.approx(-0.09)
    assert signal.action == "BUY_NO"


def test_fill_rejects_unknown_side():
    with pytest.raises(TypeError):
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
            side=Side.BUY_YES,
            price=0.50,
            size=0.0,
        )


def test_portfolio_requires_positions_dict():
    with pytest.raises(TypeError):
        Portfolio(
            cash=1000.0,
            positions=[],
        )