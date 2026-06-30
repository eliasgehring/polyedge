from models import Portfolio, Fill, MarketState
from features import compute_midpoint
from positions import (
    ensure_market_position,
    get_market_position,
    set_yes_position,
    set_no_position,
    clear_yes_position,
    clear_no_position,
)


def create_portfolio(starting_cash: float) -> Portfolio:
    return Portfolio(
        cash=starting_cash,
        positions={}
    )


# returns REALIZED PnL
def close_position(portfolio: Portfolio, market: MarketState, side: str) -> float:
    if market.market_id not in portfolio.positions:
        return 0.0

    positions_in_market = portfolio.positions[market.market_id]

    if side == "YES":
        side_data = positions_in_market["YES"]
        close_price = compute_midpoint(market.best_bid, market.best_ask)
    elif side == "NO":
        side_data = positions_in_market["NO"]
        close_price = 1 - compute_midpoint(market.best_bid, market.best_ask)
    else:
        return 0.0

    size = side_data["size"]
    avg_price = side_data["avg_price"]

    if size <= 0:
        return 0.0

    realized_pnl = size * (close_price - avg_price)

    cash_return = size * close_price
    cash_return = size * close_price
    portfolio.cash += cash_return
    if side == "YES":
        clear_yes_position(portfolio, market.market_id)
    elif side == "NO":
        clear_no_position(portfolio, market.market_id)
    return realized_pnl


def apply_fill(portfolio: Portfolio, fill: Fill, market: MarketState) -> None:
    market_positions = ensure_market_position(portfolio, fill.market_id)

    if fill.side == "BUY_YES":
        if market_positions["YES"]["size"] > 0:
            raise ValueError(f"Already holding YES in {fill.market_id}")
        if market_positions["NO"]["size"] > 0:
            raise ValueError(f"Cannot buy YES while holding NO in {fill.market_id}")

        portfolio.cash -= fill.price * fill.size
        set_yes_position(portfolio, fill.market_id, fill.size, fill.price)

    elif fill.side == "BUY_NO":
        if market_positions["NO"]["size"] > 0:
            raise ValueError(f"Already holding NO in {fill.market_id}")
        if market_positions["YES"]["size"] > 0:
            raise ValueError(f"Cannot buy NO while holding YES in {fill.market_id}")

        portfolio.cash -= fill.price * fill.size
        set_no_position(portfolio, fill.market_id, fill.size, fill.price)

    else:
        raise ValueError(f"Unsupported fill side: {fill.side}")

   

def compute_portfolio_value(
    portfolio: Portfolio,
    latest_market_state_by_id: dict[str, MarketState],
) -> float:
    total_value = portfolio.cash

    for market_id, market_position in portfolio.positions.items():
        market = latest_market_state_by_id.get(market_id)

        if market is None:
            continue

        midpoint = compute_midpoint(market.best_bid, market.best_ask)

        yes_size = market_position["YES"]["size"]
        no_size = market_position["NO"]["size"]

        yes_value = yes_size * midpoint
        no_value = no_size * (1.0 - midpoint)

        total_value += yes_value + no_value

    return total_value


def compute_unrealized_pnl(
    portfolio: Portfolio,
    latest_market_state_by_id: dict[str, MarketState],
    starting_cash: float,
) -> float:
    total_value = compute_portfolio_value(portfolio, latest_market_state_by_id)
    return total_value - starting_cash


def compute_side_unrealized_pnl(portfolio: Portfolio, market: MarketState) -> dict:
    midpoint = compute_midpoint(market.best_bid, market.best_ask)
    
    positions_in_market = get_market_position(portfolio, market.market_id)
    yes_size = positions_in_market["YES"]["size"]
    yes_avg = positions_in_market["YES"]["avg_price"]

    no_size = positions_in_market["NO"]["size"]
    no_avg = positions_in_market["NO"]["avg_price"]

    yes_market_price = midpoint
    no_market_price = 1 - midpoint

    yes_pnl = yes_size * (yes_market_price - yes_avg)
    no_pnl = no_size * (no_market_price - no_avg)

    return {
        "YES": yes_pnl,
        "NO": no_pnl,
        "TOTAL": yes_pnl + no_pnl
    }