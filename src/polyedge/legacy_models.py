from dataclasses import dataclass
from math import isfinite
from typing import Any


VALID_SIGNAL_ACTIONS = {"BUY_YES", "BUY_NO", "HOLD"}
VALID_FILL_SIDES = {"BUY_YES", "BUY_NO"}


def _validate_non_empty_string(value: str, name: str) -> None:
    if not isinstance(value, str) or value == "":
        raise ValueError(f"{name} must be a non-empty string")


def _validate_finite_number(value: float, name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be a finite number")

    if not isfinite(value):
        raise ValueError(f"{name} must be finite")


def _validate_probability(value: float, name: str) -> None:
    _validate_finite_number(value, name)

    if not (0.0 <= value <= 1.0):
        raise ValueError(f"{name} must be in [0, 1], got {value}")


def _validate_positive_number(value: float, name: str) -> None:
    _validate_finite_number(value, name)

    if value <= 0.0:
        raise ValueError(f"{name} must be positive, got {value}")


@dataclass
class MarketState:
    market_id: str
    best_bid: float
    best_ask: float

    def __post_init__(self) -> None:
        _validate_non_empty_string(self.market_id, "market_id")
        _validate_probability(self.best_bid, "best_bid")
        _validate_probability(self.best_ask, "best_ask")

        if self.best_bid > self.best_ask:
            raise ValueError(
                f"best_bid must be <= best_ask, got "
                f"best_bid={self.best_bid}, best_ask={self.best_ask}"
            )


@dataclass
class Signal:
    market_id: str
    bookmaker_prob: float
    polymarket_prob: float
    edge: float
    action: str

    def __post_init__(self) -> None:
        _validate_non_empty_string(self.market_id, "market_id")
        _validate_probability(self.bookmaker_prob, "bookmaker_prob")
        _validate_probability(self.polymarket_prob, "polymarket_prob")
        _validate_finite_number(self.edge, "edge")

        if self.action not in VALID_SIGNAL_ACTIONS:
            raise ValueError(
                f"action must be one of {sorted(VALID_SIGNAL_ACTIONS)}, "
                f"got {self.action}"
            )


@dataclass
class Fill:
    market_id: str
    side: str
    price: float
    size: float

    def __post_init__(self) -> None:
        _validate_non_empty_string(self.market_id, "market_id")

        if self.side not in VALID_FILL_SIDES:
            raise ValueError(
                f"side must be one of {sorted(VALID_FILL_SIDES)}, got {self.side}"
            )

        _validate_probability(self.price, "price")
        _validate_positive_number(self.size, "size")


@dataclass
class Portfolio:
    cash: float
    positions: dict

    def __post_init__(self) -> None:
        _validate_finite_number(self.cash, "cash")

        if not isinstance(self.positions, dict):
            raise TypeError("positions must be a dict")
