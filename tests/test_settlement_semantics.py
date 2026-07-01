from legacy_models import Fill, MarketState
from portfolio import apply_fill, create_portfolio
from settlement import check_exit_conditions


def test_buy_no_closed_when_yes_resolves_reports_event_outcome_yes_true():
    portfolio = create_portfolio(1000.0)

    entry_market = MarketState(
        market_id="market_a",
        best_bid=0.64,
        best_ask=0.66,
    )

    apply_fill(
        portfolio,
        Fill(
            market_id="market_a",
            side="BUY_NO",
            price=0.35,
            size=10.0,
        ),
        entry_market,
    )

    resolved_market = MarketState(
        market_id="market_a",
        best_bid=1.0,
        best_ask=1.0,
    )

    exit_triggered, exit_reason, exit_side, realized_pnl = check_exit_conditions(
        portfolio,
        resolved_market,
    )

    assert exit_triggered is True
    assert exit_reason == "market resolved YES_TRUE"
    assert exit_side == "NO"
    assert realized_pnl == -3.5


def test_buy_yes_closed_when_yes_false_reports_event_outcome_yes_false():
    portfolio = create_portfolio(1000.0)

    entry_market = MarketState(
        market_id="market_a",
        best_bid=0.39,
        best_ask=0.41,
    )

    apply_fill(
        portfolio,
        Fill(
            market_id="market_a",
            side="BUY_YES",
            price=0.40,
            size=10.0,
        ),
        entry_market,
    )

    resolved_market = MarketState(
        market_id="market_a",
        best_bid=0.0,
        best_ask=0.0,
    )

    exit_triggered, exit_reason, exit_side, realized_pnl = check_exit_conditions(
        portfolio,
        resolved_market,
    )

    assert exit_triggered is True
    assert exit_reason == "market resolved YES_FALSE"
    assert exit_side == "YES"
    assert realized_pnl == -4.0