from dataclasses import dataclass
from datetime import datetime
from typing import Mapping, Optional, Sequence, Tuple

from polyedge.bookmaker_consensus import (
    select_bookmaker_consensus,
)
from polyedge.bookmaker_odds import (
    BookmakerMoneylineQuote,
)
from polyedge.bookmaker_policy import (
    APPROVED_BOOKMAKERS,
    DECISION_MINUTES_BEFORE_GAME,
    MAX_BOOKMAKER_STALENESS_SECONDS,
    MAX_PROVIDER_SNAPSHOT_LAG_SECONDS,
    MIN_BOOKMAKERS,
)


@dataclass(frozen=True)
class HistoricalBookmakerObservation:
    output_market_id: str
    provider_event_id: str

    target_request_time: datetime
    observation_time: datetime
    provider_snapshot_lag_seconds: int

    provider_commence_time: Optional[datetime]
    provider_home_team: str
    provider_away_team: str

    home_fair_prob: Optional[float]
    away_fair_prob: Optional[float]

    bookmaker_count: int
    bookmaker_keys: Tuple[str, ...]
    quote_timestamps: Tuple[datetime, ...]

    oldest_quote_age_seconds: Optional[int]
    newest_quote_age_seconds: Optional[int]

    seconds_before_provider_start: Optional[int]
    pregame_at_observation: bool
    strict_t_minus_60_eligible: bool

    status: str
    exclusion_reason: Optional[str]


def _require_aware(
    value: datetime,
    field_name: str,
) -> None:
    if (
        value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise ValueError(
            f"{field_name} must be timezone-aware"
        )


def _parse_utc(value: object) -> datetime:
    if not isinstance(value, str):
        raise ValueError(
            f"Expected timestamp string, got {value!r}"
        )

    text = value.strip().replace(
        "Z",
        "+00:00",
    )

    if text.endswith("+00"):
        text += ":00"

    timestamp = datetime.fromisoformat(text)

    _require_aware(
        timestamp,
        "provider timestamp",
    )

    return timestamp


def _excluded(
    *,
    output_market_id: str,
    provider_event_id: str,
    target_request_time: datetime,
    observation_time: datetime,
    provider_snapshot_lag_seconds: int,
    provider_commence_time: Optional[datetime],
    provider_home_team: str,
    provider_away_team: str,
    bookmaker_count: int,
    seconds_before_provider_start: Optional[int],
    pregame_at_observation: bool,
    reason: str,
) -> HistoricalBookmakerObservation:
    return HistoricalBookmakerObservation(
        output_market_id=output_market_id,
        provider_event_id=provider_event_id,
        target_request_time=target_request_time,
        observation_time=observation_time,
        provider_snapshot_lag_seconds=(
            provider_snapshot_lag_seconds
        ),
        provider_commence_time=provider_commence_time,
        provider_home_team=provider_home_team,
        provider_away_team=provider_away_team,
        home_fair_prob=None,
        away_fair_prob=None,
        bookmaker_count=bookmaker_count,
        bookmaker_keys=(),
        quote_timestamps=(),
        oldest_quote_age_seconds=None,
        newest_quote_age_seconds=None,
        seconds_before_provider_start=(
            seconds_before_provider_start
        ),
        pregame_at_observation=(
            pregame_at_observation
        ),
        strict_t_minus_60_eligible=False,
        status="excluded",
        exclusion_reason=reason,
    )


def build_historical_bookmaker_observation(
    *,
    output_market_id: str,
    provider_event_id: str,
    expected_home_team: str,
    expected_away_team: str,
    target_request_time: datetime,
    observation_time: datetime,
    events: Sequence[Mapping[str, object]],
    quotes: Sequence[BookmakerMoneylineQuote],
) -> HistoricalBookmakerObservation:
    _require_aware(
        target_request_time,
        "target_request_time",
    )
    _require_aware(
        observation_time,
        "observation_time",
    )

    if observation_time > target_request_time:
        raise ValueError(
            "Provider observation occurred after "
            "the requested target time"
        )

    provider_snapshot_lag_seconds = int(
        (
            target_request_time
            - observation_time
        ).total_seconds()
    )

    matching_events = [
        event
        for event in events
        if str(
            event.get("id", "")
        ).strip() == provider_event_id
    ]

    if len(matching_events) > 1:
        raise ValueError(
            "Duplicate provider event ID inside "
            f"one snapshot: {provider_event_id}"
        )

    if not matching_events:
        return _excluded(
            output_market_id=output_market_id,
            provider_event_id=provider_event_id,
            target_request_time=target_request_time,
            observation_time=observation_time,
            provider_snapshot_lag_seconds=(
                provider_snapshot_lag_seconds
            ),
            provider_commence_time=None,
            provider_home_team=expected_home_team,
            provider_away_team=expected_away_team,
            bookmaker_count=0,
            seconds_before_provider_start=None,
            pregame_at_observation=False,
            reason="provider_event_missing",
        )

    event = matching_events[0]

    provider_home_team = str(
        event.get("home_team", "")
    ).strip()
    provider_away_team = str(
        event.get("away_team", "")
    ).strip()

    commence_time = _parse_utc(
        event.get("commence_time")
    )

    seconds_before_provider_start = int(
        (
            commence_time
            - observation_time
        ).total_seconds()
    )

    pregame_at_observation = (
        seconds_before_provider_start > 0
    )

    if (
        provider_home_team != expected_home_team
        or provider_away_team != expected_away_team
    ):
        return _excluded(
            output_market_id=output_market_id,
            provider_event_id=provider_event_id,
            target_request_time=target_request_time,
            observation_time=observation_time,
            provider_snapshot_lag_seconds=(
                provider_snapshot_lag_seconds
            ),
            provider_commence_time=commence_time,
            provider_home_team=provider_home_team,
            provider_away_team=provider_away_team,
            bookmaker_count=0,
            seconds_before_provider_start=(
                seconds_before_provider_start
            ),
            pregame_at_observation=(
                pregame_at_observation
            ),
            reason="provider_identity_mismatch",
        )

    if not pregame_at_observation:
        return _excluded(
            output_market_id=output_market_id,
            provider_event_id=provider_event_id,
            target_request_time=target_request_time,
            observation_time=observation_time,
            provider_snapshot_lag_seconds=(
                provider_snapshot_lag_seconds
            ),
            provider_commence_time=commence_time,
            provider_home_team=provider_home_team,
            provider_away_team=provider_away_team,
            bookmaker_count=0,
            seconds_before_provider_start=(
                seconds_before_provider_start
            ),
            pregame_at_observation=False,
            reason="snapshot_not_pregame",
        )

    selection = select_bookmaker_consensus(
        quotes=quotes,
        event_id=provider_event_id,
        target_decision_time=(
            target_request_time
        ),
        observation_time=observation_time,
        approved_bookmakers=set(
            APPROVED_BOOKMAKERS
        ),
        max_snapshot_lag_seconds=(
            MAX_PROVIDER_SNAPSHOT_LAG_SECONDS
        ),
        max_staleness_seconds=(
            MAX_BOOKMAKER_STALENESS_SECONDS
        ),
        min_bookmakers=MIN_BOOKMAKERS,
    )

    if selection.consensus is None:
        return _excluded(
            output_market_id=output_market_id,
            provider_event_id=provider_event_id,
            target_request_time=target_request_time,
            observation_time=observation_time,
            provider_snapshot_lag_seconds=(
                provider_snapshot_lag_seconds
            ),
            provider_commence_time=commence_time,
            provider_home_team=provider_home_team,
            provider_away_team=provider_away_team,
            bookmaker_count=(
                selection.eligible_quote_count
            ),
            seconds_before_provider_start=(
                seconds_before_provider_start
            ),
            pregame_at_observation=True,
            reason=(
                selection.reason
                or "bookmaker_consensus_unavailable"
            ),
        )

    consensus = selection.consensus

    if consensus.event_id != provider_event_id:
        raise ValueError(
            "Consensus event ID does not match "
            "the requested provider event"
        )

    if (
        consensus.home_team != provider_home_team
        or consensus.away_team != provider_away_team
    ):
        raise ValueError(
            "Consensus team identity does not "
            "match the provider event"
        )

    strict_cutoff_seconds = (
        DECISION_MINUTES_BEFORE_GAME
        * 60
    )

    return HistoricalBookmakerObservation(
        output_market_id=output_market_id,
        provider_event_id=provider_event_id,
        target_request_time=target_request_time,
        observation_time=observation_time,
        provider_snapshot_lag_seconds=(
            consensus.provider_snapshot_lag_seconds
        ),
        provider_commence_time=commence_time,
        provider_home_team=provider_home_team,
        provider_away_team=provider_away_team,
        home_fair_prob=consensus.home_fair_prob,
        away_fair_prob=consensus.away_fair_prob,
        bookmaker_count=len(
            consensus.bookmaker_keys
        ),
        bookmaker_keys=tuple(
            consensus.bookmaker_keys
        ),
        quote_timestamps=tuple(
            consensus.quote_timestamps
        ),
        oldest_quote_age_seconds=(
            consensus.oldest_quote_age_seconds
        ),
        newest_quote_age_seconds=(
            consensus.newest_quote_age_seconds
        ),
        seconds_before_provider_start=(
            seconds_before_provider_start
        ),
        pregame_at_observation=True,
        strict_t_minus_60_eligible=(
            seconds_before_provider_start
            >= strict_cutoff_seconds
        ),
        status="eligible",
        exclusion_reason=None,
    )
