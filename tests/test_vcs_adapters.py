import pytest

from daily.adapters import vcs
from daily.adapters.vcs import AzureDevOpsProvider, GitHubProvider


def test_github_provider_fetch_commit_com_requests_fake(monkeypatch):
    fake_requests = _FakeRequests(
        {
            "commit": {
                "message": "corrige parser\n\nDetalhes",
                "author": {"name": "Ana"},
            },
            "stats": {"additions": 10, "deletions": 2},
            "files": [{"filename": "src/app.py"}],
        }
    )
    monkeypatch.setattr(vcs, "requests", fake_requests)

    provider = GitHubProvider(token="gh-token")
    item = provider.fetch("https://github.com/acme/app/commit/abc123")

    assert provider.matches("https://github.com/acme/app/commit/abc123") is True
    assert item.kind == "commit"
    assert item.provider == "github"
    assert item.repo == "acme/app"
    assert item.title == "corrige parser"
    assert item.author == "Ana"
    assert item.additions == 10
    assert item.deletions == 2
    assert item.files == ["src/app.py"]
    assert fake_requests.calls[0]["headers"]["Authorization"] == "Bearer gh-token"


def test_github_provider_fetch_pr_com_requests_fake(monkeypatch):
    fake_requests = _FakeRequests(
        {
            "title": "Adiciona relatorio",
            "user": {"login": "ana"},
            "head": {"ref": "feature/report"},
            "additions": 20,
            "deletions": 4,
        }
    )
    monkeypatch.setattr(vcs, "requests", fake_requests)

    item = GitHubProvider().fetch("https://github.com/acme/app/pull/42")

    assert item.kind == "pr"
    assert item.title == "Adiciona relatorio"
    assert item.branch == "feature/report"
    assert fake_requests.calls[0]["url"] == "https://api.github.com/repos/acme/app/pulls/42"


def test_github_provider_rejeita_url_nao_reconhecida():
    with pytest.raises(ValueError, match="URL do GitHub não reconhecida"):
        GitHubProvider().fetch("https://github.com/acme/app/issues/1")


def test_azure_provider_fetch_commit_com_requests_fake(monkeypatch):
    fake_requests = _FakeRequests(
        {
            "comment": "implementa rotina",
            "author": {"name": "Bruno"},
            "changeCounts": {"Add": 3, "Delete": 1},
        }
    )
    monkeypatch.setattr(vcs, "requests", fake_requests)

    provider = AzureDevOpsProvider(pat="az-token")
    item = provider.fetch("https://dev.azure.com/org/proj/_git/repo/commit/abc123")

    assert provider.matches("https://dev.azure.com/org/proj/_git/repo/commit/abc123") is True
    assert item.kind == "commit"
    assert item.provider == "azure"
    assert item.repo == "proj/repo"
    assert item.title == "implementa rotina"
    assert item.author == "Bruno"
    assert item.additions == 3
    assert item.deletions == 1
    assert fake_requests.calls[0]["auth"] == ("", "az-token")


def test_azure_provider_fetch_pr_com_requests_fake(monkeypatch):
    fake_requests = _FakeRequests(
        {
            "title": "Publica release",
            "createdBy": {"displayName": "Carla"},
            "sourceRefName": "refs/heads/release/v1",
        }
    )
    monkeypatch.setattr(vcs, "requests", fake_requests)

    item = AzureDevOpsProvider().fetch("https://dev.azure.com/org/proj/_git/repo/pullrequest/7")

    assert item.kind == "pr"
    assert item.author == "Carla"
    assert item.branch == "release/v1"
    assert "pullRequests/7?api-version=7.1" in fake_requests.calls[0]["url"]


def test_azure_provider_rejeita_url_nao_reconhecida():
    with pytest.raises(ValueError, match="URL do Azure DevOps não reconhecida"):
        AzureDevOpsProvider().fetch("https://dev.azure.com/org/proj/_git/repo/wiki")


class _FakeRequests:
    def __init__(self, payload: dict) -> None:
        self._payload = payload
        self.calls: list[dict] = []

    def get(self, url: str, **kwargs):
        self.calls.append({"url": url, **kwargs})
        return _FakeResponse(self._payload)


class _FakeResponse:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self._payload
