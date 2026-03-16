"""
FirebirdSQL synchronization for Priorityly tasks.

Replicates the contents of the local-cache to a Firebird database.
The sync runs automatically every N seconds (same interval as the
local-cache flush) and is triggered by the application timer — no
manual user action is needed.

Requirements
------------
- ``firebird-driver`` must be installed::

      pip install firebird-driver

  If the package is missing the sync is silently disabled so the app
  continues to function without Firebird.

- The Firebird connection must be configured in
  ``~/.priorityly/config.json`` (``firebird`` section) and
  ``firebird.enabled`` must be set to ``true``.

The target table is created automatically on first successful
connection if it does not already exist.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Dict, Optional

if TYPE_CHECKING:
    from .config import FirebirdConfig
    from .models import Task

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
# DDL / DML
# --------------------------------------------------------------------------- #

_TABLE_CHECK_SQL = (
    "SELECT 1 FROM rdb$relations "
    "WHERE UPPER(rdb$relation_name) = 'TASKS'"
)

_CREATE_TABLE_SQL = """\
CREATE TABLE tasks (
    id               VARCHAR(36)   NOT NULL,
    title            VARCHAR(500)  NOT NULL,
    description      VARCHAR(2000) DEFAULT '',
    parent_id        VARCHAR(36),
    importance       SMALLINT      DEFAULT 5,
    urgency          SMALLINT      DEFAULT 5,
    comparisons_done INTEGER       DEFAULT 0,
    CONSTRAINT pk_tasks PRIMARY KEY (id)
)"""

_UPSERT_SQL = """\
UPDATE OR INSERT INTO tasks
    (id, title, description, parent_id, importance, urgency, comparisons_done)
VALUES
    (?, ?, ?, ?, ?, ?, ?)
MATCHING (id)"""

_DELETE_MISSING_SQL = "DELETE FROM tasks WHERE id NOT IN ({placeholders})"
_DELETE_ALL_SQL = "DELETE FROM tasks"


# --------------------------------------------------------------------------- #
class FirebirdSync:
    """Replicates the local task list to a FirebirdSQL database."""

    def __init__(self, config: "FirebirdConfig"):
        self._config = config
        # None  → not yet resolved
        # False → import failed (driver unavailable)
        # module → the imported firebird.driver module
        self._driver: Optional[object] = None

    # ------------------------------------------------------------------ #
    def _get_driver(self):
        """
        Lazy-import ``firebird.driver``.

        Returns the module on success, *None* if the package is not
        installed (import error is logged once and cached).
        """
        if self._driver is None:
            try:
                import firebird.driver as fbd  # type: ignore[import]

                self._driver = fbd
            except ImportError:
                logger.warning(
                    "firebird-driver package not found; Firebird sync disabled. "
                    "Install with:  pip install firebird-driver"
                )
                self._driver = False
        return self._driver if self._driver is not False else None

    def _connect(self):
        """Open a new connection to the configured Firebird database."""
        driver = self._get_driver()
        if driver is None:
            return None
        cfg = self._config
        try:
            return driver.connect(
                host=cfg.host,
                port=cfg.port,
                database=cfg.database,
                user=cfg.user,
                password=cfg.password,
            )
        except Exception as exc:  # pragma: no cover
            logger.warning("Firebird connection failed: %s", exc)
            return None

    def _ensure_table(self, con) -> bool:
        """
        Create the ``tasks`` table if it does not yet exist.

        Returns *True* when the table is ready, *False* on error.
        """
        try:
            with con.cursor() as cur:
                cur.execute(_TABLE_CHECK_SQL)
                if not cur.fetchone():
                    cur.execute(_CREATE_TABLE_SQL)
                    con.commit()
            return True
        except Exception as exc:  # pragma: no cover
            logger.warning("Failed to create Firebird table: %s", exc)
            return False

    # ------------------------------------------------------------------ #
    def sync(self, tasks: Dict[str, "Task"]) -> bool:
        """
        Replicate *tasks* to the Firebird database.

        Performs an UPSERT for every task present in the local dataset,
        then deletes rows that no longer exist locally, so the database
        stays an exact mirror of the local-cache.

        Returns *True* when the sync completed successfully and *False*
        when it was skipped (disabled, no driver, or connection error).
        """
        if not self._config.enabled:
            return False

        con = self._connect()
        if con is None:
            return False

        try:
            if not self._ensure_table(con):
                return False

            with con.cursor() as cur:
                # Upsert all current tasks.
                for task in tasks.values():
                    cur.execute(
                        _UPSERT_SQL,
                        (
                            task.id,
                            task.title,
                            task.description,
                            task.parent_id,
                            task.importance,
                            task.urgency,
                            task.comparisons_done,
                        ),
                    )

                # Remove rows that are no longer in the local dataset.
                if tasks:
                    placeholders = ",".join(["?"] * len(tasks))
                    cur.execute(
                        _DELETE_MISSING_SQL.format(placeholders=placeholders),
                        list(tasks.keys()),
                    )
                else:
                    cur.execute(_DELETE_ALL_SQL)

                con.commit()
            return True

        except Exception as exc:  # pragma: no cover
            logger.warning("Firebird sync error: %s", exc)
            try:
                con.rollback()
            except Exception:
                pass
            return False

        finally:
            try:
                con.close()
            except Exception:
                pass
