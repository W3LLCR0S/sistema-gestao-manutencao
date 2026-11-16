# ADR-0001 — Stack tecnológica

- **Status:** Aceita para documentação (Fase 01). A implementação depende da autorização de cada fase.
- **Data:** 2026-11-15
- **Relacionados:** ADR-0002, ADR-0004, ADR-0006; achados AUD-01, AUD-04, AUD-06 da [auditoria](../AUDITORIA_ARQUITETURAL.md)

## Contexto

A Entrega 1 é uma CLI em Python, sem dependências externas, com persistência em um único arquivo JSON. A Entrega 2 exige
interface web responsiva, evolução arquitetural, SOLID, ao menos um padrão de projeto e persistência desacoplada
(E2-FRT-01..03, E2-SOL-01..05, E2-PAD-01, E2-PER-01 na [matriz](../MATRIZ_RASTREABILIDADE.md)).

A auditoria mostrou que o JSON não suporta acesso simultâneo (AUD-04, AUD-05), que não há autenticação (AUD-01) e que o
domínio em Python já concentra as regras do ciclo da OS e deve ser aproveitado.

## Alternativas consideradas

| Camada | Alternativa | Motivo para não escolher |
|--------|-------------|--------------------------|
| Backend | Django (+ DRF) | ORM e *admin* embutidos incentivam entidades acopladas ao *framework*, o que dificulta demonstrar o desacoplamento exigido; maior reescrita do domínio existente |
| Backend | Flask | Exigiria montar manualmente validação, documentação da API e injeção de dependências |
| Backend | Node.js (NestJS/Express) | Troca de linguagem e descarte do domínio Python já validado |
| Frontend | Next.js | Renderização no servidor não é necessária e acrescenta decisões de hospedagem; uma SPA basta para este sistema |
| Frontend | Outros *frameworks* (Vue, Angular) | Sem vantagem concreta para o escopo; a equipe optou por React |
| Banco | Manter JSON | Não resolve AUD-04, AUD-05, AUD-06 |
| Banco | SQLite | Escrita concorrente limitada e diferenças de comportamento em relação ao ambiente de produção previsto |
| Banco | Banco não relacional | O domínio é relacional (OS ↔ equipamento ↔ usuário ↔ serviços) e exige integridade referencial e transações |

## Decisão

- **Backend:** Python com **FastAPI**.
- **Frontend:** **React + TypeScript + Vite + Tailwind CSS**, como aplicação de página única (SPA) separada do backend.
- **Banco de dados:** **PostgreSQL**.
- **ORM:** **SQLAlchemy 2**.
- **Migrações:** **Alembic**.

## Justificativa

- **Reaproveita o domínio em Python**; a CLI legada é preservada como referência (D-10).
- **FastAPI** gera a documentação OpenAPI a partir de tipos, valida entrada com Pydantic e tem injeção de dependências
  nativa (`Depends`), usada no ADR-0005.
- **PostgreSQL** oferece transações, restrições de integridade e controle de concorrência, que o JSON não oferece.
- **SQLAlchemy 2 + Alembic** permitem modelar o esquema, versionar mudanças e isolar o acesso a dados atrás de repositórios.
- **TypeScript** dá contratos tipados entre telas e API; **Tailwind** acelera interfaces responsivas e acessíveis.

## Consequências

- Duas cadeias de ferramentas (Python e Node) e, portanto, dois ambientes a configurar, documentar e testar.
- O repositório passa a ter manifestos de dependências e versões fixadas; **versões exatas serão fixadas nas fases de
  implementação** (esta ADR não as define).
- É preciso um banco PostgreSQL para desenvolvimento e testes de integração; a forma de provê-lo localmente ainda não
  está decidida.
- **Hospedagem da API e do PostgreSQL em produção não está decidida.** O frontend na Vercel é apenas uma opção. Nenhuma
  publicação ocorre sem autorização específica (Fase 10).
- A CLI e a persistência JSON são preservadas, mas deixam de ser mecanismos finais (D-10), mas as funcionalidades e regras exigidas pela Entrega 1
  devem continuar atendidas (verificado por testes de caracterização, ADR-0006).
- O diretório `app/` não é removido na Fase 01.
