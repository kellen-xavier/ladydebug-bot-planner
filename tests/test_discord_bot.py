import asyncio
import logging

from daily.adapters import discord_bot
from daily.adapters.discord_bot import (
    _find_text_channel,
    _invite_url,
    _record_voice_event,
    _sync_commands,
)


class FakeGuild:
    def __init__(self, guild_id: int, name: str) -> None:
        self.id = guild_id
        self.name = name


class FakeClient:
    def __init__(self, guilds) -> None:
        self.guilds = guilds
        self.closed = False
        self.user = None

    async def close(self) -> None:
        self.closed = True


class FakeTextChannel:
    def __init__(self, channel_id: int, name: str) -> None:
        self.id = channel_id
        self.name = name
        self.mention = f"<#{channel_id}>"

    async def send(self, message: str) -> None:
        self.message = message


class FakeDiscordGuild:
    def __init__(self, channels) -> None:
        self.text_channels = channels

    def get_channel(self, channel_id: int):
        for channel in self.text_channels:
            if channel.id == channel_id:
                return channel
        return None


class FakeInteraction:
    def __init__(self, guild) -> None:
        self.guild = guild


class FakeTree:
    def __init__(self) -> None:
        self.copied = False
        self.synced = False

    def copy_global_to(self, guild) -> None:
        self.copied = True

    async def sync(self, guild=None) -> None:
        self.synced = True


class ForbiddenTree(FakeTree):
    async def sync(self, guild=None) -> None:
        raise discord_bot.discord.Forbidden("response", "sem permissao")


class FailingDay:
    def voice_join(self, user_id: str) -> None:
        raise RuntimeError(f"falha privada para {user_id} com token SECRET")

    def voice_leave(self, user_id: str) -> None:
        raise RuntimeError(f"falha privada para {user_id} com token SECRET")


class FakeRouter:
    def __init__(self) -> None:
        self._day = FailingDay()


def test_sync_commands_fecha_cliente_quando_guild_nao_esta_visivel(capsys):
    client = FakeClient(guilds=[])
    tree = FakeTree()

    synced = asyncio.run(_sync_commands(tree, client, "123"))

    output = capsys.readouterr().out
    assert synced is False
    assert client.closed is True
    assert tree.copied is False
    assert tree.synced is False
    assert "DISCORD_GUILD_ID=123" in output
    assert "Servidores visiveis para este bot: nenhum" in output
    assert "Requires OAuth2 Code Grant" in output


def test_sync_commands_mostra_url_de_convite_quando_client_id_informado(capsys):
    client = FakeClient(guilds=[])
    tree = FakeTree()

    synced = asyncio.run(_sync_commands(tree, client, "123", client_id="456"))

    output = capsys.readouterr().out
    assert synced is False
    assert _invite_url("456") in output
    assert "DISCORD_TOKEN" in output


def test_sync_commands_sincroniza_quando_guild_esta_visivel():
    client = FakeClient(guilds=[FakeGuild(123, "Servidor Teste")])
    tree = FakeTree()

    synced = asyncio.run(_sync_commands(tree, client, "123"))

    assert synced is True
    assert client.closed is False
    assert tree.copied is True
    assert tree.synced is True


def test_sync_commands_sincroniza_global_quando_guild_id_nao_informado():
    client = FakeClient(guilds=[])
    tree = FakeTree()

    synced = asyncio.run(_sync_commands(tree, client, None))

    assert synced is True
    assert client.closed is False
    assert tree.copied is False
    assert tree.synced is True


def test_sync_commands_fecha_cliente_quando_discord_forbidden(monkeypatch, capsys):
    class FakeForbidden(Exception):
        pass

    monkeypatch.setattr(discord_bot.discord, "Forbidden", FakeForbidden)
    client = FakeClient(guilds=[FakeGuild(123, "Servidor Teste")])
    tree = ForbiddenTree()

    synced = asyncio.run(_sync_commands(tree, client, "123", client_id="456"))

    output = capsys.readouterr().out
    assert synced is False
    assert client.closed is True
    assert "DISCORD_GUILD_ID=123" in output
    assert _invite_url("456") in output


def test_find_text_channel_prefere_id_configurado():
    release = FakeTextChannel(10, "release-notes")
    reports = FakeTextChannel(20, "reports")
    interaction = FakeInteraction(FakeDiscordGuild([release, reports]))

    channel = _find_text_channel(interaction, "20", "release-notes")

    assert channel is reports


def test_find_text_channel_usa_nome_release_notes_como_fallback():
    release = FakeTextChannel(10, "release-notes")
    interaction = FakeInteraction(FakeDiscordGuild([release]))

    channel = _find_text_channel(interaction, None, "release-notes")

    assert channel is release


def test_find_text_channel_retorna_none_quando_nao_encontra_canal():
    interaction = FakeInteraction(FakeDiscordGuild([]))

    channel = _find_text_channel(interaction, "abc", "release-notes")

    assert channel is None



def test_record_voice_event_loga_falha_sem_dados_sensiveis(caplog):
    caplog.set_level(logging.INFO, logger="daily.adapters.discord_bot")

    _record_voice_event(FakeRouter(), "usuario-123", "join")

    assert "Evento de voz ignorado durante join: RuntimeError" in caplog.text
    assert "usuario-123" not in caplog.text
    assert "SECRET" not in caplog.text
    assert "falha privada" not in caplog.text
