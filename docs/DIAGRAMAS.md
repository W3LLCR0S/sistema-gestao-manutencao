# Diagramas

Diagramas em [Mermaid](https://mermaid.js.org/) (renderizados pelo GitHub). Cada um indica se representa o **baseline
verificado** (código da Entrega 1) ou a **arquitetura-alvo** (planejada, **não implementada**).

| # | Diagrama | Representa |
|---|----------|------------|
| 1 | Componentes do baseline | Baseline verificado |
| 2 | Componentes do sistema-alvo | Alvo (não implementado) |
| 3 | Dependências entre camadas | Alvo (não implementado) |
| 4 | Entidades do domínio | Baseline verificado |
| 5 | Máquina de estados da OS | Baseline verificado |
| 6 | Fluxo principal das ordens de serviço | Alvo (comportamento a preservar) |
| 7 | Anatomia de uma operação na API | Alvo (não implementado) |

## 1. Componentes do baseline (Entrega 1)

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

## 2. Componentes do sistema-alvo

Direção aprovada para documentação (ADR-0001 e ADR-0002). Nomes de pacotes e de rotas serão definidos nas fases de
implementação.

```mermaid
flowchart TB
    subgraph navegador["Navegador"]
        spa["SPA React + TypeScript<br/>Vite + Tailwind CSS"]
    end

    subgraph backend["Backend Python"]
        subgraph apic["api (FastAPI)"]
            rotas["rotas /api/v1<br/>esquemas Pydantic"]
            auth["autenticacao por requisicao"]
            erros["traducao de erros"]
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
            migr["migracoes Alembic"]
        end
        cli["CLI de transicao<br/>adaptador, Fase 02"]
    end

    pg[("PostgreSQL")]

    spa -->|"HTTP + JSON, contrato OpenAPI"| rotas
    rotas --> servicos
    cli --> servicos
    servicos --> entidades
    servicos --> portas
    reposql -.->|"implementa"| portas
    repomem -.->|"implementa"| portas
    reposql --> pg
    migr --> pg
```

## 3. Dependências entre camadas

Regra de dependência (ADR-0002): as setas indicam "pode importar". Qualquer seta no sentido oposto é defeito, verificado
por teste automatizado (ADR-0006).

```mermaid
flowchart LR
    api["api"] --> application["application"]
    application --> domain["domain"]
    infrastructure["infrastructure"] --> application
    infrastructure --> domain
    api -.->|"composicao: Depends monta<br/>implementacoes concretas"| infrastructure
```

Proibido (defeito se ocorrer): `domain` importar `application`, `infrastructure` ou `api`; `application` importar
`infrastructure` ou `api`; `domain` e `application` importarem FastAPI, SQLAlchemy ou Pydantic.

## 4. Entidades do domínio (baseline)

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
    Cargo "1" --> "1" Permissoes : permissoes
    OrdemServico "*" --> "1" Equipamento : equipamento
    OrdemServico "*" --> "0..1" Usuario : tecnico_atribuido
    OrdemServico "*" --> "0..1" Usuario : aberta_por
    OrdemServico "1" *-- "*" Servico : historico sequencial
    OrdemServico "1" *-- "*" PecaMaterial : pecas_utilizadas
    Servico "*" --> "0..1" Usuario : responsavel
    Servico "1" *-- "*" PecaMaterial : pecas
```

**Mudanças previstas (não implementadas):** credencial protegida por hash em `Usuario`; datas como tipo data/hora com
fuso; versão para controle otimista em `OrdemServico`; permissões como enumeração tipada; remoção de `to_dict`/`from_dict`
das entidades. Campos extras de `Equipamento` dependem de decisão (OPC-06 na [matriz](MATRIZ_RASTREABILIDADE.md)).

## 5. Máquina de estados da OS (baseline)

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
    ATRIBUIDA --> FIM : exige intervencao (recusa sem ela confirmada ✓)
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
- Reatribuir é recusado em "Aguardando Aprovação" ✓ e permitido em "Em Execução" mantendo o status ✓; pelo código, também é
  permitido nos demais status não finais (não executado). A atribuição a partir de "Aberta" muda o status para "Atribuída" ✓.
- O diagnóstico só é aceito em Atribuída, Em Execução e Aguardando Peça (ver AUD-21 na auditoria).
- Cancelar uma OS já encerrada é recusado ✓.

## 6. Fluxo principal das ordens de serviço

Comportamento da Entrega 1 que deve ser **preservado** na aplicação web. Os nomes das rotas serão definidos na Fase 04.

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
    opt cancelamento antes do encerramento
        G->>S: cancelar com motivo
        S-->>G: OS Cancelada, data registrada
    end
```

## 7. Anatomia de uma operação na API (alvo)

Exemplo: **apontar reparo**. Mostra onde cada responsabilidade reside (ADR-0003) e como os erros são traduzidos.

```mermaid
sequenceDiagram
    autonumber
    participant SPA as SPA React
    participant API as api (rota)
    participant AUT as autenticacao
    participant SVC as application (servico)
    participant REP as porta OrdemServicoRepository
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
    SVC->>SVC: autoriza (permissao e OS do tecnico; senao 403)
    SVC->>DOM: apontar_reparo(horas, intervencao, pecas)
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
