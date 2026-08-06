from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

from polyedge.dashboard_view import (
    build_dashboard_view,
)
from polyedge.paired_forecast_uncertainty import (
    DEFAULT_SEED,
)
from polyedge.paths import PROJECT_ROOT
from polyedge.research_command import (
    DEMO_DATASET_PATH,
    build_research_summary,
)


DEFAULT_PRIVATE_DATASET_PATH = (
    PROJECT_ROOT
    / "data/processed/nba_v2"
    / "synchronized_market_observations.csv"
)


@st.cache_data(
    show_spinner=False,
)
def load_research_summary(
    *,
    dataset_path: str,
    demo: bool,
    resamples: int,
    seed: int,
):
    return build_research_summary(
        dataset_path=Path(
            dataset_path
        ),
        demo=demo,
        resamples=resamples,
        seed=seed,
    )


def format_score(
    value: float,
) -> str:
    return f"{value:.6f}"


def format_signed_score(
    value: float,
) -> str:
    return f"{value:+.6f}"


def format_percentage(
    value: float,
) -> str:
    return f"{value:.2f}%"


def build_interval_dataframe(
    view,
) -> pd.DataFrame:
    return pd.DataFrame([
        {
            "Metric": interval.metric_label,
            "Estimate": interval.estimate,
            "Lower": interval.lower,
            "Upper": interval.upper,
        }
        for interval in view.confidence_intervals
    ])


def build_band_dataframe(
    view,
) -> pd.DataFrame:
    return pd.DataFrame([
        {
            "Consensus band": band.band_label,
            "Count": band.count,
            "Bookmaker less extreme (%)": (
                band
                .bookmaker_less_extreme_percentage
            ),
            "Mean extremeness gap (pp)": (
                band
                .mean_extremeness_gap_percentage_points
            ),
            "Mean PM minus bookmaker Brier": (
                band.mean_brier_difference
            ),
            "Brier CI lower": (
                band.brier_ci_lower
            ),
            "Brier CI upper": (
                band.brier_ci_upper
            ),
        }
        for band in view.probability_bands
    ])


def render_interval_chart(
    interval_data: pd.DataFrame,
) -> None:
    zero_line = alt.Chart(
        pd.DataFrame({
            "Zero": [0.0],
        })
    ).mark_rule(
        strokeDash=[4, 4],
    ).encode(
        x=alt.X(
            "Zero:Q",
            title=(
                "PM loss minus bookmaker loss"
            ),
        ),
    )

    intervals = alt.Chart(
        interval_data
    ).mark_rule(
        size=3,
    ).encode(
        x=alt.X(
            "Lower:Q",
            title=(
                "PM loss minus bookmaker loss"
            ),
        ),
        x2="Upper:Q",
        y=alt.Y(
            "Metric:N",
            sort=None,
            title=None,
        ),
        tooltip=[
            alt.Tooltip(
                "Metric:N",
            ),
            alt.Tooltip(
                "Estimate:Q",
                format=".8f",
            ),
            alt.Tooltip(
                "Lower:Q",
                format=".8f",
            ),
            alt.Tooltip(
                "Upper:Q",
                format=".8f",
            ),
        ],
    )

    estimates = alt.Chart(
        interval_data
    ).mark_point(
        filled=True,
        size=100,
    ).encode(
        x="Estimate:Q",
        y=alt.Y(
            "Metric:N",
            sort=None,
            title=None,
        ),
        tooltip=[
            alt.Tooltip(
                "Metric:N",
            ),
            alt.Tooltip(
                "Estimate:Q",
                format=".8f",
            ),
        ],
    )

    st.altair_chart(
        (
            zero_line
            + intervals
            + estimates
        ).properties(
            height=150,
        ),
        use_container_width=True,
    )


def main() -> None:
    st.set_page_config(
        page_title="PolyEdge V2",
        page_icon="🧭",
        layout="wide",
    )

    st.title("PolyEdge V2")
    st.caption(
        "Truth-preserving comparison of synchronized "
        "bookmaker and prediction-market probabilities."
    )

    st.sidebar.header(
        "Research input"
    )

    input_mode = st.sidebar.radio(
        "Dataset",
        options=(
            "Public synthetic demo",
            "Authorized local dataset",
        ),
    )

    demo = (
        input_mode
        == "Public synthetic demo"
    )

    if demo:
        dataset_path = DEMO_DATASET_PATH
        default_resamples = 500
        st.sidebar.info(
            "The public fixture demonstrates the workflow "
            "and supports no empirical claim."
        )
    else:
        dataset_path = Path(
            st.sidebar.text_input(
                "Dataset path",
                value=str(
                    DEFAULT_PRIVATE_DATASET_PATH
                ),
            )
        )
        default_resamples = 2000

    resamples = int(
        st.sidebar.number_input(
            "Bootstrap resamples",
            min_value=100,
            max_value=50000,
            value=default_resamples,
            step=100,
            help=(
                "More resamples reduce simulation noise in "
                "the bootstrap interval. They do not add data."
            ),
        )
    )

    seed = int(
        st.sidebar.number_input(
            "Deterministic seed",
            min_value=0,
            value=DEFAULT_SEED,
            step=1,
        )
    )

    if not dataset_path.exists():
        st.error(
            "Dataset not found: "
            + str(
                dataset_path
            )
        )
        st.stop()

    with st.spinner(
        "Running canonical research analysis..."
    ):
        try:
            summary = load_research_summary(
                dataset_path=str(
                    dataset_path
                ),
                demo=demo,
                resamples=resamples,
                seed=seed,
            )
        except Exception as error:
            st.error(
                "Research analysis failed."
            )
            st.exception(
                error
            )
            st.stop()

    view = build_dashboard_view(
        summary
    )

    if (
        view.dataset_mode
        == "SYNTHETIC_DEMONSTRATION"
    ):
        st.warning(
            "SYNTHETIC DEMONSTRATION. "
            "Empirical claims: NONE."
        )
    elif (
        view.dataset_mode
        == "PINNED_FULL_RESEARCH_DATASET"
    ):
        st.success(
            "Pinned full research dataset verified by SHA-256."
        )
    else:
        st.info(
            "Custom authorized dataset. "
            "Results apply only to this input."
        )

    st.subheader(
        "Dataset integrity"
    )

    dataset_columns = st.columns(
        4
    )

    dataset_columns[0].metric(
        "Synchronized markets",
        f"{view.row_count:,}",
    )
    dataset_columns[1].metric(
        "Strict T-60",
        f"{view.strict_row_count:,}",
    )
    dataset_columns[2].metric(
        "Within 2 percentage points",
        (
            f"{view.within_two_points_count:,} "
            f"({view.within_two_points_percentage:.1f}%)"
        ),
    )
    dataset_columns[3].metric(
        "At least 5 points apart",
        f"{view.at_least_five_points_count:,}",
    )

    st.subheader(
        "Forecast comparison"
    )

    score_columns = st.columns(
        3
    )

    score_columns[0].metric(
        "Bookmaker Brier",
        format_score(
            view.bookmaker_brier_score
        ),
    )
    score_columns[1].metric(
        "Polymarket Brier",
        format_score(
            view.polymarket_brier_score
        ),
    )
    score_columns[2].metric(
        "PM minus bookmaker",
        format_signed_score(
            view
            .brier_difference_polymarket_minus_bookmaker
        ),
        help=(
            "Positive means bookmaker loss was lower."
        ),
    )

    log_loss_columns = st.columns(
        3
    )

    log_loss_columns[0].metric(
        "Bookmaker log loss",
        format_score(
            view.bookmaker_log_loss
        ),
    )
    log_loss_columns[1].metric(
        "Polymarket log loss",
        format_score(
            view.polymarket_log_loss
        ),
    )
    log_loss_columns[2].metric(
        "PM minus bookmaker",
        format_signed_score(
            view
            .log_loss_difference_polymarket_minus_bookmaker
        ),
        help=(
            "Positive means bookmaker loss was lower."
        ),
    )

    st.caption(
        "Game-date-clustered paired-bootstrap 95% intervals. "
        "Intervals crossing zero do not establish a source-level "
        "accuracy advantage."
    )

    render_interval_chart(
        build_interval_dataframe(
            view
        )
    )

    st.subheader(
        "Probability behavior"
    )

    behavior_columns = st.columns(
        3
    )

    behavior_columns[0].metric(
        "Mean absolute gap",
        (
            f"{view.mean_absolute_discrepancy_percentage_points:.3f} pp"
        ),
    )
    behavior_columns[1].metric(
        "Bookmaker less extreme",
        (
            f"{view.bookmaker_less_extreme_count:,} "
            f"({view.bookmaker_less_extreme_percentage:.2f}%)"
        ),
    )
    behavior_columns[2].metric(
        "Mean extremeness gap",
        (
            f"{view.mean_extremeness_gap_percentage_points:+.3f} pp"
        ),
        help=(
            "Bookmaker extremeness minus Polymarket extremeness. "
            "Negative means bookmaker probabilities were closer to 0.50."
        ),
    )

    band_data = build_band_dataframe(
        view
    )

    chart_data = (
        band_data[
            [
                "Consensus band",
                "Bookmaker less extreme (%)",
            ]
        ]
        .set_index(
            "Consensus band"
        )
    )

    st.bar_chart(
        chart_data
    )

    st.dataframe(
        band_data,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Bookmaker less extreme (%)": (
                st.column_config.NumberColumn(
                    format="%.2f%%",
                )
            ),
            "Mean extremeness gap (pp)": (
                st.column_config.NumberColumn(
                    format="%.4f",
                )
            ),
            "Mean PM minus bookmaker Brier": (
                st.column_config.NumberColumn(
                    format="%.8f",
                )
            ),
            "Brier CI lower": (
                st.column_config.NumberColumn(
                    format="%.8f",
                )
            ),
            "Brier CI upper": (
                st.column_config.NumberColumn(
                    format="%.8f",
                )
            ),
        },
    )

    st.subheader(
        "Research conclusion"
    )
    st.write(
        view.conclusion
    )

    st.warning(
        "Execution semantics: "
        + view.execution_semantics
        + ". Tradable profitability: "
        + view.tradable_profitability_status
        + "."
    )

    with st.expander(
        "Dataset identity and claim boundary"
    ):
        st.code(
            "\n".join([
                "Dataset mode: "
                + view.dataset_mode,
                "Dataset status: "
                + view.dataset_status,
                "Empirical claims: "
                + view.empirical_claim_status,
                "SHA-256: "
                + view.dataset_sha256,
                "Policy: "
                + view.policy_version,
                "Source semantics: "
                + view.source_semantics,
                "Execution semantics: "
                + view.execution_semantics,
                "Tradable profitability: "
                + view.tradable_profitability_status,
            ]),
            language="text",
        )

        st.write(
            "The Polymarket input is a sampled historical "
            "probability series, not an order book, bid, ask, "
            "trade, or fill."
        )


if __name__ == "__main__":
    main()
