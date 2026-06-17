"""
SentinelOps — YOLO Experiment Comparison Dashboard
====================================================
Streamlit dashboard for comparing YOLO training experiments.

Loads experiment results from CSV and provides interactive
visualizations: bar charts, line charts, radar charts, and
a sortable leaderboard.

Usage:
    streamlit run dashboard/experiment_compare.py
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
METRIC_COLUMNS: list[str] = [
    "precision",
    "recall",
    "mAP50",
    "mAP50-95",
    "training_time_min",
    "param_count_M",
    "model_size_MB",
]

METRIC_DISPLAY_NAMES: dict[str, str] = {
    "precision": "Precision",
    "recall": "Recall",
    "mAP50": "mAP@50",
    "mAP50-95": "mAP@50-95",
    "training_time_min": "Training Time (min)",
    "param_count_M": "Parameters (M)",
    "model_size_MB": "Model Size (MB)",
}

# Metrics where higher is better (used for leaderboard highlighting)
HIGHER_IS_BETTER: set[str] = {"precision", "recall", "mAP50", "mAP50-95"}

# Radar-chart metrics (normalised [0-1] style metrics only)
RADAR_METRICS: list[str] = ["precision", "recall", "mAP50", "mAP50-95"]

# Colour palette for experiments
COLOR_PALETTE: list[str] = [
    "#6366f1",  # indigo
    "#f43f5e",  # rose
    "#10b981",  # emerald
    "#f59e0b",  # amber
    "#3b82f6",  # blue
    "#8b5cf6",  # violet
    "#ec4899",  # pink
    "#14b8a6",  # teal
]


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------
@st.cache_data
def load_experiments(path: str | Path) -> pd.DataFrame:
    """Load experiment CSV and validate required columns."""
    df = pd.read_csv(path)

    missing = [c for c in ["experiment_name"] + METRIC_COLUMNS if c not in df.columns]
    if missing:
        st.error(f"CSV is missing required columns: {missing}")
        st.stop()

    return df


def generate_sample_csv(path: Path) -> None:
    """Create a sample experiment CSV for demonstration purposes."""
    data = {
        "experiment_name": [
            "YOLOv11n-baseline",
            "YOLOv11s-baseline",
            "YOLOv11m-baseline",
            "YOLOv11n-augmented",
            "YOLOv11s-augmented",
            "YOLOv11m-augmented",
        ],
        "precision": [0.82, 0.87, 0.91, 0.85, 0.90, 0.93],
        "recall": [0.78, 0.83, 0.88, 0.81, 0.86, 0.90],
        "mAP50": [0.80, 0.86, 0.90, 0.84, 0.89, 0.92],
        "mAP50-95": [0.52, 0.60, 0.68, 0.56, 0.64, 0.71],
        "training_time_min": [12.3, 24.7, 48.5, 14.1, 27.9, 53.2],
        "param_count_M": [2.6, 9.4, 20.1, 2.6, 9.4, 20.1],
        "model_size_MB": [5.4, 18.7, 40.2, 5.4, 18.7, 40.2],
        "epochs": [50, 50, 50, 50, 50, 50],
        "batch_size": [16, 16, 8, 16, 16, 8],
        "img_size": [640, 640, 640, 640, 640, 640],
        "augmentation": [
            "none",
            "none",
            "none",
            "mosaic+mixup",
            "mosaic+mixup",
            "mosaic+mixup",
        ],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(data).to_csv(path, index=False)


# ---------------------------------------------------------------------------
# Chart builders
# ---------------------------------------------------------------------------
def build_bar_chart(
    df: pd.DataFrame,
    metric: str,
    selected: list[str],
) -> go.Figure:
    """Grouped bar chart comparing a single metric across experiments."""
    subset = df[df["experiment_name"].isin(selected)].copy()
    colors = {
        name: COLOR_PALETTE[i % len(COLOR_PALETTE)]
        for i, name in enumerate(selected)
    }

    fig = px.bar(
        subset,
        x="experiment_name",
        y=metric,
        color="experiment_name",
        color_discrete_map=colors,
        text_auto=".3f",
    )
    fig.update_layout(
        title=dict(text=METRIC_DISPLAY_NAMES.get(metric, metric), font_size=18),
        xaxis_title="",
        yaxis_title=METRIC_DISPLAY_NAMES.get(metric, metric),
        showlegend=False,
        template="plotly_dark",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=50, b=30),
        font=dict(family="Inter, sans-serif"),
    )
    fig.update_traces(textposition="outside")
    return fig


def build_line_chart(
    df: pd.DataFrame,
    metrics: list[str],
    selected: list[str],
) -> go.Figure:
    """Line chart showing multiple metrics per experiment."""
    subset = df[df["experiment_name"].isin(selected)].copy()

    fig = go.Figure()
    for i, name in enumerate(selected):
        row = subset[subset["experiment_name"] == name].iloc[0]
        vals = [row[m] for m in metrics]
        fig.add_trace(
            go.Scatter(
                x=[METRIC_DISPLAY_NAMES.get(m, m) for m in metrics],
                y=vals,
                mode="lines+markers",
                name=name,
                line=dict(
                    color=COLOR_PALETTE[i % len(COLOR_PALETTE)],
                    width=3,
                ),
                marker=dict(size=10),
            )
        )

    fig.update_layout(
        title=dict(text="Metric Comparison (Line)", font_size=18),
        xaxis_title="Metric",
        yaxis_title="Value",
        template="plotly_dark",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=50, b=30),
        font=dict(family="Inter, sans-serif"),
        legend=dict(orientation="h", yanchor="bottom", y=-0.3),
    )
    return fig


def build_radar_chart(
    df: pd.DataFrame,
    selected: list[str],
) -> go.Figure:
    """Radar (spider) chart comparing detection quality metrics."""
    subset = df[df["experiment_name"].isin(selected)].copy()
    display_names = [METRIC_DISPLAY_NAMES.get(m, m) for m in RADAR_METRICS]

    fig = go.Figure()
    for i, name in enumerate(selected):
        row = subset[subset["experiment_name"] == name].iloc[0]
        values = [row[m] for m in RADAR_METRICS]
        # close the polygon
        values_closed = values + [values[0]]
        names_closed = display_names + [display_names[0]]

        fig.add_trace(
            go.Scatterpolar(
                r=values_closed,
                theta=names_closed,
                fill="toself",
                name=name,
                line=dict(
                    color=COLOR_PALETTE[i % len(COLOR_PALETTE)],
                    width=2,
                ),
                opacity=0.6,
            )
        )

    fig.update_layout(
        title=dict(text="Detection Quality Radar", font_size=18),
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 1],
                tickfont=dict(size=10),
            ),
            bgcolor="rgba(0,0,0,0)",
        ),
        template="plotly_dark",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=60, b=40),
        font=dict(family="Inter, sans-serif"),
        legend=dict(orientation="h", yanchor="bottom", y=-0.25),
    )
    return fig


def build_leaderboard(
    df: pd.DataFrame,
    selected: list[str],
    sort_by: str,
    ascending: bool,
) -> pd.DataFrame:
    """Return a styled leaderboard DataFrame."""
    subset = df[df["experiment_name"].isin(selected)].copy()

    display_cols = ["experiment_name"] + METRIC_COLUMNS
    extra_cols = [c for c in df.columns if c not in display_cols]
    all_cols = display_cols + extra_cols

    leaderboard = subset[all_cols].sort_values(sort_by, ascending=ascending)
    leaderboard = leaderboard.reset_index(drop=True)
    leaderboard.index += 1
    leaderboard.index.name = "Rank"

    rename_map = {"experiment_name": "Experiment"}
    rename_map.update(METRIC_DISPLAY_NAMES)
    leaderboard = leaderboard.rename(columns=rename_map)

    return leaderboard


# ---------------------------------------------------------------------------
# Efficiency scatter
# ---------------------------------------------------------------------------
def build_efficiency_scatter(
    df: pd.DataFrame,
    selected: list[str],
) -> go.Figure:
    """Scatter plot: mAP50-95 vs Training Time, sized by model size."""
    subset = df[df["experiment_name"].isin(selected)].copy()
    colors = {
        name: COLOR_PALETTE[i % len(COLOR_PALETTE)]
        for i, name in enumerate(selected)
    }

    fig = px.scatter(
        subset,
        x="training_time_min",
        y="mAP50-95",
        size="model_size_MB",
        color="experiment_name",
        color_discrete_map=colors,
        hover_data=["param_count_M", "model_size_MB"],
        size_max=50,
    )
    fig.update_layout(
        title=dict(text="Efficiency: mAP@50-95 vs Training Time", font_size=18),
        xaxis_title="Training Time (min)",
        yaxis_title="mAP@50-95",
        template="plotly_dark",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=50, b=30),
        font=dict(family="Inter, sans-serif"),
        legend=dict(orientation="h", yanchor="bottom", y=-0.3),
    )
    return fig


# ---------------------------------------------------------------------------
# Streamlit app
# ---------------------------------------------------------------------------
def main() -> None:
    st.set_page_config(
        page_title="SentinelOps — Experiment Comparison",
        page_icon="🔬",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # -- Custom CSS --------------------------------------------------------
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

        html, body, [class*="st-"] {
            font-family: 'Inter', sans-serif;
        }
        .block-container {
            padding-top: 2rem;
        }
        h1, h2, h3 {
            font-weight: 700 !important;
        }
        .stMetric > div {
            background: linear-gradient(135deg, #1e1b4b 0%, #312e81 100%);
            border-radius: 12px;
            padding: 16px;
            border: 1px solid rgba(99, 102, 241, 0.3);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # -- Header ------------------------------------------------------------
    st.markdown(
        """
        <div style="text-align:center; padding: 1rem 0 0.5rem 0;">
            <h1 style="margin:0; font-size:2.2rem;">
                🔬 SentinelOps — Experiment Comparison
            </h1>
            <p style="color:#94a3b8; margin-top:0.3rem;">
                Compare YOLO training runs side-by-side
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # -- Sidebar -----------------------------------------------------------
    with st.sidebar:
        st.header("⚙️ Configuration")

        sample_csv_path = Path("artifacts/sample_experiments.csv")

        upload = st.file_uploader(
            "Upload experiment CSV",
            type=["csv"],
            help="CSV must contain: experiment_name, precision, recall, mAP50, mAP50-95, training_time_min, param_count_M, model_size_MB",
        )

        if upload is not None:
            df = load_experiments(upload)
        else:
            if not sample_csv_path.exists():
                generate_sample_csv(sample_csv_path)
            df = load_experiments(sample_csv_path)
            st.info("📂 Using sample data. Upload a CSV to use your own.")

        st.divider()

        all_experiments = df["experiment_name"].tolist()
        selected = st.multiselect(
            "Select experiments to compare",
            options=all_experiments,
            default=all_experiments,
        )

        if not selected:
            st.warning("Select at least one experiment.")
            st.stop()

        st.divider()

        sort_metric = st.selectbox(
            "Leaderboard sort metric",
            options=METRIC_COLUMNS,
            format_func=lambda m: METRIC_DISPLAY_NAMES.get(m, m),
            index=3,  # default to mAP50-95
        )

        sort_order = st.radio(
            "Sort order",
            options=["Descending", "Ascending"],
            horizontal=True,
        )

    # -- KPI cards ---------------------------------------------------------
    best_row = df[df["experiment_name"].isin(selected)]
    if not best_row.empty:
        kpi_cols = st.columns(4)
        best_map = best_row.loc[best_row["mAP50-95"].idxmax()]
        with kpi_cols[0]:
            st.metric("🏆 Best mAP@50-95", f"{best_map['mAP50-95']:.3f}", best_map["experiment_name"])
        with kpi_cols[1]:
            st.metric("🎯 Best Precision", f"{best_row['precision'].max():.3f}")
        with kpi_cols[2]:
            st.metric("📡 Best Recall", f"{best_row['recall'].max():.3f}")
        with kpi_cols[3]:
            fastest = best_row.loc[best_row["training_time_min"].idxmin()]
            st.metric("⚡ Fastest Training", f"{fastest['training_time_min']:.1f} min", fastest["experiment_name"])

    st.divider()

    # -- Tabs --------------------------------------------------------------
    tab_bar, tab_line, tab_radar, tab_efficiency, tab_leaderboard = st.tabs(
        ["📊 Bar Charts", "📈 Line Charts", "🕸️ Radar Chart", "⚡ Efficiency", "🏅 Leaderboard"]
    )

    # ── Bar charts ────────────────────────────────────────────────────────
    with tab_bar:
        st.subheader("Metric Comparison — Bar Charts")
        bar_metric = st.selectbox(
            "Select metric",
            options=METRIC_COLUMNS,
            format_func=lambda m: METRIC_DISPLAY_NAMES.get(m, m),
            key="bar_metric",
        )
        st.plotly_chart(
            build_bar_chart(df, bar_metric, selected),
            use_container_width=True,
        )

        # Side-by-side detection metrics
        st.subheader("Detection Metrics Overview")
        cols = st.columns(2)
        with cols[0]:
            st.plotly_chart(
                build_bar_chart(df, "precision", selected),
                use_container_width=True,
            )
        with cols[1]:
            st.plotly_chart(
                build_bar_chart(df, "recall", selected),
                use_container_width=True,
            )

        cols2 = st.columns(2)
        with cols2[0]:
            st.plotly_chart(
                build_bar_chart(df, "mAP50", selected),
                use_container_width=True,
            )
        with cols2[1]:
            st.plotly_chart(
                build_bar_chart(df, "mAP50-95", selected),
                use_container_width=True,
            )

    # ── Line charts ───────────────────────────────────────────────────────
    with tab_line:
        st.subheader("Metric Comparison — Line Chart")
        line_metrics = st.multiselect(
            "Select metrics to plot",
            options=RADAR_METRICS,
            default=RADAR_METRICS,
            format_func=lambda m: METRIC_DISPLAY_NAMES.get(m, m),
            key="line_metrics",
        )
        if line_metrics:
            st.plotly_chart(
                build_line_chart(df, line_metrics, selected),
                use_container_width=True,
            )
        else:
            st.info("Select at least one metric.")

    # ── Radar chart ───────────────────────────────────────────────────────
    with tab_radar:
        st.subheader("Detection Quality — Radar Chart")
        st.plotly_chart(
            build_radar_chart(df, selected),
            use_container_width=True,
        )

    # ── Efficiency scatter ────────────────────────────────────────────────
    with tab_efficiency:
        st.subheader("Model Efficiency Analysis")
        st.caption("Bubble size = model file size (MB)")
        st.plotly_chart(
            build_efficiency_scatter(df, selected),
            use_container_width=True,
        )

    # ── Leaderboard ──────────────────────────────────────────────────────
    with tab_leaderboard:
        st.subheader("🏅 Experiment Leaderboard")
        ascending = sort_order == "Ascending"
        leaderboard = build_leaderboard(df, selected, sort_metric, ascending)
        st.dataframe(
            leaderboard,
            use_container_width=True,
            height=400,
        )

        # Download button
        csv_data = leaderboard.to_csv()
        st.download_button(
            label="⬇️ Download leaderboard as CSV",
            data=csv_data,
            file_name="sentinelops_leaderboard.csv",
            mime="text/csv",
        )

    # -- Footer ------------------------------------------------------------
    st.divider()
    st.markdown(
        "<p style='text-align:center; color:#64748b; font-size:0.85rem;'>"
        "SentinelOps © 2026 — MLOps Experiment Dashboard"
        "</p>",
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
