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

    # Movimentos do dia, agrupados por tipo
    grouped: dict[EntryType, list] = defaultdict(list)
    for entry in session.entries:
        grouped[entry.type].append(entry)

    if session.entries:
        lines.append(f"\n✅ Feito hoje ({len(session.entries)} itens):")
        for etype in EntryType:
            items = grouped.get(etype)
            if not items:
                continue
            lines.append(f"\n• {_LABELS[etype]}:")
            for e in items:
                label = e.title or e.raw_input
                detail = f" — {e.summary}" if e.summary else ""
                lines.append(f"   - {label}{detail}")
    else:
        lines.append("\n✅ Nenhum movimento registrado hoje.")

    # Tarefas
    if tasks:
        by_status: dict[TaskStatus, list[Task]] = defaultdict(list)
        for t in tasks:
            by_status[t.status].append(t)
        lines.append("\n🗂 Tarefas:")
        for status in TaskStatus:
            group = by_status.get(status)
            if not group:
                continue
            titles = ", ".join(t.title for t in group)
            lines.append(f"   - {status.value} ({len(group)}): {titles}")

    lines.append("\n— Lembrete para amanhã: retomar as tarefas em andamento.")
    return "\n".join(lines)
