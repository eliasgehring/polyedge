# PolyEdge V2 Research Report

## Dataset identity

- Mode: `PINNED_FULL_RESEARCH_DATASET`
- Path: `data/processed/nba_v2/synchronized_market_observations.csv`
- SHA-256: `5a93b2ebd9fd6a1f5ff0583f8f7b1e63db75bc51548d7804c41dcb1d165a4e80`
- Rows: `1217`
- Strict T-60 rows: `1214`
- Policy: `nba_v2_sync_v1`

## Forecast quality

| Metric | Bookmaker | Polymarket | PM minus bookmaker | Date-clustered 95% CI |
|---|---:|---:|---:|---:|
| Brier score | 0.202440670629 | 0.202655496508 | 0.000214825879 | [-0.000282744527, 0.000710791553] |
| Binary log loss | 0.588823498469 | 0.589332201047 | 0.000508702578 | [-0.000936759017, 0.001982394897] |

Positive score differences mean the bookmaker forecast had lower loss.

## Discrepancy structure

- Within two percentage points: `1148`
- At least five percentage points apart: `0`
- Mean absolute discrepancy: `0.008760125244`

## Probability behavior

- Bookmaker less extreme: `935` (`76.83%`)
- Equal extremeness: `0` (`0.00%`)
- Bookmaker more extreme: `282` (`23.17%`)
- Mean extremeness gap, bookmaker minus Polymarket: `-0.006434891061`

Negative extremeness gaps mean the bookmaker forecast was closer to 0.50.

| Consensus HOME probability | Count | Bookmaker less extreme | Mean extremeness gap | Mean Brier difference | Date-clustered 95% CI | Mean log-loss difference | Date-clustered 95% CI |
|---|---:|---:|---:|---:|---:|---:|---:|
| [0.00, 0.20) | 73 | 98.63% | -0.014370283488 | -0.001543672352 | [-0.003571253004, 0.000800055057] | -0.006006408244 | [-0.013837044087, 0.002950812482] |
| [0.20, 0.35) | 168 | 83.93% | -0.007684928795 | -0.000309345056 | [-0.001723125599, 0.001149415620] | -0.000621884904 | [-0.004194514373, 0.003077927633] |
| [0.35, 0.50) | 218 | 67.89% | -0.004295203109 | 0.000673296963 | [-0.000469985436, 0.001867172878] | 0.001390066219 | [-0.000981588160, 0.003866495151] |
| [0.50, 0.65) | 266 | 63.53% | -0.002265077673 | 0.000331425205 | [-0.000580907414, 0.001242294269] | 0.000678190479 | [-0.001219027197, 0.002560794083] |
| [0.65, 0.80) | 297 | 77.10% | -0.006334029902 | 0.000263698256 | [-0.000790406618, 0.001351449837] | 0.000949894577 | [-0.001801941420, 0.003799591942] |
| [0.80, 1.00] | 195 | 90.26% | -0.010620983948 | 0.000578691903 | [-0.000663770084, 0.001967067899] | 0.002033249801 | [-0.003240826899, 0.007959777822] |

## Claim boundary

- Source semantics: `one_minute_sampled_probability_series`
- Execution semantics: `none`
- Tradable profitability: **not established**
- Empirical status: Results apply only to the dataset identified by the SHA-256 below.

The Polymarket input is a sampled historical probability series, not a historical order book, bid, ask, trade, or fill.
