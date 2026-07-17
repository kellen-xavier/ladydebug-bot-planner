# Tutorial de Reports para Equipes de Desenvolvimento (XP)

> Como a sua **equipe de engenharia** usa o Bot Daily Planner para centralizar a
> gestão do dia a dia de forma simples — e como cada report do bot já carrega, na
> prática, os valores do **Extreme Programming (XP)**.

Este guia é para **times que trabalham juntos**. A ideia é simples: cada organização
(a sua equipe) tem o seu espaço, e cada pessoa desenvolvedora registra o que faz ao
longo do dia. Ao fechar o dia, o bot gera um **report compilado** que vira a *daily
assíncrona* do time — sem reunião longa, sem planilha, sem ninguém perguntando "no que
você mexeu hoje?".

---

## 1. O que é o Bot Daily Planner para o time

O bot **centraliza a gestão** do trabalho de engenharia em um único lugar:

- Cada pessoa abre o dia (`/inicio`), registra seus movimentos (notas, links,
  commits/PRs, tarefas) e fecha o dia (`/fim`).
- Ao fechar, o bot publica um **report do dia** em um canal compartilhado
  (`#release-notes` por padrão), visível para toda a equipe.
- O report é **texto puro**, então funciona igual no **Discord** e no **Slack** — o
  mesmo núcleo atende os dois canais (arquitetura hexagonal).

O bot não substitui a liderança nem o board de tarefas. Ele **facilita a comunicação**:
transforma o esforço espalhado do dia em um resumo claro que o time inteiro consegue ler
em segundos.

---

## 2. Extreme Programming em uma frase

O **Extreme Programming (XP)** é uma metodologia ágil desenhada para melhorar a
qualidade do software e a capacidade de resposta do time por meio de **ciclos curtos de
desenvolvimento**, **feedback contínuo** e **práticas técnicas disciplinadas**.

O XP se apoia em **cinco valores centrais**:

| Valor XP | Em uma linha |
|---|---|
| **Comunicação** (Communication) | O time troca informação de forma direta e frequente. |
| **Simplicidade** (Simplicity) | Faça a coisa mais simples que funciona; nada supérfluo. |
| **Feedback** (Feedback) | Sinais rápidos e constantes sobre o que está funcionando. |
| **Coragem** (Courage) | Dizer a verdade sobre o progresso e mudar de rumo quando preciso. |
| **Respeito** (Respect) | Cada pessoa e cada contribuição do time importam. |

O Bot Daily Planner foi pensado para **representar esses valores na prática** — não como
teoria, mas como o comportamento padrão de cada comando.

---

## 3. Os 5 valores do XP dentro do bot

Cada valor do XP corresponde a algo concreto que o bot faz. Esta é a espinha dorsal do
tutorial: quando você usa o report, você já está praticando XP.

### 🗣️ Comunicação
- `/fim` publica o report no canal compartilhado (`#release-notes`): **todo o time vê**
  o que cada pessoa entregou, sem precisar perguntar.
- `/inicio` mostra um **recap do dia anterior** (o que foi registrado e as tarefas em
  aberto), retomando o contexto para quem lê.
- `/nota` e o comentário do `/link` deixam registrada a **intenção** por trás de cada
  movimento — o link vem com o "porquê", não solto.
- O mesmo report serve Discord e Slack: a comunicação não fica presa a uma ferramenta.

### 🧩 Simplicidade
- Poucos comandos, cada um com **uma responsabilidade** (`/inicio`, `/nota`, `/link`,
  `/pr`, `/task`, `/fim`).
- O report é **texto conciso**, separado em seções claras (Links → Atividades →
  Tarefas), sem ruído visual.
- **Não há horário fixo de fechamento**: o dia fecha quando você manda `/fim`. Menos
  cerimônia, menos processo.
- Se nada foi registrado, o report diz exatamente isso ("Nenhum movimento registrado
  hoje") — simples e honesto.

### 🔁 Feedback
- O **report diário é o loop de feedback** do time: em um lugar só, todos veem o que
  andou (e o que não andou).
- A **detecção de travamento** (`stalled_tasks`) sinaliza tarefas "Em Andamento" que
  ficaram paradas tempo demais — feedback automático de que algo empacou.
- A **máquina de estados** das tarefas (`Pendente → Em Andamento → Concluído → Aceito`)
  torna o progresso visível e mensurável, com **"Aceito"** representando o aceite de
  quem revisa/recebe o trabalho.
- Links e PRs recebem um **resumo factual** — feedback rápido sobre o conteúdo sem abrir
  cada um.

### 💪 Coragem
- O report mostra o dia **como ele foi**, sem inflar: registrar um dia magro é ter
  coragem de ser transparente.
- Registrar uma tarefa travada, ou **reabrir** algo dado como concluído
  (`Concluído → Em Andamento`), é encarar a realidade em vez de esconder.
- Expor bloqueios cedo, no report, é mais barato do que descobri-los na entrega.

### 🤝 Respeito
- Cada pessoa tem a **sua própria sessão de dia** (por `user_id`): o bot respeita o ritmo
  individual, sem impor um relógio comum.
- O report **conciso respeita o tempo de quem lê** — a daily assíncrona não rouba a manhã
  do time em reunião.
- **Um canal só** para reports mantém o sinal alto e não polui outros espaços do time.
- O estado terminal **"Aceito"** respeita o aceite de quem revisa: nada é dado como
  pronto por conta própria.

---

## 4. Como a equipe se organiza

```
Organização (sua equipe)  =  servidor do Discord (guild) / workspace do Slack
├── #daily-comandos     ← cada dev roda /inicio, /nota, /link, /task, /fim aqui
└── #release-notes      ← o bot publica os reports do dia (canal compartilhado)
```

- **Cada pessoa** roda o seu próprio ciclo de dia — o bot separa por usuário.
- O **canal de reports** (`#release-notes` por padrão) é onde a gestão acontece: é ali
  que o time acompanha, de forma centralizada, o que foi feito.
- Para apontar outro canal, configure `DISCORD_REPORT_CHANNEL_NAME` (ou
  `DISCORD_REPORT_CHANNEL_ID`). Detalhes no [README](../README.md).

---

## 5. O ciclo do dia, passo a passo

Este é o tutorial prático. Cada pessoa da equipe repete este ciclo:

### Passo 1 — Abrir o dia
```
/inicio
```
O bot responde com a hora de início **e** o recap do dia anterior (feedback: o que você
registrou ontem e quais tarefas seguem em aberto). Se um dia já estiver aberto, use
`/continuar`.

### Passo 2 — Registrar os movimentos (em qualquer ordem, sem pressa)
```
/nota  revisei a arquitetura do módulo de pagamentos
/link  url:https://docs.exemplo.com/adr-007  comentario:decisão de arquitetura que segui
/pr    url:https://github.com/org/repo/pull/42  comentario:refatora o LinkIngestor
/task  titulo:cobrir SimpleFetcher com testes de erro
```
- `/nota` → uma atividade em texto.
- `/link` → ingere a URL, extrai metadados e **resume** (o comentário explica o porquê).
- `/pr` → registra um Pull Request (rejeita URLs que não sejam PR, deixando a intenção
  clara).
- `/task` → cria uma tarefa na máquina de estados.
- `/task-status` → lista as tarefas do time e em que estado cada uma está.
- `/task-finish task_id:<id>` → **fecha uma tarefa depois de concluí-la**, levando-a a
  _Concluído_ em um passo só. É o "task-done": ao terminar, você encerra o ciclo da
  tarefa e isso fica visível no report.

> **Comunicação + Feedback na prática:** todo link e todo PR entram no report com um
> resumo. Quem lê entende o dia sem abrir 10 abas.

### Passo 3 — Fechar o dia e gerar o report
```
/fim
```
O bot **compila tudo** (links, atividades, tarefas, tempo em call no Discord) e publica o
report em `#release-notes`. No canal de comandos, você recebe só uma confirmação
discreta — **respeito** pela atenção do time.

### Passo 4 — O time lê a daily assíncrona
Ninguém precisa se reunir para saber o andamento. O `#release-notes` acumula os reports
do dia de cada pessoa: essa é a **gestão centralizada e facilitada** que o bot entrega.

---

## 6. Anatomia de um report

Um report de `/fim` tem esta cara (as seções só aparecem quando há conteúdo):

```txt
📋 Report do dia — 15/07/2026
🕐 Início 09:12 · Fim 18:03 · Em call: 1h20

🔗 Links e referências (1):
   • ADR-007: estratégia de ingestão de links
     Resumo factual do documento em 3–4 parágrafos, sem opinião.
     ↳ https://docs.exemplo.com/adr-007

✅ Atividades (2):

   Pull Requests:
   - PR #42 — refatora o LinkIngestor

   Notas:
   - revisei a arquitetura do módulo de pagamentos

──────────────────────────────
🗂 Tarefas:
   - Em Andamento (1): cobrir SimpleFetcher com testes de erro
   - Concluído (1): documentar tutorial de reports

— Lembrete para amanhã: retomar as tarefas em andamento.
```

Leia esse report pelas lentes do XP:

- **Comunicação**: o dia inteiro em uma tela, no canal do time.
- **Simplicidade**: seções separadas, texto limpo, sem firula.
- **Feedback**: as tarefas por status + o lembrete de amanhã fecham o ciclo.
- **Coragem**: se o dia foi magro, o report mostra — sem maquiagem.
- **Respeito**: curto o suficiente para respeitar o tempo de quem lê.

---

## 7. Reports como prática de XP no time

Os princípios do XP que sustentam o uso do report em equipe:

- **Ciclos curtos**: o "dia" é a unidade. `/inicio` → registrar → `/fim` é um ciclo
  fechado, todo dia, com uma entrega visível (o report).
- **Feedback contínuo**: o recap de `/inicio` e o report de `/fim` mantêm o time
  informado sem esperar por uma reunião semanal.
- **Comunicação sobre documentação pesada**: em vez de status report manual, o bot
  gera o compilado a partir do que realmente aconteceu.
- **Transparência (coragem + respeito)**: o report é fiel ao dia; o time confia porque o
  que está lá é o que foi feito.
- **Integração ao fluxo real**: PRs, commits e links entram no report como parte natural
  do trabalho, não como uma etapa extra de burocracia.

---

## 8. Boas práticas para a equipe

- **Registre no momento**: cole o link/PR quando ele acontece, não no fim do dia de
  memória. O resumo fica melhor e o dia fica fiel (feedback + coragem).
- **Comente a intenção**: no `/link` e no `/pr`, diga *por que* aquilo importa. Um link
  sem contexto comunica pouco.
- **Um canal de reports só**: mantenha todos os `/fim` em `#release-notes`. Isso
  respeita a atenção do time e centraliza a gestão.
- **Seja honesto com o dia magro**: um `/fim` com pouca coisa é informação válida —
  provavelmente sinaliza um bloqueio que vale conversar.
- **Reabra sem medo**: se algo "Concluído" voltou a exigir trabalho, mova de volta para
  "Em Andamento". A máquina de estados existe para refletir a realidade.
- **Feche o dia**: o report só existe no `/fim`. Sem fechar, o time não vê o seu dia.
- **Feche a tarefa ao terminar**: use `/task-finish` assim que concluir. Tarefa que
  fica "em aberto" para sempre polui o `/task-status` e esconde o progresso real
  (feedback). Encerrar o ciclo é tão importante quanto abri-lo.

---

## 9. Configuração rápida (para o time)

O passo a passo completo de instalação, `.env` e deploy está no
[README](../README.md) e em [`deploy-and-docker.md`](deploy-and-docker.md). O essencial
para uma equipe:

```env
# canal onde o /fim publica o report do dia (a "gestão centralizada")
DISCORD_REPORT_CHANNEL_NAME=release-notes
# opcional: use o ID para evitar conflito entre canais de mesmo nome
# DISCORD_REPORT_CHANNEL_ID=id_do_canal
```

Quando `#release-notes` existe no servidor, `/fim` publica o report lá e responde no
canal de comandos apenas com uma confirmação efêmera. Se o canal não for encontrado, o
bot mantém o comportamento seguro de enviar o report no canal atual.

---

## 10. Resumo

| O time quer… | …e o bot entrega via… | …ancorado no valor XP |
|---|---|---|
| Saber o que cada um fez | report do `/fim` em `#release-notes` | Comunicação |
| Menos reunião e menos processo | comandos simples + report em texto | Simplicidade |
| Acompanhar progresso e bloqueios | recap, status de tarefa, detecção de travamento | Feedback |
| Transparência real do dia | report fiel, reabertura de tarefas | Coragem |
| Ritmo individual + atenção do time | sessão por pessoa, report conciso, um canal | Respeito |

O Bot Daily Planner é, no fim, **o XP em forma de rotina**: ciclos curtos, feedback
contínuo e comunicação clara — de um jeito simples e prático, todo dia.
