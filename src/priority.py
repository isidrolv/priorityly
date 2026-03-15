"""
Priority engine for Priorityly.

Pairwise comparison uses a merge-sort inspired approach:
- Each time the user compares A vs B on importance AND urgency, we adjust
  the raw scores slightly and re-sort.
- The comparison queue is generated so every task is compared at least once
  before repeating (round-robin tournament).
"""
from __future__ import annotations
import itertools
import random
from typing import Dict, List, Optional, Tuple
from .models import Task


DELTA = 1.2   # score shift per comparison win


def sorted_by_priority(tasks: Dict[str, Task]) -> List[Task]:
    """Return all tasks sorted from highest to lowest priority."""
    return sorted(tasks.values(), key=lambda t: t.priority_score, reverse=True)


def sorted_flat(tasks: Dict[str, Task]) -> List[Task]:
    """
    Flat sorted list: root tasks first by priority, then their subtasks
    nested under them (also sorted), etc.
    """
    def collect(parent_id: Optional[str], depth: int) -> List[Tuple[int, Task]]:
        children = [t for t in tasks.values() if t.parent_id == parent_id]
        children.sort(key=lambda t: t.priority_score, reverse=True)
        result = []
        for child in children:
            result.append((depth, child))
            result.extend(collect(child.id, depth + 1))
        return result

    return collect(None, 0)


# ------------------------------------------------------------------ #
# Pairwise comparison engine
# ------------------------------------------------------------------ #

class ComparisonEngine:
    """
    Manages a queue of pairwise comparisons.
    Call next_pair() to get the next (A, B) pair.
    Call record(winner_id_importance, winner_id_urgency) to store the result.
    """

    def __init__(self, tasks: Dict[str, Task]):
        self._tasks = tasks
        self._queue: List[Tuple[str, str]] = []
        self._rebuild_queue()

    # ---------------------------------------------------------------- #
    def _rebuild_queue(self):
        ids = list(self._tasks.keys())
        if len(ids) < 2:
            self._queue = []
            return
        pairs = list(itertools.combinations(ids, 2))
        random.shuffle(pairs)
        self._queue = pairs

    def refresh(self, tasks: Dict[str, Task]):
        self._tasks = tasks
        self._rebuild_queue()

    # ---------------------------------------------------------------- #
    def has_pairs(self) -> bool:
        return len(self._queue) > 0 and len(self._tasks) >= 2

    def next_pair(self) -> Optional[Tuple[Task, Task]]:
        """Pop next pair from queue, skipping invalid IDs."""
        while self._queue:
            a_id, b_id = self._queue.pop(0)
            if a_id in self._tasks and b_id in self._tasks:
                return self._tasks[a_id], self._tasks[b_id]
        # Exhausted – rebuild for next round
        self._rebuild_queue()
        if self._queue:
            a_id, b_id = self._queue.pop(0)
            if a_id in self._tasks and b_id in self._tasks:
                return self._tasks[a_id], self._tasks[b_id]
        return None

    def pairs_remaining(self) -> int:
        return len(self._queue)

    # ---------------------------------------------------------------- #
    def record(
        self,
        winner_imp_id: str,
        loser_imp_id: str,
        winner_urg_id: str,
        loser_urg_id: str,
    ):
        """
        Update importance and urgency scores based on comparison result.
        Scores are clamped to [1, 10].
        """
        def shift(task_id: str, delta: float):
            t = self._tasks.get(task_id)
            if t:
                return t

        def clamp(v: float) -> int:
            return max(1, min(10, round(v)))

        # Importance
        if winner_imp_id != loser_imp_id:
            winner = self._tasks.get(winner_imp_id)
            loser = self._tasks.get(loser_imp_id)
            if winner and loser:
                winner.importance = clamp(winner.importance + DELTA)
                loser.importance = clamp(loser.importance - DELTA)
                winner.comparisons_done += 1
                loser.comparisons_done += 1

        # Urgency
        if winner_urg_id != loser_urg_id:
            winner = self._tasks.get(winner_urg_id)
            loser = self._tasks.get(loser_urg_id)
            if winner and loser:
                winner.urgency = clamp(winner.urgency + DELTA)
                loser.urgency = clamp(loser.urgency - DELTA)

    def record_tie(self, a_id: str, b_id: str):
        """Both are equal – increment comparison counter only."""
        for tid in (a_id, b_id):
            t = self._tasks.get(tid)
            if t:
                t.comparisons_done += 1
