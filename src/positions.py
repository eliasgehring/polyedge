from models import Portfolio


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