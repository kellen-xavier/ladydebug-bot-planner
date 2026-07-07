# Bot Daily Planner (Fase 0)

Bot de "daily updates" para **Discord**, com o núcleo já preparado para **Slack**
sem reescrita. Compila os movimentos do dia (notas, links, commits/PRs) e gera um
report ao fechar o dia.

## Arquitetura (hexagonal / ports & adapters)

```
src/daily/
├── core/            # regras de negócio puras (sem I/O, sem plataforma)
│   ├── models.py        # DaySession, Entry, Task, máquina de estados
│   ├── day_service.py   # /inicio, registrar movimentos, /fim
│   ├── task_service.py  # transições + detecção de travamento
│   ├── link_ingest.py   # detecta VCS vs página genérica
│   └── report.py        # compilado de fim de dia
├── ports/           # contratos (Storage, VCSProvider, LinkFetcher, Summarizer, Clock)
├── adapters/        # implementações concretas (trocáveis)
│   ├── storage_sqlite.py
│   ├── vcs.py           # GitHubProvider + AzureDevOpsProvider (v1)
│   ├── misc.py          # clock, fetcher, summarizer
│   └── discord_bot.py   # adaptador de plataforma (Slack entra aqui depois)
├── command_router.py   # fronteira única entre plataformas e núcleo
└── main.py             # composition root (onde tudo é montado)
```

O núcleo não importa `discord.py` nem `requests` — por isso os testes rodam em
milissegundos, sem rede. Trocar SQLite→Postgres ou adicionar o Slack mexe só nos
adapters e no `main.py`.

## Rodar os testes (TDD)

```bash
pip install -e ".[dev]"
pytest
```

## Rodar o bot

```bash
cp .env.example .env   # preencha DISCORD_TOKEN, GITHUB_TOKEN, AZURE_DEVOPS_PAT
pip install -e .
python -m daily.main
```

Comandos disponíveis nesta fase: `/inicio`, `/nota`, `/link`, `/task`, `/fim`,
e contagem de tempo em canal de voz (Discord).

## Escopo desta entrega

- Loop completo do dia: `/inicio` → registrar movimentos → `/fim` com report.
- Ingestão de links com **GitHub e Azure DevOps** (requisito v1), atrás da mesma port.
- Máquina de estados de tarefas com detecção de travamento.
- Tempo em call no Discord.
- Suíte de testes cobrindo o núcleo.

## Próximas fases

1. **Resumo real dos links**: trocar `EchoSummarizer` por um `LLMSummarizer` e o
   `SimpleFetcher` por extração dedicada (+ `mammoth` para `.docx`, Dropbox).
2. **Integrações**: Google Calendar (`/agenda`), `/repo` completo.
3. **Geração assistida**: Deployment Guide a partir de branches/PRs; consulta de arquitetura.
4. **Slack**: novo adaptador reusando 100% do núcleo (atenção: tempo de huddle tem
   API limitada — registrar reuniões via evento de calendário no Slack).
