"""Adaptadores de VCS — GitHub e Azure DevOps.

Ambos implementam a mesma port VCSProvider e devolvem VCSItem, então o núcleo
trata os dois de forma idêntica. As chamadas HTTP usam `requests` (dependência
só dos adaptadores; o núcleo e os testes não importam este módulo).

Requisitos v1: GitHub + Azure DevOps.
"""

from __future__ import annotations

import re

from daily.ports import VCSItem

try:  # requests só é necessário em runtime, não nos testes de núcleo
    import requests
except ImportError:  # pragma: no cover
    requests = None


class GitHubProvider:
    """Reconhece URLs de commit e PR do GitHub."""

    _COMMIT = re.compile(r"github\.com/([^/]+)/([^/]+)/commit/([0-9a-f]+)")
    _PR = re.compile(r"github\.com/([^/]+)/([^/]+)/pull/(\d+)")

    def __init__(self, token: str | None = None) -> None:
        self._token = token

    def matches(self, url: str) -> bool:
        return bool(self._COMMIT.search(url) or self._PR.search(url))

    def _headers(self) -> dict:
        h = {"Accept": "application/vnd.github+json"}
        if self._token:
            h["Authorization"] = f"Bearer {self._token}"
        return h

    def fetch(self, url: str) -> VCSItem:
        if requests is None:  # pragma: no cover
            raise RuntimeError("Instale 'requests' para usar o provedor GitHub.")
        m = self._COMMIT.search(url)
        if m:
            owner, repo, sha = m.groups()
            r = requests.get(
                f"https://api.github.com/repos/{owner}/{repo}/commits/{sha}",
                headers=self._headers(),
                timeout=15,
            )
            r.raise_for_status()
            d = r.json()
            stats = d.get("stats", {})
            return VCSItem(
                kind="commit",
                provider="github",
                repo=f"{owner}/{repo}",
                title=d["commit"]["message"].splitlines()[0],
                author=d["commit"]["author"]["name"],
                url=url,
                additions=stats.get("additions", 0),
                deletions=stats.get("deletions", 0),
                files=[f["filename"] for f in d.get("files", [])],
            )
        m = self._PR.search(url)
        if m:
            owner, repo, number = m.groups()
            r = requests.get(
                f"https://api.github.com/repos/{owner}/{repo}/pulls/{number}",
                headers=self._headers(),
                timeout=15,
            )
            r.raise_for_status()
            d = r.json()
            return VCSItem(
                kind="pr",
                provider="github",
                repo=f"{owner}/{repo}",
                title=d["title"],
                author=d["user"]["login"],
                url=url,
                branch=d["head"]["ref"],
                additions=d.get("additions", 0),
                deletions=d.get("deletions", 0),
            )
        raise ValueError(f"URL do GitHub não reconhecida: {url}")


class AzureDevOpsProvider:
    """Reconhece URLs de commit e PR do Azure DevOps.

    Formatos típicos:
      https://dev.azure.com/{org}/{project}/_git/{repo}/commit/{id}
      https://dev.azure.com/{org}/{project}/_git/{repo}/pullrequest/{id}
    """

    _COMMIT = re.compile(r"dev\.azure\.com/([^/]+)/([^/]+)/_git/([^/]+)/commit/([0-9a-f]+)")
    _PR = re.compile(r"dev\.azure\.com/([^/]+)/([^/]+)/_git/([^/]+)/pullrequest/(\d+)")

    def __init__(self, pat: str | None = None) -> None:
        self._pat = pat  # Personal Access Token

    def matches(self, url: str) -> bool:
        return bool(self._COMMIT.search(url) or self._PR.search(url))

    def _auth(self):
        # Azure DevOps usa Basic auth com usuário vazio + PAT
        return ("", self._pat) if self._pat else None

    def fetch(self, url: str) -> VCSItem:
        if requests is None:  # pragma: no cover
            raise RuntimeError("Instale 'requests' para usar o provedor Azure DevOps.")
        api = "https://dev.azure.com"
        version = "api-version=7.1"

        m = self._COMMIT.search(url)
        if m:
            org, project, repo, cid = m.groups()
            r = requests.get(
                f"{api}/{org}/{project}/_apis/git/repositories/{repo}/commits/{cid}?{version}",
                auth=self._auth(),
                timeout=15,
            )
            r.raise_for_status()
            d = r.json()
            changes = d.get("changeCounts", {})
            return VCSItem(
                kind="commit",
                provider="azure",
                repo=f"{project}/{repo}",
                title=d.get("comment", "").splitlines()[0] if d.get("comment") else "",
                author=d.get("author", {}).get("name", ""),
                url=url,
                additions=changes.get("Add", 0),
                deletions=changes.get("Delete", 0),
            )
        m = self._PR.search(url)
        if m:
            org, project, repo, pid = m.groups()
            r = requests.get(
                f"{api}/{org}/{project}/_apis/git/repositories/{repo}/pullRequests/{pid}?{version}",
                auth=self._auth(),
                timeout=15,
            )
            r.raise_for_status()
            d = r.json()
            return VCSItem(
                kind="pr",
                provider="azure",
                repo=f"{project}/{repo}",
                title=d.get("title", ""),
                author=d.get("createdBy", {}).get("displayName", ""),
                url=url,
                branch=(d.get("sourceRefName", "") or "").replace("refs/heads/", ""),
            )
        raise ValueError(f"URL do Azure DevOps não reconhecida: {url}")
