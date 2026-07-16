from datetime import timedelta

import pytest

from daily.core.models import InvalidTransition, TaskStatus
from daily.core.task_service import TaskNotFound, TaskService


def test_fluxo_completo_valido(storage, clock):
    svc = TaskService(storage, clock)
    t = svc.create_task("implementar /link")
    assert t.status is TaskStatus.PENDENTE
    svc.advance(t.id, TaskStatus.EM_ANDAMENTO)
    svc.advance(t.id, TaskStatus.CONCLUIDO)
    t = svc.advance(t.id, TaskStatus.ACEITO)
    assert t.status is TaskStatus.ACEITO


def test_transicao_ilegal_e_bloqueada(storage, clock):
    svc = TaskService(storage, clock)
    t = svc.create_task("x")
    with pytest.raises(InvalidTransition):
        svc.advance(t.id, TaskStatus.ACEITO)  # não pode pular de Pendente


def test_estado_terminal_nao_transiciona(storage, clock):
    svc = TaskService(storage, clock)
    t = svc.create_task("x")
    svc.advance(t.id, TaskStatus.EM_ANDAMENTO)
    svc.advance(t.id, TaskStatus.CONCLUIDO)
    svc.advance(t.id, TaskStatus.ACEITO)
    with pytest.raises(InvalidTransition):
        svc.advance(t.id, TaskStatus.EM_ANDAMENTO)


def test_deteccao_de_travamento(storage, clock):
    svc = TaskService(storage, clock)
    t = svc.create_task("tarefa lenta")
    svc.advance(t.id, TaskStatus.EM_ANDAMENTO)
    # nada de atividade por 3 dias
    clock.advance(days=3)
    travadas = svc.stalled_tasks(timedelta(days=2))
    assert [x.id for x in travadas] == [t.id]


def test_task_concluida_nao_conta_como_travada(storage, clock):
    svc = TaskService(storage, clock)
    t = svc.create_task("ok")
    svc.advance(t.id, TaskStatus.EM_ANDAMENTO)
    svc.advance(t.id, TaskStatus.CONCLUIDO)
    clock.advance(days=10)
    assert svc.stalled_tasks(timedelta(days=2)) == []


def test_finish_conclui_tarefa_pendente(storage, clock):
    svc = TaskService(storage, clock)
    t = svc.create_task("documentar setup")

    finished = svc.finish(t.id)

    # Fecha em um passo, mesmo saindo de Pendente (passa por Em Andamento).
    assert finished.status is TaskStatus.CONCLUIDO


def test_finish_conclui_tarefa_em_andamento(storage, clock):
    svc = TaskService(storage, clock)
    t = svc.create_task("subir pipeline")
    svc.advance(t.id, TaskStatus.EM_ANDAMENTO)

    finished = svc.finish(t.id)

    assert finished.status is TaskStatus.CONCLUIDO


def test_finish_e_idempotente_em_tarefa_concluida(storage, clock):
    svc = TaskService(storage, clock)
    t = svc.create_task("x")
    svc.finish(t.id)

    again = svc.finish(t.id)  # não deve levantar InvalidTransition

    assert again.status is TaskStatus.CONCLUIDO


def test_finish_nao_altera_tarefa_aceita(storage, clock):
    svc = TaskService(storage, clock)
    t = svc.create_task("x")
    svc.advance(t.id, TaskStatus.EM_ANDAMENTO)
    svc.advance(t.id, TaskStatus.CONCLUIDO)
    svc.advance(t.id, TaskStatus.ACEITO)

    kept = svc.finish(t.id)

    assert kept.status is TaskStatus.ACEITO


def test_finish_atualiza_last_activity(storage, clock):
    svc = TaskService(storage, clock)
    t = svc.create_task("x")
    clock.advance(hours=2)

    finished = svc.finish(t.id)

    assert finished.last_activity_at == clock.now()


def test_finish_tarefa_inexistente_falha_com_erro_controlado(storage, clock):
    svc = TaskService(storage, clock)

    with pytest.raises(TaskNotFound, match="Tarefa task-404 não encontrada"):
        svc.finish("task-404")


def test_add_feedback_atualiza_texto_e_atividade(storage, clock):
    svc = TaskService(storage, clock)
    task = svc.create_task("revisar PR")
    clock.advance(hours=1)

    updated = svc.add_feedback(task.id, "aguardando ajustes")

    assert updated.feedback == "aguardando ajustes"
    assert updated.last_activity_at == clock.now()


def test_attach_link_adiciona_link_e_atualiza_atividade(storage, clock):
    svc = TaskService(storage, clock)
    task = svc.create_task("documentar setup")
    clock.advance(minutes=30)

    updated = svc.attach_link(task.id, "https://exemplo.com", "referencia")

    assert updated.links == [{"url": "https://exemplo.com", "comment": "referencia"}]
    assert updated.last_activity_at == clock.now()


def test_tarefa_inexistente_falha_com_erro_controlado(storage, clock):
    svc = TaskService(storage, clock)

    with pytest.raises(TaskNotFound, match="Tarefa task-404 não encontrada"):
        svc.add_feedback("task-404", "texto")
