from collections import Counter
from dataclasses import dataclass
from typing import Any, Dict, List, Set


@dataclass(frozen=True)
class ReconciledPipelineState:
    output_rows: List[Dict[str, Any]]
    manifest_rows: List[Dict[str, Any]]
    processed_market_ids: Set[str]
    dropped_market_ids: Set[str]


def reconcile_pipeline_state(
    output_rows: List[Dict[str, Any]],
    manifest_rows: List[Dict[str, Any]],
) -> ReconciledPipelineState:
    output_market_ids = {
        row.get("market_id")
        for row in output_rows
        if row.get("market_id")
    }

    pregame_counts = Counter(
        row.get("market_id")
        for row in output_rows
        if (
            row.get("market_id")
            and str(row.get("row_type", "")).strip().upper()
            == "PREGAME"
        )
    )

    manifest_counts = Counter(
        row.get("source_market_id")
        for row in manifest_rows
        if row.get("source_market_id")
    )

    all_market_ids = (
        output_market_ids
        | set(manifest_counts)
    )

    complete_market_ids = {
        market_id
        for market_id in all_market_ids
        if (
            pregame_counts[market_id] == 1
            and manifest_counts[market_id] == 1
        )
    }

    dropped_market_ids = (
        all_market_ids - complete_market_ids
    )

    reconciled_output_rows = [
        row
        for row in output_rows
        if row.get("market_id") in complete_market_ids
    ]

    reconciled_manifest_rows = [
        row
        for row in manifest_rows
        if (
            row.get("source_market_id")
            in complete_market_ids
        )
    ]

    return ReconciledPipelineState(
        output_rows=reconciled_output_rows,
        manifest_rows=reconciled_manifest_rows,
        processed_market_ids=complete_market_ids,
        dropped_market_ids=dropped_market_ids,
    )
