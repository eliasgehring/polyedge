from pathlib import Path

import pytest

from polyedge.research_command import (
    DEMO_DATASET_PATH,
    build_research_summary,
    run_research_command,
)


def test_demo_dataset_runs_end_to_end():
    summary = build_research_summary(
        dataset_path=DEMO_DATASET_PATH,
        demo=True,
        resamples=100,
        seed=7,
    )

    assert summary.dataset_mode == (
        "SYNTHETIC_DEMONSTRATION"
    )

    assert summary.row_count == 12
    assert summary.strict_row_count == 10

    assert (
        summary.execution_semantics
        == "none"
    )


def test_demo_command_prints_claim_boundary(
    capsys,
):
    exit_code = run_research_command(
        dataset_path=None,
        demo=True,
        report_path=None,
        resamples=100,
        seed=7,
    )

    output = capsys.readouterr().out

    assert exit_code == 0
    assert (
        "SYNTHETIC_DEMONSTRATION"
        in output
    )
    assert (
        "Tradable profitability"
        in output
    )
    assert (
        "NOT ESTABLISHED"
        in output
    )
    assert (
        "Empirical claims"
        in output
    )


def test_demo_command_writes_report(
    tmp_path,
):
    output_path = (
        tmp_path
        / "research_report.md"
    )

    run_research_command(
        dataset_path=None,
        demo=True,
        report_path=str(
            output_path
        ),
        resamples=100,
        seed=7,
    )

    report = output_path.read_text(
        encoding="utf-8"
    )

    assert (
        "# PolyEdge V2 Research Report"
        in report
    )
    assert (
        "synthetic demonstration"
        in report.lower()
    )


def test_requires_exactly_one_dataset_mode():
    with pytest.raises(
        ValueError,
        match="Choose",
    ):
        run_research_command(
            dataset_path=None,
            demo=False,
            report_path=None,
            resamples=100,
            seed=7,
        )

    with pytest.raises(
        ValueError,
        match="either",
    ):
        run_research_command(
            dataset_path=str(
                DEMO_DATASET_PATH
            ),
            demo=True,
            report_path=None,
            resamples=100,
            seed=7,
        )
