# PolyEdge NBA V2 Research Report

## Result status

This is a hash-pinned probability-research result.

It is not a live-trading or executable-profitability claim.

## Dataset identity

- Observations: `1,217`
- Strict T-60 observations: `1,214`
- SHA-256: `5a93b2ebd9fd6a1f5ff0583f8f7b1e63db75bc51548d7804c41dcb1d165a4e80`
- Policy version: `nba_v2_sync_v1`
- Full row-level dataset redistributed: `false`

See `DATA_AVAILABILITY.md`.

## Source semantics

- Bookmaker input: normalized two-outcome fair probability from eligible approved bookmakers
- Polymarket input: one-minute sampled historical probability series
- Execution semantics: `none`
- Historical order-book interpretation: `false`
- Tradable-profitability claim: `not established`

## Aggregate forecast quality

Lower scores are better.

The difference is defined as:

```text
Polymarket loss minus bookmaker loss
```

Positive values mean the bookmaker forecast had lower loss.

| Population | Metric | Bookmaker | Polymarket | Difference |
|---|---|---:|---:|---:|
| All synchronized | Brier score | 0.202440670629 | 0.202655496508 | 0.000214825879 |
| All synchronized | Binary log loss | 0.588823498469 | 0.589332201047 | 0.000508702578 |
| Strict T-60 | Brier score | 0.202577787978 | 0.202810781919 | 0.000232993941 |
| Strict T-60 | Binary log loss | 0.589100064513 | 0.589652323125 | 0.000552258611 |

## Paired uncertainty

Bootstrap settings:

- resamples: `10,000`
- seed: `20260805`
- date clusters: `198`

| Population | Metric | Mean difference | Ordinary paired 95% CI | Date-clustered 95% CI |
|---|---|---:|---:|---:|
| All synchronized | Brier score | 0.000214825879 | [-0.000287353153, 0.000723103802] | [-0.000282744527, 0.000710791553] |
| All synchronized | Binary log loss | 0.000508702578 | [-0.000940227411, 0.002004420957] | [-0.000936759017, 0.001982394897] |
| Strict T-60 | Brier score | 0.000232993941 | [-0.000277955547, 0.000747062951] | [-0.000267210213, 0.000735014265] |
| Strict T-60 | Binary log loss | 0.000552258611 | [-0.000883229912, 0.002066807549] | [-0.000905037376, 0.002033499076] |

Every interval includes zero.

The data therefore do not provide credible evidence that either source was more accurate in aggregate.

## Probability discrepancy structure

The discrepancy is:

```text
bookmaker HOME probability
minus
Polymarket HOME probability
```

For all synchronized observations:

- within two percentage points: `1,148`
- between two and five percentage points: `69`
- at least five percentage points apart: `0`

The previous exploratory five-point signal threshold therefore produces zero signals under synchronized V2 observations.

## Research conclusion

At synchronized observation times, bookmaker consensus and Polymarket probabilities were usually very close.

Bookmaker point estimates had marginally lower aggregate losses, but paired uncertainty intervals included zero.

No market differed by five percentage points or more.

The earlier exploratory profitability result does not survive truthful timestamp synchronization and should not be interpreted as evidence of a tradable strategy.

## Reproduction

Public evaluator workflow:

```bash
polyedge research --demo
```

The demo fixture is synthetic and produces no empirical claims.

Authorized full-data workflow:

```bash
polyedge research \
  --dataset /path/to/synchronized_market_observations.csv \
  --resamples 10000 \
  --report reports/reproduced_nba_v2_research_report.md
```
