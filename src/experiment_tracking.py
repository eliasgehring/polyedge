import csv
import hashlib
import os
from datetime import datetime


def file_sha256(filepath: str) -> str:
    hasher = hashlib.sha256()

    with open(filepath, mode="rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            hasher.update(chunk)

    return hasher.hexdigest()


def log_run_metadata(filepath, config):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    file_exists = os.path.exists(filepath)

    fieldnames = [
        "timestamp",
        "run_file",
        "result_status",
        "threshold",
        "edge_size_multiplier",
        "max_position_size",
        "dataset_hash",
        "dataset_rows",
        "dataset_markets",
        "dataset_pregame_rows",
        "dataset_settlement_rows",
        "dataset_hard_fail",
    ]

    with open(filepath, mode="a", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)

        if not file_exists:
            writer.writeheader()

        writer.writerow({
            "timestamp": datetime.now().isoformat(),
            "run_file": config["run_file"],
            "result_status": config["result_status"],
            "threshold": config["threshold"],
            "edge_size_multiplier": config["edge_size_multiplier"],
            "max_position_size": config["max_position_size"],
            "dataset_hash": config["dataset_hash"],
            "dataset_rows": config["dataset_rows"],
            "dataset_markets": config["dataset_markets"],
            "dataset_pregame_rows": config["dataset_pregame_rows"],
            "dataset_settlement_rows": config["dataset_settlement_rows"],
            "dataset_hard_fail": config["dataset_hard_fail"],
        })

