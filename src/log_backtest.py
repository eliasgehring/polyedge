import csv
import os

from features import compute_midpoint, compute_spread
from portfolio import (
    compute_portfolio_value,
    compute_unrealized_pnl,
    compute_side_unrealized_pnl,
)
from config import STARTING_CASH
from positions import (
    get_yes_size,
    get_no_size,
    get_yes_avg_price,
    get_no_avg_price,
)


def initialize_csv_log(filepath: str) -> None:
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    file_exists = os.path.exists(filepath)

    if not file_exists:
        with open(filepath, mode="w", newline="") as file:
            writer = csv.writer(file)
            writer.writerow([
                "timestamp",
                "step",
                "market_id",
                "row_type",
                "action",
                "approved",
                "reason",
                "model_prob",
                "market_prob",
                "edge",
                "best_bid",
                "best_ask",
                "midpoint",
                "spread",
                "fill_side",
                "fill_price",
                "fill_size",
                "cash",
                "yes_size",
                "yes_avg_price",
                "no_size",
                "no_avg_price",
                "yes_pnl",
                "no_pnl",
                "unrealized_pnl",
                "exit_triggered",
                "exit_reason",
                "exit_side",
                "realized_pnl",
                "total_value"
            ])


def log_step_to_csv(
    filepath: str,
    step: int,
    timestamp: str,
    row_type: str,
    signal,
    approved: bool,
    reason: str,
    fill,
    portfolio,
    market,
    latest_market_state_by_id,
    exit_triggered: bool,
    exit_reason: str,
    exit_side: str,
    realized_pnl: float
) -> None:
    midpoint = compute_midpoint(market.best_bid, market.best_ask)
    spread = compute_spread(market.best_bid, market.best_ask)
    total_value = compute_portfolio_value(portfolio, latest_market_state_by_id)    
    unrealized_pnl = compute_unrealized_pnl(
    portfolio,
    latest_market_state_by_id,
    STARTING_CASH,)  
      
    side_pnl = compute_side_unrealized_pnl(portfolio, market)
    
    yes_size = get_yes_size(portfolio, market.market_id)
    yes_avg_price = get_yes_avg_price(portfolio, market.market_id)
    no_size = get_no_size(portfolio, market.market_id)
    no_avg_price = get_no_avg_price(portfolio, market.market_id)

    fill_side = ""
    fill_price = ""
    fill_size = ""

    if fill is not None:
        fill_side = fill.side
        fill_price = fill.price
        fill_size = fill.size

    market_id = market.market_id
    action = "NO_NEW_SIGNAL"
    bookmaker_prob = 0.0
    polymarket_prob = midpoint
    edge = 0.0

    if signal is not None:
        market_id = signal.market_id
        action = signal.action
        bookmaker_prob = signal.bookmaker_prob
        polymarket_prob = signal.polymarket_prob
        edge = signal.edge

    with open(filepath, mode="a", newline="") as file:
        writer = csv.writer(file)
        writer.writerow([
            timestamp,
            step,
            market_id,
            row_type,
            action,
            approved,
            reason,
            bookmaker_prob,
            polymarket_prob,
            edge,
            market.best_bid,
            market.best_ask,
            midpoint,
            spread,
            fill_side,
            fill_price,
            fill_size,
            portfolio.cash,
            yes_size,
            yes_avg_price,
            no_size,
            no_avg_price,
            side_pnl["YES"],
            side_pnl["NO"],
            unrealized_pnl,
            exit_triggered,
            exit_reason,
            exit_side,
            realized_pnl,
            total_value
        ])