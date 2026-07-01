from domain import ResolvedOutcome
from features import compute_midpoint
from portfolio import close_position, get_yes_size, get_no_size


def get_resolved_outcome(market):
    """
    Return the event outcome implied by the resolved market price.

    YES_TRUE means the YES contract settled to 1.
    YES_FALSE means the YES contract settled to 0.

    This is deliberately separate from which position side we close.
    """

    midpoint = compute_midpoint(market.best_bid, market.best_ask)

    if midpoint >= 0.99:
        return ResolvedOutcome.YES_TRUE

    if midpoint <= 0.01:
        return ResolvedOutcome.YES_FALSE

    return None


def check_exit_conditions(portfolio, market):
    """
    Legacy-compatible exit wrapper.

    Returns:
        exit_triggered: bool
        exit_reason: str
        exit_side: str
        realized_pnl: float

    Important semantics:
    - exit_reason describes the event outcome.
    - exit_side describes the side of the position that was closed.
    """

    resolved_outcome = get_resolved_outcome(market)

    if resolved_outcome is None:
        return False, "no exit", "", 0.0

    yes_size = get_yes_size(portfolio, market.market_id)
    no_size = get_no_size(portfolio, market.market_id)

    if yes_size > 0:
        realized_pnl = close_position(portfolio, market, "YES")
        return True, f"market resolved {resolved_outcome.value}", "YES", realized_pnl

    if no_size > 0:
        realized_pnl = close_position(portfolio, market, "NO")
        return True, f"market resolved {resolved_outcome.value}", "NO", realized_pnl

    return False, "resolved but no open position", "", 0.0