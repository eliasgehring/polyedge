from features import compute_midpoint
from portfolio import close_position
from positions import get_yes_size, get_no_size


def check_exit_conditions(portfolio, market):
    """
    Event-native version:
    Exit only when the market resolves to 0 or 1.
    """

    midpoint = compute_midpoint(market.best_bid, market.best_ask)
    
    if midpoint <= 0.01 or midpoint >= 0.99:
        yes_size = get_yes_size(portfolio, market.market_id)
        no_size = get_no_size(portfolio, market.market_id)

        if yes_size > 0:
            realized_pnl = close_position(portfolio, market, "YES")
            return True, "market resolved YES", "YES", realized_pnl

        if no_size > 0:
            realized_pnl = close_position(portfolio, market, "NO")
            return True, "market resolved NO", "NO", realized_pnl

    return False, "no exit", "", 0.0