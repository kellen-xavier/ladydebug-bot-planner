"""Máquina de estados das tarefas + detecção de travamento (autorreparo/alerta).

Pendente -> Em Andamento -> Concluído -> Aceito (com reaberturas controladas).
"""

from __future__ import annotations

from datetime import timedelta

from daily.core.models import InvalidTransition, Task, TaskStatus
from daily.ports import Clock, Storage


class TaskNotFound(Exception):
    pass


class TaskService:
    def __init__(self, storage: Storage, clock: Clock) -> None:
        self._storage = storage
        self._clock = clock

    def create_task(self, title: str) -> Task:
        now = self._clock.now()
        task = Task(title=title, created_at=now, last_activity_at=now)
        self._storage.save_task(task)
        return task

    def advance(self, task_id: str, target: TaskStatus) -> Task:
        task = self._require(task_id)
        if not task.can_transition_to(target):
            raise InvalidTransition(
                f"Não é possível ir de '{task.status.value}' para '{target.value}'."
            )
        task.status = target
        task.last_activity_at = self._clock.now()
        self._storage.save_task(task)
        return task

    def finish(self, task_id: str) -> Task:
        """Fecha uma tarefa em aberto, levando-a até 'Concluído'.

        Aceita tarefas em 'Pendente' ou 'Em Andamento' e avança pelos estados
        intermediários necessários, para que fechar seja um único passo. Tarefas
        já 'Concluído' ou 'Aceito' são devolvidas sem alteração (idempotente),
        sem levantar InvalidTransition.
        """
        task = self._require(task_id)
        if task.status in (TaskStatus.CONCLUIDO, TaskStatus.ACEITO):
            return task
        if task.status is TaskStatus.PENDENTE:
            self.advance(task_id, TaskStatus.EM_ANDAMENTO)
        return self.advance(task_id, TaskStatus.CONCLUIDO)

    def add_feedback(self, task_id: str, feedback: str) -> Task:
        task = self._require(task_id)
        task.feedback = feedback
        task.last_activity_at = self._clock.now()
        self._storage.save_task(task)
        return task

    def attach_link(self, task_id: str, url: str, comment: str = "") -> Task:
        task = self._require(task_id)
        task.links.append({"url": url, "comment": comment})
        task.last_activity_at = self._clock.now()
        self._storage.save_task(task)
        return task

    def stalled_tasks(self, threshold: timedelta) -> list[Task]:
        """Tarefas 'Em Andamento' sem atividade há mais que o limite."""
        now = self._clock.now()
        travadas = []
        for task in self._storage.list_tasks():
            if task.status is not TaskStatus.EM_ANDAMENTO:
                continue
            if task.last_activity_at is None:
                continue
            if now - task.last_activity_at > threshold:
                travadas.append(task)
        return travadas

    def _require(self, task_id: str) -> Task:
        task = self._storage.get_task(task_id)
        if task is None:
            raise TaskNotFound(f"Tarefa {task_id} não encontrada.")
        return task
