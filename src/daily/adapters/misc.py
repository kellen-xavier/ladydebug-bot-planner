"""Adaptadores simples: relógio do sistema, fetcher de página e summarizer.

O summarizer via LLM é deixado como implementação plugável — a chamada real
(ex.: API da Claude) entra aqui sem tocar no núcleo.
"""

from __future__ import annotations

from datetime import datetime

from daily.ports import FetchedPage


class SystemClock:
    def now(self) -> datetime:
        return datetime.now()


class SimpleFetcher:
    """Fetcher genérico de páginas (site, .docx, Dropbox).

    Extração real (metadados + texto limpo, mammoth para .docx) entra aqui.
    Mantido enxuto no MVP; a interface já está fixada pela port LinkFetcher.
    """

    def fetch(self, url: str) -> FetchedPage:  # pragma: no cover - I/O real
        try:
            import requests
        except ImportError as exc:
            raise RuntimeError("Instale 'requests' para o fetcher de páginas.") from exc
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        # Extração mínima; substituir por extractor dedicado na Fase 1.
        return FetchedPage(
            title=url.rsplit("/", 1)[-1],
            author="",
            published_at="",
            text=resp.text[:20000],
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
