# ADR-0002 — Arquitetura em camadas, inspirada na hexagonal simplificada

- **Status:** Aceita; **implementada na Fase 02** em `backend/src/manutencao/` (`domain`, `application`, `infrastructure`, `composicao`; `api` existe como pacote vazio reservado à Fase 04).
- **Data:** 2026-11-15
- **Relacionados:** ADR-0003, ADR-0004, ADR-0005; AUD-09, AUD-10, AUD-15, AUD-16; E2-ARQ-02, E2-SOL-05

## Contexto

A Entrega 1 tem três pacotes (`ui/`, `models/`, `persistencia/`), mas as fronteiras vazam: regras na UI (AUD-09), regras no
`Repositorio` (AUD-10) e a UI cria o repositório concreto e decide quando gravar (AUD-16). Com a Entrega 2, o mesmo domínio
precisa ser servido por uma API web (a CLI legada é preservada e não usa o novo domínio, D-10) sem duplicar regras.

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
| `domain` | Entidades (`OrdemServico`, `Servico`, `Usuario`, `Cargo`, `Equipamento`, `PecaMaterial`), enums, permissões tipadas, regras e exceções de domínio | Nada além da biblioteca padrão. **Nunca** `application`, `infrastructure`, `api` nem `composicao` |
| `application` | Casos de uso (*Service Layer*), autorização, **portas** (`Protocol`) de repositórios e de serviços externos (relógio, hash de senha) | `domain` |
| `infrastructure` | Adaptadores: repositórios (em memória e SQLAlchemy; sem JSON de transição, D-10), mapeamento ORM, migrações Alembic, hash de senha, relógio do sistema, configuração | `application` (para implementar as portas) e `domain` |
| `api` | Rotas FastAPI, esquemas Pydantic, autenticação por requisição, tradução de erros e **provedores `Depends` que obtêm os serviços já montados** | `application` (e `domain` para tipos). **Não** importa `infrastructure` |
| `composicao` | **Raiz de composição**: cria as implementações concretas, liga-as às portas, monta os serviços e a aplicação FastAPI; lê a configuração | **Todas** as camadas: `api`, `application`, `infrastructure` e `domain` |
| `frontend` | SPA React; conversa com o backend apenas pela API HTTP | Contrato OpenAPI |

**Regra de dependência:** as setas apontam para dentro (`api` → `application` → `domain`; `infrastructure` implementa as
portas definidas em `application`). `domain` e `application` **não importam** FastAPI, SQLAlchemy, Pydantic nem módulos
de infraestrutura. Em particular, **o domínio não importa a camada de aplicação**, o que inclui as portas.

**Raiz de composição.** É o **único** ponto que conhece as implementações concretas e as liga às abstrações. É a camada
mais externa e, por isso, pode importar todas as outras; nenhuma outra camada a importa. Isso resolve a contradição
anterior entre "a `api` monta as implementações concretas" e "a `api` só depende de `application`":

1. a `api` declara provedores `Depends` que **devolvem o serviço de aplicação** a partir de um contêiner guardado no
   estado da aplicação (por exemplo `app.state`), sem saber qual implementação existe por trás;
2. a `composicao` cria o contêiner (repositórios SQLAlchemy, relógio, hash), constrói os serviços e o registra;
3. nos testes, o contêiner é montado com implementações em memória (ou os provedores são trocados com
   `dependency_overrides`).

Os casos de uso dependem **somente de abstrações** (`Protocol` das portas).

**Relógio.** A porta `Relogio` pertence a `application`. A aplicação obtém o instante e o **entrega explicitamente** às
operações de domínio que precisam dele; o domínio não importa a porta
([ADR-0007](0007-datas-fuso-horario-e-relogio.md)).

Estrutura-alvo (**implementada na Fase 02**, exceto `api/`; pacote `backend/src/manutencao/`, aprovado em D-14 para evitar conflito com o `app/`
legado; convivência com o legado em [ADR-0008](0008-estrutura-do-backend-e-convivencia-com-o-legado.md)):

```
backend/
  src/
    manutencao/
      domain/
      application/
      infrastructure/
      api/
      composicao/
  tests/
frontend/
```

## Justificativa

- Torna o DIP verificável: a direção das importações pode ser conferida por teste automatizado (ADR-0006).
- Permite trocar JSON por PostgreSQL sem alterar `domain` nem `application`.
- A API é o adaptador dos casos de uso; a CLI legada permanece intacta como referência de comportamento da Entrega 1
  (D-10), protegida pelos testes de caracterização.
- Evita a Clean Architecture completa: sem *interactors* por caso de uso nem *presenters*, apenas serviços de aplicação.

## Consequências

- Mais arquivos e mapeamento explícito entre entidades de domínio e modelos de persistência (custo aceito, ver ADR-0004).
- Disciplina de revisão: qualquer importação de infraestrutura em `domain` ou `application`, e qualquer importação de
  `application` por `domain`, é defeito (verificada por teste de arquitetura, ADR-0006).
- O frontend não contém regra de negócio; validações de interface são conveniência e a API continua sendo a autoridade.
- Os nomes finais dos subpacotes podem ser ajustados na Fase 02; mudanças relevantes exigem nova ADR ou revisão desta.

## Revisão ao encerrar a Fase 02 (2026-11-17)

A regra de dependência foi implementada e é **verificada por teste**: `tests/arquitetura/test_camadas.py` (o pacote tem exatamente as cinco camadas; cada módulo respeita a regra) e `tests/arquitetura/test_injecao_de_dependencias.py`. Verificação manual na revisão: `domain` importa só a biblioteca-padrão e a si mesmo; `application` não importa `infrastructure`, `composicao` nem `api`; `infrastructure` importa só portas, entidades e erros da aplicação. A estrutura-alvo descrita acima deixou de ser apenas proposta, exceto `api/`, que continua vazio até a Fase 04.
