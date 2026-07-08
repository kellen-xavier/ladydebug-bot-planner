# AGENTS.md - Bot Daily Planner

## Visão Geral

Bot Daily Planner e um bot de daily updates para registrar movimentos do dia, tarefas, links, commits, PRs e tempo em call, gerando um report consolidado ao fechar o dia.

O projeto usa arquitetura hexagonal para manter a regra de negocio isolada das plataformas. Discord, Slack futuro, console futuro, SQLite, APIs de VCS, fetchers de links e summarizers entram como adaptadores trocaveis atras de ports.

## Objetivo

O objetivo imediato e evoluir da Fase 0 para a Fase 1 sem quebrar essa separacao: adicionar resumo real de links e documentos, extracao melhor de conteudo e tratamento previsivel de falhas, mantendo testes rapidos, offline e sem tokens.

## Estado Atual

Este projeto esta na Fase 0, com a base funcional em Python e arquitetura hexagonal.

- O nucleo fica em `src/daily/core/` e nao deve depender de Discord, rede, SQLite, `requests` ou qualquer provedor externo.
- As portas ficam em `src/daily/ports/` usando `Protocol` e dataclasses de transferencia.
- Adaptadores concretos ficam em `src/daily/adapters/`.
- `src/daily/command_router.py` e a fronteira comum para Discord e futuros adaptadores como Slack ou console.
- `src/daily/main.py` e o composition root: monte dependencias concretas apenas ali ou em factories equivalentes.
- A suite atual testa o nucleo com dublês em `tests/conftest.py`.

## Comandos de Trabalho

Use estes comandos para validar mudancas:

```bash
pip install -e ".[dev]"
pytest
```

Para rodar o bot real no Discord:

```bash
cp .env.example .env
pip install -e .
python -m daily.main
```

Antes de assumir que o fluxo de console existe, verifique se ha `console.py`. No estado atual analisado, esse arquivo nao esta presente na raiz.

## Regras Arquiteturais

- Preserve a arquitetura hexagonal: regra de negocio no core, I/O nos adapters.
- Nao importe `discord`, `requests`, SDKs de LLM, bibliotecas de parsing ou SQLite dentro de `src/daily/core/`.
- Toda dependencia externa nova deve entrar atras de uma port existente ou nova em `src/daily/ports/`.
- Prefira injeção de dependencias em vez de singletons ou acesso direto a variaveis de ambiente.
- Variaveis de ambiente devem ser lidas no composition root ou em adaptadores concretos.
- Mantenha adaptadores de plataforma finos: eles traduzem eventos para `CommandRouter` e formatam resposta.
- Todo bug corrigido deve ganhar teste de regressao primeiro quando for viavel.
- Testes unitarios nao devem fazer rede, acessar Discord ou depender de tokens.

## Fase 1 - Objetivo

Implementar resumo real de links e documentos mantendo as pecas mockaveis.

Entregaveis esperados:

- Substituir o placeholder `EchoSummarizer` por um `LLMSummarizer` plugavel.
- Manter `EchoSummarizer` ou um fake equivalente apenas para desenvolvimento/testes offline, se ainda for util.
- Evoluir `SimpleFetcher` para extrair texto limpo e metadados de paginas genericas.
- Adicionar suporte a `.docx` com dependencia dedicada, como `mammoth`, atras da port `LinkFetcher`.
- Tratar Dropbox ou links de arquivo de forma previsivel quando retornarem conteudo baixavel.
- Garantir que falhas de fetch/resumo nao derrubem a sessao do dia.
- Atualizar README com como testar offline, com LLM real e com links reais.

## Fase 1 - Implementacao Recomendada

1. Comece pelos testes do core/adapters com dublês de `LinkFetcher` e `Summarizer`.
2. Defina o comportamento de erro de ingestao de links antes de chamar APIs reais.
3. Implemente um adapter de summarizer real em `src/daily/adapters/`, sem tocar no core.
4. Implemente extratores em adapters pequenos e componha-os via `main.py`.
5. Adicione dependencias no `pyproject.toml` somente quando usadas por adapters reais.
6. Rode `pytest` e, se houver credenciais locais, faça um teste manual com URL real.

## LLM Summarizer

O provedor ainda precisa ser confirmado pela pessoa mantenedora. Se nao houver decisao explicita, nao fixe Claude, OpenAI ou outro provedor no core.

Contrato esperado da port atual:

```python
class Summarizer(Protocol):
    def summarize(self, text: str, metadata: dict) -> str: ...
```

Comportamento esperado:

- Produzir resumo factual em 3 a 4 paragrafos.
- Nao inventar detalhes ausentes no texto.
- Usar metadados como titulo, autor e data apenas quando disponiveis.
- Limitar tamanho de entrada para evitar custo excessivo e erro de contexto.
- Retornar erro controlado ou mensagem tecnica curta quando a API falhar.

## Ingestao de Links

O fluxo atual esta em `src/daily/core/link_ingest.py`:

- URLs GitHub/Azure DevOps reconhecidas por `VCSProvider` viram `EntryType.COMMIT` ou `EntryType.PR`.
- URLs genericas passam por `LinkFetcher` e depois por `Summarizer`.
- URLs terminadas em `.docx` viram `EntryType.DOC`.

Ao evoluir essa area:

- Nao coloque parsing HTML, download de arquivo ou chamada LLM dentro de `LinkIngestor`.
- Nao deixe excecoes de rede vazarem ate o Discord sem mensagem amigavel.
- Preserve os metadados relevantes em `Entry.metadata`.
- Teste separadamente deteccao VCS, pagina generica, `.docx` e erro de fetch.

## Pontos de Atencao Encontrados

- O README menciona comandos de Fase 0 e proximas fases, mas ainda nao documenta `console.py`.
- `pyproject.toml` ja comenta `mammoth` e `trafilatura` como candidatas para Fase 1, mas elas ainda nao estao ativas.
- `SimpleFetcher` faz GET real e usa `resp.text[:20000]`; isso e suficiente para MVP, mas nao para resumo factual robusto.
- `EchoSummarizer` e placeholder e nao deve ser tratado como implementacao final.
- `discord_bot.py` chama `router._day` diretamente para voz; se mexer nisso, prefira expor metodos no `CommandRouter` em vez de aumentar acesso a membros privados.

## Criterios de Aceite da Fase 1

- `pytest` passa sem tokens e sem rede.
- O core continua sem imports de adapters ou bibliotecas externas de I/O.
- `LinkIngestor` continua recebendo dependencias injetadas.
- Existe pelo menos um teste cobrindo resumo de pagina generica via dublê.
- Existe pelo menos um teste cobrindo erro de fetch/resumo sem quebrar o fechamento do dia.
- O README explica como testar camada offline e camada com APIs reais.
- Credenciais reais nao aparecem em codigo, docs ou fixtures.

## Estilo do Projeto

- Codigo simples, direto e pequeno.
- Preferir dataclasses e Protocols, seguindo o padrao atual.
- Nomes em ingles no codigo, mensagens de usuario em portugues.
- Comentarios devem explicar decisoes ou limites, nao repetir o obvio.
- Evite compatibilidade prematura; se houver duvida de produto, pergunte antes de criar duas solucoes.
