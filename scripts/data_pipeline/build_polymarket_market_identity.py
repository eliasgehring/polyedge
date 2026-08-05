import csv
from collections import Counter
from pathlib import Path
from typing import Dict, List

from polyedge.polymarket_market_identity import (
    build_polymarket_market_identity,
)


BOOKMAKER_PATH = Path(
    "data/processed/the_odds_api/"
    "historical_bookmaker_observations.csv"
)

MANIFEST_PATH = Path(
    "data/diagnostics/"
    "polymarket_match_manifest.csv"
)

LEGACY_DATASET_PATH = Path(
    "data/intermediate/historical_ready/"
    "nba_source.csv"
)

OUTPUT_PATH = Path(
    "data/processed/polymarket/"
    "polymarket_market_identity.csv"
)


OUTPUT_COLUMNS = [
    "output_market_id",
    "polymarket_market_id",
    "condition_id",
    "market_slug",
    "home_outcome",
    "away_outcome",
    "home_token_id",
    "away_token_id",
    "home_outcome_index",
    "away_outcome_index",
    "resolved_home_value",
    "resolved_away_value",
    "resolution_source",
    "settlement_time_status",
]


def read_rows(
    path: Path,
) -> List[Dict[str, str]]:
    with path.open(
        encoding="utf-8",
        newline="",
    ) as file:
        return list(
            csv.DictReader(file)
        )


def unique_index(
    rows: List[Dict[str, str]],
    field_name: str,
) -> Dict[str, Dict[str, str]]:
    values = [
        row[field_name]
        for row in rows
    ]

    duplicates = [
        value
        for value, count
        in Counter(values).items()
        if count > 1
    ]

    if duplicates:
        raise ValueError(
            f"Duplicate {field_name} values: "
            f"{duplicates[:10]}"
        )

    return {
        row[field_name]: row
        for row in rows
    }


def write_atomic(
    rows: List[Dict[str, object]],
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

    manifest_rows = read_rows(
        MANIFEST_PATH
    )

    legacy_rows = read_rows(
        LEGACY_DATASET_PATH
    )

    eligible_market_ids = sorted(
        row["output_market_id"]
        for row in bookmaker_rows
        if row["status"] == "eligible"
    )

    if len(eligible_market_ids) != len(
        set(eligible_market_ids)
    ):
        raise ValueError(
            "Eligible bookmaker market IDs "
            "are not unique"
        )

    manifest_by_market = unique_index(
        manifest_rows,
        "output_market_id",
    )

    settlement_rows = [
        row
        for row in legacy_rows
        if row.get("row_type")
        == "SETTLEMENT"
    ]

    settlement_by_market = unique_index(
        settlement_rows,
        "market_id",
    )

    output_rows: List[
        Dict[str, object]
    ] = []

    for index, market_id in enumerate(
        eligible_market_ids,
        start=1,
    ):
        manifest_row = (
            manifest_by_market.get(
                market_id
            )
        )

        if manifest_row is None:
            raise ValueError(
                "Missing manifest row for "
                f"{market_id}"
            )

        settlement_row = (
            settlement_by_market.get(
                market_id
            )
        )

        if settlement_row is None:
            raise ValueError(
                "Missing settlement row for "
                f"{market_id}"
            )

        identity = (
            build_polymarket_market_identity(
                manifest_row=manifest_row,
                settlement_row=(
                    settlement_row
                ),
            )
        )

        output_rows.append({
            "output_market_id": (
                identity.output_market_id
            ),
            "polymarket_market_id": (
                identity
                .polymarket_market_id
            ),
            "condition_id": (
                identity.condition_id
            ),
            "market_slug": (
                identity.market_slug
            ),
            "home_outcome": (
                identity.home_outcome
            ),
            "away_outcome": (
                identity.away_outcome
            ),
            "home_token_id": (
                identity.home_token_id
            ),
            "away_token_id": (
                identity.away_token_id
            ),
            "home_outcome_index": (
                identity.home_outcome_index
            ),
            "away_outcome_index": (
                identity.away_outcome_index
            ),
            "resolved_home_value": (
                identity.resolved_home_value
            ),
            "resolved_away_value": (
                identity.resolved_away_value
            ),
            "resolution_source": (
                identity.resolution_source
            ),
            "settlement_time_status": (
                identity
                .settlement_time_status
            ),
        })

        if (
            index == 1
            or index % 100 == 0
            or index
            == len(eligible_market_ids)
        ):
            print(
                f"[{index}/"
                f"{len(eligible_market_ids)}] "
                "market identities built"
            )

    if len(output_rows) != 1217:
        raise AssertionError(
            "Expected exactly 1217 eligible "
            f"identities, got {len(output_rows)}"
        )

    write_atomic(
        output_rows
    )

    home_wins = sum(
        int(
            row[
                "resolved_home_value"
            ]
        )
        for row in output_rows
    )

    away_wins = sum(
        int(
            row[
                "resolved_away_value"
            ]
        )
        for row in output_rows
    )

    print()
    print(
        "POLYMARKET MARKET IDENTITY"
    )
    print("=" * 52)
    print(
        f"Eligible markets       : "
        f"{len(eligible_market_ids)}"
    )
    print(
        f"Identity rows written  : "
        f"{len(output_rows)}"
    )
    print(
        f"Resolved home wins     : "
        f"{home_wins}"
    )
    print(
        f"Resolved away wins     : "
        f"{away_wins}"
    )
    print(
        "Settlement timestamps : "
        "not migrated"
    )
    print(
        f"Output CSV             : "
        f"{OUTPUT_PATH}"
    )


if __name__ == "__main__":
    main()
