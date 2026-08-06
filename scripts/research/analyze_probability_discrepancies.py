import csv
import hashlib
from pathlib import Path
from typing import Dict, List, Optional

from polyedge.discrepancy_analysis import (
    DiscrepancyBinResult,
    analyze_discrepancy_bins,
    parse_discrepancy_observations,
)
from polyedge.polymarket_policy import POLICY_VERSION


INPUT_PATH = Path(
    'data/processed/nba_v2/'
    'synchronized_market_observations.csv'
)

OUTPUT_PATH = Path(
    'data/diagnostics/nba_v2/'
    'probability_discrepancy_bins.csv'
)

EXPECTED_INPUT_SHA256 = (
    '5a93b2ebd9fd6a1f5ff0583f8f7b1e63'
    'db75bc51548d7804c41dcb1d165a4e80'
)

EXPECTED_COUNTS = {
    'all_synchronized': 1217,
    'strict_t_minus_60': 1214,
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def read_rows(path: Path) -> List[Dict[str, str]]:
    with path.open(encoding='utf-8', newline='') as file:
        return list(csv.DictReader(file))


def format_optional(value: Optional[float]) -> str:
    if value is None:
        return ''
    return f'{value:.12f}'


def serialize(
    *,
    result: DiscrepancyBinResult,
    input_sha256: str,
) -> Dict[str, object]:
    return {
        'input_file': str(INPUT_PATH),
        'input_sha256': input_sha256,
        'policy_version': POLICY_VERSION,
        'population': result.population_name,
        'discrepancy_definition': (
            'bookmaker_home_probability'
            '_minus_polymarket_home_probability'
        ),
        'bin_label': result.bin_label,
        'lower_bound_inclusive': (
            ''
            if result.lower_bound is None
            else format_optional(result.lower_bound)
        ),
        'upper_bound_exclusive': (
            ''
            if result.upper_bound is None
            else format_optional(result.upper_bound)
        ),
        'count': result.count,
        'mean_home_probability_discrepancy': format_optional(
            result.mean_home_probability_discrepancy
        ),
        'mean_bookmaker_home_probability': format_optional(
            result.mean_bookmaker_home_probability
        ),
        'mean_polymarket_home_probability': format_optional(
            result.mean_polymarket_home_probability
        ),
        'observed_home_win_rate': format_optional(
            result.observed_home_win_rate
        ),
        'observed_minus_bookmaker_probability': format_optional(
            result.observed_minus_bookmaker_probability
        ),
        'observed_minus_polymarket_probability': format_optional(
            result.observed_minus_polymarket_probability
        ),
        'mean_brier_score_difference_polymarket_minus_bookmaker': (
            format_optional(
                result
                .mean_brier_score_difference_polymarket_minus_bookmaker
            )
        ),
        'mean_log_loss_difference_polymarket_minus_bookmaker': (
            format_optional(
                result
                .mean_log_loss_difference_polymarket_minus_bookmaker
            )
        ),
    }


def write_csv_atomic(rows: List[Dict[str, object]]) -> None:
    if not rows:
        raise ValueError('Cannot write empty discrepancy analysis')

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = OUTPUT_PATH.with_suffix(OUTPUT_PATH.suffix + '.tmp')

    with temporary_path.open('w', encoding='utf-8', newline='') as file:
        writer = csv.DictWriter(
            file,
            fieldnames=list(rows[0].keys()),
        )
        writer.writeheader()
        writer.writerows(rows)

    temporary_path.replace(OUTPUT_PATH)


def print_result(result: DiscrepancyBinResult) -> None:
    print(
        f'{result.bin_label:18} '
        f'n={result.count:4d} '
        'disc='
        f'{format_optional(result.mean_home_probability_discrepancy):>14} '
        'book='
        f'{format_optional(result.mean_bookmaker_home_probability):>14} '
        'pm='
        f'{format_optional(result.mean_polymarket_home_probability):>14} '
        'obs='
        f'{format_optional(result.observed_home_win_rate):>14} '
        'brier_diff='
        f'{format_optional(result.mean_brier_score_difference_polymarket_minus_bookmaker):>14}'
    )


def main() -> None:
    input_sha256 = sha256_file(INPUT_PATH)

    if input_sha256 != EXPECTED_INPUT_SHA256:
        raise ValueError(
            'Synchronized input SHA-256 changed. '
            'Regenerate or version the discrepancy analysis.'
        )

    observations = parse_discrepancy_observations(read_rows(INPUT_PATH))

    populations = {
        'all_synchronized': observations,
        'strict_t_minus_60': [
            observation
            for observation in observations
            if observation.strict_t_minus_60_eligible
        ],
    }

    observed_counts = {
        name: len(rows)
        for name, rows in populations.items()
    }

    if observed_counts != EXPECTED_COUNTS:
        raise AssertionError(
            'Unexpected discrepancy populations: '
            + repr(observed_counts)
        )

    all_results = []

    for population_name, rows in populations.items():
        results = analyze_discrepancy_bins(
            rows,
            population_name=population_name,
        )
        all_results.extend(results)

        print()
        print(population_name.upper())
        print('=' * 132)
        print(
            'Discrepancy = bookmaker HOME probability '
            'minus Polymarket HOME probability.'
        )
        print(
            'Positive score difference means '
            'the bookmaker forecast had lower loss.'
        )
        print()

        for result in results:
            print_result(result)

        print()
        print(
            'Population count: '
            + str(sum(result.count for result in results))
        )

    write_csv_atomic([
        serialize(result=result, input_sha256=input_sha256)
        for result in all_results
    ])

    print()
    print(f'Input SHA-256 : {input_sha256}')
    print(f'Policy version: {POLICY_VERSION}')
    print(f'Output CSV    : {OUTPUT_PATH}')


if __name__ == '__main__':
    main()
