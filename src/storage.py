"""
JSON-based persistence for Priorityly tasks.
"""
from __future__ import annotations
import json
import os
from typing import Dict, List, Optional
from .models import Task

DEFAULT_PATH = os.path.join(os.path.expanduser("~"), ".priorityly", "tasks.json")


class Storage:
    def __init__(self, path: str = DEFAULT_PATH):
        self.path = path
        os.makedirs(os.path.dirname(self.path), exist_ok=True)

    # ------------------------------------------------------------------ #
    def load(self) -> Dict[str, Task]:
        if not os.path.exists(self.path):
            return {}
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return {d["id"]: Task.from_dict(d) for d in data}
        except (json.JSONDecodeError, KeyError):
            return {}

    def save(self, tasks: Dict[str, Task]) -> None:
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump([t.to_dict() for t in tasks.values()], f, ensure_ascii=False, indent=2)

    # ------------------------------------------------------------------ #
    # Convenience helpers
    # ------------------------------------------------------------------ #
    def root_tasks(self, tasks: Dict[str, Task]) -> List[Task]:
        return [t for t in tasks.values() if t.parent_id is None]

    def children_of(self, tasks: Dict[str, Task], parent_id: str) -> List[Task]:
        return [t for t in tasks.values() if t.parent_id == parent_id]

    def ancestors_of(self, tasks: Dict[str, Task], task_id: str) -> List[str]:
        """Returns list of ancestor IDs from root to parent."""
        ancestors = []
        current = tasks.get(task_id)
        while current and current.parent_id:
            ancestors.insert(0, current.parent_id)
            current = tasks.get(current.parent_id)
        return ancestors

    def all_descendants(self, tasks: Dict[str, Task], task_id: str) -> List[str]:
        """Recursively collect all descendant IDs."""
        result = []
        for child in self.children_of(tasks, task_id):
            result.append(child.id)
            result.extend(self.all_descendants(tasks, child.id))
        return result

    def delete_task(self, tasks: Dict[str, Task], task_id: str) -> Dict[str, Task]:
        """Delete a task and all its descendants."""
        to_delete = {task_id} | set(self.all_descendants(tasks, task_id))
        return {tid: t for tid, t in tasks.items() if tid not in to_delete}
