import pytest

from daily.command_router import CommandRouter
from daily.main import (
    build_router,
    db_path_from_env,
    discord_config_from_env,
    discord_report_channel_from_env,
)


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


def test_discord_config_from_env_rejeita_token_vazio(monkeypatch):
    monkeypatch.delenv("DISCORD_TOKEN", raising=False)

    with pytest.raises(ValueError, match="DISCORD_TOKEN e obrigatorio"):
        discord_config_from_env()


def test_discord_config_from_env_aceita_ids_opcionais(monkeypatch):
    monkeypatch.setenv("DISCORD_TOKEN", " token ")
    monkeypatch.setenv("DISCORD_GUILD_ID", " 123 ")
    monkeypatch.setenv("DISCORD_CLIENT_ID", " 456 ")

    assert discord_config_from_env() == ("token", "123", "456")


def test_discord_config_from_env_rejeita_guild_id_invalido(monkeypatch):
    monkeypatch.setenv("DISCORD_TOKEN", "token")
    monkeypatch.setenv("DISCORD_GUILD_ID", "abc")

    with pytest.raises(ValueError, match="DISCORD_GUILD_ID deve conter apenas numeros"):
        discord_config_from_env()


def test_discord_config_from_env_rejeita_client_id_invalido(monkeypatch):
    monkeypatch.setenv("DISCORD_TOKEN", "token")
    monkeypatch.setenv("DISCORD_CLIENT_ID", "abc")

    with pytest.raises(ValueError, match="DISCORD_CLIENT_ID deve conter apenas numeros"):
        discord_config_from_env()


def test_discord_report_channel_from_env_usa_release_notes_por_padrao(monkeypatch):
    monkeypatch.delenv("DISCORD_REPORT_CHANNEL_ID", raising=False)
    monkeypatch.delenv("DISCORD_REPORT_CHANNEL_NAME", raising=False)

    assert discord_report_channel_from_env() == (None, "release-notes")


def test_discord_report_channel_from_env_aceita_id_e_nome(monkeypatch):
    monkeypatch.setenv("DISCORD_REPORT_CHANNEL_ID", " 789 ")
    monkeypatch.setenv("DISCORD_REPORT_CHANNEL_NAME", " reports ")

    assert discord_report_channel_from_env() == ("789", "reports")


def test_discord_report_channel_from_env_rejeita_id_invalido(monkeypatch):
    monkeypatch.setenv("DISCORD_REPORT_CHANNEL_ID", "release-notes")

    with pytest.raises(ValueError, match="DISCORD_REPORT_CHANNEL_ID deve conter apenas numeros"):
        discord_report_channel_from_env()


def test_build_router_monta_command_router_com_sqlite_local(monkeypatch, tmp_path):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "daily.db"))
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("AZURE_DEVOPS_PAT", raising=False)

    router = build_router()

    assert isinstance(router, CommandRouter)
    assert router.task_status() == "Nenhuma tarefa."
