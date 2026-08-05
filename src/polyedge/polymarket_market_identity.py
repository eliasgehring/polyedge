from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class PolymarketMarketIdentity:
    output_market_id: str
    polymarket_market_id: str
    condition_id: str
    market_slug: str

    home_outcome: str
    away_outcome: str

    home_token_id: str
    away_token_id: str

    home_outcome_index: int
    away_outcome_index: int

    resolved_home_value: int
    resolved_away_value: int

    resolution_source: str
    settlement_time_status: str


def _required_text(
    row: Mapping[str, str],
    field_name: str,
) -> str:
    value = str(
        row.get(field_name, "")
    ).strip()

    if not value:
        raise ValueError(
            f"{field_name} must be non-empty"
        )

    return value


def _parse_outcome_index(
    row: Mapping[str, str],
    field_name: str,
) -> int:
    value = _required_text(
        row,
        field_name,
    )

    try:
        index = int(value)
    except ValueError as exc:
        raise ValueError(
            f"{field_name} must be an integer"
        ) from exc

    if index not in {0, 1}:
        raise ValueError(
            f"{field_name} must be 0 or 1"
        )

    return index


def _parse_binary_settlement(
    settlement_row: Mapping[str, str],
) -> int:
    if (
        settlement_row.get("row_type")
        != "SETTLEMENT"
    ):
        raise ValueError(
            "Settlement row must have "
            "row_type=SETTLEMENT"
        )

    try:
        best_bid = float(
            settlement_row["best_bid"]
        )
        best_ask = float(
            settlement_row["best_ask"]
        )
    except (
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        raise ValueError(
            "Settlement bid and ask must "
            "be numeric"
        ) from exc

    if best_bid != best_ask:
        raise ValueError(
            "Settlement bid and ask must agree"
        )

    if best_bid not in {0.0, 1.0}:
        raise ValueError(
            "Settlement value must be binary"
        )

    return int(best_bid)


def build_polymarket_market_identity(
    *,
    manifest_row: Mapping[str, str],
    settlement_row: Mapping[str, str],
) -> PolymarketMarketIdentity:
    source_market_id = _required_text(
        manifest_row,
        "source_market_id",
    )

    output_market_id = _required_text(
        manifest_row,
        "output_market_id",
    )

    if source_market_id != output_market_id:
        raise ValueError(
            "Manifest source and output "
            "market IDs must match"
        )

    settlement_market_id = _required_text(
        settlement_row,
        "market_id",
    )

    if (
        settlement_market_id
        != output_market_id
    ):
        raise ValueError(
            "Settlement market ID does not "
            "match manifest market ID"
        )

    home_token_id = _required_text(
        manifest_row,
        "home_token_id",
    )

    away_token_id = _required_text(
        manifest_row,
        "away_token_id",
    )

    if home_token_id == away_token_id:
        raise ValueError(
            "Home and away token IDs "
            "must be distinct"
        )

    home_outcome = _required_text(
        manifest_row,
        "home_outcome",
    )

    away_outcome = _required_text(
        manifest_row,
        "away_outcome",
    )

    if home_outcome == away_outcome:
        raise ValueError(
            "Home and away outcomes "
            "must be distinct"
        )

    home_outcome_index = (
        _parse_outcome_index(
            manifest_row,
            "home_outcome_index",
        )
    )

    away_outcome_index = (
        _parse_outcome_index(
            manifest_row,
            "away_outcome_index",
        )
    )

    if {
        home_outcome_index,
        away_outcome_index,
    } != {0, 1}:
        raise ValueError(
            "Home and away outcome indices "
            "must be opposite"
        )

    resolved_home_value = (
        _parse_binary_settlement(
            settlement_row
        )
    )

    resolved_away_value = (
        1 - resolved_home_value
    )

    return PolymarketMarketIdentity(
        output_market_id=output_market_id,
        polymarket_market_id=_required_text(
            manifest_row,
            "polymarket_market_id",
        ),
        condition_id=_required_text(
            manifest_row,
            "condition_id",
        ),
        market_slug=_required_text(
            manifest_row,
            "market_slug",
        ),
        home_outcome=home_outcome,
        away_outcome=away_outcome,
        home_token_id=home_token_id,
        away_token_id=away_token_id,
        home_outcome_index=(
            home_outcome_index
        ),
        away_outcome_index=(
            away_outcome_index
        ),
        resolved_home_value=(
            resolved_home_value
        ),
        resolved_away_value=(
            resolved_away_value
        ),
        resolution_source=(
            "legacy_nba_game_result"
        ),
        settlement_time_status=(
            "unknown_not_migrated"
        ),
    )
