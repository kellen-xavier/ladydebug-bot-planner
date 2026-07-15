# Bot Daily Planner

Bot de "daily updates" para **Discord**, com o núcleo já preparado para **Slack**
sem reescrita. Compila os movimentos do dia (notas, links, commits/PRs) e gera um
report ao fechar o dia.

> **Para equipes de engenharia:** o bot centraliza a gestão do dia a dia e o report
> do `/fim` vira a *daily assíncrona* do time — um jeito simples e prático de praticar
> os valores do **Extreme Programming (XP)**: Comunicação, Simplicidade, Feedback,
> Coragem e Respeito. Veja o
> [Tutorial de Reports para Equipes (XP)](docs/tutorial-reports-equipes-xp.md).

## Arquitetura (hexagonal / ports & adapters)

```txt
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
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
pytest
```

## Qualidade e segurança

```bash
./.venv/bin/ruff check .
./.venv/bin/ruff format .
./.venv/bin/python -m pip_audit
./.venv/bin/python -m bandit -r src
```

`pip-audit` verifica vulnerabilidades conhecidas nas dependências instaladas.
`bandit` faz análise estática de segurança no código em `src/`.

Antes de produção, gere um lockfile para fixar versões transitivas e tornar builds
reprodutíveis. Opções recomendadas para este projeto: `pip-tools` ou `uv`.

Para deploy seguro, Docker local e Fly.io, consulte
[`docs/deploy-and-docker.md`](docs/deploy-and-docker.md).

## Rodar o bot

```bash
cp .env.example .env   # preencha DISCORD_TOKEN, DISCORD_CLIENT_ID e DISCORD_GUILD_ID
source .venv/bin/activate
python -m pip install -e .
set -a; source .env; set +a
python -m daily.main
```

Se nao quiser ativar o ambiente virtual, use o Python da `.venv` diretamente:

```bash
set -a; source .env; set +a
./.venv/bin/python -m daily.main
```

## Comandos do BOT

- `/inicio`: inicia o bot no chat para inicio do dia
- `/continuar`: continua a atividade caso precisar antes do fechamento
- `/nota`: caso queira adicionar uma nota
- `/link`: adicionar links importantes durante o desenvilvimento - exe: documentação
- `/pr`: adiciona PRs abertos
- `/task`: cria tarefas
- `/fim`: e contagem de tempo em canal de voz (Discord)

Use `/pr url:<url-do-pr>` para registrar um Pull Request explicitamente. URLs de PR
também funcionam via `/link`, mas `/pr` **rejeita links que não sejam Pull Request** e
deixa a intenção mais clara no chat.

Se `/inicio` for usado com um dia já aberto, o bot responde para seguir com
`/continuar`. Use `/fim` para fechar o dia atual antes de iniciar outro.

-----

### Uso seguro do DB_PATH

`DB_PATH` define onde o SQLite local será criado. Se não for informado, o bot usa
`daily.db` na raiz do projeto.

## Boas práticas

- Use um caminho local controlado, por exemplo `daily.db` ou `data/daily.db`.
- Não versionar o banco: arquivos `*.db` já estão no `.gitignore`.
- Não coloque tokens, senhas ou dados sensíveis no valor de `DB_PATH`.
- Garanta que o diretório pai exista antes de iniciar o bot.
- Não aponte `DB_PATH` para um diretório; ele deve ser o caminho de um arquivo SQLite.

O bot valida `DB_PATH` ao iniciar e falha cedo se o valor estiver vazio, apontar para
um diretório ou usar um diretório pai inexistente.

-----

### Testar localmente em um servidor Discord

1. Crie uma aplicação no Discord Developer Portal e adicione um bot.
2. Em `Bot`, desligue `Requires OAuth2 Code Grant`.
3. Copie o token do bot para `DISCORD_TOKEN` no `.env`.
4. Copie o `Application ID`/`Client ID` para `DISCORD_CLIENT_ID` no `.env`.
5. Copie o ID do seu servidor de teste para `DISCORD_GUILD_ID` no `.env`.
6. Convide o bot para o servidor com os escopos `bot` e `applications.commands`.
7. Não coloque a URL de convite em `Redirect URI`; abra a URL no navegador.
8. Rode localmente:

```bash
source .venv/bin/activate
set -a; source .env; set +a
python -m daily.main
```

Com `DISCORD_GUILD_ID`, os slash commands sincronizam apenas no servidor de teste e aparecem mais rapido do que comandos globais. Para validar sem rede externa, use `/inicio`, `/continuar`, `/nota`, `/task` e `/fim`; `/link` pode chamar GitHub/Azure ou buscar a URL real.

Exemplo minimo de `.env` local:

```env
DISCORD_TOKEN=token_do_bot
DISCORD_CLIENT_ID=seu_client_id
DISCORD_GUILD_ID=seu_guild_id
DB_PATH=daily.db
# Opcional: canal onde o /fim publica o report. Se omitido, usa o nome release-notes.
DISCORD_REPORT_CHANNEL_NAME=release-notes
# Opcional: prefira o ID para evitar conflito se existirem canais com nomes iguais.
# DISCORD_REPORT_CHANNEL_ID=id_do_canal_release_notes
```

Quando `#release-notes` existir no servidor, `/fim` publica o report nesse canal e
responde no canal de comandos apenas com uma confirmação efêmera. Se o canal não for
encontrado, o bot mantém o comportamento seguro de enviar o report no canal atual.

Para times que trabalham em conjunto, o
[Tutorial de Reports para Equipes (XP)](docs/tutorial-reports-equipes-xp.md) mostra
como usar esse canal como gestão centralizada e como cada report reflete os valores do
Extreme Programming.

### Produção

Use as mesmas variáveis do ambiente local, mas aponte `DB_PATH` para um caminho
persistente do servidor ou volume do container:

```env
DISCORD_TOKEN=token_do_bot
DISCORD_CLIENT_ID=seu_client_id
DISCORD_GUILD_ID=seu_guild_id
DB_PATH=/app/data/daily.db
DISCORD_REPORT_CHANNEL_NAME=release-notes
```

Se quiser comandos globais em produção, deixe `DISCORD_GUILD_ID` vazio. A
propagação de slash commands globais pode demorar mais que a sincronização por
servidor.

### Deploy no Fly.io

O projeto inclui `Dockerfile` e `fly.toml`, porque o Fly não detecta este bot como
framework web automaticamente. O bot roda como worker, sem porta HTTP. Siga o guia
completo em [`docs/deploy-and-docker.md`](docs/deploy-and-docker.md).

### Diagnóstico Discord

Se o terminal mostrar `Servidores visiveis para este bot: nenhum`, confira:

- O token em `DISCORD_TOKEN` pertence ao mesmo app convidado para o servidor.
- O bot aparece em `Configurações do servidor > Integrações`.
- `DISCORD_GUILD_ID` é o ID do servidor onde o bot foi autorizado.
- `Requires OAuth2 Code Grant` está desligado em `Bot`.
- A URL de convite usa `scope=bot%20applications.commands` e não contém `redirect_uri`.

Com `DISCORD_CLIENT_ID` configurado, o bot imprime uma URL de convite correta
quando não consegue ver o servidor informado.

## Escopo

- Loop completo do dia: `/inicio` → registrar movimentos → `/fim` com report.
- Ingestão de links com **GitHub e Azure DevOps** (requisito v1), atrás da mesma port.
- Máquina de estados de tarefas com detecção de travamento.
- Tempo em call no Discord.
- Suíte de testes cobrindo o núcleo.
