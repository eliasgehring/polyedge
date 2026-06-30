# Architecture

This project tests whether bookmaker-implied NBA probabilities differ from Polymarket prices in a way that produces predictable event-level returns.

The code is organized around one pipeline:

```text
raw bookmaker odds
→ normalized bookmaker probabilities
→ Polymarket-matched event prices
→ historical backtest dataset
→ strategy simulation
→ logs and summary results