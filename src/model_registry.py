"""
SentinelOps — Model Registry
==============================
Production-grade local model registry for versioning, promoting,
and rolling back YOLO object-detection models.

Registry layout::

    artifacts/model_registry/
    ├── registry.json          # master index of all model versions
    ├── production.json        # pointer to the current production model
    └── models/
        ├── sentinelops-v1/
        │   └── metadata.json
        ├── sentinelops-v2/
        │   └── metadata.json
        └── ...

Usage (library)::

    from src.model_registry import ModelRegistry

    registry = ModelRegistry()
    registry.register(name="sentinelops", version="v3", mAP50=0.91, ...)
    best = registry.get_best_model("sentinelops", metric="mAP50-95")
    registry.promote_to_production("sentinelops", "v3")

Usage (CLI)::

    python -m src.model_registry register --name sentinelops --version v1 ...
    python -m src.model_registry list --name sentinelops
    python -m src.model_registry best --name sentinelops --metric mAP50-95
    python -m src.model_registry promote --name sentinelops --version v2
    python -m src.model_registry rollback --name sentinelops
    python -m src.model_registry production --name sentinelops
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from copy import deepcopy
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("sentinelops.model_registry")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DEFAULT_REGISTRY_ROOT = Path("artifacts/model_registry")
REGISTRY_INDEX = "registry.json"
PRODUCTION_POINTER = "production.json"
MODELS_DIR = "models"

SORTABLE_METRICS: set[str] = {
    "mAP50",
    "mAP50_95",
    "precision",
    "recall",
    "training_time_sec",
}


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------
@dataclass
class ModelVersion:
    """Immutable record of a single registered model version."""

    model_name: str
    version: str
    training_date: str
    dataset_version: str
    mAP50: float
    mAP50_95: float
    precision: float
    recall: float
    training_time_sec: float
    model_path: str
    registered_at: str = ""
    notes: str = ""
    tags: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.registered_at:
            self.registered_at = datetime.now(timezone.utc).isoformat()

    # -- Serialisation helpers ---------------------------------------------
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ModelVersion:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class ProductionPointer:
    """Tracks which model version is currently in production."""

    model_name: str
    version: str
    promoted_at: str
    previous_version: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ProductionPointer:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------
class RegistryError(Exception):
    """Base exception for registry operations."""


class ModelNotFoundError(RegistryError):
    """Raised when a requested model/version does not exist."""


class DuplicateVersionError(RegistryError):
    """Raised when attempting to register an already-existing version."""


class NoProductionModelError(RegistryError):
    """Raised when no production model has been promoted yet."""


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------
class ModelRegistry:
    """Local file-backed model registry.

    Parameters
    ----------
    root : Path
        Root directory for the registry (default: ``artifacts/model_registry``).
    """

    def __init__(self, root: Path = DEFAULT_REGISTRY_ROOT) -> None:
        self._root = root
        self._index_path = root / REGISTRY_INDEX
        self._production_path = root / PRODUCTION_POINTER
        self._models_dir = root / MODELS_DIR

        # Bootstrap the directory structure
        self._models_dir.mkdir(parents=True, exist_ok=True)

        # Load or create the master index
        self._index: dict[str, list[dict[str, Any]]] = self._load_index()

    # -- Persistence helpers -----------------------------------------------

    def _load_index(self) -> dict[str, list[dict[str, Any]]]:
        if self._index_path.exists():
            return json.loads(self._index_path.read_text(encoding="utf-8"))
        return {}

    def _save_index(self) -> None:
        self._index_path.write_text(
            json.dumps(self._index, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def _load_production(self) -> ProductionPointer | None:
        if self._production_path.exists():
            data = json.loads(self._production_path.read_text(encoding="utf-8"))
            return ProductionPointer.from_dict(data)
        return None

    def _save_production(self, pointer: ProductionPointer) -> None:
        self._production_path.write_text(
            json.dumps(pointer.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    # -- Public API --------------------------------------------------------

    def register(
        self,
        *,
        model_name: str,
        version: str,
        training_date: str,
        dataset_version: str,
        mAP50: float,
        mAP50_95: float,
        precision: float,
        recall: float,
        training_time_sec: float,
        model_path: str,
        notes: str = "",
        tags: list[str] | None = None,
    ) -> ModelVersion:
        """Register a new model version.

        Raises
        ------
        DuplicateVersionError
            If ``version`` already exists for this ``model_name``.
        """
        versions = self._index.get(model_name, [])
        if any(v["version"] == version for v in versions):
            raise DuplicateVersionError(
                f"Version '{version}' already registered for model '{model_name}'."
            )

        entry = ModelVersion(
            model_name=model_name,
            version=version,
            training_date=training_date,
            dataset_version=dataset_version,
            mAP50=mAP50,
            mAP50_95=mAP50_95,
            precision=precision,
            recall=recall,
            training_time_sec=training_time_sec,
            model_path=model_path,
            notes=notes,
            tags=tags or [],
        )

        # Persist per-version metadata file
        version_dir = self._models_dir / f"{model_name}-{version}"
        version_dir.mkdir(parents=True, exist_ok=True)
        (version_dir / "metadata.json").write_text(
            json.dumps(entry.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        # Update master index
        versions.append(entry.to_dict())
        self._index[model_name] = versions
        self._save_index()

        logger.info(
            "Registered model '%s' version '%s' (mAP50-95=%.4f)",
            model_name,
            version,
            mAP50_95,
        )
        return entry

    def list_versions(self, model_name: str) -> list[ModelVersion]:
        """Return all registered versions for a model, newest first.

        Raises
        ------
        ModelNotFoundError
            If no versions exist for ``model_name``.
        """
        versions = self._index.get(model_name)
        if not versions:
            raise ModelNotFoundError(
                f"No versions registered for model '{model_name}'."
            )
        return [ModelVersion.from_dict(v) for v in reversed(versions)]

    def get_version(self, model_name: str, version: str) -> ModelVersion:
        """Fetch a specific model version.

        Raises
        ------
        ModelNotFoundError
            If the combination does not exist.
        """
        for v in self._index.get(model_name, []):
            if v["version"] == version:
                return ModelVersion.from_dict(v)
        raise ModelNotFoundError(
            f"Version '{version}' not found for model '{model_name}'."
        )

    def get_latest(self, model_name: str) -> ModelVersion:
        """Return the most recently registered version.

        Raises
        ------
        ModelNotFoundError
        """
        versions = self._index.get(model_name)
        if not versions:
            raise ModelNotFoundError(
                f"No versions registered for model '{model_name}'."
            )
        return ModelVersion.from_dict(versions[-1])

    def get_best_model(
        self,
        model_name: str,
        metric: str = "mAP50_95",
    ) -> ModelVersion:
        """Return the version with the highest value of ``metric``.

        Parameters
        ----------
        metric : str
            One of: ``mAP50``, ``mAP50_95``, ``precision``, ``recall``.
            For ``training_time_sec`` the *lowest* value wins.

        Raises
        ------
        ModelNotFoundError
        RegistryError
            If metric is not a valid sortable metric.
        """
        if metric not in SORTABLE_METRICS:
            raise RegistryError(
                f"Invalid metric '{metric}'. Choose from: {sorted(SORTABLE_METRICS)}"
            )

        versions = self._index.get(model_name)
        if not versions:
            raise ModelNotFoundError(
                f"No versions registered for model '{model_name}'."
            )

        reverse = metric != "training_time_sec"  # lower is better for time
        best = sorted(versions, key=lambda v: v[metric], reverse=reverse)[0]
        return ModelVersion.from_dict(best)

    def promote_to_production(
        self, model_name: str, version: str
    ) -> ProductionPointer:
        """Mark a version as the current production model.

        Raises
        ------
        ModelNotFoundError
        """
        # Verify the version exists
        self.get_version(model_name, version)

        current = self._load_production()
        previous = (
            current.version
            if current and current.model_name == model_name
            else None
        )

        pointer = ProductionPointer(
            model_name=model_name,
            version=version,
            promoted_at=datetime.now(timezone.utc).isoformat(),
            previous_version=previous,
        )
        self._save_production(pointer)

        logger.info(
            "Promoted '%s' version '%s' to production (previous: %s)",
            model_name,
            version,
            previous or "none",
        )
        return pointer

    def get_production_model(self) -> tuple[ProductionPointer, ModelVersion]:
        """Return the current production pointer and its model metadata.

        Raises
        ------
        NoProductionModelError
        """
        pointer = self._load_production()
        if pointer is None:
            raise NoProductionModelError("No model has been promoted to production.")

        model = self.get_version(pointer.model_name, pointer.version)
        return pointer, model

    def rollback_production(self) -> ProductionPointer:
        """Restore the previous production model version.

        Raises
        ------
        NoProductionModelError
            If there is no production model or no previous version to rollback to.
        """
        pointer = self._load_production()
        if pointer is None:
            raise NoProductionModelError("No production model to rollback.")

        if pointer.previous_version is None:
            raise NoProductionModelError(
                "No previous version to rollback to. "
                "This was the first promoted version."
            )

        logger.info(
            "Rolling back '%s' from '%s' → '%s'",
            pointer.model_name,
            pointer.version,
            pointer.previous_version,
        )

        return self.promote_to_production(
            pointer.model_name, pointer.previous_version
        )

    def list_models(self) -> list[str]:
        """Return the names of all registered models."""
        return list(self._index.keys())

    def summary(self, model_name: str) -> dict[str, Any]:
        """Return a summary dict suitable for display/logging."""
        versions = self.list_versions(model_name)
        best = self.get_best_model(model_name, metric="mAP50_95")
        latest = self.get_latest(model_name)

        production_version: str | None = None
        try:
            ptr, _ = self.get_production_model()
            if ptr.model_name == model_name:
                production_version = ptr.version
        except NoProductionModelError:
            pass

        return {
            "model_name": model_name,
            "total_versions": len(versions),
            "latest_version": latest.version,
            "best_version": best.version,
            "best_mAP50_95": best.mAP50_95,
            "production_version": production_version,
        }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="model_registry",
        description="SentinelOps — Model Registry CLI",
    )
    parser.add_argument(
        "--registry-root",
        type=Path,
        default=DEFAULT_REGISTRY_ROOT,
        help="Registry root directory (default: artifacts/model_registry).",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # -- register ----------------------------------------------------------
    reg = sub.add_parser("register", help="Register a new model version.")
    reg.add_argument("--name", required=True, help="Model name.")
    reg.add_argument("--version", required=True, help="Version tag (e.g. v1).")
    reg.add_argument("--training-date", required=True, help="Training date (ISO).")
    reg.add_argument("--dataset-version", required=True, help="DVC dataset version.")
    reg.add_argument("--mAP50", type=float, required=True)
    reg.add_argument("--mAP50-95", type=float, required=True, dest="mAP50_95")
    reg.add_argument("--precision", type=float, required=True)
    reg.add_argument("--recall", type=float, required=True)
    reg.add_argument("--training-time", type=float, required=True, help="Seconds.")
    reg.add_argument("--model-path", required=True, help="Path to model weights.")
    reg.add_argument("--notes", default="", help="Optional notes.")
    reg.add_argument("--tags", nargs="*", default=[], help="Optional tags.")

    # -- list --------------------------------------------------------------
    ls = sub.add_parser("list", help="List all versions of a model.")
    ls.add_argument("--name", required=True, help="Model name.")

    # -- best --------------------------------------------------------------
    best = sub.add_parser("best", help="Show the best model by a metric.")
    best.add_argument("--name", required=True, help="Model name.")
    best.add_argument(
        "--metric",
        default="mAP50_95",
        choices=sorted(SORTABLE_METRICS),
        help="Metric to rank by.",
    )

    # -- promote -----------------------------------------------------------
    promo = sub.add_parser("promote", help="Promote a version to production.")
    promo.add_argument("--name", required=True, help="Model name.")
    promo.add_argument("--version", required=True, help="Version tag.")

    # -- rollback ----------------------------------------------------------
    sub.add_parser("rollback", help="Rollback to the previous production model.")

    # -- production --------------------------------------------------------
    sub.add_parser("production", help="Show the current production model.")

    return parser


def _print_model(m: ModelVersion, label: str = "") -> None:
    """Pretty-print a single model version."""
    prefix = f"[{label}] " if label else ""
    print(f"\n{prefix}Model: {m.model_name}  |  Version: {m.version}")
    print(f"  Training Date   : {m.training_date}")
    print(f"  Dataset Version : {m.dataset_version}")
    print(f"  Precision       : {m.precision:.4f}")
    print(f"  Recall          : {m.recall:.4f}")
    print(f"  mAP@50          : {m.mAP50:.4f}")
    print(f"  mAP@50-95       : {m.mAP50_95:.4f}")
    print(f"  Training Time   : {m.training_time_sec:.1f}s")
    print(f"  Model Path      : {m.model_path}")
    if m.notes:
        print(f"  Notes           : {m.notes}")
    if m.tags:
        print(f"  Tags            : {', '.join(m.tags)}")
    print(f"  Registered At   : {m.registered_at}")


def main(argv: list[str] | None = None) -> None:
    parser = _build_parser()
    args = parser.parse_args(argv)
    registry = ModelRegistry(root=args.registry_root)

    try:
        if args.command == "register":
            entry = registry.register(
                model_name=args.name,
                version=args.version,
                training_date=args.training_date,
                dataset_version=args.dataset_version,
                mAP50=args.mAP50,
                mAP50_95=args.mAP50_95,
                precision=args.precision,
                recall=args.recall,
                training_time_sec=args.training_time,
                model_path=args.model_path,
                notes=args.notes,
                tags=args.tags,
            )
            _print_model(entry, label="REGISTERED")

        elif args.command == "list":
            versions = registry.list_versions(args.name)
            print(f"\n{'=' * 60}")
            print(f"  Model: {args.name}  —  {len(versions)} version(s)")
            print(f"{'=' * 60}")
            for v in versions:
                _print_model(v)

        elif args.command == "best":
            best = registry.get_best_model(args.name, metric=args.metric)
            _print_model(best, label=f"BEST by {args.metric}")

        elif args.command == "promote":
            ptr = registry.promote_to_production(args.name, args.version)
            print(f"\n✅ Promoted '{ptr.model_name}' version '{ptr.version}' to production.")
            if ptr.previous_version:
                print(f"   Previous production version: {ptr.previous_version}")

        elif args.command == "rollback":
            ptr = registry.rollback_production()
            print(f"\n↩️  Rolled back to '{ptr.model_name}' version '{ptr.version}'.")

        elif args.command == "production":
            ptr, model = registry.get_production_model()
            print(f"\n🚀 Production Model")
            print(f"   Promoted at: {ptr.promoted_at}")
            if ptr.previous_version:
                print(f"   Previous   : {ptr.previous_version}")
            _print_model(model, label="PRODUCTION")

    except RegistryError as exc:
        logger.error(str(exc))
        sys.exit(1)


if __name__ == "__main__":
    main()
