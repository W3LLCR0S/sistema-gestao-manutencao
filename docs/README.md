# Documentação do projeto

Índice da documentação técnica. Os documentos de arquitetura descrevem o diagnóstico do baseline e a direção planejada;
**o que está marcado como planejado, proposto ou alvo não está implementado.**

## Desenvolvimento e organização

| Documento | Conteúdo |
|-----------|----------|
| [`FLUXO_DE_DESENVOLVIMENTO.md`](FLUXO_DE_DESENVOLVIMENTO.md) | Branches, commits, revisão, merge e tags |
| [`ORGANIZACAO_DO_REPOSITORIO.md`](ORGANIZACAO_DO_REPOSITORIO.md) | Estrutura atual, regras de higiene e relação entre branches e fases |
| [`LIMITACOES_E_AUDITORIA.md`](LIMITACOES_E_AUDITORIA.md) | Limitações da Entrega 1 e achados da auditoria inicial |

## Arquitetura (Fase 01)

| Documento | Conteúdo |
|-----------|----------|
| [`AUDITORIA_ARQUITETURAL.md`](AUDITORIA_ARQUITETURAL.md) | 21 achados com evidência (executada ou estática), tratamento de cada achado e análise de `app/` |
| [`DECISOES_APROVADAS.md`](DECISOES_APROVADAS.md) | Decisões aprovadas (D-02 a D-06, D-11, D-13, D-14, validações, desativação de usuários) e decisões pendentes |
| [`MATRIZ_RASTREABILIDADE.md`](MATRIZ_RASTREABILIDADE.md) | Requisitos das Entregas 1 e 2: situação, evidência, lacuna, fase e critério de aceitação; separa requisitos oficiais, decisões aprovadas e melhorias |
| [`adr/`](adr/README.md) | Decisões arquiteturais (ADR-0001 a 0009): stack, camadas, responsabilidades, Repository, injeção de dependências, testes, datas e relógio, estrutura do backend, papéis e regras da OS |
| [`DIAGRAMAS.md`](DIAGRAMAS.md) | Componentes, camadas, entidades, máquina de estados e fluxo da OS (Mermaid) |
| [`PRINCIPIOS_SOLID_E_PADROES.md`](PRINCIPIOS_SOLID_E_PADROES.md) | SOLID e padrões: situação atual × plano e como serão demonstrados |
| [`PLANO_DE_MIGRACAO.md`](PLANO_DE_MIGRACAO.md) | Roteiro incremental por fase, riscos, critérios de aceitação e decisões pendentes |

## Na raiz do repositório

- [`../README.md`](../README.md): como executar a Entrega 1 (CLI).
- [`../DOCUMENTACAO.md`](../DOCUMENTACAO.md): decisões de projeto da Entrega 1.

Ordem de leitura sugerida: auditoria → decisões aprovadas → matriz → ADRs → diagramas → SOLID e padrões → plano de migração.

As decisões aprovadas orientam fases futuras e **não estão implementadas**; o código da branch continua sendo o da
Entrega 1.
