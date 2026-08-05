"""Frozen Polymarket synchronization policy for NBA V2 research."""

MAX_HISTORY_POINT_LAG_SECONDS = 60

COMPLEMENTARITY_TOLERANCE = 1e-9

REQUIRE_BOTH_OUTCOME_HISTORIES = True

REQUIRE_IDENTICAL_LATEST_TIMESTAMPS = True

SOURCE_SEMANTICS = (
    "one_minute_sampled_probability_series"
)

EXECUTION_SEMANTICS = "none"
