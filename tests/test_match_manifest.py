from polyedge.market_matching import HomeTokenSelection
from polyedge.match_manifest import (
    MATCH_MANIFEST_COLUMNS,
    build_match_manifest_row,
)
from polyedge.price_history import PriceHistorySelection


def test_build_match_manifest_row_contains_full_provenance():
    selection = HomeTokenSelection(
        event_id="event-1",
        event_slug="nba-away-home-date",
        event_title="Away vs. Home",
        market_id="market-1",
        condition_id="condition-1",
        market_slug="market-slug",
        market_question="Away vs. Home",
        game_start_time="2024-10-22 23:30:00+00",
        home_outcome="Home",
        away_outcome="Away",
        home_token_id="home-token",
        away_token_id="away-token",
        home_outcome_index=1,
        away_outcome_index=0,
    )

    price_result = PriceHistorySelection(
        price=0.55,
        timestamp=1729600000,
        age_seconds=120,
        reason=None,
    )

    row = build_match_manifest_row(
        source_market_id="source-market",
        output_market_id="output-market",
        slug="winning-slug",
        selection=selection,
        snapshot_timestamp="2024-10-22T12:00:00",
        price_result=price_result,
        polymarket_mid=0.55,
        synthetic_total_spread=0.02,
        best_bid=0.54,
        best_ask=0.56,
        bookmaker_prob="0.60",
    )

    assert list(row.keys()) == MATCH_MANIFEST_COLUMNS
    assert row["source_market_id"] == "source-market"
    assert row["home_outcome"] == "Home"
    assert row["home_token_id"] == "home-token"
    assert row["snapshot_timestamp"] == "2024-10-22T12:00:00"
    assert row["price_timestamp"] == "1729600000"
    assert row["price_age_seconds"] == "120"
    assert row["polymarket_mid"] == "0.550000"
    assert row["best_bid"] == "0.540000"
    assert row["best_ask"] == "0.560000"
