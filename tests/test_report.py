from polyedge.backtest import run_simulation
from polyedge.paths import SAMPLE_HISTORICAL_DATA_FILE
from polyedge.report import build_markdown_report
from polyedge.paths import PROJECT_ROOT


def test_report_builds_markdown_for_sample_backtest():
    result = run_simulation(
        threshold=0.05,
        edge_size_multiplier=500,
        historical_filepath=SAMPLE_HISTORICAL_DATA_FILE,
        write_logs = False,
    )

    report = build_markdown_report(result)

    assert "# PolyEdge Sample Backtest Report" in report
    assert "EXPLORATORY" in report or "MECHANICALLY_VALID" in report
    assert "edge_yes = model_prob_yes - yes_ask" in report
    assert "Makes tradability claim" in report
    assert "data/sample/historical_sample.csv" in report
    assert str(PROJECT_ROOT) not in report