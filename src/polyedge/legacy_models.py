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
class Portfolio:
    cash: float
    positions: dict

    def __post_init__(self) -> None:
        _validate_finite_number(self.cash, "cash")

        if not isinstance(self.positions, dict):
            raise TypeError("positions must be a dict")
