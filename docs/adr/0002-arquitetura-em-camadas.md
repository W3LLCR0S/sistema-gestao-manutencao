# ADR-0002 — Arquitetura em camadas, inspirada na hexagonal simplificada

- **Status:** Aceita para documentação (Fase 01). A estrutura de pastas é uma **proposta** a refinar na Fase 02.
- **Data:** 2026-11-15
- **Relacionados:** ADR-0003, ADR-0004, ADR-0005; AUD-09, AUD-10, AUD-15, AUD-16; E2-ARQ-02, E2-SOL-05

## Contexto

A Entrega 1 tem três pacotes (`ui/`, `models/`, `persistencia/`), mas as fronteiras vazam: regras na UI (AUD-09), regras no
`Repositorio` (AUD-10) e a UI cria o repositório concreto e decide quando gravar (AUD-16). Com a Entrega 2, o mesmo domínio
precisa ser servido por uma API web (e, durante a transição, pela CLI) sem duplicar regras.

O enunciado exige adotar **um tipo de arquitetura** e **apresentar evidências** de seu uso (E2-ARQ-02).

## Alternativas consideradas

| Alternativa | Avaliação |
|-------------|-----------|
| **MVC** com *framework* full-stack | Mistura regra de negócio com controladores e modelos de ORM; não resolve o desacoplamento da persistência |
| **Camadas simples** (apresentação → negócio → dados), sem portas | Mais fácil, mas a camada de negócio passa a depender do acesso a dados concreto; não demonstra DIP |
| **Arquitetura hexagonal / Clean Architecture completa** (interactors, *presenters*, DTOs por caso de uso) | Correta, porém com cerimônia excessiva para o tamanho do sistema; risco de abstrações artificiais |
| **Baseada em serviços / microsserviços** | Custo operacional sem benefício para um sistema de um único contexto |
| **Camadas com portas e adaptadores enxutos** (escolhida) | Mantém a regra de dependência da hexagonal com o mínimo de abstração |

## Decisão

Adotar **arquitetura em camadas inspirada na hexagonal simplificada**, com quatro camadas no backend e o frontend separado:

| Camada | Conteúdo | Pode depender de |
|--------|----------|------------------|
| `domain` | Entidades (`OrdemServico`, `Servico`, `Usuario`, `Cargo`, `Equipamento`, `PecaMaterial`), enums, permissões tipadas, regras e exceções de domínio | Nada além da biblioteca padrão |
| `application` | Casos de uso (*Service Layer*), autorização, **portas** (`Protocol`) de repositórios e de serviços externos (relógio, hash de senha) | `domain` |
| `infrastructure` | Adaptadores: repositórios (em memória, JSON de transição e SQLAlchemy), mapeamento ORM, migrações Alembic, hash de senha, configuração | `application` e `domain` |
| `api` | Rotas FastAPI, esquemas Pydantic, autenticação por requisição, tradução de erros, composição das dependências | `application` (e `domain` para tipos) |
| `frontend` | SPA React; conversa com o backend apenas pela API HTTP | Contrato OpenAPI |

**Regra de dependência:** as setas apontam para dentro (`api` → `application` → `domain`; `infrastructure` implementa as
portas definidas em `application`). `domain` e `application` **não importam** FastAPI, SQLAlchemy, Pydantic nem módulos
de infraestrutura.

Esboço da estrutura-alvo (**não implementada**; nomes de pacote a definir na Fase 02, evitando conflito com o `app/` atual):

```
backend/
  <pacote>/
    domain/
    application/
    infrastructure/
    api/
  tests/
frontend/
```

## Justificativa

- Torna o DIP verificável: a direção das importações pode ser conferida por teste automatizado (ADR-0006).
- Permite trocar JSON por PostgreSQL sem alterar `domain` nem `application`.
- A CLI e a API passam a ser **adaptadores** dos mesmos casos de uso, o que protege o comportamento da Entrega 1
  durante a migração.
- Evita a Clean Architecture completa: sem *interactors* por caso de uso nem *presenters*, apenas serviços de aplicação.

## Consequências

- Mais arquivos e mapeamento explícito entre entidades de domínio e modelos de persistência (custo aceito, ver ADR-0004).
- Disciplina de revisão: qualquer importação de infraestrutura em `domain` ou `application` é defeito.
- O frontend não contém regra de negócio; validações de interface são conveniência e a API continua sendo a autoridade.
- A estrutura acima é proposta; mudanças relevantes exigem nova ADR ou revisão desta.
