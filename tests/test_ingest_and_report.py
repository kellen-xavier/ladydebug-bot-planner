from conftest import FakeFetcher, FakeGitHub, FakeSummarizer
from daily.command_router import CommandRouter
from daily.core.day_service import DayService
from daily.core.link_ingest import LinkIngestor
from daily.core.models import EntryType, TaskStatus
from daily.core.report import build_report
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
    from daily.core.models import Entry

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
