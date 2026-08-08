"""SQLite-backed persistent session store."""
from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Optional

from models import ConversationState

DB_PATH = Path(__file__).parent / "sessions.db"
TTL_SECONDS = 1800  # 30 min inactivity expiry


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


session_store = SessionStore()