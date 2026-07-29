from dataclasses import dataclass, field
from enum import Enum
from math import isfinite
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
class MarketQuote:
    """
    Executable YES-side market quote.

    best_bid and best_ask are prices for the YES contract.
    The executable NO ask is 1 - best_bid.
    """

    market_id: str
    best_bid: float
    best_ask: float

    def __post_init__(self) -> None:
        if not isinstance(self.market_id, str) or not self.market_id:
            raise ValueError("market_id must be a non-empty string")

        for name, value in (
            ("best_bid", self.best_bid),
            ("best_ask", self.best_ask),
        ):
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise TypeError(f"{name} must be a finite number")

            if not isfinite(value):
                raise ValueError(f"{name} must be finite")

            if not 0.0 <= value <= 1.0:
                raise ValueError(
                    f"{name} must be in [0, 1], got {value}"
                )

        if self.best_bid > self.best_ask:
            raise ValueError(
                "best_bid must be <= best_ask, got "
                f"best_bid={self.best_bid}, "
                f"best_ask={self.best_ask}"
            )


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
    chosen_edge is always a non-negative executable edge magnitude.
    """

    market_id: str
    side: Optional[Side]
    model_prob_yes: float
    market_prob_yes: float
    edge_yes: float
    edge_no: float
    chosen_edge: float

    def __post_init__(self) -> None:
        if not isinstance(self.market_id, str) or not self.market_id:
            raise ValueError("market_id must be a non-empty string")

        if self.side is not None and not isinstance(self.side, Side):
            raise TypeError("side must be a Side or None")

        for name, value in (
            ("model_prob_yes", self.model_prob_yes),
            ("market_prob_yes", self.market_prob_yes),
            ("edge_yes", self.edge_yes),
            ("edge_no", self.edge_no),
            ("chosen_edge", self.chosen_edge),
        ):
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise TypeError(f"{name} must be a finite number")

            if not isfinite(value):
                raise ValueError(f"{name} must be finite")

        for name, value in (
            ("model_prob_yes", self.model_prob_yes),
            ("market_prob_yes", self.market_prob_yes),
        ):
            if not 0.0 <= value <= 1.0:
                raise ValueError(
                    f"{name} must be in [0, 1], got {value}"
                )

        if self.chosen_edge < 0.0:
            raise ValueError("chosen_edge must be non-negative")

        if self.side is None and self.chosen_edge != 0.0:
            raise ValueError(
                "HOLD signal must have chosen_edge equal to zero"
            )

        if self.side is Side.BUY_YES:
            if self.chosen_edge != self.edge_yes:
                raise ValueError(
                    "BUY_YES chosen_edge must equal edge_yes"
                )

        if self.side is Side.BUY_NO:
            if self.chosen_edge != self.edge_no:
                raise ValueError(
                    "BUY_NO chosen_edge must equal edge_no"
                )

    @property
    def action(self) -> str:
        if self.side is None:
            return "HOLD"

        return self.side.value

    @property
    def signed_edge(self) -> float:
        if self.side is Side.BUY_YES:
            return self.chosen_edge

        if self.side is Side.BUY_NO:
            return -self.chosen_edge

        return 0.0


@dataclass(frozen=True)
class Fill:
    market_id: str
    side: Side
    price: float
    size: float

    def __post_init__(self) -> None:
        if not isinstance(self.market_id, str) or not self.market_id:
            raise ValueError("market_id must be a non-empty string")

        if not isinstance(self.side, Side):
            raise TypeError("side must be a Side")

        for name, value in (
            ("price", self.price),
            ("size", self.size),
        ):
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise TypeError(f"{name} must be a finite number")

            if not isfinite(value):
                raise ValueError(f"{name} must be finite")

        if not 0.0 <= self.price <= 1.0:
            raise ValueError(
                f"price must be in [0, 1], got {self.price}"
            )

        if self.size <= 0.0:
            raise ValueError(
                f"size must be positive, got {self.size}"
            )


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
    dataset_settlement_rows: int
    dataset_hard_fail: bool
    total_trades: int
    buy_yes_count: int
    buy_no_count: int
    hold_count: int
    risk_rejection_count: int
    skipped_settlement_count: int
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
