# PolyEdge

PolyEdge is a truth-preserving Python research engine for comparing synchronized bookmaker consensus probabilities with prediction-market probabilities.

Its central question is not “can a backtest print a profit?” It is:

> Does the available data support the claimed probability edge under explicit timing, scoring, and source semantics?

## Evaluator quick start

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[test]"
python -m pytest -q
polyedge research --demo
```

The public demo uses a synthetic fixture and prints:

```text
Dataset mode           : SYNTHETIC_DEMONSTRATION
Empirical claims       : NONE
Execution semantics    : none
Tradable profitability : NOT ESTABLISHED
```

## Optional dashboard

```bash
python -m pip install -e ".[dashboard]"
streamlit run streamlit_app.py
```

To install both evaluator tests and the dashboard:

```bash
python -m pip install -e ".[test,dashboard]"
```

The dashboard imports the same canonical `ResearchSummary` used by the CLI and Markdown report. It does not maintain a second metrics implementation.

## Current NBA V2 result

The full synchronized dataset is not redistributed because it was derived partly from licensed historical bookmaker data.

Pinned identity:

```text
Rows:          1,217
Strict T-60:  1,214
SHA-256:       5a93b2ebd9fd6a1f5ff0583f8f7b1e63db75bc51548d7804c41dcb1d165a4e80
Policy:        nba_v2_sync_v1
```

Headline findings:

- 1,148 of 1,217 observations were within two percentage points.
- No observation differed by five percentage points or more.
- Bookmaker consensus was less extreme in 935 observations, or 76.83%.
- Bookmaker point estimates had marginally lower aggregate loss.
- Game-date-clustered paired-bootstrap intervals crossed zero.
- Neither source demonstrated a credible aggregate accuracy advantage.
- Execution semantics are `none`; tradable profitability is not established.

The committed full-data result is:

```text
reports/nba_v2_research_report.md
```

Data policy and reproduction boundaries are documented in:

```text
DATA_AVAILABILITY.md
```

## One research engine, three views

```text
validated synchronized rows
        ↓
tested scoring and uncertainty modules
        ↓
ResearchSummary
        ↓
CLI / Markdown report / Streamlit dashboard
```

Presentation layers do not recalculate Brier scores, log loss, bootstrap intervals, discrepancies, or extremeness.

## Probability semantics

For each game:

```text
bookmaker_home_probability
polymarket_home_probability
resolved_home_value ∈ {0, 1}
```

The paired score difference is:

```text
Polymarket loss minus bookmaker loss
```

Positive values mean the bookmaker forecast had lower loss.

HOME is scored once. AWAY is the exact binary complement and is not treated as an independent sample.

## Timing and source semantics

The synchronized observation uses one common decision time.

Bookmaker probability is derived from eligible fresh bookmaker updates available by that observation time.

Polymarket probability is the latest valid sampled historical probability point at or before the same observation time.

The Polymarket series is not interpreted as:

- a historical order book
- an executable bid
- an executable ask
- a trade
- a fill

## Uncertainty

Forecast comparisons use paired loss differences because both sources forecast the same games.

The reported intervals use a deterministic game-date-clustered bootstrap:

1. Compute one paired loss difference per game.
2. Group games by date.
3. Resample dates with replacement.
4. Include every game from each selected date.
5. Recalculate the mean paired difference.
6. Repeat and take the 2.5th and 97.5th percentiles.

More bootstrap resamples reduce simulation noise. They do not add observations or strengthen the underlying evidence.

## Main command

Public evaluator workflow:

```bash
polyedge research --demo
```

Authorized full-data workflow:

```bash
polyedge research \
  --dataset /path/to/authorized/synchronized_market_observations.csv \
  --resamples 10000 \
  --report reports/reproduced_report.md
```

## Repository map

```text
src/polyedge/             canonical domain and research logic
tests/                    deterministic semantics and invariant tests
scripts/data_pipeline/    source capture and synchronized dataset builders
scripts/research/         focused research audits
data/demo/                public synthetic evaluator fixture
reports/                  pinned research reports
streamlit_app.py          optional read-only dashboard
```

The repository retains tested accounting, execution, and signal modules as internal engineering work. They are not exposed by the evaluator CLI and do not support the V2 empirical result.

## Research standard

A result is publishable only when its probability meaning, timestamp policy, dataset identity, scoring rule, uncertainty method, and claim boundary are explicit.

A profitable number that fails those tests is not a result. It is stage lighting.
