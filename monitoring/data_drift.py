"""
SentinelOps — Computer Vision Data Drift Monitor
===================================================
Compares a *reference* YOLO dataset against a *current* dataset and
produces drift scores across five dimensions:

1. **Image dimensions** — width/height distribution shift
2. **Class distribution** — label frequency divergence
3. **Bounding-box count** — objects-per-image distribution shift
4. **Bounding-box size** — normalised area distribution shift
5. **Aspect ratios** — bbox width/height ratio distribution shift

Each dimension yields a drift score in [0, 1].  The overall drift
score is the weighted mean.  A score > 0.3 is flagged as significant.

Usage (CLI)::

    python -m monitoring.data_drift \\
        --reference data/train \\
        --current   data/new_batch \\
        --classes reflective_jacket safety_helmet \\
        --output artifacts/drift_report.json \\
        --charts artifacts/drift_charts

Usage (library)::

    from monitoring.data_drift import DriftMonitor
    monitor = DriftMonitor(class_names=["reflective_jacket", "safety_helmet"])
    report  = monitor.compare("data/train", "data/new_batch")
    monitor.save_report(report, "artifacts/drift_report.json")
    monitor.save_charts(report, "artifacts/drift_charts")
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

matplotlib.use("Agg")  # headless backend for CI / server environments

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("sentinelops.data_drift")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SUPPORTED_IMAGE_EXTENSIONS: set[str] = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
DRIFT_THRESHOLD: float = 0.3  # above this → significant drift

DIMENSION_WEIGHTS: dict[str, float] = {
    "image_dimensions": 0.15,
    "class_distribution": 0.30,
    "bbox_count": 0.20,
    "bbox_size": 0.20,
    "aspect_ratio": 0.15,
}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------
@dataclass
class DimensionDrift:
    """Drift result for a single comparison dimension."""

    name: str
    score: float
    statistic: float
    p_value: float
    method: str
    is_drifted: bool
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DatasetStats:
    """Extracted statistics from a single dataset split."""

    path: str
    image_count: int
    label_count: int
    image_widths: list[int]
    image_heights: list[int]
    class_counts: dict[int, int]
    bbox_counts_per_image: list[int]
    bbox_areas: list[float]
    bbox_aspect_ratios: list[float]

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "image_count": self.image_count,
            "label_count": self.label_count,
            "mean_width": float(np.mean(self.image_widths)) if self.image_widths else 0,
            "mean_height": float(np.mean(self.image_heights)) if self.image_heights else 0,
            "class_counts": {str(k): v for k, v in sorted(self.class_counts.items())},
            "mean_bbox_per_image": float(np.mean(self.bbox_counts_per_image)) if self.bbox_counts_per_image else 0,
            "mean_bbox_area": float(np.mean(self.bbox_areas)) if self.bbox_areas else 0,
            "mean_aspect_ratio": float(np.mean(self.bbox_aspect_ratios)) if self.bbox_aspect_ratios else 0,
        }


@dataclass
class DriftReport:
    """Complete drift comparison report."""

    timestamp: str
    reference_path: str
    current_path: str
    class_names: list[str]
    overall_score: float
    is_drifted: bool
    reference_stats: DatasetStats
    current_stats: DatasetStats
    dimensions: list[DimensionDrift]

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "reference_path": self.reference_path,
            "current_path": self.current_path,
            "class_names": self.class_names,
            "overall_drift_score": round(self.overall_score, 4),
            "is_drifted": self.is_drifted,
            "drift_threshold": DRIFT_THRESHOLD,
            "reference_stats": self.reference_stats.to_dict(),
            "current_stats": self.current_stats.to_dict(),
            "dimensions": [d.to_dict() for d in self.dimensions],
        }


# ---------------------------------------------------------------------------
# Dataset statistics extraction
# ---------------------------------------------------------------------------
def _get_image_dimensions(image_path: Path) -> tuple[int, int]:
    """Read image dimensions without loading full pixel data.

    Falls back to a fixed default if the image cannot be read.
    """
    try:
        from PIL import Image

        with Image.open(image_path) as img:
            return img.size  # (width, height)
    except Exception:
        logger.debug("Could not read dimensions for %s", image_path)
        return (0, 0)


def _parse_label_file(label_path: Path) -> list[list[float]]:
    """Parse a YOLO label file into a list of [class_id, xc, yc, w, h]."""
    annotations: list[list[float]] = []
    try:
        for line in label_path.read_text(encoding="utf-8").splitlines():
            parts = line.strip().split()
            if len(parts) >= 5:
                annotations.append([float(p) for p in parts[:5]])
    except Exception:
        logger.debug("Could not parse label file %s", label_path)
    return annotations


def extract_dataset_stats(
    dataset_dir: Path,
    num_classes: int,
) -> DatasetStats:
    """Walk a YOLO split directory and compute statistics.

    Expects ``dataset_dir/images/`` and ``dataset_dir/labels/``.
    """
    images_dir = dataset_dir / "images"
    labels_dir = dataset_dir / "labels"

    if not images_dir.is_dir():
        logger.warning("Images directory not found: %s", images_dir)
    if not labels_dir.is_dir():
        logger.warning("Labels directory not found: %s", labels_dir)

    # -- Gather image paths ------------------------------------------------
    image_files = sorted(
        f
        for f in (images_dir.iterdir() if images_dir.is_dir() else [])
        if f.is_file() and f.suffix.lower() in SUPPORTED_IMAGE_EXTENSIONS
    )

    widths: list[int] = []
    heights: list[int] = []
    for img in image_files:
        w, h = _get_image_dimensions(img)
        if w > 0 and h > 0:
            widths.append(w)
            heights.append(h)

    # -- Gather label data -------------------------------------------------
    label_files = sorted(
        f
        for f in (labels_dir.iterdir() if labels_dir.is_dir() else [])
        if f.is_file() and f.suffix == ".txt"
    )

    class_counts: dict[int, int] = {i: 0 for i in range(num_classes)}
    bbox_counts: list[int] = []
    bbox_areas: list[float] = []
    bbox_aspect_ratios: list[float] = []

    for lf in label_files:
        annotations = _parse_label_file(lf)
        bbox_counts.append(len(annotations))

        for ann in annotations:
            cls_id, _, _, bw, bh = int(ann[0]), ann[1], ann[2], ann[3], ann[4]
            if cls_id in class_counts:
                class_counts[cls_id] += 1

            area = bw * bh
            bbox_areas.append(area)

            ar = bw / bh if bh > 0 else 0.0
            bbox_aspect_ratios.append(ar)

    return DatasetStats(
        path=str(dataset_dir),
        image_count=len(image_files),
        label_count=len(label_files),
        image_widths=widths,
        image_heights=heights,
        class_counts=class_counts,
        bbox_counts_per_image=bbox_counts,
        bbox_areas=bbox_areas,
        bbox_aspect_ratios=bbox_aspect_ratios,
    )


# ---------------------------------------------------------------------------
# Statistical tests
# ---------------------------------------------------------------------------
def _ks_drift_score(
    ref: list[float] | np.ndarray,
    cur: list[float] | np.ndarray,
    name: str,
) -> DimensionDrift:
    """Kolmogorov–Smirnov two-sample test → drift score."""
    ref_arr = np.asarray(ref, dtype=np.float64)
    cur_arr = np.asarray(cur, dtype=np.float64)

    if len(ref_arr) < 2 or len(cur_arr) < 2:
        return DimensionDrift(
            name=name,
            score=0.0,
            statistic=0.0,
            p_value=1.0,
            method="ks_2samp",
            is_drifted=False,
            details={"warning": "Insufficient data for KS test."},
        )

    stat, p_value = stats.ks_2samp(ref_arr, cur_arr)
    score = float(stat)  # KS statistic is already in [0, 1]

    return DimensionDrift(
        name=name,
        score=round(score, 4),
        statistic=round(float(stat), 4),
        p_value=round(float(p_value), 6),
        method="ks_2samp",
        is_drifted=score > DRIFT_THRESHOLD,
    )


def _jensen_shannon_divergence(
    ref_counts: dict[int, int],
    cur_counts: dict[int, int],
    num_classes: int,
) -> DimensionDrift:
    """Jensen–Shannon divergence for class distributions → drift score."""
    ref_arr = np.array(
        [ref_counts.get(i, 0) for i in range(num_classes)], dtype=np.float64
    )
    cur_arr = np.array(
        [cur_counts.get(i, 0) for i in range(num_classes)], dtype=np.float64
    )

    # Normalise to probability distributions (add smoothing)
    ref_prob = (ref_arr + 1e-10) / (ref_arr.sum() + num_classes * 1e-10)
    cur_prob = (cur_arr + 1e-10) / (cur_arr.sum() + num_classes * 1e-10)

    jsd = float(
        np.sqrt(
            stats.entropy(ref_prob, 0.5 * (ref_prob + cur_prob))
            + stats.entropy(cur_prob, 0.5 * (ref_prob + cur_prob))
        )
        / np.sqrt(2)
    )  # normalise to [0, 1]

    return DimensionDrift(
        name="class_distribution",
        score=round(jsd, 4),
        statistic=round(jsd, 4),
        p_value=0.0,  # JSD is not a hypothesis test
        method="jensen_shannon_divergence",
        is_drifted=jsd > DRIFT_THRESHOLD,
        details={
            "reference_distribution": {str(k): int(v) for k, v in sorted(ref_counts.items())},
            "current_distribution": {str(k): int(v) for k, v in sorted(cur_counts.items())},
        },
    )


# ---------------------------------------------------------------------------
# Core monitor
# ---------------------------------------------------------------------------
class DriftMonitor:
    """Compares a reference and current YOLO dataset for data drift.

    Parameters
    ----------
    class_names : list[str]
        Ordered class names matching YOLO class IDs.
    """

    def __init__(self, class_names: list[str]) -> None:
        self.class_names = class_names
        self.num_classes = len(class_names)

    # -- Public API --------------------------------------------------------

    def compare(
        self,
        reference_dir: str | Path,
        current_dir: str | Path,
    ) -> DriftReport:
        """Run all drift checks and return a full report."""
        ref_path = Path(reference_dir)
        cur_path = Path(current_dir)

        logger.info("Extracting reference stats from %s …", ref_path)
        ref_stats = extract_dataset_stats(ref_path, self.num_classes)

        logger.info("Extracting current stats from %s …", cur_path)
        cur_stats = extract_dataset_stats(cur_path, self.num_classes)

        dimensions: list[DimensionDrift] = []

        # 1. Image dimensions (combined width + height)
        ref_dims = [float(w) for w in ref_stats.image_widths] + [
            float(h) for h in ref_stats.image_heights
        ]
        cur_dims = [float(w) for w in cur_stats.image_widths] + [
            float(h) for h in cur_stats.image_heights
        ]
        dimensions.append(_ks_drift_score(ref_dims, cur_dims, "image_dimensions"))

        # 2. Class distribution (JSD)
        dimensions.append(
            _jensen_shannon_divergence(
                ref_stats.class_counts, cur_stats.class_counts, self.num_classes
            )
        )

        # 3. Bounding-box count per image
        dimensions.append(
            _ks_drift_score(
                [float(c) for c in ref_stats.bbox_counts_per_image],
                [float(c) for c in cur_stats.bbox_counts_per_image],
                "bbox_count",
            )
        )

        # 4. Bounding-box size (normalised area)
        dimensions.append(
            _ks_drift_score(ref_stats.bbox_areas, cur_stats.bbox_areas, "bbox_size")
        )

        # 5. Aspect ratios
        dimensions.append(
            _ks_drift_score(
                ref_stats.bbox_aspect_ratios,
                cur_stats.bbox_aspect_ratios,
                "aspect_ratio",
            )
        )

        # -- Overall drift score -------------------------------------------
        overall = sum(
            DIMENSION_WEIGHTS.get(d.name, 0.2) * d.score for d in dimensions
        )

        report = DriftReport(
            timestamp=datetime.now(timezone.utc).isoformat(),
            reference_path=str(ref_path.resolve()),
            current_path=str(cur_path.resolve()),
            class_names=self.class_names,
            overall_score=round(overall, 4),
            is_drifted=overall > DRIFT_THRESHOLD,
            reference_stats=ref_stats,
            current_stats=cur_stats,
            dimensions=dimensions,
        )

        logger.info(
            "Overall drift score: %.4f (%s)",
            overall,
            "DRIFTED" if report.is_drifted else "OK",
        )
        return report

    # -- Persistence -------------------------------------------------------

    @staticmethod
    def save_report(report: DriftReport, output_path: str | Path) -> None:
        """Write the drift report as JSON."""
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(report.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        logger.info("Drift report saved → %s", path)

    # -- Visualisation -----------------------------------------------------

    @staticmethod
    def save_charts(report: DriftReport, output_dir: str | Path) -> None:
        """Generate and save matplotlib charts for each drift dimension."""
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)

        _chart_dimension_scores(report, out)
        _chart_class_distribution(report, out)
        _chart_bbox_count(report, out)
        _chart_bbox_size(report, out)
        _chart_aspect_ratio(report, out)
        _chart_image_dimensions(report, out)

        logger.info("Drift charts saved → %s/", out)


# ---------------------------------------------------------------------------
# Chart helpers
# ---------------------------------------------------------------------------
_FIG_STYLE: dict[str, Any] = {
    "figure.facecolor": "#0f172a",
    "axes.facecolor": "#1e293b",
    "axes.edgecolor": "#334155",
    "axes.labelcolor": "#e2e8f0",
    "text.color": "#e2e8f0",
    "xtick.color": "#94a3b8",
    "ytick.color": "#94a3b8",
    "grid.color": "#334155",
    "grid.alpha": 0.5,
}


def _apply_style() -> None:
    plt.rcParams.update(_FIG_STYLE)
    plt.rcParams["font.family"] = "sans-serif"


def _chart_dimension_scores(report: DriftReport, out: Path) -> None:
    """Horizontal bar chart of per-dimension drift scores."""
    _apply_style()
    names = [d.name.replace("_", " ").title() for d in report.dimensions]
    scores = [d.score for d in report.dimensions]
    colors = ["#f43f5e" if s > DRIFT_THRESHOLD else "#10b981" for s in scores]

    fig, ax = plt.subplots(figsize=(10, 5))
    bars = ax.barh(names, scores, color=colors, height=0.5, edgecolor="none")
    ax.axvline(DRIFT_THRESHOLD, color="#f59e0b", linestyle="--", linewidth=1.5, label=f"Threshold ({DRIFT_THRESHOLD})")
    ax.set_xlim(0, 1)
    ax.set_xlabel("Drift Score")
    ax.set_title(f"Data Drift Summary  —  Overall: {report.overall_score:.4f}", fontsize=14, fontweight="bold")
    ax.legend(loc="lower right")

    for bar, score in zip(bars, scores):
        ax.text(bar.get_width() + 0.02, bar.get_y() + bar.get_height() / 2, f"{score:.3f}", va="center", fontsize=10)

    plt.tight_layout()
    fig.savefig(out / "drift_summary.png", dpi=150)
    plt.close(fig)


def _chart_class_distribution(report: DriftReport, out: Path) -> None:
    """Grouped bar chart comparing class distributions."""
    _apply_style()
    ref = report.reference_stats.class_counts
    cur = report.current_stats.class_counts

    classes = sorted(set(ref.keys()) | set(cur.keys()))
    labels = [
        report.class_names[c] if c < len(report.class_names) else f"class_{c}"
        for c in classes
    ]
    ref_vals = [ref.get(c, 0) for c in classes]
    cur_vals = [cur.get(c, 0) for c in classes]

    # Normalise to percentages
    ref_total = sum(ref_vals) or 1
    cur_total = sum(cur_vals) or 1
    ref_pct = [v / ref_total * 100 for v in ref_vals]
    cur_pct = [v / cur_total * 100 for v in cur_vals]

    x = np.arange(len(labels))
    width = 0.35

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(x - width / 2, ref_pct, width, label="Reference", color="#6366f1")
    ax.bar(x + width / 2, cur_pct, width, label="Current", color="#f43f5e")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=30, ha="right")
    ax.set_ylabel("Share (%)")
    ax.set_title("Class Distribution Comparison", fontsize=14, fontweight="bold")
    ax.legend()
    ax.grid(axis="y")

    plt.tight_layout()
    fig.savefig(out / "class_distribution.png", dpi=150)
    plt.close(fig)


def _chart_bbox_count(report: DriftReport, out: Path) -> None:
    """Histogram of bounding boxes per image."""
    _apply_style()
    ref = report.reference_stats.bbox_counts_per_image
    cur = report.current_stats.bbox_counts_per_image

    fig, ax = plt.subplots(figsize=(10, 5))
    bins = np.arange(0, max(max(ref, default=0), max(cur, default=0)) + 2) - 0.5
    ax.hist(ref, bins=bins, alpha=0.6, label="Reference", color="#6366f1", density=True)
    ax.hist(cur, bins=bins, alpha=0.6, label="Current", color="#f43f5e", density=True)
    ax.set_xlabel("Bounding Boxes per Image")
    ax.set_ylabel("Density")
    ax.set_title("BBox Count Distribution", fontsize=14, fontweight="bold")
    ax.legend()
    ax.grid(axis="y")

    plt.tight_layout()
    fig.savefig(out / "bbox_count.png", dpi=150)
    plt.close(fig)


def _chart_bbox_size(report: DriftReport, out: Path) -> None:
    """KDE plot of normalised bbox areas."""
    _apply_style()
    ref = np.asarray(report.reference_stats.bbox_areas)
    cur = np.asarray(report.current_stats.bbox_areas)

    fig, ax = plt.subplots(figsize=(10, 5))

    if len(ref) > 1:
        ref_kde = stats.gaussian_kde(ref)
        xs = np.linspace(0, max(ref.max(), cur.max() if len(cur) else ref.max()) * 1.1, 300)
        ax.fill_between(xs, ref_kde(xs), alpha=0.4, color="#6366f1", label="Reference")
        ax.plot(xs, ref_kde(xs), color="#6366f1", linewidth=2)

    if len(cur) > 1:
        cur_kde = stats.gaussian_kde(cur)
        xs = np.linspace(0, max(ref.max() if len(ref) else cur.max(), cur.max()) * 1.1, 300)
        ax.fill_between(xs, cur_kde(xs), alpha=0.4, color="#f43f5e", label="Current")
        ax.plot(xs, cur_kde(xs), color="#f43f5e", linewidth=2)

    ax.set_xlabel("Normalised BBox Area (w × h)")
    ax.set_ylabel("Density")
    ax.set_title("BBox Size Distribution", fontsize=14, fontweight="bold")
    ax.legend()
    ax.grid(axis="y")

    plt.tight_layout()
    fig.savefig(out / "bbox_size.png", dpi=150)
    plt.close(fig)


def _chart_aspect_ratio(report: DriftReport, out: Path) -> None:
    """Histogram of bbox aspect ratios."""
    _apply_style()
    ref = np.asarray(report.reference_stats.bbox_aspect_ratios)
    cur = np.asarray(report.current_stats.bbox_aspect_ratios)

    fig, ax = plt.subplots(figsize=(10, 5))
    bins = np.linspace(0, max(ref.max() if len(ref) else 3, cur.max() if len(cur) else 3) * 1.1, 40)
    ax.hist(ref, bins=bins, alpha=0.6, label="Reference", color="#6366f1", density=True)
    ax.hist(cur, bins=bins, alpha=0.6, label="Current", color="#f43f5e", density=True)
    ax.set_xlabel("Aspect Ratio (w / h)")
    ax.set_ylabel("Density")
    ax.set_title("BBox Aspect Ratio Distribution", fontsize=14, fontweight="bold")
    ax.legend()
    ax.grid(axis="y")

    plt.tight_layout()
    fig.savefig(out / "aspect_ratio.png", dpi=150)
    plt.close(fig)


def _chart_image_dimensions(report: DriftReport, out: Path) -> None:
    """Scatter plot of image widths vs heights."""
    _apply_style()
    fig, ax = plt.subplots(figsize=(8, 8))

    if report.reference_stats.image_widths:
        ax.scatter(
            report.reference_stats.image_widths,
            report.reference_stats.image_heights,
            alpha=0.4,
            s=20,
            color="#6366f1",
            label="Reference",
        )
    if report.current_stats.image_widths:
        ax.scatter(
            report.current_stats.image_widths,
            report.current_stats.image_heights,
            alpha=0.4,
            s=20,
            color="#f43f5e",
            label="Current",
        )

    ax.set_xlabel("Width (px)")
    ax.set_ylabel("Height (px)")
    ax.set_title("Image Dimensions", fontsize=14, fontweight="bold")
    ax.legend()
    ax.set_aspect("equal", adjustable="datalim")
    ax.grid(True)

    plt.tight_layout()
    fig.savefig(out / "image_dimensions.png", dpi=150)
    plt.close(fig)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="data_drift",
        description="SentinelOps — Computer Vision Data Drift Monitor",
    )
    parser.add_argument(
        "--reference",
        type=Path,
        required=True,
        help="Path to the reference dataset split (e.g. data/train).",
    )
    parser.add_argument(
        "--current",
        type=Path,
        required=True,
        help="Path to the current / new dataset split.",
    )
    parser.add_argument(
        "--classes",
        nargs="+",
        required=True,
        help="Ordered class names matching YOLO class IDs.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/drift_report.json"),
        help="JSON report output path.",
    )
    parser.add_argument(
        "--charts",
        type=Path,
        default=None,
        help="Directory to save chart images (optional).",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    args = _build_parser().parse_args(argv)

    for p, label in [(args.reference, "Reference"), (args.current, "Current")]:
        if not p.is_dir():
            logger.error("%s directory does not exist: %s", label, p)
            sys.exit(1)

    monitor = DriftMonitor(class_names=args.classes)
    report = monitor.compare(args.reference, args.current)
    monitor.save_report(report, args.output)

    if args.charts:
        monitor.save_charts(report, args.charts)

    # -- Console summary ---------------------------------------------------
    print(f"\n{'=' * 60}")
    print(f"  SentinelOps — Data Drift Report")
    print(f"{'=' * 60}")
    print(f"  Reference : {report.reference_path}")
    print(f"  Current   : {report.current_path}")
    print(f"  Timestamp : {report.timestamp}")
    print()

    for d in report.dimensions:
        icon = "🔴" if d.is_drifted else "🟢"
        print(f"  {icon}  {d.name:<22s}  score={d.score:.4f}  ({d.method})")

    print()
    verdict_icon = "🔴 DRIFT DETECTED" if report.is_drifted else "🟢 NO SIGNIFICANT DRIFT"
    print(f"  Overall Score : {report.overall_score:.4f}")
    print(f"  Verdict       : {verdict_icon}")
    print(f"{'=' * 60}\n")


if __name__ == "__main__":
    main()
