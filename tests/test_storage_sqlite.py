from datetime import datetime, timedelta

from daily.adapters.storage_sqlite import SqliteStorage
from daily.core.day_service import DayService
from daily.core.models import Entry, EntryType, SessionStatus, Task, TaskStatus, VoiceInterval


def test_sqlite_storage_persiste_e_reidrata_sessao_com_entradas_e_voz(tmp_path):
    storage = SqliteStorage(str(tmp_path / "daily.db"))
    started = datetime(2025, 1, 6, 8, 30)
    session = DayService(storage, _FixedClock(started)).start_day("u1", "c1")

    session.entries.append(
        Entry(
            type=EntryType.DOC,
            raw_input="https://exemplo.com/doc.docx",
            title="Documento",
            summary="Resumo factual",
            metadata={"author": "Equipe"},
            created_at=started + timedelta(minutes=5),
        )
    )
    session.voice.append(
        VoiceInterval(
            joined_at=started + timedelta(minutes=10),
            left_at=started + timedelta(minutes=25),
        )
    )
    session.ended_at = started + timedelta(hours=8)
    session.status = SessionStatus.FECHADA
    storage.save_session(session)

    reloaded = storage.get_session(session.id)
    last_closed = storage.get_last_closed_session("u1")

    assert reloaded is not None
    assert reloaded.status is SessionStatus.FECHADA
    assert reloaded.entries[0].type is EntryType.DOC
    assert reloaded.entries[0].metadata == {"author": "Equipe"}
    assert reloaded.voice_seconds() == 15 * 60
    assert last_closed is not None
    assert last_closed.id == session.id
    assert storage.get_open_session("u1") is None


def test_sqlite_storage_persiste_e_lista_tarefas_com_links_e_feedback(tmp_path):
    storage = SqliteStorage(str(tmp_path / "daily.db"))
    now = datetime(2025, 1, 6, 9, 0)
    task = Task(
        id="task-1",
        title="Criar pipeline",
        status=TaskStatus.EM_ANDAMENTO,
        links=[{"url": "https://exemplo.com", "comment": "referencia"}],
        feedback="aguardando review",
        created_at=now,
        last_activity_at=now + timedelta(minutes=30),
    )

    storage.save_task(task)

    reloaded = storage.get_task("task-1")
    listed = storage.list_tasks()

    assert reloaded is not None
    assert reloaded.status is TaskStatus.EM_ANDAMENTO
    assert reloaded.links == [{"url": "https://exemplo.com", "comment": "referencia"}]
    assert reloaded.feedback == "aguardando review"
    assert [task.id for task in listed] == ["task-1"]
    assert storage.get_task("inexistente") is None


class _FixedClock:
    def __init__(self, now: datetime) -> None:
        self._now = now

    def now(self) -> datetime:
        return self._now
