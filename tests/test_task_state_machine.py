from datetime import timedelta

import pytest

from daily.core.models import InvalidTransition, TaskStatus
from daily.core.task_service import TaskService


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
