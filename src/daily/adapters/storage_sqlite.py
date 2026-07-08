"""Storage em SQLite usando apenas a stdlib (sqlite3 + json).

Serializa os agregados como JSON para o MVP. Ao migrar para Postgres,
troca-se só esta classe — o núcleo não muda (é a vantagem da port Storage).
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime

from daily.core.models import (
    DaySession,
    Entry,
    EntryType,
    SessionStatus,
    Task,
    TaskStatus,
    VoiceInterval,
)


def _iso(dt: datetime | None) -> str | None:
    return dt.isoformat() if dt else None


def _dt(s: str | None) -> datetime | None:
    return datetime.fromisoformat(s) if s else None


class SqliteStorage:
    def __init__(self, path: str = "daily.db") -> None:
        self._conn = sqlite3.connect(path)
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS sessions "
            "(id TEXT PRIMARY KEY, user_id TEXT, status TEXT, data TEXT)"
        )
        self._conn.execute("CREATE TABLE IF NOT EXISTS tasks (id TEXT PRIMARY KEY, data TEXT)")
        self._conn.commit()

    # ---- sessions ----
    def save_session(self, session: DaySession) -> None:
        payload = {
            "id": session.id,
            "user_id": session.user_id,
            "channel_id": session.channel_id,
            "started_at": _iso(session.started_at),
            "ended_at": _iso(session.ended_at),
            "status": session.status.value,
            "entries": [
                {
                    "id": e.id,
                    "type": e.type.value,
                    "raw_input": e.raw_input,
                    "title": e.title,
                    "summary": e.summary,
                    "metadata": e.metadata,
                    "created_at": _iso(e.created_at),
                }
                for e in session.entries
            ],
            "voice": [
                {"joined_at": _iso(v.joined_at), "left_at": _iso(v.left_at)} for v in session.voice
            ],
        }
        self._conn.execute(
            "INSERT OR REPLACE INTO sessions (id, user_id, status, data) VALUES (?, ?, ?, ?)",
            (session.id, session.user_id, session.status.value, json.dumps(payload)),
        )
        self._conn.commit()

    def get_open_session(self, user_id: str) -> DaySession | None:
        row = self._conn.execute(
            "SELECT data FROM sessions WHERE user_id = ? AND status = ? LIMIT 1",
            (user_id, SessionStatus.ABERTA.value),
        ).fetchone()
        return self._hydrate_session(row[0]) if row else None

    def get_session(self, session_id: str) -> DaySession | None:
        row = self._conn.execute("SELECT data FROM sessions WHERE id = ?", (session_id,)).fetchone()
        return self._hydrate_session(row[0]) if row else None

    def get_last_closed_session(self, user_id: str) -> DaySession | None:
        rows = self._conn.execute(
            "SELECT data FROM sessions WHERE user_id = ? AND status = ?",
            (user_id, SessionStatus.FECHADA.value),
        ).fetchall()
        sessions = [self._hydrate_session(r[0]) for r in rows]
        if not sessions:
            return None
        return max(sessions, key=lambda s: s.ended_at)

    def _hydrate_session(self, raw: str) -> DaySession:
        d = json.loads(raw)
        session = DaySession(
            id=d["id"],
            user_id=d["user_id"],
            channel_id=d["channel_id"],
            started_at=_dt(d["started_at"]),
            ended_at=_dt(d["ended_at"]),
            status=SessionStatus(d["status"]),
        )
        session.entries = [
            Entry(
                id=e["id"],
                type=EntryType(e["type"]),
                raw_input=e["raw_input"],
                title=e["title"],
                summary=e["summary"],
                metadata=e["metadata"],
                created_at=_dt(e["created_at"]),
            )
            for e in d["entries"]
        ]
        session.voice = [
            VoiceInterval(joined_at=_dt(v["joined_at"]), left_at=_dt(v["left_at"]))
            for v in d["voice"]
        ]
        return session

    # ---- tasks ----
    def save_task(self, task: Task) -> None:
        payload = {
            "id": task.id,
            "title": task.title,
            "status": task.status.value,
            "links": task.links,
            "feedback": task.feedback,
            "created_at": _iso(task.created_at),
            "last_activity_at": _iso(task.last_activity_at),
        }
        self._conn.execute(
            "INSERT OR REPLACE INTO tasks (id, data) VALUES (?, ?)",
            (task.id, json.dumps(payload)),
        )
        self._conn.commit()

    def get_task(self, task_id: str) -> Task | None:
        row = self._conn.execute("SELECT data FROM tasks WHERE id = ?", (task_id,)).fetchone()
        return self._hydrate_task(row[0]) if row else None

    def list_tasks(self) -> list[Task]:
        rows = self._conn.execute("SELECT data FROM tasks").fetchall()
        return [self._hydrate_task(r[0]) for r in rows]

    def _hydrate_task(self, raw: str) -> Task:
        d = json.loads(raw)
        return Task(
            id=d["id"],
            title=d["title"],
            status=TaskStatus(d["status"]),
            links=d["links"],
            feedback=d["feedback"],
            created_at=_dt(d["created_at"]),
            last_activity_at=_dt(d["last_activity_at"]),
        )
