"""
config.py - Persistent configuration for DevSync.

Saves device connection info and sync pairs to ~/.devsync/config.json
so you don't need to re-configure on every run.
"""

import json
import os
from pathlib import Path


CONFIG_DIR = Path.home() / ".devsync"
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULTS = {
    "device_ip": None,
    "device_port": "5555",
    "method": "adb",
    "http_port": "8765",
    "sync_pairs": [],
}


class ConfigManager:
    def __init__(self):
        self._data = dict(DEFAULTS)
        self._load()

    def _load(self):
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE) as f:
                    saved = json.load(f)
                self._data.update(saved)
            except (json.JSONDecodeError, IOError):
                pass  # Use defaults if config is corrupt

    def save(self):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w") as f:
            json.dump(self._data, f, indent=2)

    def get(self, key: str, default=None):
        return self._data.get(key, default)

    def set(self, key: str, value):
        self._data[key] = value

    def reset(self):
        self._data = dict(DEFAULTS)
        self.save()

    @property
    def config_path(self) -> str:
        return str(CONFIG_FILE)
