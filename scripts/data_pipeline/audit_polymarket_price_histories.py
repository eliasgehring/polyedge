import csv
import json
import math
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional

from polyedge.polymarket_observations import (
    build_polymarket_outcome_observation,
    combine_polymarket_outcomes,
)

from scripts.data_pipeline.archive_polymarket_price_histories import (
    ARCHIVE_DIR,
    FIDELITY_MINUTES,
    LOOKBACK_SECONDS,
    capture_paths,
    format_utc,
    parse_utc,
    sha256_file,
    validate_payload,
)


BOOKMAKER_PATH = Path(
    "data/processed/the_odds_api/"
    "historical_bookmaker_observations.csv"
)

IDENTITY_PATH = Path(
    "data/processed/polymarket/"
    "polymarket_market_identity.csv"
)

OUTPUT_PATH = Path(
    "data/diagnostics/"
    "polymarket_price_history_audit.csv"
)

AGE_THRESHOLDS_SECONDS = [
    60,
    300,
    900,
    3600,
    21600,
]

COMPLEMENTARITY_TOLERANCES = [
    0.000000001,
    0.001,
    0.005,
    0.010,
    0.020,
    0.050,
]

OUTPUT_COLUMNS = [
    "output_market_id",
    "observation_time_utc",
    "home_token_id",
    "away_token_id",
    "home_status",
    "home_exclusion_reason",
    "home_price",
    "home_price_time_utc",
    "home_price_age_seconds",
    "away_status",
    "away_exclusion_reason",
    "away_price",
    "away_price_time_utc",
    "away_price_age_seconds",
    "pair_status",
    "pair_exclusion_reason",
    "timestamp_gap_seconds",
    "max_price_age_seconds",
    "price_sum",
    "complementarity_error",
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


def load_capture(
    *,
    market_id: str,
    side: str,
    token_id: str,
    cutoff,
) -> Dict[str, object]:
    cutoff_timestamp = int(
        cutoff.timestamp()
    )

    raw_path, metadata_path = (
        capture_paths(
            market_id=market_id,
            side=side,
            cutoff_timestamp=(
                cutoff_timestamp
            ),
        )
    )

    if not raw_path.exists():
        raise FileNotFoundError(raw_path)

    if not metadata_path.exists():
        raise FileNotFoundError(
            metadata_path
        )

    with raw_path.open(
        encoding="utf-8"
    ) as file:
        payload = validate_payload(
            json.load(file)
        )

    with metadata_path.open(
        encoding="utf-8"
    ) as file:
        metadata = json.load(file)

    expected_parameters = {
        "market": token_id,
        "startTs": (
            cutoff_timestamp
            - LOOKBACK_SECONDS
        ),
        "endTs": cutoff_timestamp,
        "fidelity": FIDELITY_MINUTES,
    }

    if (
        metadata.get("output_market_id")
        != market_id
    ):
        raise ValueError(
            f"Metadata market mismatch: "
            f"{market_id}/{side}"
        )

    if metadata.get("side") != side:
        raise ValueError(
            f"Metadata side mismatch: "
            f"{market_id}/{side}"
        )

    if metadata.get("token_id") != token_id:
        raise ValueError(
            f"Metadata token mismatch: "
            f"{market_id}/{side}"
        )

    if (
        metadata.get("common_cutoff_utc")
        != format_utc(cutoff)
    ):
        raise ValueError(
            f"Metadata cutoff mismatch: "
            f"{market_id}/{side}"
        )

    if (
        metadata.get("request_parameters")
        != expected_parameters
    ):
        raise ValueError(
            f"Request parameter mismatch: "
            f"{market_id}/{side}"
        )

    if (
        metadata.get("raw_sha256")
        != sha256_file(raw_path)
    ):
        raise ValueError(
            f"SHA-256 mismatch: "
            f"{market_id}/{side}"
        )

    point_count = len(
        payload["history"]
    )

    if (
        metadata.get("history_point_count")
        != point_count
    ):
        raise ValueError(
            f"Point-count mismatch: "
            f"{market_id}/{side}"
        )

    return payload


def optional_text(
    value,
) -> str:
    if value is None:
        return ""

    return str(value)


def optional_float(
    value: Optional[float],
) -> str:
    if value is None:
        return ""

    return f"{value:.9f}"


def percentile_nearest_rank(
    values: List[float],
    probability: float,
) -> float:
    if not values:
        raise ValueError(
            "Cannot calculate percentile "
            "of empty values"
        )

    ordered = sorted(values)

    rank = math.ceil(
        probability * len(ordered)
    )

    rank = max(
        1,
        min(rank, len(ordered)),
    )

    return ordered[rank - 1]


def print_distribution(
    label: str,
    values: List[float],
) -> None:
    if not values:
        print(f"{label}: no observations")
        return

    p50 = percentile_nearest_rank(
        values,
        0.50,
    )

    p90 = percentile_nearest_rank(
        values,
        0.90,
    )

    p95 = percentile_nearest_rank(
        values,
        0.95,
    )

    p99 = percentile_nearest_rank(
        values,
        0.99,
    )

    print(
        f"{label:<29} "
        f"min={min(values):.3f} "
        f"p50={p50:.3f} "
        f"p90={p90:.3f} "
        f"p95={p95:.3f} "
        f"p99={p99:.3f} "
        f"max={max(values):.3f}"
    )


def write_atomic(
    rows: List[Dict[str, str]],
) -> None:
    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary_path = (
        OUTPUT_PATH.with_suffix(
            OUTPUT_PATH.suffix + ".tmp"
        )
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
    bookmaker_rows = read_rows(
        BOOKMAKER_PATH
    )

    identity_rows = read_rows(
        IDENTITY_PATH
    )

    eligible_bookmakers = [
        row
        for row in bookmaker_rows
        if row["status"] == "eligible"
    ]

    bookmaker_by_market = unique_index(
        eligible_bookmakers,
        "output_market_id",
    )

    identity_by_market = unique_index(
        identity_rows,
        "output_market_id",
    )

    if set(bookmaker_by_market) != set(
        identity_by_market
    ):
        raise ValueError(
            "Bookmaker and identity market "
            "sets differ"
        )

    output_rows = []
    pair_objects = []

    for index, market_id in enumerate(
        sorted(bookmaker_by_market),
        start=1,
    ):
        bookmaker = bookmaker_by_market[
            market_id
        ]

        identity = identity_by_market[
            market_id
        ]

        cutoff = parse_utc(
            bookmaker[
                "observation_time_utc"
            ]
        )

        home_payload = load_capture(
            market_id=market_id,
            side="HOME",
            token_id=identity[
                "home_token_id"
            ],
            cutoff=cutoff,
        )

        away_payload = load_capture(
            market_id=market_id,
            side="AWAY",
            token_id=identity[
                "away_token_id"
            ],
            cutoff=cutoff,
        )

        home = (
            build_polymarket_outcome_observation(
                output_market_id=market_id,
                side="HOME",
                token_id=identity[
                    "home_token_id"
                ],
                common_cutoff=cutoff,
                history=home_payload[
                    "history"
                ],
                max_staleness_seconds=(
                    LOOKBACK_SECONDS
                ),
            )
        )

        away = (
            build_polymarket_outcome_observation(
                output_market_id=market_id,
                side="AWAY",
                token_id=identity[
                    "away_token_id"
                ],
                common_cutoff=cutoff,
                history=away_payload[
                    "history"
                ],
                max_staleness_seconds=(
                    LOOKBACK_SECONDS
                ),
            )
        )

        pair = combine_polymarket_outcomes(
            home=home,
            away=away,
        )

        pair_objects.append(pair)

        output_rows.append({
            "output_market_id": market_id,
            "observation_time_utc": (
                format_utc(cutoff)
            ),
            "home_token_id": (
                home.token_id
            ),
            "away_token_id": (
                away.token_id
            ),
            "home_status": home.status,
            "home_exclusion_reason": (
                optional_text(
                    home.exclusion_reason
                )
            ),
            "home_price": optional_float(
                home.price
            ),
            "home_price_time_utc": (
                ""
                if home.observed_at is None
                else format_utc(
                    home.observed_at
                )
            ),
            "home_price_age_seconds": (
                optional_text(
                    home.age_seconds
                )
            ),
            "away_status": away.status,
            "away_exclusion_reason": (
                optional_text(
                    away.exclusion_reason
                )
            ),
            "away_price": optional_float(
                away.price
            ),
            "away_price_time_utc": (
                ""
                if away.observed_at is None
                else format_utc(
                    away.observed_at
                )
            ),
            "away_price_age_seconds": (
                optional_text(
                    away.age_seconds
                )
            ),
            "pair_status": pair.status,
            "pair_exclusion_reason": (
                optional_text(
                    pair.exclusion_reason
                )
            ),
            "timestamp_gap_seconds": (
                optional_text(
                    pair.timestamp_gap_seconds
                )
            ),
            "max_price_age_seconds": (
                optional_text(
                    pair.max_price_age_seconds
                )
            ),
            "price_sum": optional_float(
                pair.price_sum
            ),
            "complementarity_error": (
                optional_float(
                    pair.complementarity_error
                )
            ),
        })

        if (
            index == 1
            or index % 100 == 0
            or index
            == len(bookmaker_by_market)
        ):
            print(
                f"[{index}/"
                f"{len(bookmaker_by_market)}] "
                "markets audited"
            )

    write_atomic(output_rows)

    eligible_pairs = [
        pair
        for pair in pair_objects
        if pair.status == "eligible"
    ]

    excluded_pairs = [
        pair
        for pair in pair_objects
        if pair.status != "eligible"
    ]

    home_reasons = Counter(
        pair.home.exclusion_reason
        for pair in pair_objects
        if pair.home.exclusion_reason
        is not None
    )

    away_reasons = Counter(
        pair.away.exclusion_reason
        for pair in pair_objects
        if pair.away.exclusion_reason
        is not None
    )

    pair_reasons = Counter(
        pair.exclusion_reason
        for pair in excluded_pairs
    )

    home_ages = [
        float(pair.home.age_seconds)
        for pair in eligible_pairs
        if pair.home.age_seconds
        is not None
    ]

    away_ages = [
        float(pair.away.age_seconds)
        for pair in eligible_pairs
        if pair.away.age_seconds
        is not None
    ]

    max_pair_ages = [
        float(
            pair.max_price_age_seconds
        )
        for pair in eligible_pairs
        if pair.max_price_age_seconds
        is not None
    ]

    timestamp_gaps = [
        float(
            pair.timestamp_gap_seconds
        )
        for pair in eligible_pairs
        if pair.timestamp_gap_seconds
        is not None
    ]

    complementarity_errors = [
        float(
            pair.complementarity_error
        )
        for pair in eligible_pairs
        if pair.complementarity_error
        is not None
    ]

    same_timestamp_count = sum(
        pair.timestamp_gap_seconds == 0
        for pair in eligible_pairs
    )

    print()
    print(
        "POLYMARKET PRICE-HISTORY AUDIT"
    )
    print("=" * 72)
    print(
        f"Markets audited             : "
        f"{len(pair_objects)}"
    )
    print(
        f"Both token prices usable    : "
        f"{len(eligible_pairs)}"
    )
    print(
        f"Excluded pairs              : "
        f"{len(excluded_pairs)}"
    )
    print(
        f"Identical token timestamps  : "
        f"{same_timestamp_count}"
    )
    print(
        f"Different token timestamps  : "
        f"{len(eligible_pairs) - same_timestamp_count}"
    )

    print()
    print("EXCLUSION REASONS")
    print("-" * 72)
    print("HOME:", dict(home_reasons))
    print("AWAY:", dict(away_reasons))
    print("PAIR:", dict(pair_reasons))

    print()
    print("DISTRIBUTIONS")
    print("-" * 72)

    print_distribution(
        "HOME price age seconds",
        home_ages,
    )

    print_distribution(
        "AWAY price age seconds",
        away_ages,
    )

    print_distribution(
        "Maximum pair age seconds",
        max_pair_ages,
    )

    print_distribution(
        "Token timestamp gap seconds",
        timestamp_gaps,
    )

    print_distribution(
        "Complementarity error",
        complementarity_errors,
    )

    print()
    print("SURVIVAL BY MAXIMUM PRICE AGE")
    print("-" * 72)

    for threshold in (
        AGE_THRESHOLDS_SECONDS
    ):
        survivors = sum(
            pair.max_price_age_seconds
            is not None
            and pair.max_price_age_seconds
            <= threshold
            for pair in eligible_pairs
        )

        print(
            f"≤ {threshold:5d} seconds: "
            f"{survivors:4d} / "
            f"{len(pair_objects)}"
        )

    print()
    print("COMPLEMENTARITY TOLERANCE")
    print("-" * 72)

    for tolerance in (
        COMPLEMENTARITY_TOLERANCES
    ):
        survivors = sum(
            pair.complementarity_error
            is not None
            and pair.complementarity_error
            <= tolerance
            for pair in eligible_pairs
        )

        print(
            f"≤ {tolerance:.9f}: "
            f"{survivors:4d} / "
            f"{len(eligible_pairs)}"
        )

    print()
    print(
        f"Audit CSV: {OUTPUT_PATH}"
    )


if __name__ == "__main__":
    main()
