from dataclasses import dataclass
from datetime import datetime
from statistics import median
from typing import Iterable, Optional, Tuple

from .bookmaker_odds import BookmakerMoneylineQuote


@dataclass(frozen=True)
class BookmakerConsensus:
    event_id: str
    home_team: str
    away_team: str
    decision_time: datetime
    home_fair_prob: float
    away_fair_prob: float
    bookmaker_keys: Tuple[str, ...]
    quote_timestamps: Tuple[datetime, ...]
    oldest_quote_age_seconds: int
    newest_quote_age_seconds: int


@dataclass(frozen=True)
class ConsensusSelection:
    consensus: Optional[BookmakerConsensus]
    reason: Optional[str]
    eligible_quote_count: int


def select_bookmaker_consensus(
    quotes: Iterable[BookmakerMoneylineQuote],
    event_id: str,
    decision_time: datetime,
    approved_bookmakers: Iterable[str],
    max_staleness_seconds: int,
    min_bookmakers: int = 3,
) -> ConsensusSelection:
    """
    Select one fresh quote per approved bookmaker and calculate the
    median vig-free home probability.

    A quote is eligible only when:
    - it belongs to the requested event;
    - its bookmaker is approved;
    - its market update is at or before decision_time;
    - its age does not exceed max_staleness_seconds.

    When multiple eligible quotes exist for one bookmaker, the latest
    quote at or before decision_time is selected.
    """

    if decision_time.tzinfo is None:
        raise ValueError(
            "decision_time must include a timezone"
        )

    if max_staleness_seconds < 0:
        raise ValueError(
            "max_staleness_seconds must be non-negative"
        )

    if min_bookmakers <= 0:
        raise ValueError(
            "min_bookmakers must be positive"
        )

    approved = {
        bookmaker.strip()
        for bookmaker in approved_bookmakers
        if bookmaker.strip()
    }

    if not approved:
        raise ValueError(
            "approved_bookmakers must not be empty"
        )

    latest_by_bookmaker = {}

    for quote in quotes:
        if quote.event_id != event_id:
            continue

        if quote.bookmaker_key not in approved:
            continue

        if decision_time >= quote.commence_time:
            continue

        if quote.market_last_update > decision_time:
            continue

        age_seconds = int(
            (
                decision_time
                - quote.market_last_update
            ).total_seconds()
        )

        if age_seconds > max_staleness_seconds:
            continue

        existing = latest_by_bookmaker.get(
            quote.bookmaker_key
        )

        if (
            existing is None
            or quote.market_last_update
            > existing.market_last_update
        ):
            latest_by_bookmaker[
                quote.bookmaker_key
            ] = quote

    selected = tuple(
        latest_by_bookmaker[key]
        for key in sorted(latest_by_bookmaker)
    )

    if len(selected) < min_bookmakers:
        return ConsensusSelection(
            consensus=None,
            reason="insufficient_fresh_bookmakers",
            eligible_quote_count=len(selected),
        )

    home_teams = {
        quote.home_team
        for quote in selected
    }
    away_teams = {
        quote.away_team
        for quote in selected
    }

    if len(home_teams) != 1 or len(away_teams) != 1:
        raise ValueError(
            "Selected quotes disagree on event teams"
        )

    home_fair_prob = median(
        quote.home_fair_prob
        for quote in selected
    )
    away_fair_prob = 1.0 - home_fair_prob

    quote_ages = tuple(
        int(
            (
                decision_time
                - quote.market_last_update
            ).total_seconds()
        )
        for quote in selected
    )

    consensus = BookmakerConsensus(
        event_id=event_id,
        home_team=selected[0].home_team,
        away_team=selected[0].away_team,
        decision_time=decision_time,
        home_fair_prob=home_fair_prob,
        away_fair_prob=away_fair_prob,
        bookmaker_keys=tuple(
            quote.bookmaker_key
            for quote in selected
        ),
        quote_timestamps=tuple(
            quote.market_last_update
            for quote in selected
        ),
        oldest_quote_age_seconds=max(quote_ages),
        newest_quote_age_seconds=min(quote_ages),
    )

    return ConsensusSelection(
        consensus=consensus,
        reason=None,
        eligible_quote_count=len(selected),
    )
