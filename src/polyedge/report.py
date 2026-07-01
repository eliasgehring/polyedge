from pathlib import Path

from .domain import BacktestResult, CURRENT_EXECUTION_ASSUMPTION


def format_pct(value: float) -> str:
    return f"{value * 100:.2f}%"


def build_markdown_report(result: BacktestResult) -> str:
    assumption = CURRENT_EXECUTION_ASSUMPTION

    lines = [
        "# PolyEdge Sample Backtest Report",
        "",
        "## Result Status",
        "",
        f"`{result.result_status}`",
        "",
        (
            "This is an exploratory research backtest. It is designed to test "
            "whether model-implied probabilities contain edge against "
            "prediction-market prices under explicit assumptions."
        ),
        "",
        "It is not a live-trading claim.",
        "",
        "## Dataset",
        "",
        "Dataset path:",
        "",
        "```text",
        str(result.dataset_path),
        "```",
        "",
        "## Execution Assumptions",
        "",
        "| Assumption | Value |",
        "|---|---:|",
        f"| Execution mode | `{assumption.mode.value}` |",
        f"| Uses synthetic spread | `{assumption.uses_synthetic_spread}` |",
        f"| Uses historical midpoint proxy | `{assumption.uses_historical_midpoint_proxy}` |",
        f"| Models liquidity | `{assumption.includes_liquidity}` |",
        f"| Models fees | `{assumption.includes_fees}` |",
        f"| Makes tradability claim | `{assumption.tradability_claim}` |",
        "",
        "## Probability Semantics",
        "",
        "YES means the listed market outcome resolves true.",
        "",
        "NO means the complementary contract.",
        "",
        "```text",
        "edge_yes = model_prob_yes - yes_ask",
        "edge_no  = (1 - model_prob_yes) - no_ask",
        "no_ask   = 1 - yes_bid",
        "```",
        "",
        "A positive executable YES edge maps to BUY_YES.",
        "",
        "A positive executable NO edge maps to BUY_NO.",
        "",
        "## Accounting Semantics",
        "",
        "Portfolio value is computed globally:",
        "",
        "```text",
        "total_value = cash + marked value of all open YES/NO positions",
        "```",
        "",
        (
            "Open positions are marked using the latest known market state for "
            "each market, not merely the current row."
        ),
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Start value | `{result.start_value:.2f}` |",
        f"| Final value | `{result.final_value:.2f}` |",
        f"| Total return | `{result.total_return:.2f}` |",
        f"| Total return % | `{format_pct(result.total_return / result.start_value)}` |",
        f"| Peak value | `{result.peak_value:.2f}` |",
        f"| Max drawdown | `{result.max_drawdown:.2f}` |",
        f"| Total trades | `{result.total_trades}` |",
        f"| BUY_YES trades | `{result.buy_yes_count}` |",
        f"| BUY_NO trades | `{result.buy_no_count}` |",
        f"| HOLD signals | `{result.hold_count}` |",
        f"| Risk rejections | `{result.risk_rejection_count}` |",
        "",
        "## Interpretation",
        "",
        (
            "This sample report exists to verify the engine’s mechanics, not to "
            "claim strategy profitability."
        ),
        "",
        (
            "The important guarantee is that the result is traceable through "
            "explicit probability semantics, settlement-aware accounting, "
            "dataset validation, and deterministic tests."
        ),
        "",
    ]

    return "\n".join(lines)


def save_markdown_report(result: BacktestResult, output_path: str) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(build_markdown_report(result), encoding="utf-8")