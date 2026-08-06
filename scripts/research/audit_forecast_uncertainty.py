import csv
import hashlib
from pathlib import Path
from typing import Dict, List

from polyedge.paired_forecast_uncertainty import (
    DEFAULT_CONFIDENCE_LEVEL,
    DEFAULT_RESAMPLES,
    DEFAULT_SEED,
    MetricUncertaintyAudit,
    audit_paired_uncertainty,
    parse_paired_loss_differences,
)
from polyedge.polymarket_policy import (
    POLICY_VERSION,
)


INPUT_PATH = Path(
    "data/processed/nba_v2/"
    "synchronized_market_observations.csv"
)

OUTPUT_PATH = Path(
    "data/diagnostics/nba_v2/"
    "forecast_paired_uncertainty.csv"
)

EXPECTED_INPUT_SHA256 = (
    "5a93b2ebd9fd6a1f5ff0583f8f7b1e63"
    "db75bc51548d7804c41dcb1d165a4e80"
)

EXPECTED_COUNTS = {
    "all_synchronized": 1217,
    "strict_t_minus_60": 1214,
}


def sha256_file(
    path: Path,
) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as file:
        for chunk in iter(
            lambda: file.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


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


def format_number(
    value: float,
) -> str:
    return f"{value:.12f}"


def serialize(
    *,
    audit: MetricUncertaintyAudit,
    input_sha256: str,
) -> Dict[str, object]:
    return {
        "input_file": str(
            INPUT_PATH
        ),
        "input_sha256": input_sha256,
        "policy_version": POLICY_VERSION,
        "population": (
            audit.population_name
        ),
        "metric": audit.metric_name,
        "difference_definition": (
            "polymarket_loss_minus_bookmaker_loss"
        ),
        "count": audit.count,
        "cluster_definition": (
            "canonical_game_date_from_output_market_id"
        ),
        "cluster_count": (
            audit.cluster_count
        ),
        "mean_difference": format_number(
            audit
            .mean_difference_polymarket_minus_bookmaker
        ),
        "confidence_level": format_number(
            audit
            .ordinary_paired_bootstrap
            .confidence_level
        ),
        "resamples": (
            audit
            .ordinary_paired_bootstrap
            .resamples
        ),
        "seed": (
            audit
            .ordinary_paired_bootstrap
            .seed
        ),
        "ordinary_paired_ci_lower": (
            format_number(
                audit
                .ordinary_paired_bootstrap
                .lower
            )
        ),
        "ordinary_paired_ci_upper": (
            format_number(
                audit
                .ordinary_paired_bootstrap
                .upper
            )
        ),
        "game_date_clustered_ci_lower": (
            format_number(
                audit
                .game_date_clustered_bootstrap
                .lower
            )
        ),
        "game_date_clustered_ci_upper": (
            format_number(
                audit
                .game_date_clustered_bootstrap
                .upper
            )
        ),
    }


def write_csv_atomic(
    rows: List[Dict[str, object]],
) -> None:
    if not rows:
        raise ValueError(
            "Cannot write an empty uncertainty audit"
        )

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
            fieldnames=list(
                rows[0].keys()
            ),
        )

        writer.writeheader()
        writer.writerows(rows)

    temporary_path.replace(
        OUTPUT_PATH
    )


def print_audit(
    audit: MetricUncertaintyAudit,
) -> None:
    print()
    print(
        audit.population_name.upper()
        + " / "
        + audit.metric_name.upper()
    )
    print("-" * 78)
    print(
        f"Count                    : {audit.count}"
    )
    print(
        f"Canonical date clusters  : {audit.cluster_count}"
    )
    print(
        "Mean PM minus bookmaker  : "
        + format_number(
            audit
            .mean_difference_polymarket_minus_bookmaker
        )
    )
    print(
        "Ordinary paired 95% CI   : ["
        + format_number(
            audit
            .ordinary_paired_bootstrap
            .lower
        )
        + ", "
        + format_number(
            audit
            .ordinary_paired_bootstrap
            .upper
        )
        + "]"
    )
    print(
        "Date-clustered 95% CI    : ["
        + format_number(
            audit
            .game_date_clustered_bootstrap
            .lower
        )
        + ", "
        + format_number(
            audit
            .game_date_clustered_bootstrap
            .upper
        )
        + "]"
    )


def main() -> None:
    input_sha256 = sha256_file(
        INPUT_PATH
    )

    if (
        input_sha256
        != EXPECTED_INPUT_SHA256
    ):
        raise ValueError(
            "Synchronized input SHA-256 changed. "
            "Regenerate or version the uncertainty audit."
        )

    paired_rows = parse_paired_loss_differences(
        read_rows(
            INPUT_PATH
        )
    )

    populations = {
        "all_synchronized": paired_rows,
        "strict_t_minus_60": [
            row
            for row in paired_rows
            if row.strict_t_minus_60_eligible
        ],
    }

    observed_counts = {
        name: len(rows)
        for name, rows in populations.items()
    }

    if observed_counts != EXPECTED_COUNTS:
        raise AssertionError(
            "Unexpected forecast populations: "
            + repr(observed_counts)
        )

    audits = []

    for population_name, rows in (
        populations.items()
    ):
        audits.extend(
            audit_paired_uncertainty(
                rows,
                population_name=(
                    population_name
                ),
                confidence_level=(
                    DEFAULT_CONFIDENCE_LEVEL
                ),
                resamples=DEFAULT_RESAMPLES,
                seed=DEFAULT_SEED,
            )
        )

    write_csv_atomic([
        serialize(
            audit=audit,
            input_sha256=input_sha256,
        )
        for audit in audits
    ])

    print("PAIRED FORECAST UNCERTAINTY")
    print("=" * 78)
    print(f"Input file               : {INPUT_PATH}")
    print(f"Input SHA-256            : {input_sha256}")
    print(f"Policy version           : {POLICY_VERSION}")
    print(f"Bootstrap resamples      : {DEFAULT_RESAMPLES}")
    print(f"Random seed              : {DEFAULT_SEED}")
    print()
    print(
        "Difference = Polymarket loss minus bookmaker loss."
    )
    print(
        "Positive means the bookmaker forecast scored better."
    )

    for audit in audits:
        print_audit(
            audit
        )

    print()
    print(f"Output CSV               : {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
