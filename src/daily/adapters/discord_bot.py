"""Adaptador de plataforma: Discord (discord.py).

Fino de propósito: só traduz eventos/slash commands do Discord em chamadas ao
CommandRouter e devolve o texto. A lógica está toda no núcleo.

Executar exige DISCORD_TOKEN; não é exercitado pelos testes de núcleo.
"""
from __future__ import annotations

import os

import discord
from discord import app_commands

from daily.command_router import CommandRouter


def build_client(router: CommandRouter) -> discord.Client:
    intents = discord.Intents.default()
    intents.voice_states = True
    client = discord.Client(intents=intents)
    tree = app_commands.CommandTree(client)

    @client.event
    async def on_ready():
        await tree.sync()
        print(f"Bot online como {client.user}")

    @tree.command(name="inicio", description="Inicia o dia")
    async def inicio(interaction: discord.Interaction):
        msg = router.inicio(str(interaction.user.id), str(interaction.channel_id))
        await interaction.response.send_message(msg)

    @tree.command(name="nota", description="Registra uma atividade em texto")
    async def nota(interaction: discord.Interaction, texto: str):
        await interaction.response.send_message(
            router.nota(str(interaction.user.id), texto)
        )

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
            try:
                router._day.voice_join(uid)
            except Exception:
                pass  # sem dia aberto: ignora
        elif before.channel is not None and after.channel is None:
            try:
                router._day.voice_leave(uid)
            except Exception:
                pass

    return client


def run() -> None:  # pragma: no cover
    token = os.environ["DISCORD_TOKEN"]
    # A montagem das dependências (storage, services) fica em main.py.
    from daily.main import build_router

    build_client(build_router()).run(token)
