"""Adaptadores simples: relógio do sistema, fetcher de página e summarizer.

O summarizer via LLM é deixado como implementação plugável — a chamada real
(ex.: API da Claude) entra aqui sem tocar no núcleo.
"""

from __future__ import annotations

import ipaddress
import re
import socket
from datetime import datetime
from html import unescape
from urllib.parse import urlparse

from daily.ports import FetchedPage

_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
_STRIP_BLOCKS_RE = re.compile(r"<(script|style)[^>]*>.*?</\1>", re.IGNORECASE | re.DOTALL)
_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def extract_text_from_html(html: str) -> tuple[str, str]:
    """Extrai (título, texto limpo) de um HTML, sem dependências externas.

    Descarta <script>/<style> e qualquer outra tag, deixando só o texto
    visível — evita despejar marcação crua em resumos e reports.
    """
    title_match = _TITLE_RE.search(html)
    title = _WS_RE.sub(" ", unescape(title_match.group(1))).strip() if title_match else ""

    without_blocks = _STRIP_BLOCKS_RE.sub(" ", html)
    without_tags = _TAG_RE.sub(" ", without_blocks)
    text = _WS_RE.sub(" ", unescape(without_tags)).strip()
    return title, text


def _is_blocked_ip(address: str) -> bool:
    ip = ipaddress.ip_address(address)
    return any(
        (
            ip.is_loopback,
            ip.is_private,
            ip.is_link_local,
            ip.is_multicast,
            ip.is_reserved,
            ip.is_unspecified,
        )
    )


def _validate_fetch_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("URL bloqueada: use apenas http ou https.")

    hostname = parsed.hostname
    if not hostname:
        raise ValueError("URL bloqueada: host ausente.")

    normalized_host = hostname.rstrip(".").lower()
    if normalized_host == "localhost" or normalized_host.endswith(".localhost"):
        raise ValueError("URL bloqueada: host local nao e permitido.")

    try:
        if _is_blocked_ip(normalized_host):
            raise ValueError("URL bloqueada: IP privado ou reservado nao e permitido.")
        return
    except ValueError as exc:
        if str(exc).startswith("URL bloqueada"):
            raise

    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    try:
        resolved = socket.getaddrinfo(normalized_host, port, type=socket.SOCK_STREAM)
    except OSError as exc:
        raise ValueError("URL bloqueada: nao foi possivel resolver o host.") from exc

    for item in resolved:
        resolved_ip = item[4][0]
        if _is_blocked_ip(resolved_ip):
            raise ValueError("URL bloqueada: host resolve para IP privado ou reservado.")


class SystemClock:
    def now(self) -> datetime:
        return datetime.now()


class SimpleFetcher:
    """Fetcher genérico de páginas (site, .docx, Dropbox).

    Extração real (metadados + texto limpo, mammoth para .docx) entra aqui.
    Mantido enxuto no MVP; a interface já está fixada pela port LinkFetcher.
    """

    def fetch(self, url: str) -> FetchedPage:  # pragma: no cover - I/O real
        _validate_fetch_url(url)
        try:
            import requests
        except ImportError as exc:
            raise RuntimeError("Instale 'requests' para o fetcher de páginas.") from exc
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        title, text = extract_text_from_html(resp.text[:20000])
        return FetchedPage(
            title=title or url.rsplit("/", 1)[-1],
            author="",
            published_at="",
            text=text,
        )


class EchoSummarizer:
    """Summarizer placeholder para desenvolvimento sem custo de LLM.

    Troque por um LLMSummarizer que chame a API de sua escolha e produza
    o resumo factual de 3-4 parágrafos exigido no documento.
    """

    def summarize(self, text: str, metadata: dict) -> str:
        title = metadata.get("title", "")
        prefix = f"Resumo de '{title}': " if title else "Resumo: "
        snippet = " ".join(text.split())[:280]
        return prefix + snippet + ("…" if len(text) > 280 else "")
