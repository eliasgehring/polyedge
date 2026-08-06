import argparse
import sys

from .backtest import run_simulation
from .data_validation import (
    build_diagnostics,
    load_rows,
    print_diagnostics,
)
from .paths import SAMPLE_HISTORICAL_DATA_FILE
from .report import save_markdown_report
from .research_command import (
    run_research_command,
)


def validate_command(args) -> int:
    filepath = args.dataset

    rows = load_rows(filepath)
    diagnostics = build_diagnostics(rows)

    print_diagnostics(diagnostics)

    if diagnostics["hard_fail"]:
        print(
            "\nDataset validation failed. Refusing to treat "
            "this dataset as backtest-safe."
        )
        return 1

    print("\nDataset validation passed.")
    return 0


def run_command(args) -> int:
    result = run_simulation(
        threshold=args.threshold,
        edge_size_multiplier=args.edge_size_multiplier,
        historical_filepath=args.dataset,
        start_date=args.start_date,
        end_date=args.end_date,
    )

    if args.report:
        save_markdown_report(
            result,
            args.report,
        )
        print(
            f"\nReport saved to: {args.report}"
        )

    return 0


def research_command(args) -> int:
    return run_research_command(
        dataset_path=args.dataset,
        demo=args.demo,
        report_path=args.report,
        resamples=args.resamples,
        seed=args.seed,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="polyedge",
        description=(
            "Prediction-market research engine with explicit "
            "probability semantics and settlement-aware accounting."
        ),
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    validate_parser = subparsers.add_parser(
        "validate",
        help="Validate a historical backtest dataset.",
    )
    validate_parser.add_argument(
        "--dataset",
        default=SAMPLE_HISTORICAL_DATA_FILE,
        help=(
            "Dataset CSV path. "
            f"Default: {SAMPLE_HISTORICAL_DATA_FILE}"
        ),
    )
    validate_parser.set_defaults(
        func=validate_command
    )

    run_parser = subparsers.add_parser(
        "run",
        help=(
            "Run the legacy exploratory backtest "
            "under explicit execution assumptions."
        ),
    )
    run_parser.add_argument(
        "--dataset",
        default=SAMPLE_HISTORICAL_DATA_FILE,
        help=(
            "Dataset CSV path. "
            f"Default: {SAMPLE_HISTORICAL_DATA_FILE}"
        ),
    )
    run_parser.add_argument(
        "--threshold",
        type=float,
        default=None,
        help=(
            "Minimum executable edge required "
            "to enter a trade."
        ),
    )
    run_parser.add_argument(
        "--edge-size-multiplier",
        type=float,
        default=None,
        help=(
            "Position size multiplier applied "
            "to absolute edge."
        ),
    )
    run_parser.add_argument(
        "--start-date",
        default=None,
        help=(
            "Inclusive PREGAME start date "
            "in YYYY-MM-DD format."
        ),
    )
    run_parser.add_argument(
        "--end-date",
        default=None,
        help=(
            "Inclusive PREGAME end date "
            "in YYYY-MM-DD format."
        ),
    )
    run_parser.add_argument(
        "--report",
        default=None,
        help=(
            "Optional path for a markdown report."
        ),
    )
    run_parser.set_defaults(
        func=run_command
    )

    research_parser = subparsers.add_parser(
        "research",
        help=(
            "Run the V2 probability-research workflow."
        ),
    )

    research_source_group = (
        research_parser
        .add_mutually_exclusive_group(
            required=True
        )
    )

    research_source_group.add_argument(
        "--demo",
        action="store_true",
        help=(
            "Run the public synthetic evaluator fixture. "
            "Produces no empirical claims."
        ),
    )

    research_source_group.add_argument(
        "--dataset",
        default=None,
        help=(
            "Path to an authorized synchronized "
            "research dataset."
        ),
    )

    research_parser.add_argument(
        "--report",
        default=None,
        help=(
            "Optional path for a generated "
            "markdown research report."
        ),
    )

    research_parser.add_argument(
        "--resamples",
        type=int,
        default=2000,
        help=(
            "Bootstrap resamples. Default: 2000. "
            "Use 10000 to reproduce the pinned full report."
        ),
    )

    research_parser.add_argument(
        "--seed",
        type=int,
        default=20260805,
        help=(
            "Deterministic bootstrap seed."
        ),
    )

    research_parser.set_defaults(
        func=research_command
    )

    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(
        main(
            sys.argv[1:]
        )
    )
