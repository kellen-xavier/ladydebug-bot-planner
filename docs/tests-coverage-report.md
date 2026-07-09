# Report de Cobertura de Testes

Data da análise: 2026-07-09

## Objetivo

Este report lista o que ainda precisa ser testado para aumentar o controle da
aplicação, reduzir regressões e melhorar a manutenibilidade do projeto.

A meta não é apenas aumentar quantidade de testes, mas garantir que cada
funcionalidade tenha validação útil, com cenários de sucesso, erro e borda, sem
testes enviesados ou falso positivo.

## Estado Atual

Suíte atual:

```bash
./.venv/bin/python -m pytest
```

Resultado atual:

```txt
79 passed
```

Cobertura percentual ainda não é medida porque `coverage`/`pytest-cov` não está
instalado nas dependências de desenvolvimento.

## Diretrizes Para Novos Testes

- Testes unitários devem continuar offline, sem rede, sem Discord real e sem tokens.
- Adaptadores externos devem usar fakes/mocks controlados.
- Cada teste deve falhar se o comportamento real quebrar, evitando asserts genéricos.
- Erros esperados devem retornar mensagens controladas, sem stack trace para o usuário.
- Dados sensíveis nunca devem aparecer em mensagens de usuário, logs ou fixtures.
- Fluxos felizes e fluxos de erro devem ser cobertos para cada funcionalidade pública.

## Prioridade 1 - Controle Do CommandRouter

O `CommandRouter` é a fronteira comum entre Discord e futuros adaptadores. Ele
precisa de cobertura forte porque concentra o comportamento visível dos comandos.

### Implementar testes para `task_nova`

Cenários:

- Criar tarefa retorna mensagem com ID e título.
- Tarefa criada é persistida no storage.
- Título vazio ou só espaços deve ter comportamento definido.

Decisão necessária:

- Se título vazio deve ser rejeitado, implementar validação e mensagem amigável.

### Implementar teste explícito para `link` com sucesso

Cenários:

- Com dia aberto, `router.link()` ingere link genérico e adiciona entrada na sessão.
- Com dia aberto, `router.link()` ingere commit/PR e adiciona entrada correta.
- Comentário informado aparece no resumo/entrada.

Validação esperada:

- A sessão aberta passa a ter uma nova entry.
- A mensagem retorna `🔗 Registrado: ...`.
- O tipo da entry é preservado.

### Ampliar teste de `feedback`

Cenários:

- Feedback via router atualiza `last_activity_at`.
- Feedback com texto vazio tem comportamento definido.

Decisão necessária:

- Se feedback vazio deve ser aceito ou rejeitado.

## Prioridade 2 - Persistência SQLite

O `SqliteStorage` já tem testes básicos, mas precisa de cenários de persistência
entre instâncias para simular reinício local/produção.

### Testar reabertura do banco com nova instância

Cenários:

- Salvar sessão em uma instância de `SqliteStorage`.
- Criar nova instância apontando para o mesmo arquivo.
- Recarregar sessão, entries e voice intervals.

Validação esperada:

- Dados continuam disponíveis após recriar o storage.
- Datas, enums e metadados são reidratados corretamente.

### Testar `get_last_closed_session` com múltiplas sessões

Cenários:

- Criar duas sessões fechadas para o mesmo usuário.
- Criar sessão fechada para outro usuário.
- Garantir que retorna a sessão mais recente do usuário correto.

Validação esperada:

- Não mistura usuários.
- Não retorna sessão antiga.

### Testar sessão aberta concorrente no storage

Cenários:

- Salvar uma sessão aberta.
- Salvar uma sessão fechada do mesmo usuário.
- `get_open_session` retorna apenas a aberta.

## Prioridade 3 - Fetcher E Segurança De Rede

O `SimpleFetcher` é um adaptador de I/O real. Mesmo com rede mockada, precisa de
cobertura para falhas previsíveis.

### Testar fallback de título pela URL

Cenários:

- HTML sem `<title>`.
- URL termina com `/artigo`.
- Título retornado deve ser `artigo`.

### Testar falha de DNS

Cenários:

- `socket.getaddrinfo` levanta `OSError`.
- `_validate_fetch_url` retorna `ValueError` controlado.

Validação esperada:

- Mensagem contém `URL bloqueada`.
- Erro original não vaza detalhes internos desnecessários.

### Testar host sem hostname

Cenários:

- URL malformada como `https:///sem-host`.
- Deve rejeitar com `host ausente`.

## Prioridade 4 - VCS Adapters

Os providers reais de GitHub/Azure já têm cobertura de sucesso e URL inválida.
Faltam falhas de API e ausência da dependência `requests`.

### Testar `raise_for_status`

Cenários:

- GitHub commit retorna response fake cujo `raise_for_status` falha.
- Azure PR retorna response fake cujo `raise_for_status` falha.

Validação esperada:

- A exceção é propagada para o `CommandRouter.link`, que deve retornar mensagem amigável.
- Nenhum token aparece na resposta final.

### Testar ausência de `requests`

Cenários:

- `daily.adapters.vcs.requests = None`.
- `GitHubProvider.fetch` retorna `RuntimeError` controlado.
- `AzureDevOpsProvider.fetch` retorna `RuntimeError` controlado.

Observação:

- Esse teste deve restaurar o módulo após execução via `monkeypatch`.

## Prioridade 5 - Report De Fim De Dia

O report é uma saída crítica para o usuário. Deve cobrir todos os tipos de entrada
visíveis.

### Cobrir `EntryType.REUNIAO` e `EntryType.VOZ`

Cenários:

- Sessão com entry de reunião.
- Sessão com entry de voz.

Validação esperada:

- Seções `Reuniões` e `Voz` aparecem no report.
- Títulos e resumos aparecem no local correto.

### Cobrir formatos de duração

Cenários:

- `30min` para menos de 1 hora.
- `1h` para hora exata.
- `1h05` para hora com minutos.

Validação esperada:

- Cada formato aparece exatamente como esperado.

### Cobrir tarefas por todos os estados

Cenários:

- Report com tarefas `Pendente`, `Em Andamento`, `Concluído` e `Aceito`.

Validação esperada:

- Cada estado aparece na seção de tarefas.
- Contadores por status estão corretos.

## Prioridade 6 - Discord Adapter

Os testes atuais cobrem sincronização e voz, mas não os callbacks dos slash
commands. Como Discord é plataforma externa, os testes devem usar interactions
fake.

### Testar callbacks de comandos

Cenários:

- `/inicio` chama `router.inicio` com `user.id` e `channel_id`.
- `/continuar` chama `router.continuar`.
- `/nota` chama `router.nota` com texto.
- `/link` chama `defer`, depois `followup.send`.
- `/task` chama `router.task_nova`.
- `/fim` chama `router.fim`.

Validação esperada:

- Resposta enviada ao Discord fake corresponde ao retorno do router.
- Nenhum callback deve acessar rede, storage real ou Discord real.

### Testar `build_client`

Cenários:

- Client é criado com `voice_states=True`.
- Comandos esperados são registrados na tree.

Observação:

- Se for difícil inspecionar `discord.py`, priorizar testes de callbacks extraídos
  para funções auxiliares pequenas.

## Prioridade 7 - Models E DTOs

Cobertura atual é indireta. Não é a maior prioridade, mas ajuda a documentar
contratos simples.

### Testar `VoiceInterval.seconds`

Cenários:

- Com `left_at=None`, retorna `0`.
- Com intervalo fechado, retorna segundos corretos.

### Testar `Task.can_transition_to`

Cenários:

- Transições permitidas retornam `True`.
- Transições proibidas retornam `False`.

## Métrica Objetiva De Cobertura

Adicionar ferramenta de coverage às dependências dev.

Opção recomendada:

```toml
pytest-cov>=5.0
```

Comando recomendado:

```bash
./.venv/bin/python -m pytest --cov=src/daily --cov-report=term-missing
```

Critério inicial sugerido:

- Meta mínima: 85% de cobertura total.
- Meta para `src/daily/core`: 95% ou mais.
- Meta para adapters com I/O: cobertura por fakes/mocks dos fluxos principais e erros previsíveis.

## Critérios De Aceite Para A Próxima Rodada

- Todos os testes devem passar com `pytest`.
- `ruff check .` deve passar.
- Nenhum teste deve fazer rede real.
- Nenhum teste deve depender de token, Discord real ou banco real persistente.
- Cada nova tratativa de erro deve ter teste de regressão.
- Mensagens de erro para usuário devem ser amigáveis e não conter segredo.

## Ordem Recomendada De Execução

1. Fechar lacunas do `CommandRouter`.
2. Fortalecer `SqliteStorage` com reabertura e múltiplas sessões.
3. Completar casos do `SimpleFetcher`.
4. Completar falhas de VCS.
5. Completar variações do report.
6. Extrair/testar callbacks Discord se necessário.
7. Adicionar `pytest-cov` e estabelecer meta de cobertura.
