from polyedge.polymarket_policy import (
    COMPLEMENTARITY_TOLERANCE,
    EXECUTION_SEMANTICS,
    MAX_HISTORY_POINT_LAG_SECONDS,
    REQUIRE_BOTH_OUTCOME_HISTORIES,
    REQUIRE_IDENTICAL_LATEST_TIMESTAMPS,
    SOURCE_SEMANTICS,
)


def test_v2_polymarket_policy_is_frozen():
    assert MAX_HISTORY_POINT_LAG_SECONDS == 60
    assert COMPLEMENTARITY_TOLERANCE == 1e-9

    assert REQUIRE_BOTH_OUTCOME_HISTORIES
    assert REQUIRE_IDENTICAL_LATEST_TIMESTAMPS

    assert SOURCE_SEMANTICS == (
        "one_minute_sampled_probability_series"
    )

    assert EXECUTION_SEMANTICS == "none"
