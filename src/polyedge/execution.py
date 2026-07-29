from .domain import Fill, MarketQuote, Side, Signal
from .config import (
    BASE_SLIPPAGE,
    SIZE_IMPACT
)

def compute_slippage(size: float) -> float:
    return BASE_SLIPPAGE + SIZE_IMPACT * size


def simulate_fill(signal: Signal, market: MarketQuote, size: float):
    if signal.side is None:
        return None

    slippage = compute_slippage(size)

    if signal.side is Side.BUY_YES:
        raw_price = market.best_ask
        price = min(1.0, raw_price + slippage)

        return Fill(
            market_id=market.market_id,
            side=Side.BUY_YES,
            price=price,
            size=size
        )

    if signal.side is Side.BUY_NO:
        raw_price = 1.0 - market.best_bid
        price = min(1.0, raw_price + slippage)

        return Fill(
            market_id=market.market_id,
            side=Side.BUY_NO,
            price=price,
            size=size
        )

    return None