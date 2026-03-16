"""
Application configuration for Priorityly.

Settings are persisted to ~/.priorityly/config.json and loaded
automatically on startup.  Defaults are written the first time the
application runs so users can inspect and customise the file.
"""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field

CONFIG_PATH = os.path.join(os.path.expanduser("~"), ".priorityly", "config.json")

# How often (in seconds) to auto-save the local-cache and push to Firebird.
DEFAULT_CACHE_INTERVAL = 30


@dataclass
class FirebirdConfig:
    """Connection settings for the optional FirebirdSQL replica."""

    host: str = "localhost"
    port: int = 3050
    # Absolute path to the .fdb file, e.g. /home/user/priorityly.fdb
    database: str = ""
    user: str = "SYSDBA"
    password: str = "masterkey"
    # Set to true once the database is configured to enable replication.
    enabled: bool = False


@dataclass
class AppConfig:
    """Top-level application configuration."""

    # Seconds between automatic local-cache saves and Firebird syncs.
    cache_interval_seconds: int = DEFAULT_CACHE_INTERVAL
    firebird: FirebirdConfig = field(default_factory=FirebirdConfig)

    # ------------------------------------------------------------------ #
    def to_dict(self) -> dict:
        return {
            "cache_interval_seconds": self.cache_interval_seconds,
            "firebird": asdict(self.firebird),
        }

    @classmethod
    def from_dict(cls, d: dict) -> AppConfig:
        fb = d.get("firebird", {})
        return cls(
            cache_interval_seconds=int(
                d.get("cache_interval_seconds", DEFAULT_CACHE_INTERVAL)
            ),
            firebird=FirebirdConfig(
                host=fb.get("host", "localhost"),
                port=int(fb.get("port", 3050)),
                database=fb.get("database", ""),
                user=fb.get("user", "SYSDBA"),
                password=fb.get("password", "masterkey"),
                enabled=bool(fb.get("enabled", False)),
            ),
        )

    # ------------------------------------------------------------------ #
    def save(self, path: str = CONFIG_PATH) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)

    @classmethod
    def load(cls, path: str = CONFIG_PATH) -> AppConfig:
        """
        Load configuration from *path*.

        If the file does not exist the defaults are used and the file is
        created so users can edit it.  Corrupt files are silently reset.
        """
        if not os.path.exists(path):
            config = cls()
            config.save(path)
            return config
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return cls.from_dict(data)
        except (json.JSONDecodeError, KeyError, ValueError):
            config = cls()
            config.save(path)
            return config
