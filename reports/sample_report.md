# PolyEdge Sample Backtest Report

## Result Status

`MECHANICALLY_VALID_SYNTHETIC_BACKTEST`

This is an exploratory research backtest. It is designed to test whether model-implied probabilities contain edge against prediction-market prices under explicit assumptions.

It is not a live-trading claim.

## Dataset

Dataset path:

```text
data/sample/historical_sample.csv
```

## Execution Assumptions

| Assumption | Value |
|---|---:|
| Execution mode | `SYNTHETIC_BID_ASK` |
| Uses synthetic spread | `True` |
| Uses historical midpoint proxy | `True` |
| Models liquidity | `False` |
| Models fees | `False` |
| Makes tradability claim | `False` |

## Probability Semantics

YES means the listed market outcome resolves true.

NO means the complementary contract.

```text
edge_yes = model_prob_yes - yes_ask
edge_no  = (1 - model_prob_yes) - no_ask
no_ask   = 1 - yes_bid
```

A positive executable YES edge maps to BUY_YES.

A positive executable NO edge maps to BUY_NO.

## Accounting Semantics

Portfolio value is computed globally:

```text
total_value = cash + marked value of all open YES/NO positions
```

## Dataset Integrity

| Check | Value |
|---|---:|
| Dataset SHA256 | `d49df0bed53982b8992a4aa298c80027de53b729eabe113628f702bae2ff00f9` |
| Rows | `4` |
| Markets | `2` |
| Pregame rows | `2` |
| Settlement rows | `2` |
| Hard fail | `False` |

Open positions are marked using the latest known market state for each market, not merely the current row.

## Summary

| Metric | Value |
|---|---:|
| Start value | `1000.00` |
| Final value | `1034.38` |
| Total return | `34.38` |
| Total return % | `3.44%` |
| Peak value | `1034.38` |
| Max drawdown | `1.62` |
| Total trades | `2` |
| BUY_YES trades | `1` |
| BUY_NO trades | `1` |
| HOLD signals | `0` |
| Risk rejections | `0` |
| Skipped settlement rows | `0` |

## Interpretation

This sample report exists to verify the engine’s mechanics, not to claim strategy profitability.

The important guarantee is that the result is traceable through explicit probability semantics, settlement-aware accounting, dataset validation, and deterministic tests.
