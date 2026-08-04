from dataclasses import dataclass
from datetime import datetime, timezone
from math import isfinite
from typing import Any, Dict, List


@dataclass(frozen=True)
class BookmakerMoneylineQuote:
    event_id: str
    sport_key: str
    commence_time: datetime
    home_team: str
    away_team: str
    bookmaker_key: str
    bookmaker_title: str
    bookmaker_last_update: datetime
    market_last_update: datetime
    home_decimal_odds: float
    away_decimal_odds: float
    home_fair_prob: float
    away_fair_prob: float


def parse_utc_timestamp(
    value: Any,
    field_name: str,
) -> datetime:
    text = str(value).strip()

    if not text:
        raise ValueError(
            f"{field_name} must be a non-empty timestamp"
        )

    if text.endswith("Z"):
        text = text[:-1] + "+00:00"

    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(
            f"{field_name} must be a valid ISO timestamp"
        ) from exc

    if parsed.tzinfo is None:
        raise ValueError(
            f"{field_name} must include a timezone"
        )

    return parsed.astimezone(timezone.utc)


def required_text(
    value: Any,
    field_name: str,
) -> str:
    text = str(value).strip()

    if not text:
        raise ValueError(
            f"{field_name} must be a non-empty string"
        )

    return text


def parse_decimal_odds(
    value: Any,
    field_name: str,
) -> float:
    if isinstance(value, bool):
        raise TypeError(
            f"{field_name} must be numeric decimal odds"
        )

    try:
        odds = float(value)
    except (TypeError, ValueError) as exc:
        raise TypeError(
            f"{field_name} must be numeric decimal odds"
        ) from exc

    if not isfinite(odds):
        raise ValueError(
            f"{field_name} must be finite"
        )

    if odds <= 1.0:
        raise ValueError(
            f"{field_name} must be greater than 1.0"
        )

    return odds


def fair_two_way_probabilities(
    home_decimal_odds: float,
    away_decimal_odds: float,
):
    raw_home = 1.0 / home_decimal_odds
    raw_away = 1.0 / away_decimal_odds
    total = raw_home + raw_away

    if total <= 0.0:
        raise ValueError(
            "Two-way implied probability total must be positive"
        )

    return (
        raw_home / total,
        raw_away / total,
    )


def parse_the_odds_api_moneylines(
    payload: Any,
) -> List[BookmakerMoneylineQuote]:
    if not isinstance(payload, list):
        raise TypeError(
            "The Odds API payload must be a list"
        )

    quotes = []

    for event in payload:
        if not isinstance(event, dict):
            raise TypeError(
                "Each event must be a dictionary"
            )

        event_id = required_text(
            event.get("id"),
            "event.id",
        )
        sport_key = required_text(
            event.get("sport_key"),
            "event.sport_key",
        )
        commence_time = parse_utc_timestamp(
            event.get("commence_time"),
            "event.commence_time",
        )
        home_team = required_text(
            event.get("home_team"),
            "event.home_team",
        )
        away_team = required_text(
            event.get("away_team"),
            "event.away_team",
        )

        bookmakers = event.get("bookmakers", [])

        if not isinstance(bookmakers, list):
            raise TypeError(
                "event.bookmakers must be a list"
            )

        for bookmaker in bookmakers:
            if not isinstance(bookmaker, dict):
                raise TypeError(
                    "Each bookmaker must be a dictionary"
                )

            bookmaker_key = required_text(
                bookmaker.get("key"),
                "bookmaker.key",
            )
            bookmaker_title = required_text(
                bookmaker.get("title"),
                "bookmaker.title",
            )
            bookmaker_last_update = parse_utc_timestamp(
                bookmaker.get("last_update"),
                "bookmaker.last_update",
            )

            markets = bookmaker.get("markets", [])

            if not isinstance(markets, list):
                raise TypeError(
                    "bookmaker.markets must be a list"
                )

            h2h_markets = [
                market
                for market in markets
                if isinstance(market, dict)
                and market.get("key") == "h2h"
            ]

            if not h2h_markets:
                continue

            if len(h2h_markets) != 1:
                raise ValueError(
                    f"{event_id}/{bookmaker_key} has "
                    f"{len(h2h_markets)} h2h markets"
                )

            h2h_market = h2h_markets[0]

            market_last_update = parse_utc_timestamp(
                h2h_market.get("last_update"),
                "market.last_update",
            )

            outcomes = h2h_market.get("outcomes", [])

            if not isinstance(outcomes, list):
                raise TypeError(
                    "market.outcomes must be a list"
                )

            outcomes_by_name: Dict[str, Dict[str, Any]] = {}

            for outcome in outcomes:
                if not isinstance(outcome, dict):
                    raise TypeError(
                        "Each outcome must be a dictionary"
                    )

                outcome_name = required_text(
                    outcome.get("name"),
                    "outcome.name",
                )
                outcomes_by_name[outcome_name] = outcome

            if home_team not in outcomes_by_name:
                raise ValueError(
                    f"{event_id}/{bookmaker_key} is missing "
                    f"home outcome {home_team!r}"
                )

            if away_team not in outcomes_by_name:
                raise ValueError(
                    f"{event_id}/{bookmaker_key} is missing "
                    f"away outcome {away_team!r}"
                )

            home_decimal_odds = parse_decimal_odds(
                outcomes_by_name[home_team].get("price"),
                "home decimal odds",
            )
            away_decimal_odds = parse_decimal_odds(
                outcomes_by_name[away_team].get("price"),
                "away decimal odds",
            )

            (
                home_fair_prob,
                away_fair_prob,
            ) = fair_two_way_probabilities(
                home_decimal_odds,
                away_decimal_odds,
            )

            quotes.append(
                BookmakerMoneylineQuote(
                    event_id=event_id,
                    sport_key=sport_key,
                    commence_time=commence_time,
                    home_team=home_team,
                    away_team=away_team,
                    bookmaker_key=bookmaker_key,
                    bookmaker_title=bookmaker_title,
                    bookmaker_last_update=bookmaker_last_update,
                    market_last_update=market_last_update,
                    home_decimal_odds=home_decimal_odds,
                    away_decimal_odds=away_decimal_odds,
                    home_fair_prob=home_fair_prob,
                    away_fair_prob=away_fair_prob,
                )
            )

    return quotes
