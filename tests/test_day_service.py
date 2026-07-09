import pytest

from daily.core.day_service import DayAlreadyOpen, DayService, NoOpenDay
from daily.core.models import Entry, EntryType, SessionStatus
from tests.conftest import FakeClock, FakeStorage


def test_start_day_cria_sessao_aberta(storage: FakeStorage, clock: FakeClock):
    svc = DayService(storage, clock)
    session = svc.start_day("u1", "c1")
    assert session.status is SessionStatus.ABERTA
    assert session.started_at == clock.now()


def test_nao_permite_dois_dias_abertos(storage: FakeStorage, clock: FakeClock):
    svc = DayService(storage, clock)
    svc.start_day("u1", "c1")
    with pytest.raises(DayAlreadyOpen):
        svc.start_day("u1", "c1")


def test_add_entry_anexa_ao_dia_aberto(storage: FakeStorage, clock: FakeClock):
    svc = DayService(storage, clock)
    svc.start_day("u1", "c1")
    svc.add_entry("u1", Entry(type=EntryType.NOTA, raw_input="revisei a doc"))
    session = storage.get_open_session("u1")
    assert len(session.entries) == 1
    assert session.entries[0].created_at == clock.now()


def test_add_entry_sem_dia_aberto_falha(storage: FakeStorage, clock: FakeClock):
    svc = DayService(storage, clock)
    with pytest.raises(NoOpenDay):
        svc.add_entry("u1", Entry(type=EntryType.NOTA, raw_input="x"))


def test_close_day_fecha_e_soma_voz(storage: FakeStorage, clock: FakeClock):
    svc = DayService(storage, clock)
    svc.start_day("u1", "c1")
    svc.voice_join("u1")
    clock.advance(minutes=30)
    svc.voice_leave("u1")
    clock.advance(hours=2)
    session = svc.close_day("u1")
    assert session.status is SessionStatus.FECHADA
    assert session.voice_seconds() == 30 * 60


def test_close_day_fecha_intervalo_de_voz_pendente(storage: FakeStorage, clock: FakeClock):
    svc = DayService(storage, clock)
    svc.start_day("u1", "c1")
    svc.voice_join("u1")
    clock.advance(minutes=15)
    session = svc.close_day("u1")  # entrou em call e nunca saiu
    assert session.voice_seconds() == 15 * 60
