"""Ingestão de links.

Detecta se a URL é de um repositório (GitHub / Azure DevOps) e usa o provedor
de VCS correspondente; senão trata como página genérica (site, .docx, Dropbox),
extrai metadados e gera um resumo factual. Em ambos os casos devolve uma Entry
pronta para ser anexada ao dia.
"""
from __future__ import annotations

from typing import Sequence

from daily.core.models import Entry, EntryType
from daily.ports import LinkFetcher, Summarizer, VCSItem, VCSProvider


class LinkIngestor:
    def __init__(
        self,
        vcs_providers: Sequence[VCSProvider],
        fetcher: LinkFetcher,
        summarizer: Summarizer,
    ) -> None:
        self._providers = list(vcs_providers)
        self._fetcher = fetcher
        self._summarizer = summarizer

    def ingest(self, url: str, comment: str = "") -> Entry:
        for provider in self._providers:
            if provider.matches(url):
                return self._from_vcs(provider.fetch(url), url, comment)
        return self._from_page(url, comment)

    def _from_vcs(self, item: VCSItem, url: str, comment: str) -> Entry:
        etype = EntryType.PR if item.kind == "pr" else EntryType.COMMIT
        title = f"{item.repo}: {item.title}"
        summary = (
            f"{item.provider} · {item.kind} por {item.author} "
            f"(+{item.additions} −{item.deletions})"
        )
        if comment:
            summary += f" — {comment}"
        return Entry(
            type=etype,
            raw_input=url,
            title=title,
            summary=summary,
            metadata={
                "provider": item.provider,
                "kind": item.kind,
                "branch": item.branch,
                "additions": item.additions,
                "deletions": item.deletions,
                "files": item.files,
                "author": item.author,
            },
        )

    def _from_page(self, url: str, comment: str) -> Entry:
        page = self._fetcher.fetch(url)
        summary = self._summarizer.summarize(
            page.text,
            {"title": page.title, "author": page.author, "date": page.published_at},
        )
        if comment:
            summary = f"{comment}\n\n{summary}"
        return Entry(
            type=EntryType.DOC if url.lower().endswith(".docx") else EntryType.LINK,
            raw_input=url,
            title=page.title or url,
            summary=summary,
            metadata={"author": page.author, "date": page.published_at},
        )
