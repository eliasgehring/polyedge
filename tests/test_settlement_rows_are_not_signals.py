import pytest

from polyedge.backtest import run_simulation
from polyedge.paths import SAMPLE_HISTORICAL_DATA_FILE


def test_settlement_rows_without_positions_are_not_entry_signals():
    result = run_simulation(
        threshold=0.50,
        edge_size_multiplier=500,
        historical_filepath=SAMPLE_HISTORICAL_DATA_FILE,
        write_logs=False,
        print_output=False,
    )

    assert result.total_trades == 0
    assert result.buy_yes_count == 0
    assert result.buy_no_count == 0

    # Only the two pregame rows are trading-decision rows.
    assert result.hold_count == 2

    # The two settlement rows are skipped, not counted as HOLD signals.
    assert result.skipped_settlement_count == 2

    assert result.final_value == pytest.approx(1000.0)
    assert result.total_return == pytest.approx(0.0)