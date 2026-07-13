# Deploy e Docker

Guia seguro para deixar o bot online e para testar a imagem Docker em um servidor
local. Não coloque tokens, IDs privados ou credenciais reais neste arquivo.

## Modelo de Segurança

- Secrets ficam sempre fora do Git: use `.env` local, `fly secrets` ou o cofre da plataforma.
- Nunca versionar `.env`, bancos SQLite, dumps, logs ou prints com variáveis preenchidas.
- Use tokens com o menor escopo possível e revogue qualquer token que tenha sido exposto.
- Prefira `DISCORD_REPORT_CHANNEL_ID` em produção para evitar publicar no canal errado.
- Use `DISCORD_GUILD_ID` em ambiente de teste para sincronizar slash commands só no servidor esperado.
- Em produção, se quiser comandos globais, deixe `DISCORD_GUILD_ID` vazio e aceite a propagação mais lenta.
- O bot não expõe HTTP; ele roda como worker conectado ao Discord.

## Variáveis Necessárias

Configure estes valores no ambiente da máquina, no `.env` local ou nos secrets da plataforma:

```env
DISCORD_TOKEN=token_do_bot
DISCORD_CLIENT_ID=seu_client_id
DISCORD_GUILD_ID=seu_guild_id_de_teste
GITHUB_TOKEN=token_github_com_escopo_minimo
AZURE_DEVOPS_PAT=
DB_PATH=/data/daily.db
DISCORD_REPORT_CHANNEL_NAME=release-notes
DISCORD_REPORT_CHANNEL_ID=id_do_canal_release_notes
```

Notas:

- `DISCORD_TOKEN` é obrigatório.
- `DISCORD_CLIENT_ID` é recomendado para diagnóstico e convite correto do bot.
- `DISCORD_GUILD_ID` é opcional, mas recomendado em teste local.
- `GITHUB_TOKEN` só é necessário para consultar GitHub com maior limite ou repositórios privados.
- `AZURE_DEVOPS_PAT` só é necessário se a integração Azure DevOps for usada.
- `DB_PATH` deve apontar para um arquivo, não para um diretório.

## Docker Local

Use Docker para validar a mesma forma de execução usada em produção.

### Build Da Imagem

```bash
docker build -t ladydebug-bot-planner:local .
```

### Rodar Com `.env` Local

Crie um `.env` baseado em `.env.example`, sem versionar o arquivo:

```bash
cp .env.example .env
```

Depois rode o container com volume local para persistir o SQLite:

```bash
mkdir -p data
docker run --rm \
  --env-file .env \
  -e DB_PATH=/data/daily.db \
  -v "$(pwd)/data:/data" \
  ladydebug-bot-planner:local
```

Para interromper, use `Ctrl+C`.

### Rodar Sem Arquivo `.env`

Use esta forma quando quiser passar só variáveis específicas no shell atual:

```bash
docker run --rm \
  -e DISCORD_TOKEN \
  -e DISCORD_CLIENT_ID \
  -e DISCORD_GUILD_ID \
  -e GITHUB_TOKEN \
  -e DISCORD_REPORT_CHANNEL_ID \
  -e DISCORD_REPORT_CHANNEL_NAME=release-notes \
  -e DB_PATH=/data/daily.db \
  -v "$(pwd)/data:/data" \
  ladydebug-bot-planner:local
```

### Testar Sem Subir O Bot

Para validar instalação e imports dentro da imagem:

```bash
docker run --rm ladydebug-bot-planner:local python -c "import daily.main; print('ok')"
```

Para rodar testes dentro de container, construa uma imagem de desenvolvimento ou instale
as dependências de dev temporariamente:

```bash
docker run --rm ladydebug-bot-planner:local sh -c "python -m pip install -e '.[dev]' && pytest"
```

## Deploy No Fly.io

O repositório inclui `Dockerfile` e `fly.toml`. O Fly usa o Dockerfile porque este bot
não é um framework web detectável automaticamente.

[Link do fly.io](https://fly.io/)
[Docs fly.io](https://fly.io/docs/)

### Preparar O App

Se o app já existe no Fly, confira se o nome em `fly.toml` corresponde ao app correto:

```toml
app = "ladydebug-bot-planner"
primary_region = "gru"
```

Se o nome do app for diferente, ajuste antes do deploy.

### Configurar Secrets

Configure secrets pelo CLI ou painel do Fly. Não coloque estes valores no `fly.toml`:

```bash
fly secrets set DISCORD_TOKEN=token_do_bot
fly secrets set DISCORD_CLIENT_ID=seu_client_id
fly secrets set DISCORD_GUILD_ID=seu_guild_id_de_teste
fly secrets set GITHUB_TOKEN=token_github_com_escopo_minimo
fly secrets set DISCORD_REPORT_CHANNEL_ID=id_do_canal_release_notes
```

Se usar Azure DevOps:

```bash
fly secrets set AZURE_DEVOPS_PAT=seu_pat_azure
```

### Persistir SQLite

Crie um volume na mesma região do app:

```bash
fly volumes create data --region gru --size 1
```

Depois habilite o mount em `fly.toml`:

```toml
[[mounts]]
  source = "data"
  destination = "/data"
```

Sem volume, o bot pode funcionar, mas o SQLite pode ser perdido em restart ou redeploy.

### Fazer Deploy

```bash
fly deploy
```

Depois acompanhe logs:

```bash
fly logs
```

### Configuração Como Worker

Não adicione `[http_service]` para este bot. Ele não abre porta HTTP. Em especial, evite
configurações que desliguem a máquina automaticamente, como `auto_stop_machines`, porque
o bot precisa permanecer conectado ao Discord.

## Checklist Pós-Deploy

1. Confirme que o bot aparece online no Discord.
2. Use `/inicio` no servidor de teste.
3. Registre uma nota com `/nota`.
4. Registre um PR com `/pr` usando uma URL de teste válida.
5. Use `/fim` e confirme que o report foi enviado para o canal configurado.
6. Veja os logs da plataforma e confirme que não há tokens impressos.

## Rotação De Credenciais

Revogue e recrie credenciais quando:

- Um token aparecer em print, chat, log ou commit.
- Um colaborador perder acesso ao projeto.
- O bot for movido para outra plataforma.
- Houver suspeita de acesso indevido.

Depois de rotacionar, atualize os secrets da plataforma e faça novo deploy/restart.

## O Que Pode Ser Versionado

- `Dockerfile`
- `.dockerignore`
- `fly.toml` sem secrets
- `.env.example` sem valores reais
- Documentação com placeholders

## O Que Não Pode Ser Versionado

- `.env`
- `*.db`
- tokens do Discord
- tokens do GitHub
- PATs do Azure DevOps
- logs com headers ou respostas autenticadas
- screenshots de painel com secrets preenchidos
