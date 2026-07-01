import math
from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class EquityMetrics:
    start_value: float
    final_value: float
    total_return_abs: float
    total_return_pct: float
    max_drawdown_abs: float
    max_drawdown_pct: float
    mean_step_return: float
    step_return_std: float
    step_sharpe_unannualized: float


def compute_step_returns(equity: List[float]) -> List[float]:
    if len(equity) < 2:
        return []

    returns = []

    for previous_value, current_value in zip(equity, equity[1:]):
        if previous_value <= 0:
            raise ValueError(
                "Cannot compute percentage return from non-positive equity value: "
                f"{previous_value}"
            )

        returns.append((current_value - previous_value) / previous_value)

    return returns


def compute_max_drawdown(equity: List[float]) -> tuple[float, float]:
    if not equity:
        return 0.0, 0.0

    peak = equity[0]
    max_drawdown_abs = 0.0
    max_drawdown_pct = 0.0

    for value in equity:
        if value > peak:
            peak = value

        drawdown_abs = peak - value
        drawdown_pct = drawdown_abs / peak if peak > 0 else 0.0

        if drawdown_abs > max_drawdown_abs:
            max_drawdown_abs = drawdown_abs

        if drawdown_pct > max_drawdown_pct:
            max_drawdown_pct = drawdown_pct

    return max_drawdown_abs, max_drawdown_pct


def mean(values: List[float]) -> float:
    if not values:
        return 0.0

    return sum(values) / len(values)


def population_std(values: List[float]) -> float:
    if len(values) < 2:
        return 0.0

    avg = mean(values)
    variance = sum((value - avg) ** 2 for value in values) / len(values)

    return math.sqrt(variance)


def compute_equity_metrics(equity: List[float]) -> EquityMetrics:
    if not equity:
        raise ValueError("Cannot compute metrics from empty equity curve.")

    start_value = equity[0]
    final_value = equity[-1]

    if start_value <= 0:
        raise ValueError(
            "Cannot compute total percentage return from non-positive start value: "
            f"{start_value}"
        )

    step_returns = compute_step_returns(equity)
    mean_step_return = mean(step_returns)
    step_return_std = population_std(step_returns)

    step_sharpe_unannualized = 0.0
    if step_return_std > 0:
        step_sharpe_unannualized = mean_step_return / step_return_std

    max_drawdown_abs, max_drawdown_pct = compute_max_drawdown(equity)

    total_return_abs = final_value - start_value
    total_return_pct = total_return_abs / start_value

    return EquityMetrics(
        start_value=start_value,
        final_value=final_value,
        total_return_abs=total_return_abs,
        total_return_pct=total_return_pct,
        max_drawdown_abs=max_drawdown_abs,
        max_drawdown_pct=max_drawdown_pct,
        mean_step_return=mean_step_return,
        step_return_std=step_return_std,
        step_sharpe_unannualized=step_sharpe_unannualized,
    )