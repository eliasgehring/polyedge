import json
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set


TEAM_OUTCOME_ALIASES = {
    "atlanta": {"hawks", "atlanta hawks"},
    "boston": {"celtics", "boston celtics"},
    "brooklyn": {"nets", "brooklyn nets"},
    "charlotte": {"hornets", "charlotte hornets"},
    "chicago": {"bulls", "chicago bulls"},
    "cleveland": {"cavaliers", "cavs", "cleveland cavaliers"},
    "dallas": {"mavericks", "mavs", "dallas mavericks"},
    "denver": {"nuggets", "denver nuggets"},
    "detroit": {"pistons", "detroit pistons"},
    "golden state": {"warriors", "golden state warriors"},
    "houston": {"rockets", "houston rockets"},
    "indiana": {"pacers", "indiana pacers"},
    "la clippers": {
        "clippers",
        "la clippers",
        "los angeles clippers",
    },
    "la lakers": {
        "lakers",
        "la lakers",
        "los angeles lakers",
    },
    "memphis": {"grizzlies", "memphis grizzlies"},
    "miami": {"heat", "miami heat"},
    "milwaukee": {"bucks", "milwaukee bucks"},
    "minnesota": {"timberwolves", "wolves", "minnesota timberwolves"},
    "new orleans": {"pelicans", "new orleans pelicans"},
    "new york": {"knicks", "new york knicks"},
    "oklahoma city": {
        "thunder",
        "oklahoma city thunder",
    },
    "orlando": {"magic", "orlando magic"},
    "philadelphia": {
        "76ers",
        "sixers",
        "philadelphia 76ers",
    },
    "phoenix": {"suns", "phoenix suns"},
    "portland": {
        "trail blazers",
        "blazers",
        "portland trail blazers",
    },
    "sacramento": {"kings", "sacramento kings"},
    "san antonio": {"spurs", "san antonio spurs"},
    "toronto": {"raptors", "toronto raptors"},
    "utah": {"jazz", "utah jazz"},
    "washington": {"wizards", "washington wizards"},
}


@dataclass(frozen=True)
class HomeTokenSelection:
    event_id: str
    event_slug: str
    event_title: str
    market_id: str
    condition_id: str
    market_slug: str
    market_question: str
    game_start_time: str
    home_outcome: str
    away_outcome: str
    home_token_id: str
    away_token_id: str
    home_outcome_index: int
    away_outcome_index: int


@dataclass(frozen=True)
class SelectionResult:
    selection: Optional[HomeTokenSelection]
    reason: Optional[str]
    candidate_count: int


def normalize_team_label(value: Any) -> str:
    text = str(value).strip().lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def parse_list_field(value: Any) -> List[Any]:
    if isinstance(value, list):
        return value

    if not isinstance(value, str):
        return []

    value = value.strip()

    if not value:
        return []

    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return []

    if isinstance(parsed, list):
        return parsed

    return []


def team_aliases(team_name: str) -> Optional[Set[str]]:
    canonical_name = normalize_team_label(team_name)
    configured_aliases = TEAM_OUTCOME_ALIASES.get(canonical_name)

    if configured_aliases is None:
        return None

    aliases = {
        normalize_team_label(alias)
        for alias in configured_aliases
    }
    aliases.add(canonical_name)

    return aliases


def matching_outcome_index(
    outcomes: List[str],
    aliases: Set[str],
) -> Optional[int]:
    matching_indices = [
        index
        for index, outcome in enumerate(outcomes)
        if normalize_team_label(outcome) in aliases
    ]

    if len(matching_indices) != 1:
        return None

    return matching_indices[0]


def select_home_token(
    event: Dict[str, Any],
    expected_home_team: str,
    expected_away_team: str,
) -> SelectionResult:
    home_aliases = team_aliases(expected_home_team)
    away_aliases = team_aliases(expected_away_team)

    if home_aliases is None or away_aliases is None:
        return SelectionResult(
            selection=None,
            reason="unknown_expected_team",
            candidate_count=0,
        )

    markets = event.get("markets")

    if not isinstance(markets, list):
        return SelectionResult(
            selection=None,
            reason="event_markets_not_list",
            candidate_count=0,
        )

    candidates = []

    for market in markets:
        if not isinstance(market, dict):
            continue

        market_type = normalize_team_label(
            market.get("sportsMarketType", "")
        )

        if market_type != "moneyline":
            continue

        raw_outcomes = parse_list_field(market.get("outcomes"))
        raw_token_ids = parse_list_field(
            market.get("clobTokenIds")
        )

        if len(raw_outcomes) != 2 or len(raw_token_ids) != 2:
            continue

        outcomes = [str(outcome) for outcome in raw_outcomes]
        token_ids = [str(token_id) for token_id in raw_token_ids]

        if any(not token_id.strip() for token_id in token_ids):
            continue

        home_index = matching_outcome_index(
            outcomes,
            home_aliases,
        )
        away_index = matching_outcome_index(
            outcomes,
            away_aliases,
        )

        if home_index is None or away_index is None:
            continue

        if home_index == away_index:
            continue

        candidates.append(
            HomeTokenSelection(
                event_id=str(event.get("id", "")),
                event_slug=str(event.get("slug", "")),
                event_title=str(event.get("title", "")),
                market_id=str(market.get("id", "")),
                condition_id=str(market.get("conditionId", "")),
                market_slug=str(market.get("slug", "")),
                market_question=str(market.get("question", "")),
                game_start_time=str(
                    market.get("gameStartTime", "")
                ),
                home_outcome=outcomes[home_index],
                away_outcome=outcomes[away_index],
                home_token_id=token_ids[home_index],
                away_token_id=token_ids[away_index],
                home_outcome_index=home_index,
                away_outcome_index=away_index,
            )
        )

    if len(candidates) == 0:
        return SelectionResult(
            selection=None,
            reason="no_matching_moneyline_market",
            candidate_count=0,
        )

    if len(candidates) > 1:
        return SelectionResult(
            selection=None,
            reason="ambiguous_moneyline_markets",
            candidate_count=len(candidates),
        )

    return SelectionResult(
        selection=candidates[0],
        reason=None,
        candidate_count=1,
    )
