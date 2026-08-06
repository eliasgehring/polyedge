from polyedge.cli import (
    build_parser,
)


def test_cli_accepts_research_demo_mode():
    parser = build_parser()

    args = parser.parse_args([
        "research",
        "--demo",
    ])

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
