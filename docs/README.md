# Documentação do projeto

Índice da documentação técnica. Os documentos de arquitetura descrevem o diagnóstico do baseline e a direção planejada;
**o que está marcado como planejado, proposto ou alvo não está implementado.**

## Desenvolvimento e organização

| Documento | Conteúdo |
|-----------|----------|
| [`FLUXO_DE_DESENVOLVIMENTO.md`](FLUXO_DE_DESENVOLVIMENTO.md) | Branches, commits, revisão, merge e tags |
| [`ORGANIZACAO_DO_REPOSITORIO.md`](ORGANIZACAO_DO_REPOSITORIO.md) | Estrutura atual, regras de higiene e relação entre branches e fases |
| [`LIMITACOES_E_AUDITORIA.md`](LIMITACOES_E_AUDITORIA.md) | Limitações da Entrega 1 e achados da auditoria inicial |

## Arquitetura (Fases 01 e 02)

| Documento | Conteúdo |
|-----------|----------|
| [`AUDITORIA_ARQUITETURAL.md`](AUDITORIA_ARQUITETURAL.md) | 21 achados com evidência (executada ou estática), tratamento de cada achado e análise de `app/` |
| [`DECISOES_APROVADAS.md`](DECISOES_APROVADAS.md) | Decisões aprovadas (D-02 a D-06, D-10, D-11, D-13, D-14, validações, desativação de usuários) e decisões pendentes |
| [`MATRIZ_RASTREABILIDADE.md`](MATRIZ_RASTREABILIDADE.md) | Requisitos das Entregas 1 e 2: situação, evidência, lacuna, fase e critério de aceitação; separa requisitos oficiais, decisões aprovadas e melhorias |
| [`adr/`](adr/README.md) | Decisões arquiteturais (ADR-0001 a 0009): stack, camadas, responsabilidades, Repository, injeção de dependências, testes, datas e relógio, estrutura do backend, papéis e regras da OS |
| [`DIAGRAMAS.md`](DIAGRAMAS.md) | Componentes, camadas, entidades, máquina de estados e fluxo da OS (Mermaid) |
| [`PRINCIPIOS_SOLID_E_PADROES.md`](PRINCIPIOS_SOLID_E_PADROES.md) | SOLID e padrões: situação atual × plano e como serão demonstrados |
| [`PLANO_DE_MIGRACAO.md`](PLANO_DE_MIGRACAO.md) | Roteiro incremental por fase, riscos, critérios de aceitação e decisões pendentes |
| [`RELATORIO_FASE_02.md`](RELATORIO_FASE_02.md) | Relatório final da Fase 02: implementado, requisitos, padrões, testes, limitações e transição |

## Persistência e próximas fases (Fase 03)

| Documento | Conteúdo |
|-----------|----------|
| [`PERSISTENCIA.md`](PERSISTENCIA.md) | PostgreSQL, SQLAlchemy e Alembic: modelo, decisões, configuração, comandos, testes e limitações |
| [`MAPEAMENTO_API_FRONTEND.md`](MAPEAMENTO_API_FRONTEND.md) | Requisitos obrigatórios mapeados para FastAPI e React (a API foi implementada; o React é planejamento) |
| [`API.md`](API.md) | API HTTP (Fase 04): como executar, autenticação, erros, endpoints, paginação, segurança e testes |
| [`FRONTEND.md`](FRONTEND.md) | Frontend React (Fase 05): arquitetura, telas, responsividade, testes e limitações |
| [`RELATORIO_FASE_05.md`](RELATORIO_FASE_05.md) | Relatório da Fase 05: entrega, testes executados (inclusive E2E no PostgreSQL), pendências |
| [`EXECUCAO_LOCAL.md`](EXECUCAO_LOCAL.md) | Passo a passo: PostgreSQL, API, frontend e acesso pelo celular |
| [`INSTALACAO_POSTGRESQL_WINDOWS.md`](INSTALACAO_POSTGRESQL_WINDOWS.md) | Instalação permanente do PostgreSQL 16 no Windows, banco, papel, `.env` e verificação (sem expor senhas) |
| [`ACESSO_PELO_CELULAR.md`](ACESSO_PELO_CELULAR.md) | Teste pelo celular na rede local: proxy, cookies, CSRF, CORS, firewall e limitações do HTTP |

## Na raiz do repositório

- [`../README.md`](../README.md): como executar a Entrega 1 (CLI).
- [`../DOCUMENTACAO.md`](../DOCUMENTACAO.md): decisões de projeto da Entrega 1.

Ordem de leitura sugerida: auditoria → decisões aprovadas → matriz → ADRs → diagramas → SOLID e padrões → plano de migração.

As decisões aprovadas foram implementadas no novo backend (`backend/`) na Fase 02, conforme o
[`RELATORIO_FASE_02.md`](RELATORIO_FASE_02.md); a CLI legada da Entrega 1 continua preservada e inalterada.
