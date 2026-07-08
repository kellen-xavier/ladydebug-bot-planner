"""Roteador de comandos — a fronteira única entre plataformas e núcleo.

Discord e Slack traduzem seus eventos em chamadas a estes métodos e formatam
o retorno. Nenhuma regra de negócio vive nos adaptadores de plataforma.
"""

from __future__ import annotations

from daily.core.day_service import DayService
from daily.core.link_ingest import LinkIngestor
from daily.core.models import Entry, EntryType
from daily.core.report import build_recap, build_report
from daily.core.task_service import TaskService


class CommandRouter:
    def __init__(
        self,
        day: DayService,
        tasks: TaskService,
        ingestor: LinkIngestor,
        storage,
    ) -> None:
        self._day = day
        self._tasks = tasks
        self._ingestor = ingestor
        self._storage = storage

    def inicio(self, user_id: str, channel_id: str) -> str:
        previous = self._storage.get_last_closed_session(user_id)
        tasks = self._storage.list_tasks()
        s = self._day.start_day(user_id, channel_id)
        msg = f"🟢 Dia iniciado às {s.started_at.strftime('%H:%M')}."
        recap = build_recap(previous, tasks)
        return f"{recap}\n\n{msg}" if recap else msg

    def nota(self, user_id: str, texto: str) -> str:
        self._day.add_entry(user_id, Entry(type=EntryType.NOTA, raw_input=texto, title=texto))
        return "📝 Nota registrada."

    def link(self, user_id: str, url: str, comentario: str = "") -> str:
        try:
            entry = self._ingestor.ingest(url, comentario)
        except Exception:
            return "⚠️ Não consegui processar esse link agora. Tente novamente mais tarde."
        self._day.add_entry(user_id, entry)
        return f"🔗 Registrado: {entry.title}"

    def task_nova(self, titulo: str) -> str:
        t = self._tasks.create_task(titulo)
        return f"🗂 Tarefa criada [{t.id}]: {titulo}"

    def task_status(self) -> str:
        tasks = self._storage.list_tasks()
        if not tasks:
            return "Nenhuma tarefa."
        return "\n".join(f"[{t.id}] {t.status.value} — {t.title}" for t in tasks)

    def feedback(self, task_id: str, texto: str) -> str:
        self._tasks.add_feedback(task_id, texto)
        return "💬 Feedback salvo."

    def fim(self, user_id: str) -> str:
        session = self._day.close_day(user_id)
        return build_report(session, self._storage.list_tasks())
