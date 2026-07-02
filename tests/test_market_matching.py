import copy
import json
from pathlib import Path

from polyedge.market_matching import select_home_token


FIXTURE_PATH = (
    Path(__file__).parent
    / "fixtures"
    / "polymarket"
    / "boston_vs_new_york.json"
)


def load_event():
    return json.loads(
        FIXTURE_PATH.read_text(encoding="utf-8")
    )


def test_selects_home_token_from_real_observed_schema():
    event = load_event()

    result = select_home_token(
        event=event,
        expected_home_team="boston",
        expected_away_team="new york",
    )

    assert result.reason is None
    assert result.candidate_count == 1
    assert result.selection is not None
    assert result.selection.home_outcome == "Celtics"
    assert result.selection.away_outcome == "Knicks"
    assert result.selection.home_token_id == "home-token"
    assert result.selection.away_token_id == "away-token"
    assert result.selection.home_outcome_index == 1
    assert result.selection.away_outcome_index == 0


def test_reversed_outcome_order_still_selects_home_token():
    event = load_event()
    market = event["markets"][0]

    market["outcomes"] = ["Celtics", "Knicks"]
    market["clobTokenIds"] = [
        "home-token",
        "away-token",
    ]

    result = select_home_token(
        event=event,
        expected_home_team="boston",
        expected_away_team="new york",
    )

    assert result.selection is not None
    assert result.selection.home_token_id == "home-token"
    assert result.selection.home_outcome_index == 0
    assert result.selection.away_outcome_index == 1


def test_irrelevant_first_market_is_not_selected():
    event = load_event()

    irrelevant_market = {
        "id": "irrelevant-market",
        "sportsMarketType": "totals",
        "outcomes": ["Over", "Under"],
        "clobTokenIds": ["over-token", "under-token"],
    }

    event["markets"].insert(0, irrelevant_market)

    result = select_home_token(
        event=event,
        expected_home_team="boston",
        expected_away_team="new york",
    )

    assert result.selection is not None
    assert result.selection.market_id == "510342"
    assert result.selection.home_token_id == "home-token"


def test_multiple_matching_moneyline_markets_are_rejected():
    event = load_event()

    duplicate_market = copy.deepcopy(event["markets"][0])
    duplicate_market["id"] = "duplicate-market"

    event["markets"].append(duplicate_market)

    result = select_home_token(
        event=event,
        expected_home_team="boston",
        expected_away_team="new york",
    )

    assert result.selection is None
    assert result.reason == "ambiguous_moneyline_markets"
    assert result.candidate_count == 2


def test_malformed_outcome_token_mapping_is_rejected():
    event = load_event()
    event["markets"][0]["clobTokenIds"] = ["only-one-token"]

    result = select_home_token(
        event=event,
        expected_home_team="boston",
        expected_away_team="new york",
    )

    assert result.selection is None
    assert result.reason == "no_matching_moneyline_market"
    assert result.candidate_count == 0
