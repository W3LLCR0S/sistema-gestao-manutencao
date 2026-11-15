# Registro de decisões arquiteturais (ADR)

Cada ADR registra contexto, alternativas, decisão, justificativa e consequências. Os ADRs desta fase foram aprovados
**para documentação**: descrevem a direção técnica, não código implementado. A implementação ocorre nas fases
seguintes, cada uma com autorização própria.

| ADR | Decisão | Status |
|-----|---------|--------|
| [0001](0001-stack-tecnologica.md) | Stack: FastAPI, React + TypeScript + Vite + Tailwind, PostgreSQL, SQLAlchemy 2, Alembic | Aceita para documentação |
| [0002](0002-arquitetura-em-camadas.md) | Arquitetura em camadas inspirada na hexagonal simplificada | Aceita para documentação |
| [0003](0003-separacao-de-responsabilidades.md) | Onde ficam validação, regras, autorização, transação e tradução de erros | Aceita para documentação |
| [0004](0004-repository-e-persistencia.md) | Repository por agregado; PostgreSQL via SQLAlchemy; concorrência otimista (proposta) | Aceita para documentação |
| [0005](0005-injecao-de-dependencias.md) | Injeção por construtor e composição com `Depends` do FastAPI | Aceita para documentação |
| [0006](0006-estrategia-de-testes.md) | Pirâmide de testes; caracterização antes da refatoração | Aceita para documentação |

Decisões ainda **sem ADR** por dependerem de aprovação específica: autenticação e sessão (Fase 04), hospedagem e banco em
produção (Fase 10) e migração de dados reais. Ver [`PLANO_DE_MIGRACAO.md`](../PLANO_DE_MIGRACAO.md).

Convenção: arquivos `NNNN-titulo-em-minusculas.md`; uma ADR substituída é marcada como tal, nunca apagada.
