import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from domain import MarketSnapshot, RowType, Side
from probability import generate_signal


def test_positive_executable_yes_edge_buys_yes():
    snapshot = MarketSnapshot(
        timestamp="2025-01-01T12:00:00",
        market_id="m1",
        yes_bid=0.49,
        yes_ask=0.51,
        model_prob_yes=0.62,
        row_type=RowType.PREGAME,
    )

    signal = generate_signal(snapshot, threshold=0.05)

    assert signal.side == Side.BUY_YES
    assert signal.edge_yes == pytest.approx(0.11)
    assert signal.chosen_edge == pytest.approx(0.11)


def test_positive_executable_no_edge_buys_no():
    snapshot = MarketSnapshot(
        timestamp="2025-01-01T12:00:00",
        market_id="m1",
        yes_bid=0.69,
        yes_ask=0.71,
        model_prob_yes=0.55,
        row_type=RowType.PREGAME,
    )

    signal = generate_signal(snapshot, threshold=0.05)

    # no_ask = 1 - yes_bid = 0.31
    # model_prob_no = 1 - 0.55 = 0.45
    # edge_no = 0.45 - 0.31 = 0.14
    assert signal.side == Side.BUY_NO
    assert signal.edge_no == pytest.approx(0.14)
    assert signal.chosen_edge == pytest.approx(0.14)


def test_midpoint_edge_does_not_imply_executable_yes_edge():
    snapshot = MarketSnapshot(
        timestamp="2025-01-01T12:00:00",
        market_id="m1",
        yes_bid=0.49,
        yes_ask=0.61,
        model_prob_yes=0.56,
        row_type=RowType.PREGAME,
    )

    signal = generate_signal(snapshot, threshold=0.01)

    assert signal.side is None
    assert signal.edge_yes == pytest.approx(-0.05)


def test_settlement_rows_do_not_generate_trades():
    snapshot = MarketSnapshot(
        timestamp="2025-01-02T12:00:00",
        market_id="m1",
        yes_bid=1.0,
        yes_ask=1.0,
        model_prob_yes=1.0,
        row_type=RowType.SETTLEMENT,
    )

    signal = generate_signal(snapshot, threshold=0.01)

    assert signal.side is None
    assert signal.chosen_edge == 0.0