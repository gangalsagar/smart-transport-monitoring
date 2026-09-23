from contextlib import contextmanager
import json
import sqlite3
from pathlib import Path
from typing import Optional, List, Tuple

from shared.schemas.alert_schema import Alert


class AlertQueue:
    """
    Offline-first persistent alert queue for the edge device.

    The queue is intentionally independent from the central backend.

    Alert lifecycle:

        PENDING
           |
           v
        SENT

    If upload fails:

        PENDING
           |
           v
        FAILED
           |
           v
        retry
           |
           v
        SENT

    SQLite is used so alerts survive:
        - network loss
        - application restart
        - device reboot
    """

    def __init__(self, database_path=None):

        project_root = Path(
            __file__
        ).resolve().parents[2]

        if database_path is None:
            # Check edge storage location first, fallback to legacy location
            p1 = project_root / "edge" / "data" / "alerts" / "alert_queue.db"
            p2 = project_root / "module1_road_defect" / "data" / "alerts" / "alert_queue.db"
            database_path = p1 if p1.parent.exists() else p2

        self.database_path = Path(
            database_path
        )

        self.database_path.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        self._initialize_database()

    # ========================================================
    # DATABASE
    # ========================================================

    @contextmanager
    def _connect(self):

        connection = sqlite3.connect(
            self.database_path,
            timeout=10
        )

        connection.row_factory = (
            sqlite3.Row
        )

        try:
            yield connection
        finally:
            connection.close()

    def _initialize_database(self):

        with self._connect() as connection:

            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS alerts (
                    alert_id TEXT PRIMARY KEY,
                    alert_json TEXT NOT NULL,

                    status TEXT NOT NULL
                        CHECK (
                            status IN (
                                'PENDING',
                                'FAILED',
                                'SENT'
                            )
                        ),

                    retry_count INTEGER NOT NULL
                        DEFAULT 0,

                    created_at TEXT NOT NULL,

                    sent_at TEXT,

                    last_error TEXT
                )
                """
            )

            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_alerts_status
                ON alerts(status)
                """
            )

            connection.commit()

    # ========================================================
    # ADD ALERT
    # ========================================================

    def enqueue(
        self,
        alert: Alert
    ) -> bool:
        """
        Add an alert to the persistent queue.

        Returns:
            True  -> newly inserted
            False -> alert already exists
        """

        if not isinstance(
            alert,
            Alert
        ):

            raise TypeError(
                "alert must be an Alert object"
            )

        alert_json = (
            alert.model_dump_json()
        )

        created_at = (
            alert.timestamp.isoformat()
        )

        with self._connect() as connection:

            cursor = connection.execute(
                """
                INSERT OR IGNORE INTO alerts (
                    alert_id,
                    alert_json,
                    status,
                    retry_count,
                    created_at
                )
                VALUES (
                    ?,
                    ?,
                    'PENDING',
                    0,
                    ?
                )
                """,
                (
                    alert.alert_id,
                    alert_json,
                    created_at,
                )
            )

            connection.commit()

            return (
                cursor.rowcount == 1
            )

    # ========================================================
    # GET PENDING / FAILED ALERTS
    # ========================================================

    def get_pending(
        self,
        limit: int = 20
    ) -> List[Tuple[str, Alert]]:

        if limit <= 0:

            return []

        with self._connect() as connection:

            rows = connection.execute(
                """
                SELECT
                    alert_id,
                    alert_json
                FROM alerts
                WHERE status IN (
                    'PENDING',
                    'FAILED'
                )
                ORDER BY created_at ASC
                LIMIT ?
                """,
                (limit,)
            ).fetchall()

        results = []

        for row in rows:

            alert = Alert.model_validate(
                json.loads(
                    row["alert_json"]
                )
            )

            results.append(
                (
                    row["alert_id"],
                    alert
                )
            )

        return results

    # ========================================================
    # MARK SENT
    # ========================================================

    def mark_sent(
        self,
        alert_id: str,
        sent_at: Optional[str] = None
    ):

        if sent_at is None:

            from datetime import datetime, timezone

            sent_at = (
                datetime.now(
                    timezone.utc
                ).isoformat()
            )

        with self._connect() as connection:

            connection.execute(
                """
                UPDATE alerts
                SET
                    status = 'SENT',
                    sent_at = ?,
                    last_error = NULL
                WHERE alert_id = ?
                """,
                (
                    sent_at,
                    alert_id,
                )
            )

            connection.commit()

    # ========================================================
    # MARK FAILED
    # ========================================================

    def mark_failed(
        self,
        alert_id: str,
        error: str
    ):

        with self._connect() as connection:

            connection.execute(
                """
                UPDATE alerts
                SET
                    status = 'FAILED',
                    retry_count =
                        retry_count + 1,
                    last_error = ?
                WHERE alert_id = ?
                """,
                (
                    str(error),
                    alert_id,
                )
            )

            connection.commit()

    # ========================================================
    # GET STATUS
    # ========================================================

    def get_status(
        self,
        alert_id: str
    ):

        with self._connect() as connection:

            row = connection.execute(
                """
                SELECT
                    alert_id,
                    status,
                    retry_count,
                    created_at,
                    sent_at,
                    last_error
                FROM alerts
                WHERE alert_id = ?
                """,
                (alert_id,)
            ).fetchone()

        if row is None:

            return None

        return dict(row)

    # ========================================================
    # COUNTS
    # ========================================================

    def count(
        self,
        status: Optional[str] = None
    ) -> int:

        with self._connect() as connection:

            if status is None:

                row = connection.execute(
                    """
                    SELECT COUNT(*)
                    AS count
                    FROM alerts
                    """
                ).fetchone()

            else:

                row = connection.execute(
                    """
                    SELECT COUNT(*)
                    AS count
                    FROM alerts
                    WHERE status = ?
                    """,
                    (status,)
                ).fetchone()

        return int(
            row["count"]
        )

    # ========================================================
    # SUMMARY
    # ========================================================

    def summary(self):

        return {
            "total":
                self.count(),

            "pending":
                self.count("PENDING"),

            "failed":
                self.count("FAILED"),

            "sent":
                self.count("SENT"),
        }

    # ========================================================
    # READ ALERT
    # ========================================================

    def get_alert(
        self,
        alert_id: str
    ) -> Optional[Alert]:

        with self._connect() as connection:

            row = connection.execute(
                """
                SELECT alert_json
                FROM alerts
                WHERE alert_id = ?
                """,
                (alert_id,)
            ).fetchone()

        if row is None:

            return None

        return Alert.model_validate(
            json.loads(
                row["alert_json"]
            )
        )
