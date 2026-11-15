# ADR-0006 — Estratégia de testes

- **Status:** Aceita para documentação (Fase 01). Ferramentas além das aprovadas dependem de justificativa.
- **Data:** 2026-11-15
- **Relacionados:** ADR-0001 a ADR-0005; AUD-17; E2-OBJ-01 (testabilidade), E2-SOL-03, E2-DOC-02

## Contexto

O baseline não tem testes automatizados, manifesto de dependências nem integração contínua (AUD-17). A refatoração
exigida pela Entrega 2 altera estrutura e persistência, mas **deve preservar** o comportamento da Entrega 1. Sem testes
anteriores à mudança, não há como provar a preservação. A auditoria também executou verificações ad hoc que revelaram
defeitos reais, mas esse script não é versionado.

## Alternativas consideradas

| Alternativa | Avaliação |
|-------------|-----------|
| Teste manual da CLI e da interface | Não reproduzível nem auditável; não detecta regressões |
| Apenas testes de ponta a ponta | Lentos, frágeis e pouco precisos para localizar falhas de regra |
| `unittest` da biblioteca padrão | Funcional, porém com menos recursos de parametrização e *fixtures* que o `pytest` |
| Refatorar primeiro e testar depois | Impossibilita separar regressão de mudança intencional |
| **Pirâmide de testes, com caracterização antes da refatoração** (escolhida) | Protege o comportamento e dá retorno rápido |

## Decisão

| Nível | Ferramenta | Escopo |
|-------|------------|--------|
| **Caracterização** (Fase 02, **antes** de alterar regras) | `pytest` | Fixa o comportamento atual do domínio da Entrega 1: transições de status, permissões, histórico sequencial, inativação e exclusão, disponibilidade, aprovação e reprovação. Registra também as divergências conhecidas (por exemplo AUD-09, AUD-11), marcadas como tal, para decidir caso a caso |
| **Unidade** (domínio) | `pytest` | Máquina de estados (tabela de transições, casos válidos e inválidos), invariantes, permissões |
| **Aplicação** | `pytest` com repositórios em memória | Casos de uso, autorização, orquestração e erros, sem banco nem HTTP |
| **Contrato de repositório** | `pytest` | A mesma suíte roda contra a implementação em memória e a SQLAlchemy (evidência de LSP) |
| **Integração** | `pytest` + banco PostgreSQL de teste | Repositórios reais, migrações, concorrência (duas escritas simultâneas) e rotas da API (401/403/404/409/422) |
| **Arquitetura** | `pytest` | Falha se `domain` ou `application` importar FastAPI, SQLAlchemy ou `infrastructure` |
| **Frontend** | `Vitest` | Componentes, formulários, proteção de rotas e cliente HTTP tipado |
| **Ponta a ponta** | A definir | Fluxos Gestor e Técnico; **ferramenta ainda não escolhida** e exige justificativa |

Regras adicionais:

- **Testes de caracterização antes da refatoração**: nenhuma regra é movida sem teste que a cubra.
- **Testes nunca usam dados reais**: apenas fixtures e bancos de teste isolados; nada de `dados/dados.json` local.
- **Resultados reais**: relatórios de fase registram comandos executados e saídas; nunca se declara um teste como
  executado sem evidência.
- Integração contínua com jobs separados para API e frontend, análise estática e verificação de tipos na Fase 09
  (ferramentas a definir e justificar).

## Justificativa

- Protege o contrato funcional da Entrega 1 durante a migração.
- A suíte de contrato é o meio concreto de demonstrar que as implementações de repositório são substituíveis.
- O teste de arquitetura transforma a regra de dependência (ADR-0002) em verificação automática.
- Testes de aplicação com dublês em memória são rápidos, o que sustenta ciclos curtos de desenvolvimento.

## Consequências

- Esforço inicial concentrado na Fase 02, antes de qualquer ganho visível ao usuário.
- É necessário um PostgreSQL para os testes de integração; **como provê-lo localmente e no CI não está decidido**
  (nenhuma instalação é feita nesta fase).
- Metas numéricas de cobertura **não foram definidas**; proposta pendente para a Fase 09.
- O script de verificação usado na auditoria deve ser convertido em testes versionados, e não reutilizado como está.
