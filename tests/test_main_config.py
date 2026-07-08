import pytest

from daily.main import db_path_from_env


def test_db_path_from_env_usa_default_quando_nao_configurado(monkeypatch):
    monkeypatch.delenv("DB_PATH", raising=False)

    assert db_path_from_env() == "daily.db"


def test_db_path_from_env_rejeita_valor_vazio(monkeypatch):
    monkeypatch.setenv("DB_PATH", "   ")

    with pytest.raises(ValueError, match="DB_PATH nao pode ficar vazio"):
        db_path_from_env()


def test_db_path_from_env_rejeita_diretorio(monkeypatch, tmp_path):
    monkeypatch.setenv("DB_PATH", str(tmp_path))

    with pytest.raises(ValueError, match="nao um diretorio"):
        db_path_from_env()


def test_db_path_from_env_rejeita_diretorio_pai_inexistente(monkeypatch, tmp_path):
    db_path = tmp_path / "inexistente" / "daily.db"
    monkeypatch.setenv("DB_PATH", str(db_path))

    with pytest.raises(ValueError, match="Diretorio pai de DB_PATH nao existe"):
        db_path_from_env()
