from pathlib import Path


PACKAGE_DIR = Path(__file__).resolve().parent
SRC_DIR = PACKAGE_DIR.parent
PROJECT_ROOT = SRC_DIR.parent

DATA_DIR = PROJECT_ROOT / "data"
RESULTS_DIR = PROJECT_ROOT / "results"


# Data directories

RAW_DATA_DIR = DATA_DIR / "raw"
INTERMEDIATE_DATA_DIR = DATA_DIR / "intermediate"
DIAGNOSTICS_DIR = DATA_DIR / "diagnostics"
FINAL_DATA_DIR = DATA_DIR / "final"


# Raw external data

NBA_RAW_DIR = RAW_DATA_DIR
NBA_RAW_FILE = NBA_RAW_DIR / "nba_new.csv"


# Intermediate pipeline outputs

BOOKMAKER_SOURCE_DIR = INTERMEDIATE_DATA_DIR / "bookmaker_source"
BOOKMAKER_SOURCE_FILE = BOOKMAKER_SOURCE_DIR / "nba_source.csv"

HISTORICAL_READY_DIR = INTERMEDIATE_DATA_DIR / "historical_ready"
HISTORICAL_READY_FILE = HISTORICAL_READY_DIR / "nba_source.csv"


# Diagnostics

POLYMARKET_REVIEW_FILE = DIAGNOSTICS_DIR / "review_needed.csv"
DATASET_DIAGNOSTICS_FILE = DIAGNOSTICS_DIR / "dataset_diagnostics.json"


# Final backtest input

HISTORICAL_DATA_DIR = FINAL_DATA_DIR
HISTORICAL_DATA_FILE = HISTORICAL_DATA_DIR / "historical_data.csv"


# Result directories

RESULT_LOGS_DIR = RESULTS_DIR / "logs"
RESULT_TABLES_DIR = RESULTS_DIR / "tables"
RESULT_FIGURES_DIR = RESULTS_DIR / "figures"

RUN_METADATA_FILE = RESULT_TABLES_DIR / "run_metadata.csv"
LEADERBOARD_FILE = RESULT_TABLES_DIR / "leaderboard.csv"


def ensure_dir(path) -> None:
    Path(path).mkdir(parents=True, exist_ok=True)


def ensure_parent_dir(filepath) -> None:
    Path(filepath).parent.mkdir(parents=True, exist_ok=True)