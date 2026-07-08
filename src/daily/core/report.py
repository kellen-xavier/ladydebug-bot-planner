"""Report de fim de dia: compilado conciso e informativo.

Saída em texto puro, boa tanto para Discord quanto para Slack.
"""

from __future__ import annotations

from collections import defaultdict

from daily.core.models import DaySession, EntryType, Task, TaskStatus

_LABELS = {
    EntryType.COMMIT: "Commits",
    EntryType.PR: "Pull Requests",
    EntryType.DOC: "Documentos",
    EntryType.LINK: "Links",
    EntryType.NOTA: "Notas",
    EntryType.REUNIAO: "Reuniões",
    EntryType.VOZ: "Voz",
}

# Links e documentos ganham uma seção própria no report, separada das
# atividades e das tarefas — são coisas diferentes e não devem se misturar.
_LINK_TYPES = {EntryType.LINK, EntryType.DOC}


def _fmt_duration(seconds: int) -> str:
    h, rem = divmod(seconds, 3600)
    m = rem // 60
    if h and m:
        return f"{h}h{m:02d}"
    if h:
        return f"{h}h"
    return f"{m}min"


def _fmt_time(dt) -> str:
    return dt.strftime("%H:%M") if dt else "—"


def build_report(session: DaySession, tasks: list[Task] | None = None) -> str:
    tasks = tasks or []
    lines: list[str] = []

    day = session.started_at.strftime("%d/%m/%Y")
    lines.append(f"📋 Report do dia — {day}")
    header = f"🕐 Início {_fmt_time(session.started_at)} · Fim {_fmt_time(session.ended_at)}"
    voz = session.voice_seconds()
    if voz:
        header += f" · Em call: {_fmt_duration(voz)}"
    lines.append(header)

    link_entries = [e for e in session.entries if e.type in _LINK_TYPES]
    activity_entries = [e for e in session.entries if e.type not in _LINK_TYPES]

    # Links e referências: seção própria, com a URL sempre visível, para não
    # se confundir com atividades nem com tarefas.
    if link_entries:
        lines.append(f"\n🔗 Links e referências ({len(link_entries)}):")
        for e in link_entries:
            label = e.title or e.raw_input
            lines.append(f"   • {label}")
            if e.summary:
                lines.append(f"     {e.summary}")
            lines.append(f"     ↳ {e.raw_input}")

    # Demais movimentos do dia (commits, PRs, notas, reuniões, voz)
    if activity_entries:
        grouped: dict[EntryType, list] = defaultdict(list)
        for entry in activity_entries:
            grouped[entry.type].append(entry)
        lines.append(f"\n✅ Atividades ({len(activity_entries)}):")
        for etype in EntryType:
            if etype in _LINK_TYPES:
                continue
            items = grouped.get(etype)
            if not items:
                continue
            lines.append(f"\n   {_LABELS[etype]}:")
            for e in items:
                label = e.title or e.raw_input
                detail = f" — {e.summary}" if e.summary else ""
                lines.append(f"   - {label}{detail}")

    if not session.entries:
        lines.append("\n✅ Nenhum movimento registrado hoje.")

    # Tarefas: separadas por uma divisória, para não se misturar com links/atividades.
    if tasks:
        by_status: dict[TaskStatus, list[Task]] = defaultdict(list)
        for t in tasks:
            by_status[t.status].append(t)
        lines.append("\n" + "─" * 30)
        lines.append("🗂 Tarefas:")
        for status in TaskStatus:
            group = by_status.get(status)
            if not group:
                continue
            titles = ", ".join(t.title for t in group)
            lines.append(f"   - {status.value} ({len(group)}): {titles}")

    lines.append("\n— Lembrete para amanhã: retomar as tarefas em andamento.")
    return "\n".join(lines)


def build_recap(previous: DaySession | None, tasks: list[Task] | None = None) -> str:
    """Recap do dia anterior, exibido ao dar /inicio.

    Mostra o que foi registrado na última sessão fechada do usuário e as
    tarefas que ainda estão em aberto (Pendente/Em Andamento).
    """
    if previous is None:
        return ""

    tasks = tasks or []
    open_tasks = [t for t in tasks if t.status in (TaskStatus.PENDENTE, TaskStatus.EM_ANDAMENTO)]

    if not previous.entries and not open_tasks:
        return ""

    day = previous.started_at.strftime("%d/%m/%Y")
    lines = [f"↩️ Retomando de {day}:"]

    if previous.entries:
        lines.append("   Ontem você registrou:")
        for e in previous.entries:
            label = e.title or e.raw_input
            lines.append(f"   • {label}")

    if open_tasks:
        lines.append("   Tarefas ainda em aberto:")
        for t in open_tasks:
            lines.append(f"   • [{t.status.value}] {t.title}")

    return "\n".join(lines)
