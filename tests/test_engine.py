from legacy_models import Portfolio, MarketState
from portfolio import compute_portfolio_value


def test_latest_market_state_book_keeps_stale_market_values():
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

    latest_market_state_by_id = {}

    market_a_initial = MarketState(
        market_id="market_a",
        best_bid=0.49,
        best_ask=0.51,
    )
    market_b_initial = MarketState(
        market_id="market_b",
        best_bid=0.59,
        best_ask=0.61,
    )

    latest_market_state_by_id[market_a_initial.market_id] = market_a_initial
    latest_market_state_by_id[market_b_initial.market_id] = market_b_initial

    initial_value = compute_portfolio_value(
        portfolio,
        latest_market_state_by_id,
    )

    assert initial_value == 1002.0

    market_a_updated = MarketState(
        market_id="market_a",
        best_bid=0.69,
        best_ask=0.71,
    )

    latest_market_state_by_id[market_a_updated.market_id] = market_a_updated

    updated_value = compute_portfolio_value(
        portfolio,
        latest_market_state_by_id,
    )

    # cash = 993
    # market_a YES value = 10 * 0.70 = 7
    # market_b NO value still uses latest known B state: 10 * (1 - 0.60) = 4
    # total = 1004
    assert updated_value == 1004.0