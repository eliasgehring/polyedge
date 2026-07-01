import pytest

from polyedge.backtest import run_simulation
from polyedge.paths import SAMPLE_HISTORICAL_DATA_FILE


def test_sample_backtest_is_deterministic():
    result = run_simulation(
        threshold=0.05,
        edge_size_multiplier=500,
        historical_filepath=SAMPLE_HISTORICAL_DATA_FILE,
        write_logs = False,
    )

    assert result.result_status == "MECHANICALLY_VALID_SYNTHETIC_BACKTEST"
    assert result.total_trades == 2
    assert result.buy_yes_count == 1
    assert result.buy_no_count == 1
    assert result.final_value == pytest.approx(1034.38)
    assert result.total_return == pytest.approx(34.38)
    assert result.max_drawdown == pytest.approx(1.62)