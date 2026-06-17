"""
SentinelOps — YOLO Dataset Validator
=====================================
Production-grade validation script for YOLO-format object detection datasets.

Validates directory structure, annotation integrity, class distributions,
and generates both a rich console report and a JSON artifact.

Usage:
    python -m src.data.validate_dataset /path/to/dataset --classes reflective_jacket safety_helmet
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from tqdm import tqdm

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("sentinelops.validate_dataset")

console = Console()

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SUPPORTED_IMAGE_EXTENSIONS: set[str] = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
SPLITS: list[str] = ["train", "valid", "test"]


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------
@dataclass
class AnnotationError:
    """Represents a single annotation-level issue."""

    file: str
    line: int
    message: str


@dataclass
class SplitReport:
    """Aggregated validation results for one data split."""

    name: str
    exists: bool = False
    images_dir_exists: bool = False
    labels_dir_exists: bool = False
    image_count: int = 0
    label_count: int = 0
    missing_labels: list[str] = field(default_factory=list)
    orphan_labels: list[str] = field(default_factory=list)
    empty_labels: list[str] = field(default_factory=list)
    annotation_errors: list[AnnotationError] = field(default_factory=list)
    class_distribution: dict[int, int] = field(default_factory=dict)

    # -- derived --
    @property
    def has_issues(self) -> bool:
        return bool(
            self.missing_labels
            or self.orphan_labels
            or self.empty_labels
            or self.annotation_errors
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "exists": self.exists,
            "images_dir_exists": self.images_dir_exists,
            "labels_dir_exists": self.labels_dir_exists,
            "image_count": self.image_count,
            "label_count": self.label_count,
            "missing_labels_count": len(self.missing_labels),
            "missing_labels": self.missing_labels,
            "orphan_labels_count": len(self.orphan_labels),
            "orphan_labels": self.orphan_labels,
            "empty_labels_count": len(self.empty_labels),
            "empty_labels": self.empty_labels,
            "annotation_errors_count": len(self.annotation_errors),
            "annotation_errors": [
                {"file": e.file, "line": e.line, "message": e.message}
                for e in self.annotation_errors
            ],
            "class_distribution": {
                str(k): v for k, v in sorted(self.class_distribution.items())
            },
        }


@dataclass
class DatasetReport:
    """Full dataset validation report."""

    dataset_path: str
    timestamp: str
    class_names: list[str]
    splits: list[SplitReport] = field(default_factory=list)

    @property
    def total_images(self) -> int:
        return sum(s.image_count for s in self.splits)

    @property
    def total_labels(self) -> int:
        return sum(s.label_count for s in self.splits)

    @property
    def total_annotation_errors(self) -> int:
        return sum(len(s.annotation_errors) for s in self.splits)

    @property
    def is_healthy(self) -> bool:
        return all(not s.has_issues for s in self.splits)

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset_path": self.dataset_path,
            "timestamp": self.timestamp,
            "class_names": self.class_names,
            "total_images": self.total_images,
            "total_labels": self.total_labels,
            "total_annotation_errors": self.total_annotation_errors,
            "is_healthy": self.is_healthy,
            "splits": [s.to_dict() for s in self.splits],
        }


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------
def _collect_stems(directory: Path, extensions: set[str]) -> set[str]:
    """Return the set of file stems matching the given extensions."""
    return {
        f.stem
        for f in directory.iterdir()
        if f.is_file() and f.suffix.lower() in extensions
    }


def _validate_annotation_line(
    line: str,
    line_no: int,
    num_classes: int,
) -> AnnotationError | None:
    """Validate a single YOLO annotation line.

    Expected format: ``<class_id> <x_center> <y_center> <width> <height>``
    All values normalised to [0, 1] except class_id (integer).
    """
    parts = line.strip().split()

    if len(parts) < 5:
        return AnnotationError(
            file="",
            line=line_no,
            message=f"Expected 5+ fields, got {len(parts)}: '{line.strip()}'",
        )

    # Class ID
    try:
        class_id = int(parts[0])
    except ValueError:
        return AnnotationError(
            file="",
            line=line_no,
            message=f"Non-integer class id: '{parts[0]}'",
        )

    if class_id < 0 or class_id >= num_classes:
        return AnnotationError(
            file="",
            line=line_no,
            message=f"Class id {class_id} out of range [0, {num_classes - 1}]",
        )

    # Bounding-box values
    for i, name in enumerate(
        ["x_center", "y_center", "width", "height"], start=1
    ):
        try:
            val = float(parts[i])
        except ValueError:
            return AnnotationError(
                file="",
                line=line_no,
                message=f"Non-numeric {name}: '{parts[i]}'",
            )
        if val < 0.0 or val > 1.0:
            return AnnotationError(
                file="",
                line=line_no,
                message=f"{name}={val:.4f} outside [0, 1]",
            )

    return None


# ---------------------------------------------------------------------------
# Core validation
# ---------------------------------------------------------------------------
def validate_split(
    dataset_root: Path,
    split_name: str,
    num_classes: int,
) -> SplitReport:
    """Run all validations on a single data split."""
    report = SplitReport(name=split_name)
    split_dir = dataset_root / split_name

    if not split_dir.is_dir():
        logger.warning("Split directory not found: %s", split_dir)
        return report

    report.exists = True

    images_dir = split_dir / "images"
    labels_dir = split_dir / "labels"

    report.images_dir_exists = images_dir.is_dir()
    report.labels_dir_exists = labels_dir.is_dir()

    if not report.images_dir_exists:
        logger.warning("Images directory missing: %s", images_dir)
    if not report.labels_dir_exists:
        logger.warning("Labels directory missing: %s", labels_dir)

    # -- Counts & stem sets ------------------------------------------------
    image_stems: set[str] = set()
    label_stems: set[str] = set()

    if report.images_dir_exists:
        image_stems = _collect_stems(images_dir, SUPPORTED_IMAGE_EXTENSIONS)
        report.image_count = len(image_stems)

    if report.labels_dir_exists:
        label_stems = _collect_stems(labels_dir, {".txt"})
        report.label_count = len(label_stems)

    # -- Missing / orphan labels -------------------------------------------
    report.missing_labels = sorted(image_stems - label_stems)
    report.orphan_labels = sorted(label_stems - image_stems)

    if report.missing_labels:
        logger.warning(
            "[%s] %d images without labels", split_name, len(report.missing_labels)
        )
    if report.orphan_labels:
        logger.warning(
            "[%s] %d orphan labels without images",
            split_name,
            len(report.orphan_labels),
        )

    # -- Annotation validation ---------------------------------------------
    if not report.labels_dir_exists:
        return report

    class_counter: Counter[int] = Counter()
    label_files = sorted(labels_dir.glob("*.txt"))

    for label_file in tqdm(
        label_files,
        desc=f"  Validating {split_name}/labels",
        unit="file",
        leave=False,
    ):
        lines = label_file.read_text(encoding="utf-8").splitlines()

        # Empty file check
        non_blank = [ln for ln in lines if ln.strip()]
        if not non_blank:
            report.empty_labels.append(label_file.name)
            continue

        for line_no, line in enumerate(lines, start=1):
            if not line.strip():
                continue

            err = _validate_annotation_line(line, line_no, num_classes)
            if err:
                err.file = label_file.name
                report.annotation_errors.append(err)
            else:
                class_id = int(line.strip().split()[0])
                class_counter[class_id] += 1

    report.class_distribution = dict(class_counter)
    return report


def validate_dataset(
    dataset_root: Path,
    class_names: list[str],
) -> DatasetReport:
    """Validate an entire YOLO dataset across all splits."""
    logger.info("Validating dataset at: %s", dataset_root)
    num_classes = len(class_names)

    report = DatasetReport(
        dataset_path=str(dataset_root.resolve()),
        timestamp=datetime.now(timezone.utc).isoformat(),
        class_names=class_names,
    )

    for split in SPLITS:
        split_report = validate_split(dataset_root, split, num_classes)
        report.splits.append(split_report)

    return report


# ---------------------------------------------------------------------------
# Pretty console output
# ---------------------------------------------------------------------------
def print_report(report: DatasetReport) -> None:
    """Render a rich console report."""
    console.print()
    console.rule("[bold cyan]SentinelOps — Dataset Validation Report[/bold cyan]")
    console.print(f"  [dim]Path:[/dim]      {report.dataset_path}")
    console.print(f"  [dim]Timestamp:[/dim] {report.timestamp}")
    console.print(f"  [dim]Classes:[/dim]   {', '.join(report.class_names)}")
    console.print()

    # ── Per-split tables ──────────────────────────────────────────────────
    overview = Table(
        title="Split Overview",
        show_header=True,
        header_style="bold magenta",
        border_style="dim",
    )
    overview.add_column("Split", style="cyan", min_width=8)
    overview.add_column("Exists", justify="center")
    overview.add_column("Images", justify="right")
    overview.add_column("Labels", justify="right")
    overview.add_column("Missing Labels", justify="right")
    overview.add_column("Orphan Labels", justify="right")
    overview.add_column("Empty Labels", justify="right")
    overview.add_column("Annotation Errors", justify="right")

    for s in report.splits:
        exists_icon = "✅" if s.exists else "❌"
        overview.add_row(
            s.name,
            exists_icon,
            str(s.image_count),
            str(s.label_count),
            _colored_count(len(s.missing_labels)),
            _colored_count(len(s.orphan_labels)),
            _colored_count(len(s.empty_labels)),
            _colored_count(len(s.annotation_errors)),
        )

    console.print(overview)
    console.print()

    # ── Class distribution ────────────────────────────────────────────────
    global_dist: Counter[int] = Counter()
    for s in report.splits:
        global_dist.update(s.class_distribution)

    if global_dist:
        dist_table = Table(
            title="Class Distribution (All Splits)",
            show_header=True,
            header_style="bold magenta",
            border_style="dim",
        )
        dist_table.add_column("Class ID", justify="center", style="cyan")
        dist_table.add_column("Class Name", style="white")
        dist_table.add_column("Instances", justify="right", style="green")

        for cls_id in sorted(global_dist):
            name = (
                report.class_names[cls_id]
                if cls_id < len(report.class_names)
                else f"unknown_{cls_id}"
            )
            dist_table.add_row(str(cls_id), name, f"{global_dist[cls_id]:,}")

        console.print(dist_table)
        console.print()

    # ── Per-split class breakdown ─────────────────────────────────────────
    for s in report.splits:
        if not s.class_distribution:
            continue
        split_dist = Table(
            title=f"Class Distribution — {s.name}",
            show_header=True,
            header_style="bold blue",
            border_style="dim",
        )
        split_dist.add_column("Class ID", justify="center", style="cyan")
        split_dist.add_column("Class Name", style="white")
        split_dist.add_column("Instances", justify="right", style="green")
        split_dist.add_column("Share (%)", justify="right", style="yellow")

        total = sum(s.class_distribution.values())
        for cls_id in sorted(s.class_distribution):
            name = (
                report.class_names[cls_id]
                if cls_id < len(report.class_names)
                else f"unknown_{cls_id}"
            )
            pct = (s.class_distribution[cls_id] / total) * 100 if total else 0
            split_dist.add_row(
                str(cls_id),
                name,
                f"{s.class_distribution[cls_id]:,}",
                f"{pct:.1f}",
            )

        console.print(split_dist)
        console.print()

    # ── Sample errors (first 10 per split) ────────────────────────────────
    for s in report.splits:
        if s.annotation_errors:
            err_table = Table(
                title=f"Annotation Errors — {s.name} (showing first 10)",
                show_header=True,
                header_style="bold red",
                border_style="dim",
            )
            err_table.add_column("File", style="cyan")
            err_table.add_column("Line", justify="right")
            err_table.add_column("Message", style="red")

            for err in s.annotation_errors[:10]:
                err_table.add_row(err.file, str(err.line), err.message)

            console.print(err_table)
            console.print()

    # ── Health verdict ────────────────────────────────────────────────────
    if report.is_healthy:
        console.print(
            Panel(
                Text("✅  Dataset is HEALTHY — no issues detected.", style="bold green"),
                border_style="green",
            )
        )
    else:
        console.print(
            Panel(
                Text("⚠️  Dataset has ISSUES — review the tables above.", style="bold yellow"),
                border_style="yellow",
            )
        )

    console.print()


def _colored_count(n: int) -> str:
    """Return a rich-styled string — green for 0, red otherwise."""
    return f"[green]{n}[/green]" if n == 0 else f"[red]{n}[/red]"


# ---------------------------------------------------------------------------
# JSON export
# ---------------------------------------------------------------------------
def save_json_report(report: DatasetReport, output_path: Path) -> None:
    """Persist the report as a JSON file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report.to_dict(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    logger.info("JSON report saved to: %s", output_path)


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------
def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="SentinelOps — YOLO Dataset Validator",
    )
    parser.add_argument(
        "dataset_root",
        type=Path,
        help="Path to the YOLO dataset root directory.",
    )
    parser.add_argument(
        "--classes",
        nargs="+",
        required=True,
        help="Ordered list of class names (e.g., --classes dog cat).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/dataset_report.json"),
        help="Path for the JSON report (default: artifacts/dataset_report.json).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)

    if not args.dataset_root.is_dir():
        logger.error("Dataset root does not exist: %s", args.dataset_root)
        sys.exit(1)

    report = validate_dataset(args.dataset_root, args.classes)
    print_report(report)
    save_json_report(report, args.output)


if __name__ == "__main__":
    main()
