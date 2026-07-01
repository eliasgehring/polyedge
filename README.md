# PolyEdge

Prediction-market backtesting engine with explicit probability semantics and settlement-aware accounting.

## Purpose

PolyEdge is a reproducible Python research engine for testing whether model-implied probabilities contain edge against prediction-market prices.

The goal is not to build a betting bot. The goal is to prevent false backtest conclusions from bad YES/NO mapping, synthetic execution assumptions, missing settlements, stale marks, and incorrect portfolio accounting.

## Current status

This project is under active cleanup toward a lean V2 research engine.

Current guarantees:
- explicit executable YES/NO edge semantics
- settlement-aware accounting tests
- global portfolio valuation across open markets
- dataset diagnostics before backtest execution
- honest percentage-return metrics

Current limitations:
- historical Polymarket prices are treated as midpoint observations
- bid/ask is synthetic unless real order-book data is supplied
- liquidity, partial fills, latency, and fees are not modeled
- results are exploratory, not direct live-trading claims

## Run tests

```bash
python -m pytest -q