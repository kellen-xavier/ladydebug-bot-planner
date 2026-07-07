# Bot Daily Planner — Arquitetura & Roadmap

> Compilado do "Bot Planner Daily.md" + os requisitos que você descreveu, transformados num plano construível. Discord primeiro, Slack depois **sem reescrever nada**.

---

## 1. O princípio central: construir uma vez, plugar em vários canais

A sua exigência mais forte ("faço os testes no Discord, mas preciso que seja compatível com Slack") define a arquitetura inteira. A resposta certa é **arquitetura hexagonal (ports & adapters)**:

```txt
                 ┌─────────────────────────────┐
   Discord  ───▶ │                             │
   Slack    ───▶ │   ADAPTERS (mensageria)     │
                 │  discord.js  /  @slack/bolt  │
                 └──────────────┬──────────────┘
                                │  (mesmos comandos)
                 ┌──────────────▼──────────────┐
                 │        NÚCLEO (core)         │
                 │  regras do dia, tarefas,     │
                 │  ingestão de links, resumo,  │
                 │  geração de report           │
                 └──────────────┬──────────────┘
                                │  (ports)
        ┌───────────┬───────────┼───────────┬───────────┐
     Storage    LinkFetcher  Summarizer  Calendar   VCS (GitHub/
     (SQLite)   (URL→meta)   (LLM)       (Google)   Azure DevOps)
```

O **núcleo não sabe se está no Discord ou no Slack.** Ele recebe um comando abstrato (`iniciarDia`, `registrarLink`, `fecharDia`) e devolve um resultado. Cada plataforma é um adaptador fino que traduz eventos da plataforma → comandos do núcleo e resultado do núcleo → mensagem da plataforma.

Ganho prático: quando o Discord estiver funcionando, o Slack é ~1 adaptador novo + registrar os mesmos comandos. E — importante pra você — o núcleo é 100% testável com adaptadores falsos (dublês), o que casa direto com o requisito de TDD.

---

## 2. Stack recomendada

| Camada | Escolha | Motivo |
|---|---|---|
| Runtime | **Node + TypeScript** | Melhor ecossistema para Discord **e** Slack no mesmo código; tipagem ajuda no núcleo/testes |
| Discord | `discord.js` v14 | Slash commands, eventos de voz nativos |
| Slack | `@slack/bolt` | Slash commands, eventos, o modelo bate com o do Discord |
| Persistência | **SQLite** (via Prisma ou `better-sqlite3`) no MVP → Postgres depois | Zero infra no começo; migração indolor |
| URL → metadados/conteúdo | `undici`/`fetch` + extrator (ex.: `@extractus/article-extractor`) | Título, autor, data, texto limpo |
| Word (.docx) | `mammoth` | Extrai texto de arquivos/links Word para resumir |
| Resumo factual | Chamada a um LLM (ex.: API da Claude) | Os "3–4 parágrafos factuais" do seu doc |
| Testes | **Vitest** (ou Jest) | Rápido, bom para TDD |
| Agendamento | `node-cron` + fila leve | Cron, gatilhos, guardrails |

> Alternativa: dá para fazer tudo em **Python** (`discord.py` + `slack-bolt` + `SQLModel`). Recomendo TypeScript pela paridade Discord/Slack, mas se você prefere Python, o plano inteiro continua valendo — só troca as bibliotecas.

**Restrição de hospedagem (importante):** este bot precisa de um **processo sempre ligado** (não serverless por request), porque ele mantém conexão de gateway com o Discord, escuta entrada/saída de canal de voz e roda cron de fim de dia. Um contêiner pequeno (Railway, Fly.io, uma VPS, ou um Raspberry ligado) resolve. Isso afeta o desenho, por isso já registro aqui.

---

## 3. Modelo de dados (MVP)

- **day_sessions** — `id`, `user_id`, `channel_id`, `started_at`, `ended_at`, `total_voice_seconds`, `status` (aberta/fechada)
- **entries** — cada "movimento do dia": `id`, `session_id`, `type` (link | commit | pr | doc | nota | reuniao | voz), `raw_input`, `title`, `summary`, `metadata_json`, `created_at`
- **tasks** — `id`, `title`, `status` (Pendente→Em Andamento→Concluído→Aceito), `links_json`, `feedback`, `last_activity_at`, `created_at`
- **task_links** — documentação/PRs anexados a uma task, com comentário informativo
- **voice_sessions** — `id`, `session_id`, `joined_at`, `left_at` (soma para o tempo em call)

Uma `day_session` agrega **todas** as `entries` e o tempo de voz daquele dia. O report de fim de dia é uma consulta sobre isso.

---

## 4. Ciclo do dia

```txt
/inicio  ──▶ cria day_session (status=aberta), responde "Dia iniciado 08:32"
   │
   │  durante o dia (em qualquer ordem, sem pressa):
   ├─ você cola um link de commit  → entry(commit)  + resumo
   ├─ você cola link de doc Word/Dropbox/site → entry(doc/link) + metadados + resumo factual
   ├─ /nota "revisei a doc de arquitetura" → entry(nota)
   ├─ /task nova ... / /feedback ... → tasks
   ├─ entrou no canal de voz → voice_session começa a contar
   │
/fim  ──▶ fecha a session, soma tudo, gera REPORT resumido e informativo
```

O ponto que você enfatizou: **o fim do dia não tem horário fixo.** O dia só fecha quando você mandar `/fim`. Até lá tudo que chega é anexado à sessão aberta.

---

## 5. Ingestão de links (o trabalho pesado)

Quando chega uma URL, o núcleo detecta o tipo e trata:

- **Commit/PR do GitHub** → API do GitHub: autor, mensagem, arquivos, linhas +/−, branch, PR associado
- **Azure DevOps** → API REST equivalente (repo, commits, PRs) — mesma interface `VCS` do núcleo
- **Word (.docx) / Dropbox / site genérico** → baixa, extrai metadados (título, data, autor) e conteúdo, faz **resumo factual de 3–4 parágrafos, sem opinião** (exatamente como no seu doc)
- Cada item vira uma `entry` anexada ao dia.

A abstração `VCS` (uma port) faz GitHub e Azure DevOps compartilharem o mesmo formato de saída — o núcleo não sabe qual é qual.

---

## 6. Máquina de estados das tarefas

`Pendente → Em Andamento → Concluído → Aceito`, com:

- **detecção de travamento**: se `last_activity_at` passa de X dias em "Em Andamento", o bot sinaliza (o "autorreparo/alerta" do seu doc)
- `/task-status` mostra quais estão perto de terminar
- `/feedback` grava o "task feedback" do que foi feito

Isso é um ótimo primeiro alvo de TDD: a transição de estados é lógica pura, testável sem Discord nenhum.

---

## 7. Tempo em call — e um aviso honesto

- **Discord**: fácil e confiável. O evento `voiceStateUpdate` diz quando você entra/sai de um canal de voz. Somamos os intervalos → `total_voice_seconds`.
- **Slack**: aqui preciso ser transparente — o rastreamento de **huddles** tem API bem limitada; nem sempre dá pra medir tempo de call como no Discord. Provável saída: no Slack registrar reuniões de forma manual/via evento de calendário, e deixar o cronômetro automático como recurso "Discord-first". Melhor você saber disso agora do que descobrir na Fase 5.

---

## 8. Comandos (MVP)

Os mesmos comandos existem nas duas plataformas (slash commands do Discord e do Slack apontam para o mesmo handler do núcleo):

| Comando | O que faz |
| --- | --- |
| `/inicio` | Abre o dia |
| `/fim` | Fecha o dia e gera o report |
| `/nota <texto>` | Registra uma atividade em texto |
| `/link <url> [comentário]` | Ingere e resume um link |
| `/task nova <título>` | Cria tarefa |
| `/task-status` | Lista tarefas e progresso |
| `/feedback <task> <texto>` | Feedback do que foi feito |
| `/agenda` | Reuniões/eventos do dia |
| `/repo <url>` | Feedback do repositório (linhas, commits, PRs, linguagens) |
| `/report` | Prévia do compilado a qualquer momento |

---

## 9. Roadmap faseado

**Fase 0 — Esqueleto + núcleo testável (Discord)**
Scaffold TS, arquitetura hexagonal, storage SQLite, `/inicio` `/fim` `/nota`, e a suíte de testes já rodando. Fecha o dia com um report simples. *Prova o loop do diário ponta a ponta.*

**Fase 1 — Ingestão de links + resumo**
`/link` com detecção de tipo, metadados, resumo factual via LLM, e integração GitHub (commits/PRs). Report de fim de dia já traz os links resumidos.

**Fase 2 — Tarefas + máquina de estados**
`/task`, transições, detecção de travamento, `/feedback`, `/task-status`.

**Fase 3 — Integrações pesadas**
Google Calendar (OAuth), Dropbox, Azure DevOps, extração de .docx. `/agenda` e `/repo` completos.

**Fase 4 — Voz + geração assistida**
Tempo em call no Discord; *Deployment Guide* a partir de branches/PRs; consulta de arquitetura do projeto com base no novo código.

**Fase 5 — Adaptador Slack**
Reaproveita o núcleo inteiro. Só o adaptador novo + registro de comandos + o ajuste honesto de huddles.

Cron/gatilhos/guardrails (tempo de espera, máximo de tarefas simultâneas, desduplicação) entram como camada transversal a partir da Fase 2.

---

## 10. TDD, do jeito que você trabalha

- O **núcleo é lógica pura** (sessão do dia, transições de task, montagem do report) → testes unitários rápidos com dublês de Storage/LinkFetcher/Summarizer.
- Todo bug → **teste de regressão** que reproduz o bug antes do fix (Red → Green → Refactor).
- Os adaptores (Discord/Slack) ficam finos de propósito, então quase toda regra sob teste vive no núcleo, longe da rede.
- Contratos das *ports* (ex.: `VCS`, `CalendarProvider`) testados com um "contract test" reaproveitável entre GitHub/Azure e Google/outros calendários.

---

## 11. Decisões que preciso de você antes de escrever código

1. **Stack**: confirma TypeScript, ou prefere Python?
2. **Hospedagem**: você já tem onde rodar um processo sempre ligado (VPS/Railway/Fly/máquina local)?
3. **Prioridade do MVP**: as Fases 0–1 (loop do diário + links resumidos) atendem primeiro, ou tem alguma integração (ex.: Google Calendar ou Azure DevOps) que é indispensável já na primeira versão?
