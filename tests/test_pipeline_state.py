from polyedge.pipeline_state import (
    reconcile_pipeline_state,
)


def test_complete_market_is_preserved():
    output_rows = [
        {
            "market_id": "market_a",
            "row_type": "PREGAME",
        },
        {
            "market_id": "market_a",
            "row_type": "SETTLEMENT",
        },
    ]

    manifest_rows = [
        {
            "source_market_id": "market_a",
        }
    ]

    state = reconcile_pipeline_state(
        output_rows=output_rows,
        manifest_rows=manifest_rows,
    )

    assert state.output_rows == output_rows
    assert state.manifest_rows == manifest_rows
    assert state.processed_market_ids == {"market_a"}
    assert state.dropped_market_ids == set()


def test_output_only_market_is_removed_for_rebuild():
    state = reconcile_pipeline_state(
        output_rows=[
            {
                "market_id": "market_a",
                "row_type": "PREGAME",
            },
            {
                "market_id": "market_a",
                "row_type": "SETTLEMENT",
            },
        ],
        manifest_rows=[],
    )

    assert state.output_rows == []
    assert state.manifest_rows == []
    assert state.processed_market_ids == set()
    assert state.dropped_market_ids == {"market_a"}


def test_manifest_only_market_is_removed_for_rebuild():
    state = reconcile_pipeline_state(
        output_rows=[],
        manifest_rows=[
            {
                "source_market_id": "market_a",
            }
        ],
    )

    assert state.output_rows == []
    assert state.manifest_rows == []
    assert state.processed_market_ids == set()
    assert state.dropped_market_ids == {"market_a"}


def test_duplicate_state_is_removed_for_rebuild():
    state = reconcile_pipeline_state(
        output_rows=[
            {
                "market_id": "market_a",
                "row_type": "PREGAME",
            },
            {
                "market_id": "market_a",
                "row_type": "PREGAME",
            },
        ],
        manifest_rows=[
            {
                "source_market_id": "market_a",
            }
        ],
    )

    assert state.output_rows == []
    assert state.manifest_rows == []
    assert state.processed_market_ids == set()
    assert state.dropped_market_ids == {"market_a"}
