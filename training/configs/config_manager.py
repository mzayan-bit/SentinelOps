"""
SentinelOps — Training Configuration Manager
===============================================
Centralised, validated configuration for YOLO training pipelines.

Features:
    • Load from YAML files
    • Override any field via environment variables (prefixed ``SENTINELOPS_``)
    • Built-in presets: ``small``, ``medium``, ``large``
    • Schema validation via Pydantic v2
    • Sensible defaults for every field

Usage (library)::

    from training.configs.config_manager import ConfigManager

    # From a YAML file
    cfg = ConfigManager.from_yaml("training/configs/presets/medium.yaml")

    # From a built-in preset
    cfg = ConfigManager.from_preset("large")

    # Access typed sub-configs
    print(cfg.model.architecture)
    print(cfg.training.epochs)
    print(cfg.mlflow.tracking_uri)

Usage (CLI)::

    python -m training.configs.config_manager show   --preset medium
    python -m training.configs.config_manager show   --file  training/configs/presets/custom.yaml
    python -m training.configs.config_manager export  --preset large --output my_config.yaml
    python -m training.configs.config_manager validate --file  training/configs/presets/medium.yaml

Environment variable overrides::

    SENTINELOPS_TRAINING__EPOCHS=200      → cfg.training.epochs = 200
    SENTINELOPS_TRAINING__BATCH_SIZE=32   → cfg.training.batch_size = 32
    SENTINELOPS_MLFLOW__TRACKING_URI=...  → cfg.mlflow.tracking_uri = ...

    Nesting uses double-underscore ``__`` as a separator.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("sentinelops.config")

# ---------------------------------------------------------------------------
# Sub-config schemas
# ---------------------------------------------------------------------------
ENV_PREFIX = "SENTINELOPS_"


class ModelConfig(BaseModel):
    """YOLO model configuration."""

    architecture: str = Field(
        default="yolo11n.pt",
        description="Base model architecture or path to pretrained weights.",
    )
    num_classes: int = Field(default=2, ge=1, description="Number of object classes.")
    input_size: int = Field(default=640, ge=32, description="Input image size (px).")
    class_names: list[str] = Field(
        default_factory=lambda: ["reflective_jacket", "safety_helmet"],
        description="Ordered list of class names.",
    )

    @field_validator("input_size")
    @classmethod
    def _input_must_be_multiple_of_32(cls, v: int) -> int:
        if v % 32 != 0:
            raise ValueError(f"input_size must be a multiple of 32, got {v}")
        return v

    @model_validator(mode="after")
    def _class_names_match_count(self) -> "ModelConfig":
        if len(self.class_names) != self.num_classes:
            raise ValueError(
                f"class_names length ({len(self.class_names)}) "
                f"!= num_classes ({self.num_classes})"
            )
        return self


class TrainingConfig(BaseModel):
    """Hyperparameters and training loop settings."""

    epochs: int = Field(default=100, ge=1, description="Training epochs.")
    batch_size: int = Field(default=16, ge=1, description="Batch size.")
    learning_rate: float = Field(default=0.01, gt=0, description="Initial LR.")
    optimizer: str = Field(default="auto", description="Optimizer (auto|SGD|Adam|AdamW).")
    patience: int = Field(default=50, ge=0, description="Early-stopping patience.")
    save_period: int = Field(default=-1, description="Save checkpoint every N epochs (-1=disabled).")
    device: str = Field(default="auto", description="Device (auto|cpu|cuda|mps).")
    workers: int = Field(default=8, ge=0, description="Dataloader workers.")
    seed: int = Field(default=42, description="Random seed for reproducibility.")
    resume: bool = Field(default=False, description="Resume from last checkpoint.")
    pretrained: bool = Field(default=True, description="Use pretrained backbone.")


class AugmentationConfig(BaseModel):
    """Data augmentation settings."""

    hsv_h: float = Field(default=0.015, ge=0, le=1, description="HSV-Hue augmentation.")
    hsv_s: float = Field(default=0.7, ge=0, le=1, description="HSV-Saturation augmentation.")
    hsv_v: float = Field(default=0.4, ge=0, le=1, description="HSV-Value augmentation.")
    degrees: float = Field(default=0.0, ge=0, description="Rotation (degrees).")
    translate: float = Field(default=0.1, ge=0, le=1, description="Translation fraction.")
    scale: float = Field(default=0.5, ge=0, description="Scaling factor.")
    shear: float = Field(default=0.0, ge=0, description="Shear (degrees).")
    flipud: float = Field(default=0.0, ge=0, le=1, description="Vertical flip probability.")
    fliplr: float = Field(default=0.5, ge=0, le=1, description="Horizontal flip probability.")
    mosaic: float = Field(default=1.0, ge=0, le=1, description="Mosaic augmentation probability.")
    mixup: float = Field(default=0.0, ge=0, le=1, description="MixUp augmentation probability.")
    copy_paste: float = Field(default=0.0, ge=0, le=1, description="Copy-paste augmentation probability.")


class DatasetConfig(BaseModel):
    """Dataset paths and versioning."""

    root: str = Field(default="data", description="Dataset root directory.")
    yaml_path: str = Field(default="data/data.yaml", description="YOLO data.yaml path.")
    dvc_remote: str = Field(default="localremote", description="DVC remote name.")
    version: str = Field(default="v1", description="Dataset version tag.")
    train_split: str = Field(default="train", description="Training split name.")
    val_split: str = Field(default="valid", description="Validation split name.")
    test_split: str = Field(default="test", description="Test split name.")


class MLflowConfig(BaseModel):
    """MLflow experiment tracking settings."""

    enabled: bool = Field(default=True, description="Enable MLflow tracking.")
    tracking_uri: str = Field(
        default="http://localhost:5000",
        description="MLflow tracking server URI.",
    )
    experiment_name: str = Field(
        default="sentinelops-detection",
        description="MLflow experiment name.",
    )
    run_name: str | None = Field(default=None, description="Optional run name.")
    log_artifacts: bool = Field(default=True, description="Log model artifacts to MLflow.")
    registry_name: str = Field(
        default="sentinelops-yolo",
        description="MLflow model registry name.",
    )


class DVCConfig(BaseModel):
    """DVC data versioning settings."""

    enabled: bool = Field(default=True, description="Enable DVC tracking.")
    remote: str = Field(default="localremote", description="DVC remote name.")
    auto_push: bool = Field(default=False, description="Auto-push data after training.")


class LoggingConfig(BaseModel):
    """Logging settings."""

    level: str = Field(default="INFO", description="Log level.")
    log_dir: str = Field(default="logs", description="Directory for log files.")
    console: bool = Field(default=True, description="Log to console.")
    file: bool = Field(default=True, description="Log to file.")
    format: str = Field(
        default="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        description="Log format string.",
    )


class OutputConfig(BaseModel):
    """Output paths for training artifacts."""

    project_dir: str = Field(default="runs/detect", description="Project output directory.")
    run_name: str = Field(default="train", description="Run name (subdirectory).")
    save_dir: str = Field(default="models", description="Model save directory.")
    artifacts_dir: str = Field(default="artifacts", description="Artifacts directory.")


# ---------------------------------------------------------------------------
# Top-level config
# ---------------------------------------------------------------------------
class SentinelOpsConfig(BaseModel):
    """Root configuration schema for SentinelOps training pipelines.

    All fields have sensible defaults.  Any field can be overridden
    via YAML files or environment variables.
    """

    project_name: str = Field(default="SentinelOps", description="Project name.")
    preset: str | None = Field(default=None, description="Preset name (small|medium|large).")

    model: ModelConfig = Field(default_factory=ModelConfig)
    training: TrainingConfig = Field(default_factory=TrainingConfig)
    augmentation: AugmentationConfig = Field(default_factory=AugmentationConfig)
    dataset: DatasetConfig = Field(default_factory=DatasetConfig)
    mlflow: MLflowConfig = Field(default_factory=MLflowConfig)
    dvc: DVCConfig = Field(default_factory=DVCConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)


# ---------------------------------------------------------------------------
# Presets
# ---------------------------------------------------------------------------
PRESETS: dict[str, dict[str, Any]] = {
    "small": {
        "preset": "small",
        "model": {
            "architecture": "yolo11n.pt",
            "input_size": 640,
        },
        "training": {
            "epochs": 50,
            "batch_size": 32,
            "learning_rate": 0.01,
            "patience": 20,
            "workers": 4,
        },
        "augmentation": {
            "mosaic": 1.0,
            "mixup": 0.0,
            "scale": 0.5,
        },
    },
    "medium": {
        "preset": "medium",
        "model": {
            "architecture": "yolo11s.pt",
            "input_size": 640,
        },
        "training": {
            "epochs": 100,
            "batch_size": 16,
            "learning_rate": 0.01,
            "patience": 50,
            "workers": 8,
        },
        "augmentation": {
            "mosaic": 1.0,
            "mixup": 0.1,
            "scale": 0.5,
            "fliplr": 0.5,
        },
    },
    "large": {
        "preset": "large",
        "model": {
            "architecture": "yolo11m.pt",
            "input_size": 640,
        },
        "training": {
            "epochs": 200,
            "batch_size": 8,
            "learning_rate": 0.001,
            "optimizer": "AdamW",
            "patience": 80,
            "workers": 8,
        },
        "augmentation": {
            "mosaic": 1.0,
            "mixup": 0.3,
            "copy_paste": 0.1,
            "scale": 0.9,
            "fliplr": 0.5,
            "degrees": 10.0,
            "translate": 0.2,
        },
    },
}


# ---------------------------------------------------------------------------
# Environment variable override helper
# ---------------------------------------------------------------------------
def _apply_env_overrides(data: dict[str, Any]) -> dict[str, Any]:
    """Scan environment variables prefixed with ``SENTINELOPS_`` and
    merge them into the config dict.

    Nesting is expressed with double-underscore::

        SENTINELOPS_TRAINING__EPOCHS=200
        → data["training"]["epochs"] = 200
    """
    for key, value in os.environ.items():
        if not key.startswith(ENV_PREFIX):
            continue

        parts = key[len(ENV_PREFIX):].lower().split("__")
        target = data
        for part in parts[:-1]:
            target = target.setdefault(part, {})

        leaf = parts[-1]

        # Attempt type coercion
        if value.lower() in ("true", "false"):
            value = value.lower() == "true"  # type: ignore[assignment]
        else:
            for cast in (int, float):
                try:
                    value = cast(value)  # type: ignore[assignment]
                    break
                except ValueError:
                    continue

        target[leaf] = value
        logger.debug("Env override: %s = %s", key, value)

    return data


# ---------------------------------------------------------------------------
# Config Manager
# ---------------------------------------------------------------------------
class ConfigManager:
    """Factory for creating, loading, and exporting ``SentinelOpsConfig``."""

    @staticmethod
    def from_yaml(path: str | Path) -> SentinelOpsConfig:
        """Load config from a YAML file, then apply env overrides."""
        filepath = Path(path)
        if not filepath.exists():
            raise FileNotFoundError(f"Config file not found: {filepath}")

        with open(filepath, "r", encoding="utf-8") as fh:
            raw: dict[str, Any] = yaml.safe_load(fh) or {}

        raw = _apply_env_overrides(raw)
        cfg = SentinelOpsConfig(**raw)
        logger.info("Config loaded from %s (preset=%s)", filepath, cfg.preset)
        return cfg

    @staticmethod
    def from_preset(name: str) -> SentinelOpsConfig:
        """Load a built-in preset, then apply env overrides.

        Raises
        ------
        ValueError
            If ``name`` is not one of the known presets.
        """
        if name not in PRESETS:
            raise ValueError(
                f"Unknown preset '{name}'. Available: {sorted(PRESETS.keys())}"
            )
        raw = _deep_copy_dict(PRESETS[name])
        raw = _apply_env_overrides(raw)
        cfg = SentinelOpsConfig(**raw)
        logger.info("Config loaded from preset '%s'", name)
        return cfg

    @staticmethod
    def from_dict(data: dict[str, Any]) -> SentinelOpsConfig:
        """Build config from a plain dictionary."""
        data = _apply_env_overrides(data)
        return SentinelOpsConfig(**data)

    @staticmethod
    def default() -> SentinelOpsConfig:
        """Return the default config (all Pydantic defaults)."""
        raw = _apply_env_overrides({})
        return SentinelOpsConfig(**raw)

    @staticmethod
    def export_yaml(cfg: SentinelOpsConfig, path: str | Path) -> None:
        """Dump the current config to a YAML file."""
        filepath = Path(path)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as fh:
            yaml.dump(
                cfg.model_dump(),
                fh,
                default_flow_style=False,
                sort_keys=False,
                allow_unicode=True,
            )
        logger.info("Config exported → %s", filepath)

    @staticmethod
    def validate_file(path: str | Path) -> tuple[bool, list[str]]:
        """Validate a YAML config file and return ``(is_valid, errors)``."""
        errors: list[str] = []
        try:
            ConfigManager.from_yaml(path)
        except Exception as exc:
            errors.append(str(exc))
        return (len(errors) == 0, errors)

    @staticmethod
    def show(cfg: SentinelOpsConfig) -> None:
        """Pretty-print the config to stdout."""
        print(yaml.dump(
            cfg.model_dump(),
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
        ))


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------
def _deep_copy_dict(d: dict[str, Any]) -> dict[str, Any]:
    """Simple recursive dict copy (avoids importing copy for this)."""
    out: dict[str, Any] = {}
    for k, v in d.items():
        out[k] = _deep_copy_dict(v) if isinstance(v, dict) else v
    return out


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="config_manager",
        description="SentinelOps — Training Configuration Manager",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # show
    show = sub.add_parser("show", help="Display a resolved config.")
    show_src = show.add_mutually_exclusive_group(required=True)
    show_src.add_argument("--preset", choices=sorted(PRESETS.keys()))
    show_src.add_argument("--file", type=Path)

    # export
    export = sub.add_parser("export", help="Export a config to YAML.")
    export_src = export.add_mutually_exclusive_group(required=True)
    export_src.add_argument("--preset", choices=sorted(PRESETS.keys()))
    export_src.add_argument("--file", type=Path)
    export.add_argument("--output", type=Path, required=True)

    # validate
    validate = sub.add_parser("validate", help="Validate a config YAML.")
    validate.add_argument("--file", type=Path, required=True)

    return parser


def main(argv: list[str] | None = None) -> None:
    args = _build_parser().parse_args(argv)

    if args.command == "show":
        cfg = (
            ConfigManager.from_preset(args.preset)
            if args.preset
            else ConfigManager.from_yaml(args.file)
        )
        ConfigManager.show(cfg)

    elif args.command == "export":
        cfg = (
            ConfigManager.from_preset(args.preset)
            if args.preset
            else ConfigManager.from_yaml(args.file)
        )
        ConfigManager.export_yaml(cfg, args.output)
        print(f"✅ Config exported → {args.output}")

    elif args.command == "validate":
        ok, errors = ConfigManager.validate_file(args.file)
        if ok:
            print(f"✅ Config is valid: {args.file}")
        else:
            print(f"❌ Config has errors:")
            for e in errors:
                print(f"   • {e}")
            sys.exit(1)


if __name__ == "__main__":
    main()
