# ladydebug-bot-planner — Estado do Projeto (retomada)

_Snapshot para continuar depois. Referência: 08/07/2026._
_Repositório: github.com/kellen-xavier/ladydebug-bot-planner_

## Objetivo

Bot de "daily updates" para **Discord**, com o núcleo preparado para portar ao
**Slack** sem reescrita. Coleta os movimentos do dia (notas, links, commits/PRs,
documentos, tempo em call) e, ao fechar o dia (`/fim`), gera um **report
compilado, conciso e informativo**. Requisitos originais em `Bot Planner Daily.md`.

## Decisões já fechadas

- **Linguagem:** Python.
- **Arquitetura:** hexagonal (ports & adapters) — núcleo puro + adapters finos,
  para permitir o swap Discord↔Slack sem tocar na lógica.
- **Persistência:** SQLite no MVP (migrar para Postgres depois troca só o adapter).
- **VCS na v1:** GitHub **e** Azure DevOps, ambos atrás da mesma port `VCSProvider`.
- **Hospedagem:** ainda não definida. Recomendado **Railway** ou **Fly.io** (menor
  atrito); VPS + `systemd` como alternativa. Precisa ser **processo sempre ligado**
  (não serverless — mantém gateway do Discord, escuta voz, roda cron de fim de dia).
- **TDD é requisito:** toda funcionalidade acompanha teste; bug vira teste de regressão.
- **Ressalva conhecida:** tempo em call é "Discord-first". No Slack a API de huddle
  é limitada — provável registrar reuniões via evento de calendário.

## Estado atual — Fase 0 concluída e testada

- Núcleo implementado: `DaySession`, `Entry`, `Task` (máquina de estados),
  `day_service`, `task_service`, `link_ingest`, `report`.
- Adapters: SQLite, GitHub, Azure DevOps, Discord (`discord.py`), fetcher/summarizer
  em placeholder.
- Loop do dia funcionando: `/inicio` → `nota`/`link`/`task` → `/fim` com report.
- **14 testes passando** (~0,04s): ciclo do dia, transições de tarefa, detecção de
  travamento, ingestão de link, geração de report.
- `console.py`: CLI interativo para testar sem Discord/token.
- Entregue como zip com histórico git (2 commits: núcleo + console).

## Estrutura (resumo)

```
src/daily/core/      regras puras (models, day_service, task_service, link_ingest, report)
src/daily/ports/     contratos (Storage, VCSProvider, LinkFetcher, Summarizer, Clock)
src/daily/adapters/  SQLite, vcs (GitHub+Azure), discord_bot, misc
src/daily/command_router.py   fronteira única entre plataformas e núcleo
src/daily/main.py             composition root (wiring)
console.py                    console de teste local
tests/                        suíte de testes + fakes (conftest)
```

## Pendências

1. **Push para o GitHub** — precisa partir do Kellen (o assistente não autentica na
   conta). Caminhos: `git push` (o zip já vem com `.git` e commit inicial) ou upload
   pela interface web do GitHub.
2. **Testar localmente**, em 3 camadas: `pytest` → `console.py` → GitHub/Azure reais
   (com `GITHUB_TOKEN` / `AZURE_DEVOPS_PAT` no `.env`).
3. **Decisão em aberto (bloqueia a Fase 1):** qual provedor de LLM para o summarizer
   (ex.: API da Claude ou outro).

## Fase 1 (próxima) — escopo

- Substituir `EchoSummarizer` por um `LLMSummarizer` real → resumo factual de 3–4
  parágrafos, sem opinião (conforme o documento original).
- Substituir `SimpleFetcher` por extração dedicada de páginas + `mammoth` para
  `.docx`; incluir suporte a links de documento (Dropbox etc.).
- Tudo atrás de ports mockáveis → melhora a cobertura de teste.
- **Bloqueio:** definir o provedor de LLM antes de implementar o resumo.

## Fases seguintes (visão geral)

- **Fase 2:** tarefas completas (`/task`, `/feedback`, `/task-status`) + guardrails/cron.
- **Fase 3:** Google Calendar (`/agenda`), Dropbox, `/repo` completo.
- **Fase 4:** tempo em call (Discord), Deployment Guide a partir de branches/PRs,
  consulta de arquitetura do projeto.
- **Fase 5:** adapter do Slack reusando 100% do núcleo (com a ressalva de huddle).

## Como retomar

```bash
cd bot_daily
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\Activate.ps1
pip install -e ".[dev]"
pytest              # confirma que a base está íntegra (14 testes)
python console.py   # dirige o bot localmente, sem Discord
```

**Próxima ação sugerida:** validar localmente, fazer o push, e escolher o provedor
de LLM para destravar a Fase 1.
