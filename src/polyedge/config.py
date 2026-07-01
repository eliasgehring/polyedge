STARTING_CASH = 1000.0

# Minimum absolute edge required to enter a trade.
# edge = bookmaker_prob - polymarket_prob
THRESHOLD = 0.10

# Maximum number of contracts/shares per market.
MAX_POSITION_SIZE = 30

# Position size rule:
# size = abs(edge) * EDGE_SIZE_MULTIPLIER,
# capped by MAX_POSITION_SIZE.
EDGE_SIZE_MULTIPLIER = 500

# Only trade when Polymarket home-team probability is inside this band.
# This avoids extremely skewed 0/1-like markets.
MIN_MARKET_PROB = 0.25
MAX_MARKET_PROB = 0.75

# Simple execution-cost assumptions.
BASE_SLIPPAGE = 0.002
SIZE_IMPACT = 0.0005

RESULT_STATUS = "MECHANICALLY_VALID_SYNTHETIC_BACKTEST"

VERBOSE= False
