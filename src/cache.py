"""
Local JSON cache for Priorityly tasks.

Keeps a persistent snapshot of the current in-memory task list in
~/.priorityly/local-cache.json.  The file is refreshed automatically
every N seconds (configured in config.json) and is read back on
startup so the session is fully restored after a restart.
"""
from __future__ import annotations

import json
import os
from typing import Dict

from .models import Task

CACHE_PATH = os.path.join(os.path.expanduser("~"), ".priorityly", "local-cache.json")


class LocalCache:
    """Persistent JSON snapshot of the active task list."""

    def __init__(self, path: str = CACHE_PATH):
        self.path = path
        os.makedirs(os.path.dirname(self.path), exist_ok=True)

    # ------------------------------------------------------------------ #
    def save(self, tasks: Dict[str, Task]) -> None:
        """Overwrite the cache file with the current task list."""
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(
                [t.to_dict() for t in tasks.values()],
                f,
                ensure_ascii=False,
                indent=2,
            )

    def load(self) -> Dict[str, Task]:
        """
        Read the cache file and return a task dictionary.

        Returns an empty dict if the file does not exist or is corrupt.
        """
        if not os.path.exists(self.path):
            return {}
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return {d["id"]: Task.from_dict(d) for d in data}
        except (json.JSONDecodeError, KeyError):
            return {}
