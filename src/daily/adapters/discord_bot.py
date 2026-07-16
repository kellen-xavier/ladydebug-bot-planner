"""Adaptador de plataforma: Discord (discord.py).

Fino de propósito: só traduz eventos/slash commands do Discord em chamadas ao
CommandRouter e devolve o texto. A lógica está toda no núcleo.

Executar exige DISCORD_TOKEN; não é exercitado pelos testes de núcleo.
"""

from __future__ import annotations

import logging
import os

import discord
from discord import app_commands

from daily.command_router import CommandRouter

logger = logging.getLogger(__name__)

BOT_PERMISSIONS = 2148780096


def _invite_url(client_id: str) -> str:
    return (
        "https://discord.com/oauth2/authorize?"
        f"client_id={client_id}&permissions={BOT_PERMISSIONS}"
        "&integration_type=0&scope=bot%20applications.commands"
    )


def _bot_identity(client: discord.Client) -> str:
    user = client.user
    if user is None:
        return "desconhecido"
    return f"{user} (id={user.id})"


def _known_guilds(client: discord.Client) -> str:
    return ", ".join(f"{g.name} ({g.id})" for g in client.guilds) or "nenhum"


def _find_text_channel(
    interaction: discord.Interaction,
    channel_id: str | None,
    channel_name: str | None,
):
    guild = interaction.guild
    if guild is None:
        return None

    if channel_id:
        try:
            channel = guild.get_channel(int(channel_id))
        except ValueError:
            channel = None
        if channel is not None and hasattr(channel, "send"):
            return channel

    if channel_name:
        for channel in getattr(guild, "text_channels", []):
            if channel.name == channel_name and hasattr(channel, "send"):
                return channel

    return None


def _guild_access_error(
    guild_id: str,
    client: discord.Client,
    client_id: str | None = None,
) -> str:
    message = (
        "Nao foi possivel sincronizar comandos no servidor informado em "
        f"DISCORD_GUILD_ID={guild_id}. Confira se o ID e do servidor correto, "
        "se o bot esta nesse servidor e se foi convidado com os escopos "
        "'bot' e 'applications.commands'. "
        f"Bot conectado: {_bot_identity(client)}. "
        f"Servidores visiveis para este bot: {_known_guilds(client)}. "
        "Se a lista estiver vazia, verifique se DISCORD_TOKEN pertence ao app correto, "
        "se o bot foi autorizado no servidor e se 'Requires OAuth2 Code Grant' esta desligado."
    )
    if client_id:
        message += f" URL de convite: {_invite_url(client_id)}"
    return message


async def _sync_commands(
    tree: app_commands.CommandTree,
    client: discord.Client,
    guild_id: str | None,
    client_id: str | None = None,
) -> bool:
    if guild_id:
        if not any(str(g.id) == guild_id for g in client.guilds):
            print(_guild_access_error(guild_id, client, client_id))
            await client.close()
            return False

        guild = discord.Object(id=int(guild_id))
        try:
            tree.copy_global_to(guild=guild)
            await tree.sync(guild=guild)
        except discord.Forbidden:
            print(_guild_access_error(guild_id, client, client_id))
            await client.close()
            return False
    else:
        await tree.sync()

    return True


def _record_voice_event(router: CommandRouter, user_id: str, action: str) -> None:
    try:
        if action == "join":
            router._day.voice_join(user_id)
        elif action == "leave":
            router._day.voice_leave(user_id)
    except Exception as exc:
        logger.info(
            "Evento de voz ignorado durante %s: %s",
            action,
            type(exc).__name__,
        )


def build_client(
    router: CommandRouter,
    guild_id: str | None = None,
    client_id: str | None = None,
    report_channel_id: str | None = None,
    report_channel_name: str | None = "release-notes",
) -> discord.Client:
    intents = discord.Intents.default()
    intents.voice_states = True
    client = discord.Client(intents=intents)
    tree = app_commands.CommandTree(client)

    @client.event
    async def on_ready():
        synced = await _sync_commands(tree, client, guild_id, client_id)
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

    @tree.command(name="continuar", description="Continua um dia ja iniciado")
    async def continuar(interaction: discord.Interaction):
        await interaction.response.send_message(router.continuar(str(interaction.user.id)))

    @tree.command(name="link", description="Ingere e resume um link")
    async def link(interaction: discord.Interaction, url: str, comentario: str = ""):
        await interaction.response.defer()
        msg = router.link(str(interaction.user.id), url, comentario)
        await interaction.followup.send(msg)

    @tree.command(name="pr", description="Registra um Pull Request para aparecer no report")
    async def pr(interaction: discord.Interaction, url: str, comentario: str = ""):
        await interaction.response.defer()
        msg = router.pr(str(interaction.user.id), url, comentario)
        await interaction.followup.send(msg)

    @tree.command(name="task", description="Cria uma nova tarefa")
    async def task(interaction: discord.Interaction, titulo: str):
        await interaction.response.send_message(router.task_nova(titulo))

    @tree.command(name="task-status", description="Lista as tarefas e seus status")
    async def task_status(interaction: discord.Interaction):
        await interaction.response.send_message(router.task_status())

    @tree.command(name="task-finish", description="Conclui uma tarefa em aberto")
    async def task_finish(interaction: discord.Interaction, task_id: str):
        await interaction.response.send_message(router.task_finish(task_id))

    @tree.command(name="fim", description="Fecha o dia e gera o report")
    async def fim(interaction: discord.Interaction):
        report = router.fim(str(interaction.user.id))
        if report.startswith("⚠️"):
            await interaction.response.send_message(report)
            return

        channel = _find_text_channel(interaction, report_channel_id, report_channel_name)
        if channel is None:
            await interaction.response.send_message(report)
            return

        try:
            await channel.send(report)
        except (discord.Forbidden, discord.HTTPException):
            await interaction.response.send_message(report)
            return

        mention = getattr(channel, "mention", f"#{getattr(channel, 'name', 'canal configurado')}")
        await interaction.response.send_message(f"📣 Report enviado em {mention}.", ephemeral=True)

    @client.event
    async def on_voice_state_update(member, before, after):
        uid = str(member.id)
        if before.channel is None and after.channel is not None:
            _record_voice_event(router, uid, "join")
        elif before.channel is not None and after.channel is None:
            _record_voice_event(router, uid, "leave")

    return client


def run() -> None:  # pragma: no cover
    token = os.environ["DISCORD_TOKEN"]
    guild_id = os.environ.get("DISCORD_GUILD_ID")
    client_id = os.environ.get("DISCORD_CLIENT_ID")
    report_channel_id = os.environ.get("DISCORD_REPORT_CHANNEL_ID")
    report_channel_name = os.environ.get("DISCORD_REPORT_CHANNEL_NAME", "release-notes")
    # A montagem das dependências (storage, services) fica em main.py.
    from daily.main import build_router

    build_client(
        build_router(),
        guild_id=guild_id,
        client_id=client_id,
        report_channel_id=report_channel_id,
        report_channel_name=report_channel_name,
    ).run(token)
