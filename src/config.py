import os
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def load_config(path: str | None = None) -> dict:
    config_path = Path(path) if path else PROJECT_ROOT / "config.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    cfg["_project_root"] = str(PROJECT_ROOT)
    return cfg


def resolve_path(cfg: dict, relative: str) -> Path:
    root = Path(cfg["_project_root"])
    p = Path(relative)
    return p if p.is_absolute() else root / p


def credentials_path(cfg: dict) -> Path:
    env_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if env_path:
        return Path(env_path)
    return resolve_path(cfg, cfg["google_sheets"]["credentials_path"])
