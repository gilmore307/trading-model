"""Environment-overridable runtime paths for trading-model.

Defaults preserve the OpenClaw project layout, while tests and downloaded copies can
set environment variables or pass explicit paths so import/test paths do not depend
on ``/root/projects`` or ``/root/secrets`` existing.
"""
from __future__ import annotations

import os
from pathlib import Path


def _path_from_env(name: str, default: Path) -> Path:
    value = os.environ.get(name, "").strip()
    return Path(value).expanduser() if value else default


def projects_root() -> Path:
    return _path_from_env("TRADING_PROJECTS_ROOT", Path("/root/projects"))


def model_root() -> Path:
    return _path_from_env("TRADING_MODEL_ROOT", projects_root() / "trading-model")


def trading_data_root() -> Path:
    return _path_from_env("TRADING_DATA_ROOT", projects_root() / "trading-data")


def trading_manager_root() -> Path:
    return _path_from_env("TRADING_MANAGER_ROOT", projects_root() / "trading-manager")


def trading_storage_root() -> Path:
    return _path_from_env("TRADING_STORAGE_ROOT", projects_root() / "trading-storage")


def component_storage_root(component: str) -> Path:
    return trading_storage_root() / "storage" / component


def model_storage_root() -> Path:
    return _path_from_env("TRADING_MODEL_STORAGE_ROOT", component_storage_root("model"))


def model_runtime_root() -> Path:
    return model_storage_root() / "runtime"


def data_storage_root() -> Path:
    return _path_from_env("TRADING_DATA_STORAGE_ROOT", component_storage_root("data"))


def secret_root() -> Path:
    return _path_from_env("TRADING_SECRET_ROOT", Path("/root/secrets"))


def database_url_file() -> Path:
    return _path_from_env("TRADING_MODEL_DATABASE_URL_FILE", secret_root() / "openclaw" / "database-url")
