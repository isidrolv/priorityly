"""
Task model and priority logic for Priorityly.
"""
from __future__ import annotations
import uuid
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Task:
    title: str
    description: str = ""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    parent_id: Optional[str] = None

    # Eisenhower scores (1–10 scale, >=6 means True for that axis)
    importance: int = 5   # 1=not important ... 10=very important
    urgency: int = 5      # 1=not urgent    ... 10=very urgent

    # How many pairwise comparisons have been done (for progress tracking)
    comparisons_done: int = 0

    # ------------------------------------------------------------------ #
    @property
    def is_important(self) -> bool:
        return self.importance >= 6

    @property
    def is_urgent(self) -> bool:
        return self.urgency >= 6

    @property
    def quadrant(self) -> int:
        """
        1 – Important  + Urgent      → DO FIRST
        2 – Important  + Not Urgent  → SCHEDULE
        3 – Not Import + Urgent      → DELEGATE
        4 – Not Import + Not Urgent  → ELIMINATE
        """
        if self.is_important and self.is_urgent:
            return 1
        if self.is_important and not self.is_urgent:
            return 2
        if not self.is_important and self.is_urgent:
            return 3
        return 4

    @property
    def quadrant_label(self) -> str:
        labels = {
            1: "Q1 – Hacer ya",
            2: "Q2 – Planificar",
            3: "Q3 – Delegar",
            4: "Q4 – Eliminar",
        }
        return labels[self.quadrant]

    @property
    def priority_score(self) -> float:
        """
        Combined score used for final sorting.
        Quadrant takes precedence, fine-grained by (importance + urgency).
        Higher = more critical.
        """
        quad_weight = {1: 1000, 2: 100, 3: 10, 4: 0}
        return quad_weight[self.quadrant] + self.importance + self.urgency

    # ------------------------------------------------------------------ #
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "parent_id": self.parent_id,
            "importance": self.importance,
            "urgency": self.urgency,
            "comparisons_done": self.comparisons_done,
        }

    @classmethod
    def from_dict(cls, d: dict) -> Task:
        return cls(
            id=d.get("id", str(uuid.uuid4())),
            title=d["title"],
            description=d.get("description", ""),
            parent_id=d.get("parent_id"),
            importance=d.get("importance", 5),
            urgency=d.get("urgency", 5),
            comparisons_done=d.get("comparisons_done", 0),
        )


QUADRANT_COLORS = {
    1: "#d32f2f",   # red   – do first
    2: "#1976d2",   # blue  – schedule
    3: "#f57c00",   # orange– delegate
    4: "#616161",   # grey  – eliminate
}

QUADRANT_NAMES = {
    1: "Urgente + Importante",
    2: "No Urgente + Importante",
    3: "Urgente + No Importante",
    4: "No Urgente + No Importante",
}
