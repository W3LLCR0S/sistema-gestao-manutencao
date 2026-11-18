# Registro de decisões arquiteturais (ADR)

Cada ADR registra contexto, alternativas, decisão, justificativa e consequências. Os ADRs foram aprovados na Fase 01 e **revisados ao encerrar a Fase 02**
(seção "Revisão ao encerrar a Fase 02" em cada um): a coluna Status distingue o que está implementado do que segue
planejado. A implementação das demais partes ocorre nas fases seguintes, cada uma com autorização própria. As decisões funcionais e os identificadores `D-nn` estão consolidados em
[`DECISOES_APROVADAS.md`](../DECISOES_APROVADAS.md).

| ADR | Decisão | Status |
|-----|---------|--------|
| [0001](0001-stack-tecnologica.md) | Stack: FastAPI, React + TypeScript + Vite + Tailwind, PostgreSQL, SQLAlchemy 2, Alembic | Aceita (só D-13 adotada) |
| [0002](0002-arquitetura-em-camadas.md) | Arquitetura em camadas inspirada na hexagonal simplificada | Aceita; implementada (exceto `api/`) |
| [0003](0003-separacao-de-responsabilidades.md) | Onde ficam validação, regras, autorização, transação e tradução de erros | Aceita; parcialmente implementada (validação, regras, autorização) |
| [0004](0004-repository-e-persistencia.md) | Repository por agregado; PostgreSQL via SQLAlchemy; concorrência otimista (proposta) | Aceita; portas e memória implementadas, banco na Fase 03 |
| [0005](0005-injecao-de-dependencias.md) | Injeção por construtor e composição com `Depends` do FastAPI | Aceita; implementada (sem `Depends`, Fase 04) |
| [0006](0006-estrategia-de-testes.md) | Pirâmide de testes; caracterização antes da refatoração; pytest, ruff e mypy desde a Fase 02 (D-13) | Aceita; aplicada na Fase 02 |
| [0007](0007-datas-fuso-horario-e-relogio.md) | Datas com fuso em UTC, exibição em America/Sao_Paulo; relógio na aplicação (D-11) | Aprovada; implementada (domínio e aplicação) |
| [0008](0008-estrutura-do-backend-e-convivencia-com-o-legado.md) | Pacote `backend/src/manutencao/`; convivência com o legado (D-14) | Aprovada; implementada |
| [0009](0009-papeis-autorizacao-e-regras-da-os.md) | Papéis, autorização e regras da OS (D-02 a D-06, validações, usuários inativos) | Aprovada; implementada no novo backend (Operação E) |
| [0010](0010-autenticacao-e-sessao.md) | Autenticação por login e senha (Argon2id), sessões do servidor, cookie `HttpOnly`, CSRF (D-01) | Aprovada (2026-11-17); implementada na Fase 04 |

Decisões ainda **sem ADR** por dependerem de aprovação específica: hospedagem e banco
em produção (D-09, Fase 10), migração de dados reais (D-08) e demais pendências listadas em
[`DECISOES_APROVADAS.md`](../DECISOES_APROVADAS.md). Ver [`PLANO_DE_MIGRACAO.md`](../PLANO_DE_MIGRACAO.md).

Convenção: arquivos `NNNN-titulo-em-minusculas.md`; uma ADR substituída é marcada como tal, nunca apagada.
