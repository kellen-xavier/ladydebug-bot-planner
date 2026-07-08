import asyncio

from daily.adapters.discord_bot import _sync_commands


class FakeGuild:
    def __init__(self, guild_id: int, name: str) -> None:
        self.id = guild_id
        self.name = name


class FakeClient:
    def __init__(self, guilds) -> None:
        self.guilds = guilds
        self.closed = False

    async def close(self) -> None:
        self.closed = True


class FakeTree:
    def __init__(self) -> None:
        self.copied = False
        self.synced = False

    def copy_global_to(self, guild) -> None:
        self.copied = True

    async def sync(self, guild=None) -> None:
        self.synced = True


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


def test_sync_commands_sincroniza_quando_guild_esta_visivel():
    client = FakeClient(guilds=[FakeGuild(123, "Servidor Teste")])
    tree = FakeTree()

    synced = asyncio.run(_sync_commands(tree, client, "123"))

    assert synced is True
    assert client.closed is False
    assert tree.copied is True
    assert tree.synced is True
