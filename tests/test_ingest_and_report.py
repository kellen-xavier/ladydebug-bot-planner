from datetime import datetime, timedelta

from conftest import FakeFetcher, FakeGitHub, FakeSummarizer
from daily.command_router import CommandRouter
from daily.core.day_service import DayService
from daily.core.link_ingest import LinkIngestor
from daily.core.models import DaySession, Entry, EntryType, Task, TaskStatus, VoiceInterval
from daily.core.report import build_recap, build_report
from daily.core.task_service import TaskService
from daily.ports import FetchedPage, VCSItem


class FailingFetcher:
    def fetch(self, url: str):
        raise RuntimeError("fetch falhou com token SECRET")


class FailingSummarizer:
    def summarize(self, text: str, metadata: dict) -> str:
        raise RuntimeError("resumo falhou com token SECRET")


class FakePRProvider:
    def matches(self, url: str) -> bool:
        return "pull" in url

    def fetch(self, url: str) -> VCSItem:
        return VCSItem(
            kind="pr",
            provider="github",
            repo="acme/app",
            title="Adiciona comando continuar",
            author="ana",
            url=url,
            branch="feature/continuar",
            additions=12,
            deletions=3,
            files=["src/daily/command_router.py"],
        )


class UntitledFetcher:
    def fetch(self, url: str) -> FetchedPage:
        return FetchedPage(title="", author="", published_at="", text="conteudo sem titulo")


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


def test_ingest_pr_vira_entry_de_pr_com_comentario_e_metadados():
    ingestor = LinkIngestor([FakePRProvider()], FakeFetcher(), FakeSummarizer())

    entry = ingestor.ingest("https://github.com/acme/app/pull/10", "validar no staging")

    assert entry.type is EntryType.PR
    assert entry.title == "acme/app: Adiciona comando continuar"
    assert "github · pr por ana (+12 −3)" in entry.summary
    assert "validar no staging" in entry.summary
    assert entry.metadata["branch"] == "feature/continuar"
    assert entry.metadata["files"] == ["src/daily/command_router.py"]


def test_router_pr_registra_pull_request_para_report(storage, clock):
    day = DayService(storage, clock)
    tasks = TaskService(storage, clock)
    ingestor = LinkIngestor([FakePRProvider()], FakeFetcher(), FakeSummarizer())
    router = CommandRouter(day, tasks, ingestor, storage)

    router.inicio("u1", "c1")
    msg = router.pr("u1", "https://github.com/acme/app/pull/10", "validar no staging")
    report = router.fim("u1")

    assert msg == "🔀 PR registrado: acme/app: Adiciona comando continuar"
    assert "Pull Requests:" in report
    assert "acme/app: Adiciona comando continuar" in report
    assert "validar no staging" in report


def test_router_pr_rejeita_url_que_nao_e_pull_request(storage, clock):
    day = DayService(storage, clock)
    tasks = TaskService(storage, clock)
    ingestor = LinkIngestor([FakeGitHub()], FakeFetcher(), FakeSummarizer())
    router = CommandRouter(day, tasks, ingestor, storage)

    router.inicio("u1", "c1")
    msg = router.pr("u1", "https://github.com/acme/app/commit/abc123")

    assert msg == "⚠️ A URL informada não parece ser um Pull Request."
    assert storage.get_open_session("u1").entries == []


def test_ingest_docx_vira_entry_de_doc_e_preserva_comentario():
    ingestor = LinkIngestor([], FakeFetcher(), FakeSummarizer())

    entry = ingestor.ingest("https://exemplo.com/plano.docx", "documento prioritario")

    assert entry.type is EntryType.DOC
    assert entry.title == "Documento de Arquitetura"
    assert entry.summary.startswith("documento prioritario\n\n")
    assert "[resumo] Documento de Arquitetura" in entry.summary
    assert entry.metadata == {"author": "equipe", "date": "2025-01-01"}


def test_ingest_url_generica_sem_titulo_usa_url_como_fallback():
    ingestor = LinkIngestor([], UntitledFetcher(), FakeSummarizer())

    entry = ingestor.ingest("https://exemplo.com/sem-titulo")

    assert entry.type is EntryType.LINK
    assert entry.title == "https://exemplo.com/sem-titulo"


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


def test_report_sessao_sem_movimentos_exibe_mensagem_explicita():
    session = DaySession(
        user_id="u1",
        channel_id="c1",
        started_at=datetime(2025, 1, 6, 8, 0),
        ended_at=datetime(2025, 1, 6, 17, 0),
    )

    report = build_report(session)

    assert "✅ Nenhum movimento registrado hoje." in report
    assert "Lembrete para amanhã" in report


def test_report_exibe_documentos_em_links_e_pr_em_atividades():
    session = DaySession(
        user_id="u1",
        channel_id="c1",
        started_at=datetime(2025, 1, 6, 8, 0),
        ended_at=datetime(2025, 1, 6, 17, 0),
    )
    session.entries = [
        Entry(
            type=EntryType.DOC,
            raw_input="https://exemplo.com/plano.docx",
            title="Plano",
            summary="Resumo do plano",
        ),
        Entry(
            type=EntryType.PR,
            raw_input="https://github.com/acme/app/pull/1",
            title="acme/app: PR",
            summary="github · pr por ana",
        ),
    ]

    report = build_report(session)

    assert "🔗 Links e referências (1):" in report
    assert "https://exemplo.com/plano.docx" in report
    assert "Pull Requests:" in report
    assert "acme/app: PR — github · pr por ana" in report


def test_report_formata_duracao_de_voz_com_horas_e_minutos():
    start = datetime(2025, 1, 6, 8, 0)
    session = DaySession(
        user_id="u1",
        channel_id="c1",
        started_at=start,
        ended_at=start + timedelta(hours=8),
    )
    session.voice = [VoiceInterval(joined_at=start, left_at=start + timedelta(hours=1, minutes=5))]

    report = build_report(session)

    assert "Em call: 1h05" in report


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


def test_task_status_sem_tarefas_retorna_mensagem_vazia(storage, clock):
    day = DayService(storage, clock)
    tasks = TaskService(storage, clock)
    ingestor = LinkIngestor([], FakeFetcher(), FakeSummarizer())
    router = CommandRouter(day, tasks, ingestor, storage)

    assert router.task_status() == "Nenhuma tarefa."


def test_task_status_lista_tarefas_com_status(storage, clock):
    day = DayService(storage, clock)
    tasks = TaskService(storage, clock)
    ingestor = LinkIngestor([], FakeFetcher(), FakeSummarizer())
    router = CommandRouter(day, tasks, ingestor, storage)

    created = tasks.create_task("Criar checklist")

    msg = router.task_status()

    assert f"[{created.id}] Pendente — Criar checklist" in msg


def test_feedback_salva_texto_na_tarefa(storage, clock):
    day = DayService(storage, clock)
    tasks = TaskService(storage, clock)
    ingestor = LinkIngestor([], FakeFetcher(), FakeSummarizer())
    router = CommandRouter(day, tasks, ingestor, storage)
    task = tasks.create_task("Revisar doc")

    msg = router.feedback(task.id, "faltou validar no servidor")

    assert msg == "💬 Feedback salvo."
    assert storage.get_task(task.id).feedback == "faltou validar no servidor"


def test_feedback_com_tarefa_inexistente_retorna_mensagem_amigavel(storage, clock):
    day = DayService(storage, clock)
    tasks = TaskService(storage, clock)
    ingestor = LinkIngestor([], FakeFetcher(), FakeSummarizer())
    router = CommandRouter(day, tasks, ingestor, storage)

    msg = router.feedback("task-inexistente", "texto")

    assert msg == "⚠️ Tarefa task-inexistente não encontrada."
