"""Regras do ciclo do dia: /inicio -> registrar movimentos -> /fim.

Lógica pura. Recebe Storage e Clock por injeção (ports), nunca I/O direto.
"""

from __future__ import annotations

from daily.core.models import (
    DaySession,
    Entry,
    SessionStatus,
    VoiceInterval,
)
from daily.ports import Clock, Storage


class DayAlreadyOpen(Exception):
    pass


class NoOpenDay(Exception):
    pass


class DayService:
    def __init__(self, storage: Storage, clock: Clock) -> None:
        self._storage = storage
        self._clock = clock

    def start_day(self, user_id: str, channel_id: str) -> DaySession:
        if self._storage.get_open_session(user_id) is not None:
            raise DayAlreadyOpen("Já existe um dia aberto para este usuário.")
        session = DaySession(
            user_id=user_id,
            channel_id=channel_id,
            started_at=self._clock.now(),
        )
        self._storage.save_session(session)
        return session

    def add_entry(self, user_id: str, entry: Entry) -> DaySession:
        session = self._require_open(user_id)
        if entry.created_at is None:
            entry.created_at = self._clock.now()
        session.entries.append(entry)
        self._storage.save_session(session)
        return session

    def voice_join(self, user_id: str) -> None:
        session = self._require_open(user_id)
        session.voice.append(VoiceInterval(joined_at=self._clock.now()))
        self._storage.save_session(session)

    def voice_leave(self, user_id: str) -> None:
        session = self._require_open(user_id)
        for interval in reversed(session.voice):
            if interval.left_at is None:
                interval.left_at = self._clock.now()
                break
        self._storage.save_session(session)

    def close_day(self, user_id: str) -> DaySession:
        session = self._require_open(user_id)
        now = self._clock.now()
        # fecha qualquer intervalo de voz ainda aberto
        for interval in session.voice:
            if interval.left_at is None:
                interval.left_at = now
        session.ended_at = now
        session.status = SessionStatus.FECHADA
        self._storage.save_session(session)
        return session

    def _require_open(self, user_id: str) -> DaySession:
        session = self._storage.get_open_session(user_id)
        if session is None:
            raise NoOpenDay("Nenhum dia aberto. Use /inicio primeiro.")
        return session
