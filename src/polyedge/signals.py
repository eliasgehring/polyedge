from .legacy_models import MarketState, Signal
from .pricing import compute_midpoint
from .config import (
    MIN_MARKET_PROB,
    MAX_MARKET_PROB,
)
from .domain import MarketSnapshot, RowType, Side
from .probability import generate_signal as generate_probability_signal


def generate_signal(
    market: MarketState,
    bookmaker_prob: float,
    threshold: float,
) -> Signal:
    """
    Legacy-compatible signal wrapper.

    The old engine expects models.Signal with:
    - bookmaker_prob
    - polymarket_prob
    - edge
    - action as a string

    The new semantic core computes executable edge explicitly:
    - edge_yes = model_prob_yes - yes_ask
    - edge_no = (1 - model_prob_yes) - no_ask
    - no_ask = 1 - yes_bid

    For backward compatibility, this wrapper returns:
    - positive edge for BUY_YES
    - negative edge for BUY_NO
    - zero edge for HOLD

    This lets the old backtest keep running while the new probability
    semantics become the source of truth.
    """

    polymarket_prob = compute_midpoint(market.best_bid, market.best_ask)

    if not (MIN_MARKET_PROB < polymarket_prob < MAX_MARKET_PROB):
        return Signal(
            market_id=market.market_id,
            bookmaker_prob=bookmaker_prob,
            polymarket_prob=polymarket_prob,
            edge=0.0,
            action="HOLD",
        )

    snapshot = MarketSnapshot(
        timestamp="",
        market_id=market.market_id,
        yes_bid=market.best_bid,
        yes_ask=market.best_ask,
        model_prob_yes=bookmaker_prob,
        row_type=RowType.PREGAME,
    )

    semantic_signal = generate_probability_signal(
        snapshot=snapshot,
        threshold=threshold,
    )

    if semantic_signal.side == Side.BUY_YES:
        return Signal(
            market_id=market.market_id,
            bookmaker_prob=bookmaker_prob,
            polymarket_prob=polymarket_prob,
            edge=semantic_signal.edge_yes,
            action="BUY_YES",
        )

    if semantic_signal.side == Side.BUY_NO:
        return Signal(
            market_id=market.market_id,
            bookmaker_prob=bookmaker_prob,
            polymarket_prob=polymarket_prob,
            edge=-semantic_signal.edge_no,
            action="BUY_NO",
        )

    return Signal(
        market_id=market.market_id,
        bookmaker_prob=bookmaker_prob,
        polymarket_prob=polymarket_prob,
        edge=0.0,
        action="HOLD",
    )