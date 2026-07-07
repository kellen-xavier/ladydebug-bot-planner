from datetime import datetime

from daily.core.day_service import DayService
from daily.core.link_ingest import LinkIngestor
from daily.core.models import EntryType
from daily.core.report import build_report
from daily.core.task_service import TaskService
from daily.core.models import TaskStatus

from conftest import FakeFetcher, FakeGitHub, FakeSummarizer


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
