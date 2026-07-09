from typing import Dict

from polyedge.market_matching import HomeTokenSelection
from polyedge.price_history import PriceHistorySelection


MATCH_MANIFEST_COLUMNS = [
    "source_market_id",
    "output_market_id",
    "slug",
    "event_id",
    "event_slug",
    "event_title",
    "polymarket_market_id",
    "condition_id",
    "market_slug",
    "market_question",
    "home_outcome",
    "away_outcome",
    "home_token_id",
    "away_token_id",
    "home_outcome_index",
    "away_outcome_index",
    "game_start_time",
    "snapshot_timestamp",
    "price_timestamp",
    "price_age_seconds",
    "polymarket_mid",
    "synthetic_total_spread",
    "best_bid",
    "best_ask",
    "bookmaker_prob",
]


def build_match_manifest_row(
    source_market_id: str,
    output_market_id: str,
    slug: str,
    selection: HomeTokenSelection,
    snapshot_timestamp: str,
    price_result: PriceHistorySelection,
    polymarket_mid: float,
    synthetic_total_spread: float,
    best_bid: float,
    best_ask: float,
    bookmaker_prob: str,
) -> Dict[str, str]:
    return {
        "source_market_id": source_market_id,
        "output_market_id": output_market_id,
        "slug": slug,
        "event_id": selection.event_id,
        "event_slug": selection.event_slug,
        "event_title": selection.event_title,
        "polymarket_market_id": selection.market_id,
        "condition_id": selection.condition_id,
        "market_slug": selection.market_slug,
        "market_question": selection.market_question,
        "home_outcome": selection.home_outcome,
        "away_outcome": selection.away_outcome,
        "home_token_id": selection.home_token_id,
        "away_token_id": selection.away_token_id,
        "home_outcome_index": str(selection.home_outcome_index),
        "away_outcome_index": str(selection.away_outcome_index),
        "game_start_time": selection.game_start_time,
        "snapshot_timestamp": snapshot_timestamp,
        "price_timestamp": (
            "" if price_result.timestamp is None else str(price_result.timestamp)
        ),
        "price_age_seconds": (
            "" if price_result.age_seconds is None else str(price_result.age_seconds)
        ),
        "polymarket_mid": f"{polymarket_mid:.6f}",
        "synthetic_total_spread": f"{synthetic_total_spread:.6f}",
        "best_bid": f"{best_bid:.6f}",
        "best_ask": f"{best_ask:.6f}",
        "bookmaker_prob": bookmaker_prob,
    }
