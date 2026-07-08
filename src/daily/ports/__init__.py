"""Ports: os contratos (interfaces) do núcleo.

O núcleo depende destes Protocols, nunca de implementações concretas.
Isso permite trocar SQLite por Postgres, GitHub por Azure DevOps, ou
injetar dublês nos testes sem tocar na lógica de domínio.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol

from daily.core.models import DaySession, Task


class Clock(Protocol):
    def now(self) -> datetime: ...


class Storage(Protocol):
    def save_session(self, session: DaySession) -> None: ...
    def get_open_session(self, user_id: str) -> DaySession | None: ...
    def get_session(self, session_id: str) -> DaySession | None: ...
    def save_task(self, task: Task) -> None: ...
    def get_task(self, task_id: str) -> Task | None: ...
    def list_tasks(self) -> list[Task]: ...


@dataclass
class VCSItem:
    """Saída normalizada de GitHub e Azure DevOps — o núcleo não sabe qual é."""

    kind: str  # "commit" | "pr"
    provider: str  # "github" | "azure"
    repo: str
    title: str
    author: str
    url: str
    branch: str = ""
    additions: int = 0
    deletions: int = 0
    files: list[str] = field(default_factory=list)


class VCSProvider(Protocol):
    """Um provedor de repositório (GitHub, Azure DevOps, ...)."""

    def matches(self, url: str) -> bool: ...
    def fetch(self, url: str) -> VCSItem: ...


@dataclass
class FetchedPage:
    title: str
    author: str
    published_at: str
    text: str


class LinkFetcher(Protocol):
    """Abre uma URL genérica (site, .docx, Dropbox) e devolve metadados + texto."""

    def fetch(self, url: str) -> FetchedPage: ...


class Summarizer(Protocol):
    """Resumo factual (3-4 parágrafos, sem opinião) — normalmente via LLM."""

    def summarize(self, text: str, metadata: dict) -> str: ...
