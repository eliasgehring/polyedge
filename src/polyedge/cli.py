import argparse
import sys

from .research_command import run_research_command


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
            "Truth-preserving comparison of synchronized "
            "bookmaker and prediction-market probabilities."
        ),
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    research_parser = subparsers.add_parser(
        "research",
        help="Run the canonical V2 probability-research workflow.",
    )

    source_group = research_parser.add_mutually_exclusive_group(
        required=True
    )
    source_group.add_argument(
        "--demo",
        action="store_true",
        help=(
            "Run the public synthetic evaluator fixture. "
            "Produces no empirical claims."
        ),
    )
    source_group.add_argument(
        "--dataset",
        default=None,
        help="Path to an authorized synchronized research dataset.",
    )

    research_parser.add_argument(
        "--report",
        default=None,
        help="Optional path for a generated Markdown research report.",
    )
    research_parser.add_argument(
        "--resamples",
        type=int,
        default=2000,
        help=(
            "Bootstrap resamples. Default: 2000. "
            "Use 10000 to reproduce the pinned report."
        ),
    )
    research_parser.add_argument(
        "--seed",
        type=int,
        default=20260805,
        help="Deterministic bootstrap seed.",
    )
    research_parser.set_defaults(func=research_command)

    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
