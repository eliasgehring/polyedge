import pytest

from polyedge.cli import build_parser


def test_cli_accepts_research_demo_mode():
    parser = build_parser()
    args = parser.parse_args(["research", "--demo"])

    assert args.command == "research"
    assert args.demo is True
    assert args.dataset is None


def test_cli_accepts_authorized_dataset_path():
    parser = build_parser()
    args = parser.parse_args([
        "research",
        "--dataset",
        "authorized.csv",
        "--resamples",
        "500",
    ])

    assert args.command == "research"
    assert args.demo is False
    assert args.dataset == "authorized.csv"
    assert args.resamples == 500


def test_cli_does_not_expose_legacy_backtest_commands():
    parser = build_parser()
    help_text = parser.format_help()

    assert "validate" not in help_text
    assert "legacy exploratory backtest" not in help_text

    with pytest.raises(SystemExit):
        parser.parse_args(["run"])
