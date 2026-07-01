import pytest

from metrics import (
    compute_equity_metrics,
    compute_max_drawdown,
    compute_step_returns,
)


def test_step_returns_are_percentage_returns_not_dollar_differences():
    equity = [1000.0, 1010.0, 1000.0]

    returns = compute_step_returns(equity)

    assert returns == pytest.approx([0.01, -0.009900990099])


def test_step_returns_reject_non_positive_previous_equity():
    equity = [1000.0, 0.0, 100.0]

    with pytest.raises(ValueError):
        compute_step_returns(equity)


def test_max_drawdown_reports_absolute_and_percentage_drawdown():
    equity = [1000.0, 1100.0, 990.0, 1200.0]

    max_drawdown_abs, max_drawdown_pct = compute_max_drawdown(equity)

    assert max_drawdown_abs == pytest.approx(110.0)
    assert max_drawdown_pct == pytest.approx(0.10)


def test_equity_metrics_total_return_and_drawdown():
    equity = [1000.0, 1100.0, 990.0, 1200.0]

    metrics = compute_equity_metrics(equity)

    assert metrics.start_value == 1000.0
    assert metrics.final_value == 1200.0
    assert metrics.total_return_abs == pytest.approx(200.0)
    assert metrics.total_return_pct == pytest.approx(0.20)
    assert metrics.max_drawdown_abs == pytest.approx(110.0)
    assert metrics.max_drawdown_pct == pytest.approx(0.10)