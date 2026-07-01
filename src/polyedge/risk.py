from .legacy_models import Signal, Portfolio
from .portfolio import has_open_position


def get_trade_decision(signal: Signal, portfolio: Portfolio, max_position_size: float):
    """
    Event-native logic:
    - Only ONE trade per market
    - No flipping
    - No adding after entry
    """

    if signal.action == "HOLD":
        return False, "HOLD signal"
    
    if has_open_position(portfolio, signal.market_id):
        return False, "already in market"
    return True, "approved"