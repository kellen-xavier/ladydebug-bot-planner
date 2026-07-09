import socket
import sys

import pytest

from daily.adapters.misc import SimpleFetcher, _validate_fetch_url


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "http://localhost:8080",
        "http://app.localhost",
        "http://127.0.0.1:8080",
        "http://0.0.0.0",
        "http://10.0.0.1",
        "http://172.16.0.1",
        "http://192.168.0.1",
        "http://169.254.169.254/latest/meta-data",
    ],
)
def test_validate_fetch_url_bloqueia_urls_ssrf(url):
    with pytest.raises(ValueError, match="URL bloqueada"):
        _validate_fetch_url(url)


def test_validate_fetch_url_bloqueia_hostname_que_resolve_para_ip_privado(monkeypatch):
    def fake_getaddrinfo(host, port, type=0):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", port))]

    monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)

    with pytest.raises(ValueError, match="URL bloqueada"):
        _validate_fetch_url("https://exemplo.test/artigo")


def test_simple_fetcher_fetch_extrai_titulo_e_texto_sem_rede(monkeypatch):
    _allow_public_dns(monkeypatch)
    fake_requests = _FakeRequests(
        _FakeResponse(
            """
            <html><head><title>Artigo Teste</title></head>
            <body><h1>Titulo</h1><p>Conteudo relevante.</p></body></html>
            """
        )
    )
    monkeypatch.setitem(sys.modules, "requests", fake_requests)

    page = SimpleFetcher().fetch("https://exemplo.test/artigo")

    assert page.title == "Artigo Teste"
    assert "Conteudo relevante." in page.text
    assert fake_requests.calls == [{"url": "https://exemplo.test/artigo", "timeout": 15}]


def test_simple_fetcher_fetch_propaga_erro_http_sem_mascarar(monkeypatch):
    _allow_public_dns(monkeypatch)
    fake_requests = _FakeRequests(_FakeResponse("erro", error=RuntimeError("HTTP 500")))
    monkeypatch.setitem(sys.modules, "requests", fake_requests)

    with pytest.raises(RuntimeError, match="HTTP 500"):
        SimpleFetcher().fetch("https://exemplo.test/falha")


def _allow_public_dns(monkeypatch):
    def fake_getaddrinfo(host, port, type=0):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", port))]

    monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)


class _FakeRequests:
    def __init__(self, response) -> None:
        self._response = response
        self.calls: list[dict] = []

    def get(self, url: str, timeout: int):
        self.calls.append({"url": url, "timeout": timeout})
        return self._response


class _FakeResponse:
    def __init__(self, text: str, error: Exception | None = None) -> None:
        self.text = text
        self._error = error

    def raise_for_status(self) -> None:
        if self._error:
            raise self._error
