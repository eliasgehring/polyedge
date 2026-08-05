from copy import deepcopy

import pytest

from polyedge.forecast_audit import (
    ForecastAuditError,
    audit_forecast_rows,
    parse_forecast_audit_row,
)


def row(
    *,
    market_id,
    bookmaker_home,
    polymarket_home,
    outcome,
    strict,
):
    bookmaker_away = 1.0 - bookmaker_home
    polymarket_away = 1.0 - polymarket_home

    home_edge = (
        bookmaker_home
        - polymarket_home
    )

    away_edge = (
        bookmaker_away
        - polymarket_away
    )

    return {
        "output_market_id": market_id,
        "strict_t_minus_60_eligible": (
            str(strict).lower()
        ),
        "bookmaker_home_fair_probability": (
            str(bookmaker_home)
        ),
        "bookmaker_away_fair_probability": (
            str(bookmaker_away)
        ),
        "polymarket_home_probability": (
            str(polymarket_home)
        ),
        "polymarket_away_probability": (
            str(polymarket_away)
        ),
        "home_probability_edge": str(
            home_edge
        ),
        "away_probability_edge": str(
            away_edge
        ),
        "resolved_home_value": str(
            outcome
        ),
        "resolved_away_value": str(
            1 - outcome
        ),
        "source_semantics": (
            "one_minute_sampled_probability_series"
        ),
        "execution_semantics": "none",
        "policy_version": "nba_v2_sync_v1",
    }


def example_rows():
    return [
        row(
            market_id="m1",
            bookmaker_home=0.8,
            polymarket_home=0.6,
            outcome=1,
            strict=True,
        ),
        row(
            market_id="m2",
            bookmaker_home=0.2,
            polymarket_home=0.4,
            outcome=0,
            strict=True,
        ),
        row(
            market_id="m3",
            bookmaker_home=0.7,
            polymarket_home=0.55,
            outcome=1,
            strict=False,
        ),
    ]


def test_audits_all_and_strict_populations():
    audits = audit_forecast_rows(
        example_rows()
    )

    assert [
        audit.population_name
        for audit in audits
    ] == [
        "all_synchronized",
        "strict_t_minus_60",
    ]

    assert audits[0].count == 3
    assert audits[1].count == 2

    assert (
        audits[0]
        .brier_score_difference_polymarket_minus_bookmaker
        > 0
    )

    assert (
        audits[0]
        .log_loss_difference_polymarket_minus_bookmaker
        > 0
    )


def test_home_outcome_is_scored_once_not_as_two_signals():
    audits = audit_forecast_rows(
        example_rows()
    )

    assert (
        audits[0]
        .bookmaker
        .score
        .count
    ) == 3

    assert (
        audits[0]
        .polymarket
        .score
        .count
    ) == 3


def test_rejects_duplicate_market_ids():
    rows = example_rows()
    rows.append(
        deepcopy(
            rows[0]
        )
    )

    with pytest.raises(
        ForecastAuditError,
        match="Duplicate",
    ):
        audit_forecast_rows(
            rows
        )


def test_rejects_edge_mismatch():
    broken = row(
        market_id="m1",
        bookmaker_home=0.8,
        polymarket_home=0.6,
        outcome=1,
        strict=True,
    )

    broken[
        "home_probability_edge"
    ] = "0.3"

    with pytest.raises(
        ForecastAuditError,
        match="HOME edge",
    ):
        parse_forecast_audit_row(
            broken
        )


def test_rejects_noncomplementary_probability_pair():
    broken = row(
        market_id="m1",
        bookmaker_home=0.8,
        polymarket_home=0.6,
        outcome=1,
        strict=True,
    )

    broken[
        "polymarket_away_probability"
    ] = "0.5"

    with pytest.raises(
        ForecastAuditError,
        match="Polymarket probabilities",
    ):
        parse_forecast_audit_row(
            broken
        )


def test_rejects_wrong_policy_version():
    broken = row(
        market_id="m1",
        bookmaker_home=0.8,
        polymarket_home=0.6,
        outcome=1,
        strict=True,
    )

    broken["policy_version"] = "other"

    with pytest.raises(
        ForecastAuditError,
        match="policy version",
    ):
        parse_forecast_audit_row(
            broken
        )
