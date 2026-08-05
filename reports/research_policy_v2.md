# PolyEdge NBA V2 Research Policy

## Status

This policy was frozen before examining the profitability of the synchronized V2 dataset.

## Research question

Do timestamp-aligned bookmaker fair probabilities systematically differ from contemporaneous Polymarket probabilities, and do those discrepancies contain information about eventual NBA game outcomes?

## Common observation clock

The canonical observation time is the actual historical Odds API wrapper timestamp.

For every included market:

- bookmaker quotes must have existed at or before the observation time
- the selected Polymarket history point must be at or before the observation time
- future observations are never eligible

The requested target time is scheduling metadata. It is not treated as the actual observation time.

## Bookmaker probability

The bookmaker probability is the normalized two-outcome fair probability produced from eligible approved bookmakers.

Approved bookmakers:

- BetMGM
- BetRivers
- DraftKings
- FanDuel

At least three fresh and valid approved bookmakers are required.

Individual invalid decimal odds are rejected rather than repaired or clamped.

## Polymarket probability

The Polymarket CLOB price-history endpoint is interpreted as a one-minute sampled probability series.

It is not interpreted as:

- a historical order book
- a trade tape
- an executable bid
- an executable ask
- an executable fill

Canonical terminology:

- `polymarket_home_probability`
- `polymarket_away_probability`
- `history_point_lag_seconds`

## Polymarket inclusion rules

A market is eligible only when:

1. both HOME and AWAY histories exist
2. timestamps are strictly increasing
3. the latest HOME and AWAY timestamps are identical
4. the latest timestamp is at or before the common observation time
5. the latest history-point lag is at most 60 seconds
6. HOME probability plus AWAY probability equals one within `1e-9`

Exact 60-second spacing between every intermediate sample is not required.

Observed second-level sampling jitter does not affect eligibility when the selected endpoint satisfies the rules above.

## Empirical coverage at policy freeze

- eligible bookmaker observations: 1,217
- markets with both Polymarket histories: 1,217
- markets passing the 60-second endpoint-lag rule: 1,217
- markets with identical latest HOME and AWAY timestamps: 1,217
- markets passing complementarity tolerance: 1,217
- future selected observations: 0

Observed latest history-point lag:

- minimum: 23 seconds
- median: 34 seconds
- 95th percentile: 36 seconds
- maximum: 38 seconds

## Probability discrepancy semantics

For the home-team YES outcome:

```text
home_probability_edge
=
bookmaker_home_fair_probability
-
polymarket_home_probability
```

For the away-team NO outcome:

```text
away_probability_edge
=
bookmaker_away_fair_probability
-
polymarket_away_probability
```

Positive home edge maps to `BUY_YES`.

Positive away edge maps to `BUY_NO`.

Negative home edge must never automatically map to `BUY_NO` unless the separately calculated away edge is positive.

## Settlement semantics

Each market resolves to exactly one binary outcome:

```text
resolved_home_value in {0, 1}
resolved_away_value = 1 - resolved_home_value
```

Legacy synthetic settlement timestamps are not treated as factual and are not migrated.

## Claim hierarchy

The final report must distinguish:

1. observed probability discrepancy
2. idealized settlement performance
3. conservatively stressed tradability

The sampled Polymarket probability is suitable for discrepancy research.

It does not by itself establish historical executability or tradable profitability.

## Policy changes

Any later change to these rules must:

- create a new policy version
- state the reason
- report results under both the original and changed policies
- never silently overwrite this policy
