"""
SentinelOps — Chart Builder
===============================
Renders analytics data into matplotlib chart images (PNG).

All methods accept analytics response models and return the ``Path``
to a saved PNG file.  Charts use a consistent dark theme with
SentinelOps-branded accent colours.

Usage::

    from app.services.chart_builder import ChartBuilder

    builder = ChartBuilder(output_dir=Path("/tmp/charts"))
    path    = builder.violations_per_day_chart(vpd_response)
"""

from __future__ import annotations

import logging
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # non-interactive backend — must be before pyplot
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

from app.models.analytics import (
    ComplianceRateResponse,
    HourlyTrendsResponse,
    TopViolationTypesResponse,
    ViolationsPerCameraResponse,
    ViolationsPerDayResponse,
)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logger = logging.getLogger("sentinelops.chart_builder")

# ---------------------------------------------------------------------------
# Theme constants
# ---------------------------------------------------------------------------
_BG_COLOR = "#1a1a2e"
_PANEL_COLOR = "#16213e"
_TEXT_COLOR = "#e0e0e0"
_ACCENT_COLORS = [
    "#0f9b8e",  # teal
    "#e94560",  # coral-red
    "#f5a623",  # amber
    "#5b86e5",  # blue
    "#9b59b6",  # purple
    "#1abc9c",  # mint
    "#e67e22",  # orange
    "#2ecc71",  # green
]
_GRID_COLOR = "#2a2a4a"


def _apply_theme(ax: plt.Axes, fig: plt.Figure) -> None:
    """Apply the SentinelOps dark theme to a figure/axes pair."""
    fig.patch.set_facecolor(_BG_COLOR)
    ax.set_facecolor(_PANEL_COLOR)
    ax.tick_params(colors=_TEXT_COLOR, labelsize=9)
    ax.xaxis.label.set_color(_TEXT_COLOR)
    ax.yaxis.label.set_color(_TEXT_COLOR)
    ax.title.set_color(_TEXT_COLOR)
    for spine in ax.spines.values():
        spine.set_color(_GRID_COLOR)
    ax.grid(True, color=_GRID_COLOR, alpha=0.3, linestyle="--")


class ChartBuilder:
    """Renders analytics data into PNG chart images.

    Parameters
    ----------
    output_dir : Path
        Directory where chart PNGs are saved.
    """

    def __init__(self, output_dir: Path) -> None:
        self._dir = output_dir
        self._dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Charts
    # ------------------------------------------------------------------
    def violations_per_day_chart(
        self, data: ViolationsPerDayResponse
    ) -> Path:
        """Vertical bar chart of violations per calendar day."""
        fig, ax = plt.subplots(figsize=(10, 5))
        _apply_theme(ax, fig)

        dates = [d.date for d in data.data]
        counts = [d.count for d in data.data]

        if dates:
            ax.bar(dates, counts, color=_ACCENT_COLORS[0], edgecolor="none", width=0.6)
            # Rotate labels if many dates
            if len(dates) > 7:
                plt.xticks(rotation=45, ha="right")
        else:
            ax.text(
                0.5, 0.5, "No data available",
                transform=ax.transAxes, ha="center", va="center",
                color=_TEXT_COLOR, fontsize=14,
            )

        ax.set_xlabel("Date")
        ax.set_ylabel("Violations")
        ax.set_title("Violations Per Day", fontsize=14, fontweight="bold")
        ax.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))

        path = self._dir / "violations_per_day.png"
        fig.tight_layout()
        fig.savefig(path, dpi=150, facecolor=fig.get_facecolor())
        plt.close(fig)
        logger.debug("Chart saved: %s", path)
        return path

    def violations_per_camera_chart(
        self, data: ViolationsPerCameraResponse
    ) -> Path:
        """Horizontal bar chart of violations per camera."""
        fig, ax = plt.subplots(figsize=(10, max(4, len(data.data) * 0.5 + 1)))
        _apply_theme(ax, fig)

        cameras = [d.camera_id for d in data.data]
        counts = [d.count for d in data.data]

        if cameras:
            # Reverse so highest is at top
            cameras = cameras[::-1]
            counts = counts[::-1]
            colors = [_ACCENT_COLORS[i % len(_ACCENT_COLORS)] for i in range(len(cameras))]
            ax.barh(cameras, counts, color=colors, edgecolor="none", height=0.6)
        else:
            ax.text(
                0.5, 0.5, "No data available",
                transform=ax.transAxes, ha="center", va="center",
                color=_TEXT_COLOR, fontsize=14,
            )

        ax.set_xlabel("Violations")
        ax.set_ylabel("Camera")
        ax.set_title("Violations Per Camera", fontsize=14, fontweight="bold")
        ax.xaxis.set_major_locator(ticker.MaxNLocator(integer=True))

        path = self._dir / "violations_per_camera.png"
        fig.tight_layout()
        fig.savefig(path, dpi=150, facecolor=fig.get_facecolor())
        plt.close(fig)
        logger.debug("Chart saved: %s", path)
        return path

    def compliance_pie_chart(self, data: ComplianceRateResponse) -> Path:
        """Pie chart of compliant vs non-compliant."""
        fig, ax = plt.subplots(figsize=(7, 7))
        fig.patch.set_facecolor(_BG_COLOR)

        if data.total_checks == 0:
            ax.set_facecolor(_PANEL_COLOR)
            ax.text(
                0.5, 0.5, "No data available",
                transform=ax.transAxes, ha="center", va="center",
                color=_TEXT_COLOR, fontsize=14,
            )
            ax.set_xlim(0, 1)
            ax.set_ylim(0, 1)
            ax.axis("off")
        else:
            sizes = [data.compliant, data.non_compliant]
            labels = [
                f"Compliant\n({data.compliant})",
                f"Non-Compliant\n({data.non_compliant})",
            ]
            colors = [_ACCENT_COLORS[0], _ACCENT_COLORS[1]]
            explode = (0.03, 0.03)

            wedges, texts, autotexts = ax.pie(
                sizes,
                labels=labels,
                colors=colors,
                autopct="%1.1f%%",
                startangle=90,
                explode=explode,
                textprops={"color": _TEXT_COLOR, "fontsize": 11},
            )
            for t in autotexts:
                t.set_fontweight("bold")

        ax.set_title(
            "PPE Compliance Rate", fontsize=14, fontweight="bold", color=_TEXT_COLOR
        )

        path = self._dir / "compliance_rate.png"
        fig.tight_layout()
        fig.savefig(path, dpi=150, facecolor=fig.get_facecolor())
        plt.close(fig)
        logger.debug("Chart saved: %s", path)
        return path

    def hourly_trends_chart(self, data: HourlyTrendsResponse) -> Path:
        """Line chart of violations by hour of day."""
        fig, ax = plt.subplots(figsize=(10, 5))
        _apply_theme(ax, fig)

        hours = [d.hour for d in data.data]
        counts = [d.count for d in data.data]

        ax.plot(
            hours, counts,
            color=_ACCENT_COLORS[3],
            linewidth=2,
            marker="o",
            markersize=5,
            markerfacecolor=_ACCENT_COLORS[1],
            markeredgecolor=_ACCENT_COLORS[1],
        )
        ax.fill_between(hours, counts, alpha=0.15, color=_ACCENT_COLORS[3])

        ax.set_xlabel("Hour of Day")
        ax.set_ylabel("Violations")
        ax.set_title("Hourly Violation Trends", fontsize=14, fontweight="bold")
        ax.set_xticks(range(0, 24))
        ax.set_xlim(-0.5, 23.5)
        ax.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))

        path = self._dir / "hourly_trends.png"
        fig.tight_layout()
        fig.savefig(path, dpi=150, facecolor=fig.get_facecolor())
        plt.close(fig)
        logger.debug("Chart saved: %s", path)
        return path

    def top_violations_chart(
        self, data: TopViolationTypesResponse
    ) -> Path:
        """Horizontal bar chart of the most frequent violation types."""
        fig, ax = plt.subplots(figsize=(10, max(4, len(data.data) * 0.6 + 1)))
        _apply_theme(ax, fig)

        types = [d.violation_type for d in data.data]
        counts = [d.count for d in data.data]

        if types:
            types = types[::-1]
            counts = counts[::-1]
            colors = [_ACCENT_COLORS[i % len(_ACCENT_COLORS)] for i in range(len(types))]
            ax.barh(types, counts, color=colors, edgecolor="none", height=0.6)
        else:
            ax.text(
                0.5, 0.5, "No data available",
                transform=ax.transAxes, ha="center", va="center",
                color=_TEXT_COLOR, fontsize=14,
            )

        ax.set_xlabel("Count")
        ax.set_ylabel("Violation Type")
        ax.set_title("Top Violation Types", fontsize=14, fontweight="bold")
        ax.xaxis.set_major_locator(ticker.MaxNLocator(integer=True))

        path = self._dir / "top_violations.png"
        fig.tight_layout()
        fig.savefig(path, dpi=150, facecolor=fig.get_facecolor())
        plt.close(fig)
        logger.debug("Chart saved: %s", path)
        return path
