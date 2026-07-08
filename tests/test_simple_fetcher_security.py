import socket

import pytest

from daily.adapters.misc import _validate_fetch_url


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
