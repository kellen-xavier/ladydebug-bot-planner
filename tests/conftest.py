"""Dublês (fakes) — permitem testar o núcleo sem SQLite, rede ou Discord."""

from __future__ import annotations

from datetime import datetime

import pytest

from daily.core.models import DaySession, SessionStatus, Task
from daily.ports import FetchedPage, VCSItem


class FakeClock:
    def __init__(self, start: datetime) -> None:
        self._now = start

    def now(self) -> datetime:
        return self._now

    def advance(self, **kwargs) -> None:
        from datetime import timedelta

        self._now = self._now + timedelta(**kwargs)


class FakeStorage:
    def __init__(self) -> None:
        self.sessions: dict[str, DaySession] = {}
        self.tasks: dict[str, Task] = {}

    def save_session(self, session: DaySession) -> None:
        self.sessions[session.id] = session

    def get_open_session(self, user_id: str) -> DaySession | None:
        for s in self.sessions.values():
            if s.user_id == user_id and s.status is SessionStatus.ABERTA:
                return s
        return None

    def get_session(self, session_id: str) -> DaySession | None:
        return self.sessions.get(session_id)

    def get_last_closed_session(self, user_id: str) -> DaySession | None:
        closed = [
            s
            for s in self.sessions.values()
            if s.user_id == user_id and s.status is SessionStatus.FECHADA
        ]
        if not closed:
            return None
        return max(closed, key=lambda s: s.ended_at)

    def save_task(self, task: Task) -> None:
        self.tasks[task.id] = task

    def get_task(self, task_id: str) -> Task | None:
        return self.tasks.get(task_id)

    def list_tasks(self) -> list[Task]:
        return list(self.tasks.values())


class FakeGitHub:
    def matches(self, url: str) -> bool:
        return "github.com" in url

    def fetch(self, url: str) -> VCSItem:
        return VCSItem(
            kind="commit",
            provider="github",
            repo="acme/app",
            title="corrige parser de datas",
            author="ana",
            url=url,
            additions=45,
            deletions=12,
        )


class FakeFetcher:
    def fetch(self, url: str) -> FetchedPage:
        return FetchedPage(
            title="Documento de Arquitetura",
            author="equipe",
            published_at="2025-01-01",
            text="Conteúdo do documento sobre a arquitetura do sistema.",
        )


class FakeSummarizer:
    def summarize(self, text: str, metadata: dict) -> str:
        return f"[resumo] {metadata.get('title', '')}"


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock(datetime(2025, 1, 6, 8, 32))


@pytest.fixture
def storage() -> FakeStorage:
    return FakeStorage()
