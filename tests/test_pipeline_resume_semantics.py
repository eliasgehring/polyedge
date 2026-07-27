from scripts.data_pipeline.match_polymarket_prices import (
    processed_market_ids_with_manifest,
)


def test_market_is_processed_only_when_output_and_manifest_exist():
    processed = processed_market_ids_with_manifest(
        output_pregame_market_ids={
            "market_with_both",
            "market_output_only",
        },
        manifest_rows=[
            {"source_market_id": "market_with_both"},
            {"source_market_id": "market_manifest_only"},
        ],
    )

    assert processed == {"market_with_both"}


def test_empty_manifest_means_no_markets_are_complete():
    processed = processed_market_ids_with_manifest(
        output_pregame_market_ids={"market_a"},
        manifest_rows=[],
    )

    assert processed == set()


def test_blank_manifest_ids_are_ignored():
    processed = processed_market_ids_with_manifest(
        output_pregame_market_ids={"market_a"},
        manifest_rows=[
            {"source_market_id": ""},
            {},
        ],
    )

    assert processed == set()
