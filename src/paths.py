import os


SRC_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SRC_DIR)

DATA_DIR = os.path.join(PROJECT_ROOT, "data")
RESULTS_DIR = os.path.join(PROJECT_ROOT, "results")


# Data directories


RAW_DATA_DIR = os.path.join(DATA_DIR, "raw")
INTERMEDIATE_DATA_DIR = os.path.join(DATA_DIR, "intermediate")
DIAGNOSTICS_DIR = os.path.join(DATA_DIR, "diagnostics")
FINAL_DATA_DIR = os.path.join(DATA_DIR, "final")


# Raw external data.
NBA_RAW_DIR = RAW_DATA_DIR
NBA_RAW_FILE = os.path.join(NBA_RAW_DIR, "nba_new.csv")


# Intermediate pipeline outputs.
BOOKMAKER_SOURCE_DIR = os.path.join(INTERMEDIATE_DATA_DIR, "bookmaker_source")
BOOKMAKER_SOURCE_FILE = os.path.join(BOOKMAKER_SOURCE_DIR, "nba_source.csv")

HISTORICAL_READY_DIR = os.path.join(INTERMEDIATE_DATA_DIR, "historical_ready")
HISTORICAL_READY_FILE = os.path.join(HISTORICAL_READY_DIR, "nba_source.csv")


# Diagnostics.
# Diagnostics.
POLYMARKET_REVIEW_FILE = os.path.join(DIAGNOSTICS_DIR, "review_needed.csv")
DATASET_DIAGNOSTICS_FILE = os.path.join(
    DIAGNOSTICS_DIR,
    "dataset_diagnostics.json",
)


# Final backtest input.
HISTORICAL_DATA_DIR = FINAL_DATA_DIR
HISTORICAL_DATA_FILE = os.path.join(HISTORICAL_DATA_DIR, "historical_data.csv")


# Result directories

RESULT_LOGS_DIR = os.path.join(RESULTS_DIR, "logs")
RESULT_TABLES_DIR = os.path.join(RESULTS_DIR, "tables")
RESULT_FIGURES_DIR = os.path.join(RESULTS_DIR, "figures")

RUN_METADATA_FILE = os.path.join(RESULT_TABLES_DIR, "run_metadata.csv")
LEADERBOARD_FILE = os.path.join(RESULT_TABLES_DIR, "leaderboard.csv")



# Helpers

def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def ensure_parent_dir(filepath: str) -> None:
    os.makedirs(os.path.dirname(filepath), exist_ok=True)