from legacy_models import Portfolio, Fill, MarketState
from pricing import compute_midpoint


def empty_market_position() -> dict:
    return {
        "YES": {"size": 0.0, "avg_price": 0.0},
        "NO": {"size": 0.0, "avg_price": 0.0},
    }


def ensure_market_position(portfolio: Portfolio, market_id: str) -> dict:
    if market_id not in portfolio.positions:
        portfolio.positions[market_id] = empty_market_position()

    return portfolio.positions[market_id]


def get_market_position(portfolio: Portfolio, market_id: str) -> dict:
    return portfolio.positions.get(market_id, empty_market_position())


def get_yes_position(portfolio: Portfolio, market_id: str) -> dict:
    return get_market_position(portfolio, market_id)["YES"]


def get_no_position(portfolio: Portfolio, market_id: str) -> dict:
    return get_market_position(portfolio, market_id)["NO"]


def get_yes_size(portfolio: Portfolio, market_id: str) -> float:
    return get_yes_position(portfolio, market_id)["size"]


def get_no_size(portfolio: Portfolio, market_id: str) -> float:
    return get_no_position(portfolio, market_id)["size"]


def get_yes_avg_price(portfolio: Portfolio, market_id: str) -> float:
    return get_yes_position(portfolio, market_id)["avg_price"]


def get_no_avg_price(portfolio: Portfolio, market_id: str) -> float:
    return get_no_position(portfolio, market_id)["avg_price"]


def has_open_position(portfolio: Portfolio, market_id: str) -> bool:
    return (
        get_yes_size(portfolio, market_id) > 0.0
        or get_no_size(portfolio, market_id) > 0.0
    )


def set_yes_position(
    portfolio: Portfolio,
    market_id: str,
    size: float,
    avg_price: float,
) -> None:
    market_position = ensure_market_position(portfolio, market_id)
    market_position["YES"]["size"] = size
    market_position["YES"]["avg_price"] = avg_price


def set_no_position(
    portfolio: Portfolio,
    market_id: str,
    size: float,
    avg_price: float,
) -> None:
    market_position = ensure_market_position(portfolio, market_id)
    market_position["NO"]["size"] = size
    market_position["NO"]["avg_price"] = avg_price


def clear_yes_position(portfolio: Portfolio, market_id: str) -> None:
    set_yes_position(portfolio, market_id, 0.0, 0.0)


def clear_no_position(portfolio: Portfolio, market_id: str) -> None:
    set_no_position(portfolio, market_id, 0.0, 0.0)


def create_portfolio(starting_cash: float) -> Portfolio:
    return Portfolio(
        cash=starting_cash,
        positions={},
    )


def close_position(portfolio: Portfolio, market: MarketState, side: str) -> float:
    if market.market_id not in portfolio.positions:
        return 0.0

    positions_in_market = portfolio.positions[market.market_id]

    if side == "YES":
        side_data = positions_in_market["YES"]
        close_price = compute_midpoint(market.best_bid, market.best_ask)
    elif side == "NO":
        side_data = positions_in_market["NO"]
        close_price = 1.0 - compute_midpoint(market.best_bid, market.best_ask)
    else:
        return 0.0

    size = side_data["size"]
    avg_price = side_data["avg_price"]

    if size <= 0:
        return 0.0

    realized_pnl = size * (close_price - avg_price)
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
        return

    if fill.side == "BUY_NO":
        if market_positions["NO"]["size"] > 0:
            raise ValueError(f"Already holding NO in {fill.market_id}")

        if market_positions["YES"]["size"] > 0:
            raise ValueError(f"Cannot buy NO while holding YES in {fill.market_id}")

        portfolio.cash -= fill.price * fill.size
        set_no_position(portfolio, fill.market_id, fill.size, fill.price)
        return

    raise ValueError(f"Unsupported fill side: {fill.side}")


def compute_portfolio_value(
    portfolio: Portfolio,
    latest_market_state_by_id: dict,
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
    latest_market_state_by_id: dict,
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
    no_market_price = 1.0 - midpoint

    yes_pnl = yes_size * (yes_market_price - yes_avg)
    no_pnl = no_size * (no_market_price - no_avg)

    return {
        "YES": yes_pnl,
        "NO": no_pnl,
        "TOTAL": yes_pnl + no_pnl,
    }