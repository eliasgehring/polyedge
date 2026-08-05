import pytest

from polyedge.polymarket_market_identity import (
    build_polymarket_market_identity,
)


def manifest_row():
    return {
        "source_market_id": "market_1",
        "output_market_id": "market_1",
        "polymarket_market_id": "510342",
        "condition_id": "condition_1",
        "market_slug": "example-market",
        "home_outcome": "Home Team",
        "away_outcome": "Away Team",
        "home_token_id": "home-token",
        "away_token_id": "away-token",
        "home_outcome_index": "1",
        "away_outcome_index": "0",
        "snapshot_timestamp": (
            "2024-10-22T12:00:00"
        ),
        "polymarket_mid": "0.685",
        "best_bid": "0.675",
        "best_ask": "0.695",
    }


def settlement_row(
    value="1.0",
):
    return {
        "timestamp": (
            "2024-10-23T12:00:00"
        ),
        "market_id": "market_1",
        "best_bid": value,
        "best_ask": value,
        "bookmaker_prob": value,
        "row_type": "SETTLEMENT",
    }


def test_builds_identity_and_resolution():
    result = (
        build_polymarket_market_identity(
            manifest_row=manifest_row(),
            settlement_row=settlement_row(
                "1.0"
            ),
        )
    )

    assert result.output_market_id == (
        "market_1"
    )

    assert result.home_token_id == (
        "home-token"
    )

    assert result.away_token_id == (
        "away-token"
    )

    assert result.resolved_home_value == 1
    assert result.resolved_away_value == 0

    assert result.resolution_source == (
        "legacy_nba_game_result"
    )

    assert result.settlement_time_status == (
        "unknown_not_migrated"
    )


def test_does_not_migrate_synthetic_timing():
    result = (
        build_polymarket_market_identity(
            manifest_row=manifest_row(),
            settlement_row=settlement_row(),
        )
    )

    assert not hasattr(
        result,
        "snapshot_timestamp",
    )

    assert not hasattr(
        result,
        "settlement_timestamp",
    )


def test_rejects_duplicate_token_ids():
    row = manifest_row()

    row["away_token_id"] = (
        row["home_token_id"]
    )

    with pytest.raises(ValueError):
        build_polymarket_market_identity(
            manifest_row=row,
            settlement_row=settlement_row(),
        )


def test_rejects_inconsistent_outcome_indices():
    row = manifest_row()

    row["home_outcome_index"] = "1"
    row["away_outcome_index"] = "1"

    with pytest.raises(ValueError):
        build_polymarket_market_identity(
            manifest_row=row,
            settlement_row=settlement_row(),
        )


def test_rejects_non_binary_settlement():
    with pytest.raises(ValueError):
        build_polymarket_market_identity(
            manifest_row=manifest_row(),
            settlement_row=settlement_row(
                "0.55"
            ),
        )


def test_rejects_market_id_mismatch():
    row = settlement_row()

    row["market_id"] = "different_market"

    with pytest.raises(ValueError):
        build_polymarket_market_identity(
            manifest_row=manifest_row(),
            settlement_row=row,
        )
