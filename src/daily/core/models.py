"""Modelos de domínio — puros, sem dependência de plataforma ou I/O.

Tudo aqui é testável isoladamente (é o coração da arquitetura hexagonal).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


class EntryType(str, Enum):
    LINK = "link"
    COMMIT = "commit"
    PR = "pr"
    DOC = "doc"
    NOTA = "nota"
    REUNIAO = "reuniao"
    VOZ = "voz"


class SessionStatus(str, Enum):
    ABERTA = "aberta"
    FECHADA = "fechada"


class TaskStatus(str, Enum):
    PENDENTE = "Pendente"
    EM_ANDAMENTO = "Em Andamento"
    CONCLUIDO = "Concluído"
    ACEITO = "Aceito"


# Máquina de estados das tarefas. Fluxo normal para frente + reabertura controlada.
ALLOWED_TRANSITIONS: dict[TaskStatus, set[TaskStatus]] = {
    TaskStatus.PENDENTE: {TaskStatus.EM_ANDAMENTO},
    TaskStatus.EM_ANDAMENTO: {TaskStatus.CONCLUIDO, TaskStatus.PENDENTE},
    TaskStatus.CONCLUIDO: {TaskStatus.ACEITO, TaskStatus.EM_ANDAMENTO},
    TaskStatus.ACEITO: set(),  # estado terminal
}


class InvalidTransition(Exception):
    """Transição de estado não permitida pela máquina de estados."""


@dataclass
class Entry:
    """Um 'movimento do dia': um link, commit, doc, nota, reunião, etc."""

    type: EntryType
    raw_input: str
    title: str = ""
    summary: str = ""
    metadata: dict = field(default_factory=dict)
    id: str = field(default_factory=_new_id)
    created_at: datetime | None = None


@dataclass
class VoiceInterval:
    joined_at: datetime
    left_at: datetime | None = None

    def seconds(self) -> int:
        if self.left_at is None:
            return 0
        return int((self.left_at - self.joined_at).total_seconds())


@dataclass
class DaySession:
    user_id: str
    channel_id: str
    started_at: datetime
    id: str = field(default_factory=_new_id)
    ended_at: datetime | None = None
    status: SessionStatus = SessionStatus.ABERTA
    entries: list[Entry] = field(default_factory=list)
    voice: list[VoiceInterval] = field(default_factory=list)

    def voice_seconds(self) -> int:
        return sum(v.seconds() for v in self.voice)


@dataclass
class Task:
    title: str
    id: str = field(default_factory=_new_id)
    status: TaskStatus = TaskStatus.PENDENTE
    links: list[dict] = field(default_factory=list)  # {"url":..., "comment":...}
    feedback: str = ""
    created_at: datetime | None = None
    last_activity_at: datetime | None = None

    def can_transition_to(self, target: TaskStatus) -> bool:
        return target in ALLOWED_TRANSITIONS[self.status]
