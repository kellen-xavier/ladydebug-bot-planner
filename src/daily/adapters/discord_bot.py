"""Adaptador de plataforma: Discord (discord.py).

Fino de propósito: só traduz eventos/slash commands do Discord em chamadas ao
CommandRouter e devolve o texto. A lógica está toda no núcleo.

Executar exige DISCORD_TOKEN; não é exercitado pelos testes de núcleo.
"""

from __future__ import annotations

import os
from contextlib import suppress

import discord
from discord import app_commands

from daily.command_router import CommandRouter


def _known_guilds(client: discord.Client) -> str:
    return ", ".join(f"{g.name} ({g.id})" for g in client.guilds) or "nenhum"


def _guild_access_error(guild_id: str, client: discord.Client) -> str:
    return (
        "Nao foi possivel sincronizar comandos no servidor informado em "
        f"DISCORD_GUILD_ID={guild_id}. Confira se o ID e do servidor correto, "
        "se o bot esta nesse servidor e se foi convidado com o escopo "
        "'applications.commands'. "
        f"Servidores visiveis para este bot: {_known_guilds(client)}."
    )


async def _sync_commands(
    tree: app_commands.CommandTree,
    client: discord.Client,
    guild_id: str | None,
) -> bool:
    if guild_id:
        if not any(str(g.id) == guild_id for g in client.guilds):
            print(_guild_access_error(guild_id, client))
            await client.close()
            return False

        guild = discord.Object(id=int(guild_id))
        try:
            tree.copy_global_to(guild=guild)
            await tree.sync(guild=guild)
        except discord.Forbidden:
            print(_guild_access_error(guild_id, client))
            await client.close()
            return False
    else:
        await tree.sync()

    return True


def build_client(router: CommandRouter, guild_id: str | None = None) -> discord.Client:
    intents = discord.Intents.default()
    intents.voice_states = True
    client = discord.Client(intents=intents)
    tree = app_commands.CommandTree(client)

    @client.event
    async def on_ready():
        synced = await _sync_commands(tree, client, guild_id)
        if not synced:
            return
        print(f"Bot online como {client.user}")

    @tree.command(name="inicio", description="Inicia o dia")
    async def inicio(interaction: discord.Interaction):
        msg = router.inicio(str(interaction.user.id), str(interaction.channel_id))
        await interaction.response.send_message(msg)

    @tree.command(name="nota", description="Registra uma atividade em texto")
    async def nota(interaction: discord.Interaction, texto: str):
        await interaction.response.send_message(router.nota(str(interaction.user.id), texto))

    @tree.command(name="link", description="Ingere e resume um link")
    async def link(interaction: discord.Interaction, url: str, comentario: str = ""):
        await interaction.response.defer()
        msg = router.link(str(interaction.user.id), url, comentario)
        await interaction.followup.send(msg)

    @tree.command(name="task", description="Cria uma nova tarefa")
    async def task(interaction: discord.Interaction, titulo: str):
        await interaction.response.send_message(router.task_nova(titulo))

    @tree.command(name="fim", description="Fecha o dia e gera o report")
    async def fim(interaction: discord.Interaction):
        await interaction.response.send_message(router.fim(str(interaction.user.id)))

    @client.event
    async def on_voice_state_update(member, before, after):
        uid = str(member.id)
        if before.channel is None and after.channel is not None:
            with suppress(Exception):
                router._day.voice_join(uid)
        elif before.channel is not None and after.channel is None:
            with suppress(Exception):
                router._day.voice_leave(uid)

    return client


def run() -> None:  # pragma: no cover
    token = os.environ["DISCORD_TOKEN"]
    guild_id = os.environ.get("DISCORD_GUILD_ID")
    # A montagem das dependências (storage, services) fica em main.py.
    from daily.main import build_router

    build_client(build_router(), guild_id=guild_id).run(token)
