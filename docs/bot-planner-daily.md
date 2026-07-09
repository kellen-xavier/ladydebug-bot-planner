# Bot Planner Daily

Preciso criar um Bot para o Discord, que seja compatível também como bot para o Slack (Mensagens multicanal), que faça um compilado de "Updates do dia" (ou Daily, Work updates: what has been done today) o que foi feito, qual minhas tasks, qual os meus commits e branchs com PRs, quais documentos foram envolvidos, e que me permita que eu envie links, envie links de commits do github (e seja compatível com Azure DevOps Repositorio) - então deve ser possível ver o repositório, commits e PRs. Os meus comentários ao longo da semana, que eu enviar são sobre o que foi feito na atividade do commit. Deve ser possível a partir das atividades do repositório, também poder anexar Tarefas (Links), para que seja acompanhada as Tasks/Tarefas, as tarefas também deve poder enviar links de documentações (ou apenas comentar do que se trata os links de forma informativa para quem o ler). A partir das branchs e os PRs deve me dar um Deployment Guide. Deve com base de comandos, solicitar a arquitetura do projeto e como esta ficando com base no novo código a ser desenvolvido. Todos os links enviados no dia (ou seja todo movimento do dia) deve ser anexado com os "Updates do dia", ou seja deve ser dado como uma daily para informar, que foi iniciado (comando para iniciar o bot) e pode monitorar de forma like "Gestão" o que foi feito, e quando dado (comando para fim do dia) deve gerar o report do que foi feito. Isso deve incluir também, se caso for feita chamadas (via Discord/Slack) deve informar o tempo em chamada. Deve ser informativo.

Deve criar também uma lista de comandos para que seja possível selecionar a opção, para enviar o link de documento, gerar uma nova tarefa, acompanhar se essa tarefa esta quase terminando (status), e poder escrever um feedback do que foi feito (task feedback), agendas realizadas no dia.

Tarefas agendadas — Cron, gatilhos de eventos (padrão de mensagem, eventos do sistema), invocação manual com "guardrails" (tempo de espera, número máximo de tarefas simultâneas, desduplicação)

Máquina de estados de tarefas — Rastreamento completo do ciclo de vida (Pendente→Em Andamento→Concluído→Aceito) com detecção de travamentos e autorreparo.

Sempre que este bot receber minhas mensagens, ele precisará fazer o seguinte:

- Abra a URL, obtenha os metadados (título, data e hora, autor, etc.) e o conteúdo. Faça um breve resumo factual do conteúdo, sem opiniões, apenas o que está explícito no artigo, a essência dele. Um resumo conciso, com no máximo 3 ou 4 parágrafos.

- Analise os commits que foram enviados.
- Fim do dia: Update daily com o compilado do que foi realizado, como lembrete para o dia seguinte.
- Comunicação: clara e objetiva.
- Comentar as atividades feitas quando solicitar para enviar o compilado do dia.

## Repositório Feedback

Deve informar o repositório referente ao projeto, deve informar as linhas de código, comments, commits, Codes, Files, Languagens, PRs.

## Commands bot

## Rules

- Test-Driven Development: toda funcionalidade deve vir acompanhada de testes unitários. Toda correção de bug precisa de testes de regressão.
