"""Composition root: onde as peças concretas são montadas.

É o único lugar que conhece as implementações concretas. Trocar SQLite por
Postgres, ou adicionar o adaptador do Slack, se resolve aqui.
"""

from __future__ import annotations

import os
from pathlib import Path

from daily.adapters.misc import EchoSummarizer, SimpleFetcher, SystemClock
from daily.adapters.storage_sqlite import SqliteStorage
from daily.adapters.vcs import AzureDevOpsProvider, GitHubProvider
from daily.command_router import CommandRouter
from daily.core.day_service import DayService
from daily.core.link_ingest import LinkIngestor
from daily.core.task_service import TaskService


def db_path_from_env() -> str:
    raw_path = os.environ.get("DB_PATH", "daily.db").strip()
    if not raw_path:
        raise ValueError("DB_PATH nao pode ficar vazio.")

    path = Path(raw_path).expanduser()
    if path.exists() and path.is_dir():
        raise ValueError(f"DB_PATH deve apontar para um arquivo, nao um diretorio: {path}")
    if not path.parent.exists():
        raise ValueError(f"Diretorio pai de DB_PATH nao existe: {path.parent}")

    return str(path)


def build_router() -> CommandRouter:
    clock = SystemClock()
    storage = SqliteStorage(db_path_from_env())

    day = DayService(storage, clock)
    tasks = TaskService(storage, clock)

    providers = [
        GitHubProvider(token=os.environ.get("GITHUB_TOKEN")),
        AzureDevOpsProvider(pat=os.environ.get("AZURE_DEVOPS_PAT")),
    ]
    ingestor = LinkIngestor(providers, SimpleFetcher(), EchoSummarizer())

    return CommandRouter(day, tasks, ingestor, storage)


if __name__ == "__main__":  # pragma: no cover
    from daily.adapters.discord_bot import build_client

    token = os.environ["DISCORD_TOKEN"]
    guild_id = os.environ.get("DISCORD_GUILD_ID")
    build_client(build_router(), guild_id=guild_id).run(token)
