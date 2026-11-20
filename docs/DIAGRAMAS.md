# Diagramas

Diagramas em [Mermaid](https://mermaid.js.org/) (renderizados pelo GitHub). O documento tem duas partes:

* **Parte A: arquitetura implementada.** Conferida no código do commit `8427977` (tag `entrega-2`). Nomes de classes,
  módulos e rotas são os reais.
* **Parte B: planejamento histórico** (Fases 00 a 02). Preservada como registro das propostas. Os diagramas do
  baseline (Entrega 1) continuam corretos para a CLI legada; os de "alvo" foram **superados** pela Parte A (foram
  planejados antes da implementação, usavam, por exemplo, Tailwind CSS, que não foi adotado).

| # | Diagrama | Representa |
|---|---|---|
| A1 | Arquitetura geral | Implementado |
| A2 | Dependências entre camadas | Implementado (verificado por `tests/arquitetura/`) |
| A3 | Fluxo de autenticação | Implementado |
| A4 | Ciclo de vida da ordem de serviço | Implementado (`domain/transicoes.py`) |
| A5 | Frontend → API → serviços → persistência | Implementado |
| H-1 a H-7 | Baseline e alvo planejado | Histórico |

# Parte A: arquitetura implementada

## A1. Arquitetura geral

```mermaid
flowchart TB
    subgraph nav["Navegador"]
        spa["SPA React + TypeScript + Vite<br/>frontend/src: paginas, api, auth"]
    end
    subgraph vite["Servidor de desenvolvimento Vite :5173"]
        proxy["proxy /api -> 127.0.0.1:8000"]
    end
    subgraph back["Backend Python: backend/src/manutencao"]
        api["api/<br/>FastAPI, rotas /api/v1, esquemas Pydantic, seguranca"]
        app["application/<br/>servicos + portas Protocol + DTOs"]
        dom["domain/<br/>entidades, permissoes, transicoes"]
        infra["infrastructure/<br/>postgres, memoria, relogio, seguranca"]
        comp["composicao/<br/>container, fabrica, aplicacao, banco, servidor"]
    end
    pg[("PostgreSQL 16<br/>Alembic 0001-0003")]
    spa --> proxy --> api
    api --> app --> dom
    infra -. "implementa as portas" .-> app
    infra --> pg
    comp -. "liga tudo" .-> api
    comp -. "escolhe implementacoes" .-> infra
```

## A2. Dependências entre camadas

As setas cheias são `import`. A camada `composicao` é a única que conhece todas. `domain` não importa ninguém.

```mermaid
flowchart LR
    composicao --> api
    composicao --> application
    composicao --> infrastructure
    composicao --> domain
    api --> application
    api --> domain
    infrastructure --> application
    infrastructure --> domain
    application --> domain
```

## A3. Fluxo de autenticação (login por matrícula)

Fonte: `api/rotas/autenticacao.py`, `application/servicos/autenticacao.py`, `api/seguranca.py`.

```mermaid
sequenceDiagram
    participant B as Navegador (React)
    participant R as Rota POST /auth/login
    participant L as LimitadorDeTentativas
    participant S as ServicoDeAutenticacao
    participant U as UsuarioRepository / CredencialRepository
    participant H as HasherDeSenha (Argon2id)
    participant SS as SessaoRepository
    B->>R: {matricula, senha}
    R->>L: verificar(IP + matricula)
    R->>S: login(matricula, senha)
    S->>U: obter_por_matricula, obter_por_usuario
    S->>H: verificar(hash ou hash de isca, senha)
    alt matricula/senha invalidas ou usuario inativo
        S-->>R: CredenciaisInvalidasError
        R->>L: registrar_falha
        R-->>B: 401 credenciais_invalidas
    else valido
        S->>SS: adicionar(sha256 do token, csrf, expira_em)
        R-->>B: 200 {usuario, csrf_token, expira_em} + cookie HttpOnly SameSite=Lax
    end
    Note over B,R: Demais requisicoes: cookie + (POST/PUT/PATCH/DELETE) cabecalho X-CSRF-Token
    B->>R: requisicao protegida
    R->>S: autenticar(token do cookie)
    S->>SS: obter(sha256 do token)
    S-->>R: Autenticacao(usuario atual, sessao) ou 401
```

## A4. Ciclo de vida da ordem de serviço

Fonte: `_TABELA` em `domain/transicoes.py` (as pré-condições de cada operação ficam em `OrdemServico`).

```mermaid
stateDiagram-v2
    [*] --> Aberta: abrir (abrir_os)
    Aberta --> Atribuida: atribuir (atribuir_os)
    Aberta --> Cancelada: cancelar (aprovar_os)
    Atribuida --> EmExecucao: tecnico altera status / apontar reparo
    Atribuida --> AguardandoPeca
    Atribuida --> ReparoFinalizado
    Atribuida --> Cancelada
    EmExecucao --> AguardandoPeca
    EmExecucao --> ReparoFinalizado: exige diagnostico e intervencao
    EmExecucao --> Cancelada
    AguardandoPeca --> EmExecucao
    AguardandoPeca --> ReparoFinalizado
    AguardandoPeca --> Cancelada
    ReparoFinalizado --> EmExecucao
    ReparoFinalizado --> AguardandoPeca
    ReparoFinalizado --> AguardandoAprovacao: conclusao tecnica (concluir_os)
    ReparoFinalizado --> Cancelada
    AguardandoAprovacao --> Concluida: aprovar (aprovar_os)
    AguardandoAprovacao --> EmExecucao: reprovar (aprovar_os)
    AguardandoAprovacao --> Cancelada
    Concluida --> [*]
    Cancelada --> [*]
```

Nomes na interface: Aberta, Atribuída, Em Execução, Aguardando Peça, Reparo Finalizado, Aguardando Aprovação,
Concluída, Cancelada.

## A5. Interação frontend → API → serviços → persistência (exemplo: aprovar uma OS)

```mermaid
sequenceDiagram
    participant P as OrdemDetalhe.tsx
    participant C as api/cliente.ts
    participant V as Vite /api
    participant Rt as api/rotas/ordens.py
    participant Sg as api/seguranca.py
    participant Sv as ServicoDeOrdens
    participant D as OrdemServico (domain)
    participant Rp as OrdemServicoRepository (porta)
    participant Pg as OrdensNoBanco (PostgreSQL)
    P->>C: aprovar(numero)
    C->>V: POST /api/v1/ordens/{n}/aprovacao + X-CSRF-Token
    V->>Rt: encaminha (cookie de sessao)
    Rt->>Sg: autenticar + conferir CSRF
    Rt->>Sv: aprovar(ator_id da sessao, numero)
    Sv->>Sv: exige permissao aprovar_os
    Sv->>Rp: obter(numero)
    Rp->>Pg: SELECT
    Sv->>D: aprovar(gestor, quando=relogio.agora())
    D-->>Sv: status Concluida ou erro de dominio
    Sv->>Rp: salvar(ordem)
    Rp->>Pg: UPDATE (transacao)
    Rt-->>C: 200 OrdemSaida (ou 403/409/422 com codigo)
    C-->>P: estado atualizado
```

---

# Parte B: planejamento histórico (Fases 00 a 02)

Os diagramas abaixo foram preservados sem alteração de conteúdo. **H-1, H-4 e H-5** representam o baseline da
Entrega 1 e continuam válidos para a CLI. **H-2, H-3, H-6 e H-7** são o alvo planejado na época e foram superados
pela Parte A (consulte-a para o que existe de fato).

### H-1. Componentes do baseline (Entrega 1)

Origem: leitura dos imports e do código (ver [`AUDITORIA_ARQUITETURAL.md`](AUDITORIA_ARQUITETURAL.md)).

```mermaid
flowchart LR
    main["main.py"] --> aplicacao["ui/aplicacao.py<br/>login por ID e menu"]
    aplicacao --> telas["ui/tela_*.py<br/>telas do terminal"]
    aplicacao -->|"instancia diretamente"| repo["persistencia/repositorio.py<br/>Repositorio"]
    telas --> repo
    telas --> models["models/<br/>entidades, enums, permissoes"]
    repo --> models
    repo -->|"regrava o arquivo inteiro"| json[("dados/dados.json")]

    subgraph paralelo["app/ - paralela, sem ponto de entrada, nao importada"]
        menu["menu e modulos"] --> ctx["contexto.py"] --> persapp["persistencia.py"]
    end
    persapp -.->|"mesmo caminho, formato diferente"| json
```

### H-2. Componentes do sistema-alvo

Direção aprovada para documentação (ADR-0001, ADR-0002 e ADR-0008). O pacote do backend será
`backend/src/manutencao/` (D-14). Nomes de rotas serão definidos nas fases de implementação. Por D-10 (aprovada),
não há CLI sobre os novos serviços: a CLI legada permanece intacta e fora do sistema-alvo; a interface principal é web.

```mermaid
flowchart TB
    subgraph navegador["Navegador"]
        spa["SPA React + TypeScript<br/>Vite + Tailwind CSS"]
    end

    subgraph backend["Backend Python - manutencao"]
        subgraph apic["api (FastAPI)"]
            rotas["rotas /api/v1<br/>esquemas Pydantic"]
            auth["autenticacao por requisicao"]
            erros["traducao de erros"]
            provedores["provedores Depends<br/>obtem servico pronto"]
        end
        subgraph appc["application"]
            servicos["servicos de caso de uso<br/>Service Layer"]
            portas["portas Protocol<br/>repositorios, relogio, hash"]
        end
        subgraph domc["domain"]
            entidades["entidades e regras<br/>OrdemServico, Usuario, Equipamento"]
        end
        subgraph infc["infrastructure"]
            reposql["repositorios SQLAlchemy 2"]
            repomem["repositorios em memoria<br/>testes"]
            relsis["relogio do sistema UTC"]
            migr["migracoes Alembic"]
        end
        comp["composicao<br/>raiz de composicao"]
    end

    pg[("PostgreSQL")]

    spa -->|"HTTP + JSON, contrato OpenAPI"| rotas
    rotas --> provedores
    provedores --> servicos
    servicos --> entidades
    servicos --> portas
    reposql -.->|"implementa"| portas
    repomem -.->|"implementa"| portas
    relsis -.->|"implementa"| portas
    reposql --> pg
    migr --> pg
    comp -.->|"cria e liga implementacoes"| reposql
    comp -.->|"monta servicos e app"| servicos
```

### H-3. Dependências entre camadas

Regra de dependência (ADR-0002): as setas indicam "pode importar". Qualquer seta no sentido oposto é defeito, verificado
por teste automatizado (ADR-0006).

```mermaid
flowchart LR
    api["api"] --> application["application"]
    application --> domain["domain"]
    infrastructure["infrastructure"] --> application
    infrastructure --> domain
    composicao["composicao<br/>raiz de composicao"] --> api
    composicao --> application
    composicao --> infrastructure
    composicao --> domain
```

Dependências permitidas por camada:

| Camada | Pode importar |
|--------|---------------|
| `domain` | Somente a biblioteca padrão |
| `application` | `domain` |
| `infrastructure` | `application` (portas) e `domain` |
| `api` | `application` e `domain` (tipos) |
| `composicao` | Todas as camadas (é a única que conhece as implementações concretas) |

Proibido (defeito se ocorrer): `domain` importar `application`, `infrastructure`, `api` ou `composicao`; `application`
importar `infrastructure`, `api` ou `composicao`; `api` importar `infrastructure`; qualquer camada importar `composicao`;
`domain` e `application` importarem FastAPI, SQLAlchemy ou Pydantic. O relógio é uma porta de `application`; o instante é
entregue ao domínio como argumento (ADR-0007).

### H-4. Entidades do domínio (baseline)

Origem: `models/*.py`. Campos de segredo ou de versão **não existem** no baseline; mudanças previstas estão listadas
abaixo do diagrama.

```mermaid
classDiagram
    class Usuario {
        +int id
        +str nome
        +str email
        +str escala
        +Disponibilidade disponibilidade
        +pode(acesso) bool
        +exigir(acesso)
        +e_tecnico bool
    }
    class Disponibilidade {
        <<enumeration>>
        Disponivel
        EmAtendimento
        Ausente
    }
    class Cargo {
        +int id
        +str nome
    }
    class Permissoes {
        +bool ver_equipamentos
        +bool ver_os
        +bool abrir_os
        +bool ver_disponibilidade
        +bool registrar_apontamento
        +bool diagnosticar
        +bool apontar_reparo
        +bool atualizar_status
        +bool concluir_os
        +bool gerir_equipamentos
        +bool gerir_usuarios
        +bool atribuir_os
        +bool aprovar_os
    }
    class Equipamento {
        +int id
        +str nome
        +str modelo
        +bool ativo
    }
    class OrdemServico {
        +int numero
        +StatusOS status
        +str falha
        +Criticidade criticidade
        +str diagnostico
        +str causa_raiz
        +float horas_trabalhadas
        +str teste_funcional
        +str motivo_cancelamento
        +str data_abertura
        +str data_conclusao
        +abrir()
        +atribuir()
        +registrar_diagnostico()
        +apontar_reparo()
        +alterar_status()
        +concluir_tecnicamente()
        +aprovar()
        +reprovar()
        +cancelar()
    }
    class Servico {
        +int numero
        +TipoServico tipo
        +str descricao
        +str data
        +float horas
    }
    class PecaMaterial {
        +str descricao
        +float quantidade
    }
    Usuario "*" --> "1" Cargo : cargo
    Usuario "*" --> "1" Disponibilidade : disponibilidade gravada
    Cargo "1" --> "1" Permissoes : permissoes
    OrdemServico "*" --> "1" Equipamento : equipamento
    OrdemServico "*" --> "0..1" Usuario : tecnico_atribuido
    OrdemServico "*" --> "0..1" Usuario : aberta_por
    OrdemServico "1" *-- "*" Servico : historico sequencial
    OrdemServico "1" *-- "*" PecaMaterial : pecas_utilizadas
    Servico "*" --> "0..1" Usuario : responsavel
    Servico "1" *-- "*" PecaMaterial : pecas
```

**Disponibilidade no baseline:** é um **atributo gravado** em `Usuario`, atualizado pelo `Repositorio` quando a interface
chama `atualizar_disponibilidades()` (`persistencia/repositorio.py:112-119`); `Ausente` é definido manualmente. `e_tecnico`
é derivado da permissão `apontar_reparo`, não do cargo (AUD-20).

**Mudanças previstas (não implementadas):**
- papel (Gestor ou Técnico) explícito no domínio, independente das permissões (D-02);
- ausência manual registrada **separadamente** e disponibilidade operacional **calculada** a partir das OS Em Execução,
  com a ausência prevalecendo (D-05); deixa de ser atributo gravado;
- campo `ativo` em `Usuario` (desativação sem exclusão);
- datas como `datetime` com fuso, armazenadas em UTC (D-11);
- credencial protegida por hash em `Usuario`; versão para controle otimista em `OrdemServico`; permissões como
  enumeração tipada; remoção de `to_dict`/`from_dict` das entidades.

Campos extras de `Equipamento` dependem de decisão (D-07/OPC-06 na [matriz](MATRIZ_RASTREABILIDADE.md)).

### H-5. Máquina de estados da OS (baseline)

Origem: métodos de `models/ordem_servico.py`. As transições marcadas com ✓ foram confirmadas por execução (2026-11-15);
as demais vêm da leitura do código e **não foram executadas**.

```mermaid
stateDiagram-v2
    state "Aberta" as ABERTA
    state "Atribuída" as ATRIBUIDA
    state "Em Execução" as EXEC
    state "Aguardando Peça" as PECA
    state "Reparo Finalizado" as FIM
    state "Aguardando Aprovação" as APROV
    state "Concluída" as CONC
    state "Cancelada" as CANC

    [*] --> ABERTA : abrir (qualquer usuario com permissao) ✓
    ABERTA --> ATRIBUIDA : atribuir (Gestor) ✓
    ATRIBUIDA --> EXEC : apontar reparo (automatico) ✓ ou alterar status
    ATRIBUIDA --> PECA : alterar status (Tecnico) ✓
    EXEC --> PECA : alterar status
    PECA --> EXEC : alterar status
    EXEC --> FIM : alterar status, exige intervencao ✓
    PECA --> FIM : alterar status, exige intervencao
    FIM --> EXEC : alterar status (Tecnico) ✓
    FIM --> PECA : alterar status
    FIM --> FIM : teste funcional reprovado ✓ (permanece)
    FIM --> APROV : conclusao tecnica, exige diagnostico e teste aprovado ✓
    APROV --> CONC : aprovar (Gestor) ✓
    APROV --> EXEC : reprovar (Gestor) ✓
    ABERTA --> CANC : cancelar (Gestor) ✓
    ATRIBUIDA --> CANC : cancelar (Gestor) ✓
    EXEC --> CANC : cancelar
    PECA --> CANC : cancelar
    FIM --> CANC : cancelar
    APROV --> CANC : cancelar
    CONC --> [*]
    CANC --> [*]
```

Observações verificadas:
- **Não há transição direta Atribuída → Reparo Finalizado.** O código permite tentar (`alterar_status` aceita a
  origem Atribuída), mas exige ao menos uma intervenção, e a primeira intervenção (`apontar_reparo`) já move a OS para
  Em Execução (`ordem_servico.py:118-119,133-134`). Por isso a aresta não existe no diagrama (a recusa sem intervenção foi
  confirmada por execução).
- **Alvo (D-06, não implementado):** a transição para Reparo Finalizado passa a exigir também o diagnóstico registrado;
  as demais arestas acima são preservadas.
- Reatribuir é recusado em "Aguardando Aprovação" ✓ e permitido em "Em Execução" mantendo o status ✓; pelo código, também é
  permitido nos demais status não finais (não executado). A atribuição a partir de "Aberta" muda o status para "Atribuída" ✓.
- O diagnóstico só é aceito em Atribuída, Em Execução e Aguardando Peça (ver AUD-21 na auditoria).
- Cancelar uma OS já encerrada é recusado ✓.

### H-6. Fluxo principal das ordens de serviço

Comportamento da Entrega 1 que deve ser **preservado** na aplicação web, com as mudanças aprovadas assinaladas (D-03 a
D-06, **não implementadas**). Os nomes das rotas serão definidos na Fase 04.

```mermaid
sequenceDiagram
    autonumber
    actor U as Gestor ou Tecnico
    actor G as Gestor
    actor T as Tecnico
    participant S as Sistema (API + servicos)

    U->>S: abrir chamado (equipamento ativo, falha, criticidade)
    S-->>U: OS Aberta, historico #1 Abertura
    G->>S: atribuir a um tecnico
    Note over G,S: alvo D-03: tecnico Ausente exige confirmacao explicita enviada ao servidor
    S-->>G: OS Atribuida, historico registra a atribuicao
    opt reatribuicao antes da aprovacao
        G->>S: reatribuir a outro tecnico
        S-->>G: historico registra "de para"
    end
    T->>S: registrar diagnostico e causa-raiz
    T->>S: apontar reparo (horas, intervencao, pecas)
    S-->>T: OS Em Execucao, historico registra horas e pecas
    loop enquanto necessario
        T->>S: alterar status (Aguardando Peca / Em Execucao)
        S-->>T: status atualizado, historico registra a mudanca
    end
    T->>S: alterar status para Reparo Finalizado (exige intervencao)
    Note over T,S: alvo D-06: exige tambem o diagnostico registrado
    T->>S: conclusao tecnica com teste funcional
    alt teste aprovado
        S-->>T: OS Aguardando Aprovacao
        alt gestor aprova
            G->>S: aprovar e encerrar
            S-->>G: OS Concluida, data de conclusao registrada
        else gestor reprova
            G->>S: reprovar com motivo
            S-->>G: OS volta a Em Execucao
        end
    else teste reprovado
        S-->>T: OS permanece em Reparo Finalizado
    end
    opt observacao em OS ativa (alvo D-04)
        U->>S: registrar observacao (gestor, tecnico responsavel ou autor da abertura)
        S-->>U: historico registra autor, data e tipo, mantendo o status
    end
    opt cancelamento antes do encerramento
        G->>S: cancelar com motivo
        S-->>G: OS Cancelada, data registrada
    end
```

### H-7. Anatomia de uma operação na API (alvo)

Exemplo: **apontar reparo**. Mostra onde cada responsabilidade reside (ADR-0003), como o relógio é obtido pela aplicação
e entregue ao domínio (ADR-0007) e como os erros são traduzidos. Serviço e repositório chegam à rota já montados pela raiz
de composição (ADR-0005), que não aparece na sequência por atuar na inicialização.

```mermaid
sequenceDiagram
    autonumber
    participant SPA as SPA React
    participant API as api (rota)
    participant AUT as autenticacao
    participant SVC as application (servico)
    participant REP as porta OrdemServicoRepository
    participant REL as porta Relogio
    participant DOM as domain (OrdemServico)
    participant DB as PostgreSQL

    SPA->>API: requisicao com credencial e dados do reparo
    API->>API: valida formato (esquema Pydantic)
    API->>AUT: identificar usuario
    AUT-->>API: usuario autenticado (senao 401)
    API->>SVC: apontar_reparo(usuario, id da OS, dados)
    SVC->>REP: obter OS por id
    REP->>DB: SELECT da OS com historico e pecas
    DB-->>REP: registros e versao
    REP-->>SVC: entidade OrdemServico
    SVC->>SVC: autoriza permissao e responsabilidade pela OS, caso contrario retorna 403
    SVC->>REL: agora()
    REL-->>SVC: instante com fuso (UTC)
    SVC->>DOM: apontar_reparo(horas, intervencao, pecas, instante)
    DOM-->>SVC: estado e historico atualizados (senao 409 ou 422)
    SVC->>REP: salvar OS
    REP->>DB: UPDATE condicionado a versao
    alt versao desatualizada
        DB-->>REP: nenhuma linha atualizada
        REP-->>SVC: conflito de concorrencia
        SVC-->>API: erro
        API-->>SPA: 409
    else gravado
        DB-->>REP: confirmacao
        SVC-->>API: resultado
        API-->>SPA: 200 com a OS atualizada
    end
```
