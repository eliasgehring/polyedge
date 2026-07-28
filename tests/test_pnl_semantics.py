import pytest

from polyedge.legacy_models import MarketState
from polyedge.portfolio import (
    compute_total_pnl,
    compute_unrealized_pnl,
    create_portfolio,
)


def test_closed_portfolio_has_zero_unrealized_pnl():
    portfolio = create_portfolio(1000.0)
    portfolio.cash = 1199.50

    result = compute_unrealized_pnl(
        portfolio=portfolio,
        latest_market_state_by_id={},
    )

    assert result == 0.0


def test_total_pnl_includes_realized_cash_gain():
    portfolio = create_portfolio(1000.0)
    portfolio.cash = 1199.50

    result = compute_total_pnl(
        portfolio=portfolio,
        latest_market_state_by_id={},
        starting_cash=1000.0,
    )

    assert result == 199.50


def test_open_yes_position_unrealized_pnl():
    portfolio = create_portfolio(1000.0)

    portfolio.positions["market_a"] = {
        "YES": {
            "size": 10.0,
            "avg_price": 0.40,
        },
        "NO": {
            "size": 0.0,
            "avg_price": 0.0,
        },
    }

    portfolio.cash = 996.0

    market = MarketState(
        market_id="market_a",
        best_bid=0.49,
        best_ask=0.51,
    )

    result = compute_unrealized_pnl(
        portfolio=portfolio,
        latest_market_state_by_id={
            "market_a": market,
        },
    )

    assert result == pytest.approx(1.0)


def test_total_pnl_equals_realized_plus_unrealized():
    portfolio = create_portfolio(1000.0)

    portfolio.positions["market_a"] = {
        "YES": {
            "size": 10.0,
            "avg_price": 0.40,
        },
        "NO": {
            "size": 0.0,
            "avg_price": 0.0,
        },
    }

    # Initial cost was 4.00. Cash also contains 5.00
    # of previously realized profit.
    portfolio.cash = 1001.0

    market = MarketState(
        market_id="market_a",
        best_bid=0.49,
        best_ask=0.51,
    )

    unrealized_pnl = compute_unrealized_pnl(
        portfolio=portfolio,
        latest_market_state_by_id={
            "market_a": market,
        },
    )

    total_pnl = compute_total_pnl(
        portfolio=portfolio,
        latest_market_state_by_id={
            "market_a": market,
        },
        starting_cash=1000.0,
    )

    cumulative_realized_pnl = (
        total_pnl - unrealized_pnl
    )

    assert unrealized_pnl == pytest.approx(1.0)
    assert total_pnl == pytest.approx(6.0)
    assert cumulative_realized_pnl == pytest.approx(5.0)
