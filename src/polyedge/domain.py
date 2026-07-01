from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional, Tuple


class Side(str, Enum):
    BUY_YES = "BUY_YES"
    BUY_NO = "BUY_NO"


class RowType(str, Enum):
    PREGAME = "PREGAME"
    SETTLEMENT = "SETTLEMENT"


class ResolvedOutcome(str, Enum):
    YES_TRUE = "YES_TRUE"
    YES_FALSE = "YES_FALSE"


class ExecutionMode(str, Enum):
    SYNTHETIC_BID_ASK = "SYNTHETIC_BID_ASK"


@dataclass(frozen=True)
class MarketSnapshot:
    """
    One observed market state.

    yes_bid and yes_ask are prices for the YES contract.
    model_prob_yes is the model or baseline probability that YES resolves true.
    """

    timestamp: str
    market_id: str
    yes_bid: float
    yes_ask: float
    model_prob_yes: float
    row_type: RowType


@dataclass(frozen=True)
class Signal:
    """
    Explicit probability semantics.

    edge_yes = model_prob_yes - yes_ask
    edge_no = (1 - model_prob_yes) - no_ask
    no_ask = 1 - yes_bid

    side is None when no trade should be made.
    """

    market_id: str
    side: Optional[Side]
    model_prob_yes: float
    market_prob_yes: float
    edge_yes: float
    edge_no: float
    chosen_edge: float


@dataclass(frozen=True)
class Fill:
    market_id: str
    side: Side
    price: float
    size: float


@dataclass(frozen=True)
class Position:
    market_id: str
    side: Side
    size: float
    avg_price: float


@dataclass
class Portfolio:
    cash: float
    positions: Dict[Tuple[str, Side], Position] = field(default_factory=dict)


@dataclass(frozen=True)
class ExitResult:
    triggered: bool
    resolved_outcome: Optional[ResolvedOutcome]
    closed_side: Optional[Side]
    realized_pnl: float


@dataclass(frozen=True)
class ExecutionAssumption:
    mode: ExecutionMode
    uses_synthetic_spread: bool
    uses_historical_midpoint_proxy: bool
    includes_liquidity: bool
    includes_fees: bool
    tradability_claim: bool

@dataclass(frozen=True)
class BacktestResult:
    result_status: str
    dataset_path: str
    dataset_hash: str
    dataset_rows: int
    dataset_markets: int
    dataset_pregame_rows: int
    dataset_har_fail: bool
    total_trades: int
    buy_yes_count: int
    buy_no_count: int
    hold_count: int
    risk_rejection_count: int
    start_value: float
    final_value: float
    total_return: float
    peak_value: float
    max_drawdown: float


CURRENT_EXECUTION_ASSUMPTION = ExecutionAssumption(
    mode=ExecutionMode.SYNTHETIC_BID_ASK,
    uses_synthetic_spread=True,
    uses_historical_midpoint_proxy=True,
    includes_liquidity=False,
    includes_fees=False,
    tradability_claim=False,
)