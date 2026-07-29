from .config import MAX_MARKET_PROB, MIN_MARKET_PROB
from .domain import (
    MarketQuote,
    MarketSnapshot,
    RowType,
    Signal,
)
from .pricing import compute_midpoint
from .probability import generate_signal as generate_probability_signal


def generate_signal(
    market: MarketQuote,
    bookmaker_prob: float,
    threshold: float,
) -> Signal:
    """
    Generate an executable probability signal.

    YES and NO edges are calculated against their respective asks.
    A HOLD signal has side=None and chosen_edge=0.
    """

    market_prob_yes = compute_midpoint(
        market.best_bid,
        market.best_ask,
    )

    if not (
        MIN_MARKET_PROB
        < market_prob_yes
        < MAX_MARKET_PROB
    ):
        return Signal(
            market_id=market.market_id,
            side=None,
            model_prob_yes=bookmaker_prob,
            market_prob_yes=market_prob_yes,
            edge_yes=0.0,
            edge_no=0.0,
            chosen_edge=0.0,
        )

    snapshot = MarketSnapshot(
        timestamp="",
        market_id=market.market_id,
        yes_bid=market.best_bid,
        yes_ask=market.best_ask,
        model_prob_yes=bookmaker_prob,
        row_type=RowType.PREGAME,
    )

    return generate_probability_signal(
        snapshot=snapshot,
        threshold=threshold,
    )
