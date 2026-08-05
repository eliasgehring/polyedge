import csv
from dataclasses import asdict
import hashlib
import math
from pathlib import Path
from typing import Dict, List

from polyedge.forecast_audit import (
    ForecastPopulationAudit,
    audit_forecast_rows,
)
from polyedge.polymarket_policy import (
    POLICY_VERSION,
)


INPUT_PATH = Path(
    "data/processed/nba_v2/"
    "synchronized_market_observations.csv"
)

SUMMARY_PATH = Path(
    "data/diagnostics/nba_v2/"
    "forecast_scoring_summary.csv"
)

CALIBRATION_PATH = Path(
    "data/diagnostics/nba_v2/"
    "forecast_calibration_bins.csv"
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
    if math.isinf(value):
        return "inf"

    return f"{value:.12f}"


def summary_rows(
    *,
    audits: List[ForecastPopulationAudit],
    source_sha256: str,
) -> List[Dict[str, object]]:
    result = []

    for audit in audits:
        for source in (
            audit.bookmaker,
            audit.polymarket,
        ):
            result.append({
                "input_file": str(
                    INPUT_PATH
                ),
                "input_sha256": (
                    source_sha256
                ),
                "policy_version": (
                    POLICY_VERSION
                ),
                "population": (
                    audit.population_name
                ),
                "count": audit.count,
                "source": (
                    source.source_name
                ),
                "brier_score": (
                    format_number(
                        source.score.brier_score
                    )
                ),
                "binary_log_loss": (
                    format_number(
                        source
                        .score
                        .binary_log_loss
                    )
                ),
                "brier_score_difference_polymarket_minus_bookmaker": (
                    format_number(
                        audit
                        .brier_score_difference_polymarket_minus_bookmaker
                    )
                ),
                "log_loss_difference_polymarket_minus_bookmaker": (
                    format_number(
                        audit
                        .log_loss_difference_polymarket_minus_bookmaker
                    )
                ),
            })

    return result


def calibration_rows(
    *,
    audits: List[ForecastPopulationAudit],
    source_sha256: str,
) -> List[Dict[str, object]]:
    result = []

    for audit in audits:
        for source in (
            audit.bookmaker,
            audit.polymarket,
        ):
            for calibration_bin in (
                source.calibration_bins
            ):
                row = asdict(
                    calibration_bin
                )

                result.append({
                    "input_file": str(
                        INPUT_PATH
                    ),
                    "input_sha256": (
                        source_sha256
                    ),
                    "policy_version": (
                        POLICY_VERSION
                    ),
                    "population": (
                        audit.population_name
                    ),
                    "source": (
                        source.source_name
                    ),
                    "lower_bound": (
                        f"{row['lower_bound']:.1f}"
                    ),
                    "upper_bound": (
                        f"{row['upper_bound']:.1f}"
                    ),
                    "upper_bound_inclusive": str(
                        row[
                            "upper_bound_inclusive"
                        ]
                    ).lower(),
                    "count": row["count"],
                    "mean_probability": (
                        ""
                        if row[
                            "mean_probability"
                        ] is None
                        else format_number(
                            row[
                                "mean_probability"
                            ]
                        )
                    ),
                    "observed_home_win_rate": (
                        ""
                        if row[
                            "observed_positive_rate"
                        ] is None
                        else format_number(
                            row[
                                "observed_positive_rate"
                            ]
                        )
                    ),
                    "observed_minus_forecast": (
                        ""
                        if row[
                            "observed_minus_forecast"
                        ] is None
                        else format_number(
                            row[
                                "observed_minus_forecast"
                            ]
                        )
                    ),
                })

    return result


def write_csv_atomic(
    *,
    path: Path,
    rows: List[Dict[str, object]],
) -> None:
    if not rows:
        raise ValueError(
            f"Cannot write empty CSV: {path}"
        )

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary_path = path.with_suffix(
        path.suffix + ".tmp"
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
        path
    )


def main() -> None:
    source_sha256 = sha256_file(
        INPUT_PATH
    )

    if (
        source_sha256
        != EXPECTED_INPUT_SHA256
    ):
        raise ValueError(
            "Synchronized input SHA-256 changed. "
            "Regenerate or version the forecast audit."
        )

    audits = audit_forecast_rows(
        read_rows(
            INPUT_PATH
        )
    )

    observed_counts = {
        audit.population_name: audit.count
        for audit in audits
    }

    if observed_counts != EXPECTED_COUNTS:
        raise AssertionError(
            "Unexpected forecast populations: "
            + repr(observed_counts)
        )

    write_csv_atomic(
        path=SUMMARY_PATH,
        rows=summary_rows(
            audits=audits,
            source_sha256=source_sha256,
        ),
    )

    write_csv_atomic(
        path=CALIBRATION_PATH,
        rows=calibration_rows(
            audits=audits,
            source_sha256=source_sha256,
        ),
    )

    print("FORECAST QUALITY AUDIT")
    print("=" * 72)
    print(f"Input file        : {INPUT_PATH}")
    print(f"Input SHA-256     : {source_sha256}")
    print(f"Policy version    : {POLICY_VERSION}")
    print()
    print(
        "Advantages are defined as "
        "Polymarket score minus bookmaker score."
    )
    print(
        "Positive values mean the bookmaker forecast "
        "scored better."
    )

    for audit in audits:
        print()
        print(audit.population_name.upper())
        print("-" * 72)
        print(f"Count             : {audit.count}")
        print(
            "Bookmaker Brier    : "
            + format_number(
                audit.bookmaker.score.brier_score
            )
        )
        print(
            "Polymarket Brier   : "
            + format_number(
                audit.polymarket.score.brier_score
            )
        )
        print(
            "Bookmaker advantage: "
            + format_number(
                audit.brier_score_difference_polymarket_minus_bookmaker
            )
        )
        print(
            "Bookmaker log loss : "
            + format_number(
                audit
                .bookmaker
                .score
                .binary_log_loss
            )
        )
        print(
            "Polymarket log loss: "
            + format_number(
                audit
                .polymarket
                .score
                .binary_log_loss
            )
        )
        print(
            "Bookmaker advantage: "
            + format_number(
                audit.log_loss_difference_polymarket_minus_bookmaker
            )
        )

    print()
    print(f"Summary CSV       : {SUMMARY_PATH}")
    print(f"Calibration CSV   : {CALIBRATION_PATH}")


if __name__ == "__main__":
    main()
