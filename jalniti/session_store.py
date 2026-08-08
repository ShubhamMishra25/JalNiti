"""SQLite-backed persistent session store."""
from __future__ import annotations

import json
import logging
import sqlite3
import time
from pathlib import Path
from typing import Optional

from .config import settings
from .models import ConversationState

logger = logging.getLogger(__name__)

TTL_SECONDS = 1800  # 30 min inactivity expiry


def _default_db_path() -> Path:
    return Path(__file__).resolve().parent.parent / "data" / "sessions.db"


DB_PATH = Path(settings.session_db_path) if settings.session_db_path else _default_db_path()
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS sessions (
            user_id TEXT PRIMARY KEY,
            data TEXT NOT NULL,
            updated_at REAL NOT NULL
        )
        """
    )
    return conn


class SessionStore:
    def get(self, user_id: str) -> Optional[ConversationState]:
        conn = _get_conn()
        try:
            row = conn.execute(
                "SELECT data, updated_at FROM sessions WHERE user_id = ?", (user_id,)
            ).fetchone()
        finally:
            conn.close()

        if not row:
            return None

        data, updated_at = row
        if time.time() - updated_at > TTL_SECONDS:
            self.delete(user_id)
            return None

        return ConversationState.from_dict(json.loads(data))

    def save(self, user_id: str, state: ConversationState) -> None:
        conn = _get_conn()
        try:
            conn.execute(
                "INSERT OR REPLACE INTO sessions (user_id, data, updated_at) VALUES (?, ?, ?)",
                (user_id, json.dumps(state.to_dict()), time.time()),
            )
            conn.commit()
        finally:
            conn.close()

    def delete(self, user_id: str) -> None:
        conn = _get_conn()
        try:
            conn.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
            conn.commit()
        finally:
            conn.close()


class MessageLedger:
    """Persistent dedup of already-processed WhatsApp message IDs.

    WhatsApp re-delivers webhook payloads when we don't acknowledge in time
    (or after a crash/restart). Tracking seen message IDs in SQLite makes
    dedup survive process restarts and work across multiple gunicorn
    workers, so a redelivered message never produces a duplicate reply.
    """

    _PRUNE_KEEP_SECONDS = 48 * 60 * 60  # keep ids for 48h

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(DB_PATH)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS seen_messages (
                message_id TEXT PRIMARY KEY,
                seen_at REAL NOT NULL
            )
            """
        )
        return conn

    def register(self, message_id: str) -> bool:
        """Atomically record message_id as seen.

        Returns True if this ID was NOT seen before (i.e. should be
        processed), False if it is a duplicate.
        """
        if not message_id:
            return True
        conn = self._get_conn()
        try:
            with conn:
                exists = conn.execute(
                    "SELECT 1 FROM seen_messages WHERE message_id = ?", (message_id,)
                ).fetchone()
                if exists:
                    return False
                conn.execute(
                    "INSERT INTO seen_messages (message_id, seen_at) VALUES (?, ?)",
                    (message_id, time.time()),
                )
            self._prune(conn)
            return True
        except sqlite3.IntegrityError:
            # Lost a race with a concurrent process inserting the same ID.
            # Treating it as seen guarantees the message is processed once.
            return False
        finally:
            conn.close()

    def _prune(self, conn: sqlite3.Connection) -> None:
        try:
            conn.execute(
                "DELETE FROM seen_messages WHERE seen_at < ?",
                (time.time() - self._PRUNE_KEEP_SECONDS,),
            )
            conn.commit()
        except sqlite3.Error:
            logger.exception("Failed to prune seen_messages")


message_ledger = MessageLedger()


session_store = SessionStore()