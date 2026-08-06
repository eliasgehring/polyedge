from polyedge.research_command import (
    DEMO_DATASET_PATH,
    build_research_summary,
)


def test_research_summary_includes_extremeness_analysis():
    summary = build_research_summary(
        dataset_path=DEMO_DATASET_PATH,
        demo=True,
        resamples=50,
        seed=7,
    )

    extremeness = (
        summary.extremeness_analysis
    )

    assert extremeness.count == 12

    assert (
        extremeness.bookmaker_less_extreme_count
        + extremeness.equal_extremeness_count
        + extremeness.bookmaker_more_extreme_count
        == 12
    )

    assert sum(
        band.count
        for band in extremeness.probability_bands
    ) == 12
