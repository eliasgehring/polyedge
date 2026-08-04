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
    target_decision_time: datetime
    observation_time: datetime
    provider_snapshot_lag_seconds: int
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


def _require_timezone(
    timestamp: datetime,
    field_name: str,
) -> None:
    if timestamp.tzinfo is None:
        raise ValueError(
            f"{field_name} must include a timezone"
        )


def select_bookmaker_consensus(
    quotes: Iterable[BookmakerMoneylineQuote],
    event_id: str,
    target_decision_time: datetime,
    observation_time: datetime,
    approved_bookmakers: Iterable[str],
    max_snapshot_lag_seconds: int,
    max_staleness_seconds: int,
    min_bookmakers: int = 3,
) -> ConsensusSelection:
    """
    Construct a bookmaker consensus using only information available
    in the provider snapshot.

    target_decision_time:
        Intended strategy time, such as provider commence time minus
        sixty minutes.

    observation_time:
        Timestamp of the historical provider snapshot actually
        returned. This must be no later than target_decision_time.

    Bookmaker quote age is measured from observation_time, not from
    target_decision_time.
    """

    _require_timezone(
        target_decision_time,
        "target_decision_time",
    )
    _require_timezone(
        observation_time,
        "observation_time",
    )

    if max_snapshot_lag_seconds < 0:
        raise ValueError(
            "max_snapshot_lag_seconds must be non-negative"
        )

    if max_staleness_seconds < 0:
        raise ValueError(
            "max_staleness_seconds must be non-negative"
        )

    if min_bookmakers <= 0:
        raise ValueError(
            "min_bookmakers must be positive"
        )

    if observation_time > target_decision_time:
        raise ValueError(
            "observation_time must not be after "
            "target_decision_time"
        )

    snapshot_lag_seconds = int(
        (
            target_decision_time
            - observation_time
        ).total_seconds()
    )

    if snapshot_lag_seconds > max_snapshot_lag_seconds:
        return ConsensusSelection(
            consensus=None,
            reason="provider_snapshot_too_old",
            eligible_quote_count=0,
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

    event_quotes = [
        quote
        for quote in quotes
        if quote.event_id == event_id
    ]

    if not event_quotes:
        return ConsensusSelection(
            consensus=None,
            reason="event_not_found",
            eligible_quote_count=0,
        )

    commence_times = {
        quote.commence_time
        for quote in event_quotes
    }

    if len(commence_times) != 1:
        raise ValueError(
            "Quotes disagree on event commence time"
        )

    commence_time = next(iter(commence_times))

    if target_decision_time >= commence_time:
        return ConsensusSelection(
            consensus=None,
            reason="decision_not_pregame",
            eligible_quote_count=0,
        )

    latest_by_bookmaker = {}

    for quote in event_quotes:
        if quote.bookmaker_key not in approved:
            continue

        if quote.market_last_update > observation_time:
            continue

        quote_age_seconds = int(
            (
                observation_time
                - quote.market_last_update
            ).total_seconds()
        )

        if quote_age_seconds > max_staleness_seconds:
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

    quote_ages = tuple(
        int(
            (
                observation_time
                - quote.market_last_update
            ).total_seconds()
        )
        for quote in selected
    )

    consensus = BookmakerConsensus(
        event_id=event_id,
        home_team=selected[0].home_team,
        away_team=selected[0].away_team,
        target_decision_time=target_decision_time,
        observation_time=observation_time,
        provider_snapshot_lag_seconds=(
            snapshot_lag_seconds
        ),
        home_fair_prob=home_fair_prob,
        away_fair_prob=1.0 - home_fair_prob,
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
