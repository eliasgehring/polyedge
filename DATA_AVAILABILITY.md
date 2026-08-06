# Data Availability

## Public evaluator fixture

The repository includes a small synthetic fixture at:

```text
data/demo/nba_v2_research_demo.csv
```

It exists only to exercise the complete research workflow.

Results produced from this fixture carry no empirical claim.

## Full synchronized research dataset

The full synchronized dataset contains 1,217 derived NBA observations built partly from licensed historical bookmaker data.

It is not redistributed in this repository.

Dataset identity:

- observations: `1,217`
- strict T-60 observations: `1,214`
- SHA-256: `5a93b2ebd9fd6a1f5ff0583f8f7b1e63db75bc51548d7804c41dcb1d165a4e80`
- policy version: `nba_v2_sync_v1`

Users with authorized source access can rebuild the dataset using the included pipeline.

Every committed full-data result is tied to the dataset hash above.

## Research semantics

The Polymarket input is treated as a one-minute sampled historical probability series.

It is not treated as:

- a historical order book
- an executable bid
- an executable ask
- a trade
- a fill

The full-data analysis establishes forecast-comparison results only.

It does not establish tradable profitability.
