from models import MarketState, Signal
from features import compute_midpoint
from config import (
    MIN_MARKET_PROB,
    MAX_MARKET_PROB,
)


def generate_signal(market: MarketState, bookmaker_prob: float, threshold: float) -> Signal:
    polymarket_prob = compute_midpoint(market.best_bid, market.best_ask)
    edge = bookmaker_prob - polymarket_prob

    # Probability filter:
    # skip extreme markets where payoff skew / tail risk gets worse
    if not (MIN_MARKET_PROB < polymarket_prob < MAX_MARKET_PROB):
        action = "HOLD"    
    else:
            if edge > threshold:
                action = "BUY_YES"
            elif edge < -threshold:
                action = "BUY_NO"
            else:
                action = "HOLD"

    return Signal(
        market_id=market.market_id,
        bookmaker_prob=bookmaker_prob,
        polymarket_prob=polymarket_prob,
        edge=edge,
        action=action
    )