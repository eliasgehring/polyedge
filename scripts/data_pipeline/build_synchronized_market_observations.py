import csv
import json
from pathlib import Path
from typing import Dict, List

from polyedge.synchronized_market_observations import (
    SynchronizedMarketObservation,
    build_synchronized_market_observation,
)

from scripts.data_pipeline.archive_polymarket_price_histories import (
    capture_paths,
    parse_utc,
    sha256_file,
)


BOOKMAKER_PATH = Path(
    "data/processed/the_odds_api/"
    "historical_bookmaker_observations.csv"
)

IDENTITY_PATH = Path(
    "data/processed/polymarket/"
    "polymarket_market_identity.csv"
)

POLYMARKET_AUDIT_PATH = Path(
    "data/diagnostics/"
    "polymarket_price_history_audit.csv"
)

OUTPUT_PATH = Path(
    "data/processed/nba_v2/"
    "synchronized_market_observations.csv"
)


OUTPUT_COLUMNS = [
    "output_market_id",
    "observation_time_utc",
    "provider_event_id",
    "target_request_time_utc",
    "provider_snapshot_lag_seconds",
    "provider_commence_time_at_observation_utc",
    "provider_home_team",
    "provider_away_team",
    "bookmaker_home_fair_probability",
    "bookmaker_away_fair_probability",
    "bookmaker_count",
    "oldest_quote_age_seconds",
    "newest_quote_age_seconds",
    "seconds_before_provider_start",
    "strict_t_minus_60_eligible",
    "polymarket_market_id",
    "condition_id",
    "market_slug",
    "home_outcome",
    "away_outcome",
    "home_token_id",
    "away_token_id",
    "polymarket_history_time_utc",
    "history_point_lag_seconds",
    "polymarket_home_probability",
    "polymarket_away_probability",
    "home_probability_edge",
    "away_probability_edge",
    "resolved_home_value",
    "resolved_away_value",
    "resolution_source",
    "settlement_time_status",
    "source_semantics",
    "execution_semantics",
    "policy_version",
    "bookmaker_raw_file",
    "bookmaker_raw_sha256",
    "polymarket_home_raw_file",
    "polymarket_home_raw_sha256",
    "polymarket_away_raw_file",
    "polymarket_away_raw_sha256",
]


def read_rows(
    path: Path,
) -> List[Dict[str, str]]:
    with path.open(
        encoding="utf-8",
        newline="",
    ) as file:
        return list(csv.DictReader(file))


def unique_index(
    rows: List[Dict[str, str]],
    field_name: str,
) -> Dict[str, Dict[str, str]]:
    result = {}

    for row in rows:
        value = row[field_name]

        if value in result:
            raise ValueError(
                f"Duplicate {field_name}: {value}"
            )

        result[value] = row

    return result


def format_utc(value) -> str:
    return value.isoformat().replace(
        "+00:00",
        "Z",
    )


def load_polymarket_provenance(
    *,
    market_id: str,
    side: str,
    token_id: str,
    observation_time_utc: str,
) -> Dict[str, str]:
    cutoff = parse_utc(
        observation_time_utc
    )

    raw_path, metadata_path = capture_paths(
        market_id=market_id,
        side=side,
        cutoff_timestamp=int(
            cutoff.timestamp()
        ),
    )

    if not raw_path.exists():
        raise FileNotFoundError(raw_path)

    if not metadata_path.exists():
        raise FileNotFoundError(
            metadata_path
        )

    with metadata_path.open(
        encoding="utf-8"
    ) as file:
        metadata = json.load(file)

    if metadata.get("output_market_id") != market_id:
        raise ValueError(
            f"Metadata market mismatch: {market_id}/{side}"
        )

    if metadata.get("side") != side:
        raise ValueError(
            f"Metadata side mismatch: {market_id}/{side}"
        )

    if metadata.get("token_id") != token_id:
        raise ValueError(
            f"Metadata token mismatch: {market_id}/{side}"
        )

    actual_sha256 = sha256_file(raw_path)

    if metadata.get("raw_sha256") != actual_sha256:
        raise ValueError(
            f"Raw SHA mismatch: {market_id}/{side}"
        )

    return {
        "raw_file": str(raw_path),
        "raw_sha256": actual_sha256,
    }


def serialize(
    observation: SynchronizedMarketObservation,
    *,
    bookmaker_row: Dict[str, str],
    home_provenance: Dict[str, str],
    away_provenance: Dict[str, str],
) -> Dict[str, object]:
    return {
        "output_market_id": observation.output_market_id,
        "observation_time_utc": format_utc(
            observation.observation_time
        ),
        "provider_event_id": observation.provider_event_id,
        "target_request_time_utc": format_utc(
            observation.target_request_time
        ),
        "provider_snapshot_lag_seconds": (
            observation.provider_snapshot_lag_seconds
        ),
        "provider_commence_time_at_observation_utc": (
            format_utc(
                observation
                .provider_commence_time_at_observation
            )
        ),
        "provider_home_team": (
            observation.provider_home_team
        ),
        "provider_away_team": (
            observation.provider_away_team
        ),
        "bookmaker_home_fair_probability": (
            f"{observation.bookmaker_home_fair_probability:.15f}"
        ),
        "bookmaker_away_fair_probability": (
            f"{observation.bookmaker_away_fair_probability:.15f}"
        ),
        "bookmaker_count": observation.bookmaker_count,
        "oldest_quote_age_seconds": (
            observation.oldest_quote_age_seconds
        ),
        "newest_quote_age_seconds": (
            observation.newest_quote_age_seconds
        ),
        "seconds_before_provider_start": (
            observation.seconds_before_provider_start
        ),
        "strict_t_minus_60_eligible": str(
            observation.strict_t_minus_60_eligible
        ).lower(),
        "polymarket_market_id": (
            observation.polymarket_market_id
        ),
        "condition_id": observation.condition_id,
        "market_slug": observation.market_slug,
        "home_outcome": observation.home_outcome,
        "away_outcome": observation.away_outcome,
        "home_token_id": observation.home_token_id,
        "away_token_id": observation.away_token_id,
        "polymarket_history_time_utc": format_utc(
            observation.polymarket_history_time
        ),
        "history_point_lag_seconds": (
            observation.history_point_lag_seconds
        ),
        "polymarket_home_probability": (
            f"{observation.polymarket_home_probability:.9f}"
        ),
        "polymarket_away_probability": (
            f"{observation.polymarket_away_probability:.9f}"
        ),
        "home_probability_edge": (
            f"{observation.home_probability_edge:.15f}"
        ),
        "away_probability_edge": (
            f"{observation.away_probability_edge:.15f}"
        ),
        "resolved_home_value": (
            observation.resolved_home_value
        ),
        "resolved_away_value": (
            observation.resolved_away_value
        ),
        "resolution_source": (
            observation.resolution_source
        ),
        "settlement_time_status": (
            observation.settlement_time_status
        ),
        "source_semantics": (
            observation.source_semantics
        ),
        "execution_semantics": (
            observation.execution_semantics
        ),
        "policy_version": observation.policy_version,
        "bookmaker_raw_file": bookmaker_row["raw_file"],
        "bookmaker_raw_sha256": (
            bookmaker_row["raw_sha256"]
        ),
        "polymarket_home_raw_file": (
            home_provenance["raw_file"]
        ),
        "polymarket_home_raw_sha256": (
            home_provenance["raw_sha256"]
        ),
        "polymarket_away_raw_file": (
            away_provenance["raw_file"]
        ),
        "polymarket_away_raw_sha256": (
            away_provenance["raw_sha256"]
        ),
    }


def write_atomic(
    rows: List[Dict[str, object]],
) -> None:
    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary_path = OUTPUT_PATH.with_suffix(
        OUTPUT_PATH.suffix + ".tmp"
    )

    with temporary_path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=OUTPUT_COLUMNS,
        )
        writer.writeheader()
        writer.writerows(rows)

    temporary_path.replace(
        OUTPUT_PATH
    )


def main() -> None:
    bookmaker_rows = [
        row
        for row in read_rows(
            BOOKMAKER_PATH
        )
        if row["status"] == "eligible"
    ]

    identity_rows = read_rows(
        IDENTITY_PATH
    )

    polymarket_rows = [
        row
        for row in read_rows(
            POLYMARKET_AUDIT_PATH
        )
        if row["pair_status"] == "eligible"
    ]

    bookmaker_by_market = unique_index(
        bookmaker_rows,
        "output_market_id",
    )

    identity_by_market = unique_index(
        identity_rows,
        "output_market_id",
    )

    polymarket_by_market = unique_index(
        polymarket_rows,
        "output_market_id",
    )

    market_sets = {
        frozenset(bookmaker_by_market),
        frozenset(identity_by_market),
        frozenset(polymarket_by_market),
    }

    if len(market_sets) != 1:
        raise ValueError(
            "Bookmaker, identity, and Polymarket market sets differ"
        )

    observations = []

    for index, market_id in enumerate(
        sorted(bookmaker_by_market),
        start=1,
    ):
        bookmaker_row = bookmaker_by_market[
            market_id
        ]

        identity_row = identity_by_market[
            market_id
        ]

        polymarket_row = polymarket_by_market[
            market_id
        ]

        observation = (
            build_synchronized_market_observation(
                bookmaker_row=bookmaker_row,
                identity_row=identity_row,
                polymarket_row=polymarket_row,
            )
        )

        home_provenance = load_polymarket_provenance(
            market_id=market_id,
            side="HOME",
            token_id=observation.home_token_id,
            observation_time_utc=(
                bookmaker_row["observation_time_utc"]
            ),
        )

        away_provenance = load_polymarket_provenance(
            market_id=market_id,
            side="AWAY",
            token_id=observation.away_token_id,
            observation_time_utc=(
                bookmaker_row["observation_time_utc"]
            ),
        )

        observations.append(
            serialize(
                observation,
                bookmaker_row=bookmaker_row,
                home_provenance=home_provenance,
                away_provenance=away_provenance,
            )
        )

        if (
            index == 1
            or index % 100 == 0
            or index == len(bookmaker_by_market)
        ):
            print(
                f"[{index}/{len(bookmaker_by_market)}] "
                "synchronized observations built"
            )

    observations.sort(
        key=lambda row: (
            row["observation_time_utc"],
            row["output_market_id"],
        )
    )

    if len(observations) != 1217:
        raise AssertionError(
            "Expected 1217 synchronized rows, "
            f"got {len(observations)}"
        )

    write_atomic(observations)

    strict_count = sum(
        row["strict_t_minus_60_eligible"] == "true"
        for row in observations
    )

    home_wins = sum(
        int(row["resolved_home_value"])
        for row in observations
    )

    away_wins = sum(
        int(row["resolved_away_value"])
        for row in observations
    )

    positive_home_edges = sum(
        float(row["home_probability_edge"]) > 0
        for row in observations
    )

    positive_away_edges = sum(
        float(row["away_probability_edge"]) > 0
        for row in observations
    )

    print()
    print("SYNCHRONIZED MARKET OBSERVATIONS")
    print("=" * 64)
    print(
        f"Rows written                : {len(observations)}"
    )
    print(
        f"Strict T-60 eligible        : {strict_count}"
    )
    print(
        f"Resolved HOME outcomes      : {home_wins}"
    )
    print(
        f"Resolved AWAY outcomes      : {away_wins}"
    )
    print(
        f"Positive HOME edges         : {positive_home_edges}"
    )
    print(
        f"Positive AWAY edges         : {positive_away_edges}"
    )
    print(
        "Source semantics            : "
        + observations[0]["source_semantics"]
    )
    print(
        "Execution semantics         : "
        + observations[0]["execution_semantics"]
    )
    print(
        "Policy version              : "
        + observations[0]["policy_version"]
    )
    print(f"Output CSV                  : {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
