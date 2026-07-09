"""Roteador de comandos — a fronteira única entre plataformas e núcleo.

Discord e Slack traduzem seus eventos em chamadas a estes métodos e formatam
o retorno. Nenhuma regra de negócio vive nos adaptadores de plataforma.
"""

from __future__ import annotations

from daily.core.day_service import DayAlreadyOpen, DayService, NoOpenDay
from daily.core.link_ingest import LinkIngestor
from daily.core.models import Entry, EntryType
from daily.core.report import build_recap, build_report
from daily.core.task_service import TaskNotFound, TaskService


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
        try:
            s = self._day.start_day(user_id, channel_id)
        except DayAlreadyOpen:
            return "🟡 Já existe um dia aberto para você. Use `/continuar` para seguir o seu dia."
        msg = f"🟢 Dia iniciado às {s.started_at.strftime('%H:%M')}."
        recap = build_recap(previous, tasks)
        return f"{recap}\n\n{msg}" if recap else msg

    def continuar(self, user_id: str) -> str:
        session = self._storage.get_open_session(user_id)
        if session is None:
            return "⚠️ Nenhum dia aberto. Use /inicio primeiro."
        return (
            f"🟢 Dia aberto desde {session.started_at.strftime('%H:%M')}. "
            "Pode seguir registrando suas atividades."
        )

    def nota(self, user_id: str, texto: str) -> str:
        try:
            self._day.add_entry(user_id, Entry(type=EntryType.NOTA, raw_input=texto, title=texto))
        except NoOpenDay:
            return "⚠️ Nenhum dia aberto. Use /inicio primeiro."
        return "📝 Nota registrada."

    def link(self, user_id: str, url: str, comentario: str = "") -> str:
        if self._storage.get_open_session(user_id) is None:
            return "⚠️ Nenhum dia aberto. Use /inicio primeiro."
        try:
            entry = self._ingestor.ingest(url, comentario)
        except Exception:
            return "⚠️ Não consegui processar esse link agora. Tente novamente mais tarde."
        try:
            self._day.add_entry(user_id, entry)
        except NoOpenDay:
            return "⚠️ Nenhum dia aberto. Use /inicio primeiro."
        return f"🔗 Registrado: {entry.title}"

    def pr(self, user_id: str, url: str, comentario: str = "") -> str:
        if self._storage.get_open_session(user_id) is None:
            return "⚠️ Nenhum dia aberto. Use /inicio primeiro."
        try:
            entry = self._ingestor.ingest(url, comentario)
        except Exception:
            return "⚠️ Não consegui processar esse PR agora. Tente novamente mais tarde."
        if entry.type is not EntryType.PR:
            return "⚠️ A URL informada não parece ser um Pull Request."
        try:
            self._day.add_entry(user_id, entry)
        except NoOpenDay:
            return "⚠️ Nenhum dia aberto. Use /inicio primeiro."
        return f"🔀 PR registrado: {entry.title}"

    def task_nova(self, titulo: str) -> str:
        t = self._tasks.create_task(titulo)
        return f"🗂 Tarefa criada [{t.id}]: {titulo}"

    def task_status(self) -> str:
        tasks = self._storage.list_tasks()
        if not tasks:
            return "Nenhuma tarefa."
        return "\n".join(f"[{t.id}] {t.status.value} — {t.title}" for t in tasks)

    def feedback(self, task_id: str, texto: str) -> str:
        try:
            self._tasks.add_feedback(task_id, texto)
        except TaskNotFound:
            return f"⚠️ Tarefa {task_id} não encontrada."
        return "💬 Feedback salvo."

    def fim(self, user_id: str) -> str:
        try:
            session = self._day.close_day(user_id)
        except NoOpenDay:
            return "⚠️ Nenhum dia aberto para fechar. Use /inicio para começar."
        return build_report(session, self._storage.list_tasks())
