import csv
import json
from pathlib import Path

from polyedge.price_history import PriceHistorySelection
from scripts.data_pipeline import match_polymarket_prices as pipeline


FIXTURE_PATH = (
    Path(__file__).parent
    / "fixtures"
    / "polymarket"
    / "boston_vs_new_york.json"
)


def write_source_file(path: Path) -> None:
    rows = [
        {
            "timestamp": "2024-10-22T12:00:00",
            "market_id": (
                "nba_20241022_boston_vs_new_york_home_win"
            ),
            "best_bid": "0.59",
            "best_ask": "0.61",
            "bookmaker_prob": "0.60",
            "row_type": "PREGAME",
        },
        {
            "timestamp": "2024-10-23T12:00:00",
            "market_id": (
                "nba_20241022_boston_vs_new_york_home_win"
            ),
            "best_bid": "1.0",
            "best_ask": "1.0",
            "bookmaker_prob": "1.0",
            "row_type": "SETTLEMENT",
        },
    ]

    with path.open(
        mode="w",
        newline="",
        encoding="utf-8",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=pipeline.OUTPUT_COLUMNS,
        )
        writer.writeheader()
        writer.writerows(rows)


def read_csv_rows(path: Path):
    with path.open(
        mode="r",
        newline="",
        encoding="utf-8",
    ) as file:
        return list(csv.DictReader(file))


def patch_pipeline_paths(monkeypatch, tmp_path):
    monkeypatch.setattr(
        pipeline,
        "MATCH_MANIFEST_FILE",
        tmp_path / "match_manifest.csv",
    )
    monkeypatch.setattr(
        pipeline,
        "REVIEW_FILE",
        tmp_path / "review.csv",
    )


def patch_event_lookup(monkeypatch):
    event = json.loads(
        FIXTURE_PATH.read_text(encoding="utf-8")
    )

    monkeypatch.setattr(
        pipeline,
        "find_event_from_slug_candidates",
        lambda slug_candidates: (
            event,
            "nba-nyk-bos-2024-10-22",
        ),
    )


def test_pipeline_writes_aligned_output_and_manifest(
    tmp_path,
    monkeypatch,
):
    input_path = tmp_path / "source.csv"
    output_path = tmp_path / "historical.csv"

    write_source_file(input_path)
    patch_pipeline_paths(monkeypatch, tmp_path)
    patch_event_lookup(monkeypatch)

    monkeypatch.setattr(
        pipeline,
        "fetch_price_before_snapshot",
        lambda token_id, snapshot_dt: PriceHistorySelection(
            price=0.55,
            timestamp=1729598280,
            age_seconds=120,
            reason=None,
        ),
    )

    review_rows = []

    pipeline.process_source_file(
        input_path=str(input_path),
        output_path=str(output_path),
        review_rows=review_rows,
    )

    output_rows = read_csv_rows(output_path)
    manifest_rows = read_csv_rows(
        pipeline.MATCH_MANIFEST_FILE
    )

    assert review_rows == []
    assert len(output_rows) == 2
    assert len(manifest_rows) == 1

    pregame_row = output_rows[0]
    settlement_row = output_rows[1]
    manifest_row = manifest_rows[0]

    assert pregame_row["row_type"] == "PREGAME"
    assert (
        pregame_row["timestamp"]
        == "2024-10-22T12:00:00"
    )
    assert pregame_row["best_bid"] == "0.540000"
    assert pregame_row["best_ask"] == "0.560000"
    assert pregame_row["bookmaker_prob"] == "0.60"

    assert settlement_row["row_type"] == "SETTLEMENT"
    assert settlement_row["best_bid"] == "1.0"
    assert settlement_row["best_ask"] == "1.0"

    assert manifest_row["home_outcome"] == "Celtics"
    assert manifest_row["away_outcome"] == "Knicks"
    assert manifest_row["home_token_id"] == "home-token"
    assert (
        manifest_row["snapshot_timestamp"]
        == "2024-10-22T12:00:00"
    )
    assert manifest_row["price_timestamp"] == "1729598280"
    assert manifest_row["price_age_seconds"] == "120"
    assert manifest_row["polymarket_mid"] == "0.550000"


def test_pipeline_rejects_stale_price(
    tmp_path,
    monkeypatch,
):
    input_path = tmp_path / "source.csv"
    output_path = tmp_path / "historical.csv"

    write_source_file(input_path)
    patch_pipeline_paths(monkeypatch, tmp_path)
    patch_event_lookup(monkeypatch)

    monkeypatch.setattr(
        pipeline,
        "fetch_price_before_snapshot",
        lambda token_id, snapshot_dt: PriceHistorySelection(
            price=None,
            timestamp=1729573200,
            age_seconds=25200,
            reason="price_too_stale",
        ),
    )

    review_rows = []

    pipeline.process_source_file(
        input_path=str(input_path),
        output_path=str(output_path),
        review_rows=review_rows,
    )

    assert read_csv_rows(output_path) == []
    assert read_csv_rows(
        pipeline.MATCH_MANIFEST_FILE
    ) == []

    assert len(review_rows) == 1
    assert review_rows[0]["reason"] == "price_too_stale"
    assert review_rows[0]["price_age_seconds"] == 25200
