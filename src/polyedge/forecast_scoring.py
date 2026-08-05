from dataclasses import dataclass
import math
from typing import List, Optional, Sequence, Tuple


@dataclass(frozen=True)
class ForecastScore:
    count: int
    brier_score: float
    binary_log_loss: float


@dataclass(frozen=True)
class CalibrationBin:
    lower_bound: float
    upper_bound: float
    upper_bound_inclusive: bool
    count: int
    mean_probability: Optional[float]
    observed_positive_rate: Optional[float]
    observed_minus_forecast: Optional[float]


def _validated_pairs(
    probabilities: Sequence[float],
    outcomes: Sequence[int],
) -> List[Tuple[float, int]]:
    if len(probabilities) != len(outcomes):
        raise ValueError(
            "Probabilities and outcomes must have equal length."
        )

    if not probabilities:
        raise ValueError(
            "Cannot score an empty forecast collection."
        )

    pairs = []

    for index, (
        probability,
        outcome,
    ) in enumerate(
        zip(
            probabilities,
            outcomes,
        )
    ):
        if isinstance(
            probability,
            bool,
        ):
            raise ValueError(
                f"Probability at index {index} cannot be boolean."
            )

        probability_value = float(
            probability
        )

        if not math.isfinite(
            probability_value
        ):
            raise ValueError(
                f"Probability at index {index} must be finite."
            )

        if not (
            0.0
            <= probability_value
            <= 1.0
        ):
            raise ValueError(
                f"Probability at index {index} "
                "must be between zero and one."
            )

        if (
            isinstance(outcome, bool)
            or not isinstance(outcome, int)
            or outcome not in (0, 1)
        ):
            raise ValueError(
                f"Outcome at index {index} must be binary."
            )

        pairs.append(
            (
                probability_value,
                outcome,
            )
        )

    return pairs


def _brier_from_pairs(
    pairs: Sequence[Tuple[float, int]],
) -> float:
    return sum(
        (
            probability
            - outcome
        )
        ** 2
        for probability, outcome in pairs
    ) / len(pairs)


def _log_loss_from_pairs(
    pairs: Sequence[Tuple[float, int]],
) -> float:
    losses = []

    for probability, outcome in pairs:
        if outcome == 1:
            if probability == 0.0:
                return math.inf

            losses.append(
                -math.log(
                    probability
                )
            )
            continue

        if probability == 1.0:
            return math.inf

        losses.append(
            -math.log1p(
                -probability
            )
        )

    return sum(losses) / len(losses)


def brier_score(
    probabilities: Sequence[float],
    outcomes: Sequence[int],
) -> float:
    pairs = _validated_pairs(
        probabilities,
        outcomes,
    )

    return _brier_from_pairs(
        pairs
    )


def binary_log_loss(
    probabilities: Sequence[float],
    outcomes: Sequence[int],
) -> float:
    pairs = _validated_pairs(
        probabilities,
        outcomes,
    )

    return _log_loss_from_pairs(
        pairs
    )


def score_binary_forecasts(
    probabilities: Sequence[float],
    outcomes: Sequence[int],
) -> ForecastScore:
    pairs = _validated_pairs(
        probabilities,
        outcomes,
    )

    return ForecastScore(
        count=len(pairs),
        brier_score=(
            _brier_from_pairs(
                pairs
            )
        ),
        binary_log_loss=(
            _log_loss_from_pairs(
                pairs
            )
        ),
    )


def fixed_width_calibration_bins(
    probabilities: Sequence[float],
    outcomes: Sequence[int],
) -> List[CalibrationBin]:
    pairs = _validated_pairs(
        probabilities,
        outcomes,
    )

    bucket_probabilities = [
        []
        for _ in range(10)
    ]

    bucket_outcomes = [
        []
        for _ in range(10)
    ]

    for probability, outcome in pairs:
        bucket_index = min(
            int(
                probability * 10
            ),
            9,
        )

        bucket_probabilities[
            bucket_index
        ].append(
            probability
        )

        bucket_outcomes[
            bucket_index
        ].append(
            outcome
        )

    result = []

    for bucket_index in range(10):
        lower_bound = (
            bucket_index / 10
        )

        upper_bound = (
            bucket_index + 1
        ) / 10

        probabilities_in_bucket = (
            bucket_probabilities[
                bucket_index
            ]
        )

        outcomes_in_bucket = (
            bucket_outcomes[
                bucket_index
            ]
        )

        if probabilities_in_bucket:
            mean_probability = sum(
                probabilities_in_bucket
            ) / len(
                probabilities_in_bucket
            )

            observed_positive_rate = sum(
                outcomes_in_bucket
            ) / len(
                outcomes_in_bucket
            )

            observed_minus_forecast = (
                observed_positive_rate
                - mean_probability
            )
        else:
            mean_probability = None
            observed_positive_rate = None
            observed_minus_forecast = None

        result.append(
            CalibrationBin(
                lower_bound=(
                    lower_bound
                ),
                upper_bound=(
                    upper_bound
                ),
                upper_bound_inclusive=(
                    bucket_index == 9
                ),
                count=len(
                    probabilities_in_bucket
                ),
                mean_probability=(
                    mean_probability
                ),
                observed_positive_rate=(
                    observed_positive_rate
                ),
                observed_minus_forecast=(
                    observed_minus_forecast
                ),
            )
        )

    return result
