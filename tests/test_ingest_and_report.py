from conftest import FakeFetcher, FakeGitHub, FakeSummarizer
from daily.command_router import CommandRouter
from daily.core.day_service import DayService
from daily.core.link_ingest import LinkIngestor
from daily.core.models import Entry, EntryType, Task, TaskStatus
from daily.core.report import build_recap, build_report
from daily.core.task_service import TaskService


class FailingFetcher:
    def fetch(self, url: str):
        raise RuntimeError("fetch falhou com token SECRET")


class FailingSummarizer:
    def summarize(self, text: str, metadata: dict) -> str:
        raise RuntimeError("resumo falhou com token SECRET")


def test_ingest_github_vira_entry_de_commit(clock):
    ingestor = LinkIngestor([FakeGitHub()], FakeFetcher(), FakeSummarizer())
    entry = ingestor.ingest("https://github.com/acme/app/commit/abc123", "revisão")
    assert entry.type is EntryType.COMMIT
    assert "acme/app" in entry.title
    assert entry.metadata["additions"] == 45


def test_ingest_url_generica_usa_summarizer(clock):
    ingestor = LinkIngestor([FakeGitHub()], FakeFetcher(), FakeSummarizer())
    entry = ingestor.ingest("https://exemplo.com/artigo")
    assert entry.type is EntryType.LINK
    assert entry.summary.startswith("[resumo]")


def test_report_agrupa_e_e_conciso(storage, clock):
    day = DayService(storage, clock)
    tasks = TaskService(storage, clock)
    ingestor = LinkIngestor([FakeGitHub()], FakeFetcher(), FakeSummarizer())

    day.start_day("u1", "c1")
    day.add_entry("u1", ingestor.ingest("https://github.com/acme/app/commit/abc"))
    day.add_entry("u1", Entry(type=EntryType.NOTA, raw_input="revisei a doc de arquitetura"))
    t = tasks.create_task("implementar /fim")
    tasks.advance(t.id, TaskStatus.EM_ANDAMENTO)

    session = day.close_day("u1")
    report = build_report(session, storage.list_tasks())

    assert "Report do dia" in report
    assert "Commits" in report
    assert "revisei a doc de arquitetura" in report
    assert "Em Andamento (1)" in report


def test_erro_de_fetch_nao_quebra_fechamento_do_dia(storage, clock):
    day = DayService(storage, clock)
    tasks = TaskService(storage, clock)
    ingestor = LinkIngestor([], FailingFetcher(), FakeSummarizer())
    router = CommandRouter(day, tasks, ingestor, storage)

    router.inicio("u1", "c1")
    msg = router.link("u1", "https://exemplo.com/privado")
    report = router.fim("u1")

    assert "Não consegui processar esse link" in msg
    assert "SECRET" not in msg
    assert "Report do dia" in report


def test_report_separa_links_de_tarefas(storage, clock):
    day = DayService(storage, clock)
    ingestor = LinkIngestor([], FakeFetcher(), FakeSummarizer())

    day.start_day("u1", "c1")
    day.add_entry("u1", ingestor.ingest("https://exemplo.com/artigo"))
    session = day.close_day("u1")

    task = Task(title="Criar Pipeline no Github Actions", status=TaskStatus.PENDENTE)
    report = build_report(session, [task])

    links_idx = report.index("🔗 Links e referências")
    task_idx = report.index("🗂 Tarefas")
    assert links_idx < task_idx
    # a URL do link aparece na seção de links, não misturada com a de tarefas
    assert "https://exemplo.com/artigo" in report[links_idx:task_idx]
    assert "https://exemplo.com/artigo" not in report[task_idx:]
    assert task.title not in report[links_idx:task_idx]


def test_erro_de_resumo_nao_quebra_fechamento_do_dia(storage, clock):
    day = DayService(storage, clock)
    tasks = TaskService(storage, clock)
    ingestor = LinkIngestor([], FakeFetcher(), FailingSummarizer())
    router = CommandRouter(day, tasks, ingestor, storage)

    router.inicio("u1", "c1")
    msg = router.link("u1", "https://exemplo.com/doc")
    report = router.fim("u1")

    assert "Não consegui processar esse link" in msg
    assert "SECRET" not in msg
    assert "Report do dia" in report


def test_build_recap_sem_sessao_anterior_e_vazio():
    assert build_recap(None) == ""


def test_build_recap_lista_entradas_de_ontem_e_tarefas_abertas(storage, clock):
    day = DayService(storage, clock)
    day.start_day("u1", "c1")
    day.add_entry("u1", Entry(type=EntryType.NOTA, raw_input="referencias para documentacao"))
    previous = day.close_day("u1")

    aberta = Task(title="Criar Pipeline no Github Actions", status=TaskStatus.PENDENTE)
    concluida = Task(title="tarefa já concluída", status=TaskStatus.CONCLUIDO)

    recap = build_recap(previous, [aberta, concluida])

    assert "referencias para documentacao" in recap
    assert "Criar Pipeline no Github Actions" in recap
    assert "tarefa já concluída" not in recap


def test_inicio_retoma_atividades_do_dia_anterior(storage, clock):
    day = DayService(storage, clock)
    tasks = TaskService(storage, clock)
    ingestor = LinkIngestor([], FakeFetcher(), FakeSummarizer())
    router = CommandRouter(day, tasks, ingestor, storage)

    router.inicio("u1", "c1")
    day.add_entry("u1", Entry(type=EntryType.NOTA, raw_input="trabalho de ontem"))
    tasks.create_task("tarefa pendente de ontem")
    router.fim("u1")

    clock.advance(hours=12)
    msg = router.inicio("u1", "c1")

    assert "↩️ Retomando de" in msg
    assert "trabalho de ontem" in msg
    assert "tarefa pendente de ontem" in msg
    assert "🟢 Dia iniciado" in msg


def test_inicio_com_dia_aberto_retorna_mensagem_amigavel(storage, clock):
    day = DayService(storage, clock)
    tasks = TaskService(storage, clock)
    ingestor = LinkIngestor([], FakeFetcher(), FakeSummarizer())
    router = CommandRouter(day, tasks, ingestor, storage)

    router.inicio("u1", "c1")
    msg = router.inicio("u1", "c1")

    assert msg == "🟡 Já existe um dia aberto para você. Use `/continuar` para seguir o seu dia."


def test_continuar_com_dia_aberto_permite_seguir_o_dia(storage, clock):
    day = DayService(storage, clock)
    tasks = TaskService(storage, clock)
    ingestor = LinkIngestor([], FakeFetcher(), FakeSummarizer())
    router = CommandRouter(day, tasks, ingestor, storage)

    router.inicio("u1", "c1")
    msg = router.continuar("u1")
    note_msg = router.nota("u1", "continuei as atividades")

    assert "Dia aberto desde 08:32" in msg
    assert note_msg == "📝 Nota registrada."
    assert len(storage.get_open_session("u1").entries) == 1


def test_continuar_sem_dia_aberto_orienta_inicio(storage, clock):
    day = DayService(storage, clock)
    tasks = TaskService(storage, clock)
    ingestor = LinkIngestor([], FakeFetcher(), FakeSummarizer())
    router = CommandRouter(day, tasks, ingestor, storage)

    msg = router.continuar("u1")

    assert msg == "⚠️ Nenhum dia aberto. Use /inicio primeiro."


def test_nota_sem_dia_aberto_retorna_mensagem_amigavel(storage, clock):
    day = DayService(storage, clock)
    tasks = TaskService(storage, clock)
    ingestor = LinkIngestor([], FakeFetcher(), FakeSummarizer())
    router = CommandRouter(day, tasks, ingestor, storage)

    msg = router.nota("u1", "sem inicio")

    assert msg == "⚠️ Nenhum dia aberto. Use /inicio primeiro."


def test_fim_sem_dia_aberto_retorna_mensagem_amigavel(storage, clock):
    day = DayService(storage, clock)
    tasks = TaskService(storage, clock)
    ingestor = LinkIngestor([], FakeFetcher(), FakeSummarizer())
    router = CommandRouter(day, tasks, ingestor, storage)

    msg = router.fim("u1")

    assert msg == "⚠️ Nenhum dia aberto para fechar. Use /inicio para começar."


def test_link_sem_dia_aberto_retorna_mensagem_amigavel(storage, clock):
    day = DayService(storage, clock)
    tasks = TaskService(storage, clock)
    ingestor = LinkIngestor([], FailingFetcher(), FakeSummarizer())
    router = CommandRouter(day, tasks, ingestor, storage)

    msg = router.link("u1", "https://exemplo.com/doc")

    assert msg == "⚠️ Nenhum dia aberto. Use /inicio primeiro."
