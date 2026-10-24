"""Tiny user settings file (KEY=VALUE) under $XDG_CONFIG_HOME/tiptoi-linux/."""

from __future__ import annotations

import os
from pathlib import Path

SETTINGS_NAME = "settings"


def settings_path() -> Path:
    xdg_config = os.environ.get("XDG_CONFIG_HOME")
    base = Path(xdg_config) if xdg_config else Path.home() / ".config"
    return base / "tiptoi-linux" / "settings"


def load_settings() -> dict[str, str]:
    try:
        text = settings_path().read_text(encoding="utf-8")
    except OSError:
        return {}
    settings: dict[str, str] = {}
    for line in text.splitlines():
        key, sep, value = line.partition("=")
        if sep and key.strip():
            settings.setdefault(key.strip(), value.strip())
    return settings


def save_setting(key: str, value: str) -> None:
    settings = load_settings()
    settings[key] = value
    path = settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    body = "".join(f"{k}={v}\n" for k, v in sorted(settings.items()))
    path.write_text(body, encoding="utf-8")
