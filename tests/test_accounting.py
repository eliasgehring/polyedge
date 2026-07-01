import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from legacy_models import Portfolio, MarketState, Fill
from portfolio import (
    create_portfolio,
    apply_fill,
    close_position,
    compute_portfolio_value,
)


def test_global_portfolio_value_includes_all_open_markets():
    portfolio = Portfolio(
        cash=993.0,
        positions={
            "market_a": {
                "YES": {"size": 10.0, "avg_price": 0.40},
                "NO": {"size": 0.0, "avg_price": 0.0},
            },
            "market_b": {
                "YES": {"size": 0.0, "avg_price": 0.0},
                "NO": {"size": 10.0, "avg_price": 0.30},
            },
        },
    )

    latest_market_state_by_id = {
        "market_a": MarketState(
            market_id="market_a",
            best_bid=0.49,
            best_ask=0.51,
        ),
        "market_b": MarketState(
            market_id="market_b",
            best_bid=0.59,
            best_ask=0.61,
        ),
    }

    total_value = compute_portfolio_value(
        portfolio,
        latest_market_state_by_id,
    )

    assert total_value == 1002.0




def test_buy_yes_resolves_yes():
    portfolio = create_portfolio(1000.0)

    entry_market = MarketState(
        market_id="market_yes",
        best_bid=0.39,
        best_ask=0.41,
    )
    fill = Fill(
        market_id="market_yes",
        side="BUY_YES",
        price=0.40,
        size=10.0,
    )

    apply_fill(portfolio, fill, entry_market)

    assert portfolio.cash == 996.0

    resolved_market = MarketState(
        market_id="market_yes",
        best_bid=1.0,
        best_ask=1.0,
    )
    realized_pnl = close_position(portfolio, resolved_market, "YES")

    assert realized_pnl == 6.0
    assert portfolio.cash == 1006.0


def test_buy_yes_resolves_no():
    portfolio = create_portfolio(1000.0)

    entry_market = MarketState(
        market_id="market_yes",
        best_bid=0.39,
        best_ask=0.41,
    )
    fill = Fill(
        market_id="market_yes",
        side="BUY_YES",
        price=0.40,
        size=10.0,
    )

    apply_fill(portfolio, fill, entry_market)

    resolved_market = MarketState(
        market_id="market_yes",
        best_bid=0.0,
        best_ask=0.0,
    )
    realized_pnl = close_position(portfolio, resolved_market, "YES")

    assert realized_pnl == -4.0
    assert portfolio.cash == 996.0


def test_buy_no_resolves_no():
    portfolio = create_portfolio(1000.0)

    entry_market = MarketState(
        market_id="market_no",
        best_bid=0.64,
        best_ask=0.66,
    )
    fill = Fill(
        market_id="market_no",
        side="BUY_NO",
        price=0.35,
        size=10.0,
    )

    apply_fill(portfolio, fill, entry_market)

    assert portfolio.cash == 996.5

    resolved_market = MarketState(
        market_id="market_no",
        best_bid=0.0,
        best_ask=0.0,
    )
    realized_pnl = close_position(portfolio, resolved_market, "NO")

    assert realized_pnl == 6.5
    assert portfolio.cash == 1006.5


def test_buy_no_resolves_yes():
    portfolio = create_portfolio(1000.0)

    entry_market = MarketState(
        market_id="market_no",
        best_bid=0.64,
        best_ask=0.66,
    )
    fill = Fill(
        market_id="market_no",
        side="BUY_NO",
        price=0.35,
        size=10.0,
    )

    apply_fill(portfolio, fill, entry_market)

    resolved_market = MarketState(
        market_id="market_no",
        best_bid=1.0,
        best_ask=1.0,
    )
    realized_pnl = close_position(portfolio, resolved_market, "NO")

    assert realized_pnl == -3.5
    assert portfolio.cash == 996.5 