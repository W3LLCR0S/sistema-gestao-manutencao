# Decisões aprovadas e pendentes

Registro das decisões funcionais e arquiteturais da Fase 01. Fonte única para os identificadores `D-nn` citados na
[auditoria](AUDITORIA_ARQUITETURAL.md), na [matriz](MATRIZ_RASTREABILIDADE.md), nos [ADRs](adr/README.md) e no
[plano de migração](PLANO_DE_MIGRACAO.md).

> **Aprovar uma decisão não é implementá-la.** O baseline (`e6f7354`, tag `entrega-1`) e o legado (`models/`, `ui/`,
> `persistencia/`) continuam com o comportamento descrito na coluna "Baseline". As decisões D-02 a D-06 e as melhorias
> aprovadas (validação de entradas e usuário ativo) foram **implementadas só no novo backend** (`backend/src/manutencao/`)
> na Operação E da Fase 02: ver a [seção 8](#8-deltas-de-regras-de-negócio-operação-e-dlt-01-a-dlt-09). O que não consta
> da seção 8 continua sem implementação. A **regularização da Operação E** (REG-E-01 a REG-E-08, DLT-18 a DLT-23) está
> na [seção 9](#9-regularização-da-operação-e-reg-e-01-a-reg-e-08).

## 1. Como ler a classificação

| Classe | Significado |
|--------|-------------|
| **Requisito oficial** | Consta literalmente nos enunciados das Entregas 1 e 2 |
| **Decisão técnica ou funcional aprovada** | Decidida pela equipe (este documento); orienta a implementação, ainda não implementada |
| **Melhoria recomendada** | Proposta da equipe derivada da auditoria; não exigida pelos enunciados |
| **Não implementada** | Estado de qualquer item acima enquanto não houver código e teste que o comprovem |

Autenticação e integridade dos dados são tratadas como **necessárias para a solução web proposta** (uma API sem
credencial ou sem controle de concorrência não é segura nem confiável), e **não** como exigências literais do enunciado.

## 2. Resumo

| ID | Tema | Situação | Origem | Fase de implementação |
|----|------|----------|--------|-----------------------|
| D-01 | Autenticação: sessão ou token, senha inicial, recuperação | **Pendente** | AUD-01 | Decidir antes da 04 |
| D-02 | Definição de Técnico | **Aprovada; implementada** (DLT-01) | AUD-20 | 02 |
| D-03 | Atribuição a Técnico Ausente | **Aprovada; implementada** (DLT-02) | AUD-09 | 02 |
| D-04 | Apontamentos e observações em OS | **Aprovada; implementada** (DLT-03, DLT-04) | AUD-11 | 02 |
| D-05 | Disponibilidade dos técnicos | **Aprovada; implementada** (DLT-05) | AUD-13 | 02 |
| D-06 | Diagnóstico obrigatório antes de Reparo Finalizado | **Aprovada; implementada** (DLT-06) | AUD-21 | 02 |
| D-07 | Campos extras de equipamento | **Pendente** | OPC-06 | Decidir antes da 03 |
| D-08 | Importação dos dados JSON existentes | **Pendente** | OPC-07, AUD-06 | Decidir antes da 03 |
| D-09 | Hospedagem da API e do banco | **Pendente** | ADR-0001 | Decidir antes da 10 |
| D-10 | Futuro da CLI e do diretório `app/` | **Aprovada para o planejamento** (remoção do legado segue sem decisão, ver 4) | AUD-18 | 02 (convivência); remoções só com autorização posterior |
| D-11 | Datas e fuso horário | **Aprovada** | AUD-07 | 02 (tipos); conversão de dados legados depois |
| D-12 | Provisionamento do PostgreSQL | **Pendente** | ADR-0006 | Decidir antes da 03 |
| D-13 | Ferramentas de qualidade | **Aprovada** (backend) | AUD-17 | 02 |
| D-14 | Estrutura do novo backend | **Aprovada** | ADR-0002 | 02 |
| D-15 | OS atrasada e prazos | **Pendente** | E2-FRT-03 | Decidir antes da 08 |
| — | Validação de entradas | **Aprovada** (melhoria); **implementada** (DLT-08) | AUD-12 | 02 (domínio), 04 (API) |
| — | Desativação de usuários | **Aprovada** (melhoria); **implementada no modelo** (DLT-09) | AUD-10, AUD-08 | 02 (modelo), 03 (persistência), 06 (cadastro) |
| — | Regularização da Operação E (REG-E-01 a REG-E-08) | **Aprovada; implementada** (DLT-18 a DLT-23; REG-E-07 e REG-E-08 são de rastreabilidade) | Auditoria de leitura da Operação E | 02 |

## 3. Decisões funcionais aprovadas (D-02 a D-06)

As regras abaixo são detalhadas no [ADR-0009](adr/0009-papeis-autorizacao-e-regras-da-os.md). Cada item registra o
comportamento do baseline, a regra aprovada e os testes que a comprovarão.

### D-02 — Definição de Técnico

- **Baseline:** `Usuario.e_tecnico` retorna `pode("apontar_reparo")` (`models/usuario.py:32-35`). Retirar essa permissão
  do cargo Técnico faz os técnicos saírem de `Repositorio.tecnicos()`; concedê-la ao cargo Gestor faz gestores
  aparecerem como técnicos (AUD-20, não executado).
- **Aprovado:** Gestor e Técnico são **papéis definidos explicitamente no domínio**. A identidade do papel não depende de
  nenhuma permissão. Permissões continuam configuráveis. Retirar a permissão de apontamento de um Técnico **não** o
  torna outro papel; conceder uma permissão técnica a um Gestor **não** o torna Técnico.
- **Identidade do papel × autorização:** o papel responde "quem este usuário é" (pode receber OS, aparece na lista de
  técnicos, tem carga e disponibilidade). A permissão responde "o que ele pode executar". Um Técnico sem a permissão de
  apontar continua sendo Técnico e continua atribuível, mas recebe `403` ao tentar apontar.
- **Testes necessários:** (a) técnico sem `apontar_reparo` continua listado como técnico e atribuível, e é negado ao
  apontar; (b) gestor com permissões técnicas concedidas não aparece na lista de técnicos nem recebe atribuição;
  (c) a lista de técnicos independe do conjunto de permissões; (d) mudar o papel de um usuário é uma operação explícita
  e restrita ao Gestor.
- **Fora do escopo desta decisão:** como o papel é persistido e como se muda o papel de um usuário com OS ativas
  (a política de reatribuição não é inventada, ver seção 5.2).

### D-03 — Atribuição a Técnico Ausente

- **Baseline:** só a tela confirma ("Técnico está ausente. Atribuir mesmo assim?", `ui/tela_gestor.py:27-29`). O domínio
  aceitou a atribuição sem erro (AUD-09, executado, Apêndice A B2).
- **Aprovado:** a atribuição a um Técnico Ausente é **recusada por padrão**. O Gestor pode **confirmar explicitamente**
  a atribuição. A confirmação **chega ao servidor** como parâmetro explícito da operação e é **validada na camada de
  aplicação**. Uma chamada direta à API não pode contornar a regra por não haver interface de confirmação.
- **Comportamento esperado:** sem confirmação, a operação falha com erro de conflito de regra (409, ver ADR-0003); com a
  confirmação explícita, é aceita e o histórico registra que a atribuição foi feita a técnico ausente.
- **Testes necessários:** (a) atribuir a Ausente sem confirmação é recusado e não altera a OS nem o histórico;
  (b) com confirmação explícita é aceito e registrado; (c) teste de API chamando a rota sem o campo de confirmação;
  (d) a confirmação não é aceita de quem não tem a permissão de atribuir; (e) a regra vale igualmente para reatribuição.

### D-04 — Apontamentos e observações em OS

- **Baseline:** `adicionar_apontamento` exige só a permissão `registrar_apontamento` (`models/ordem_servico.py:98-100`)
  e a tela lista **todas** as OS (`ui/tela_ordens.py:62`). Um técnico não dono incluiu um apontamento em OS **Concluída**
  (AUD-11, executado, Apêndice A B1). Neste documento, o "apontamento" do baseline (`TipoServico.APONTAMENTO`) é
  chamado **observação**, para distinguir de `apontar_reparo`.
- **Aprovado:**
  1. **Bloquear** novos apontamentos e observações em OS **Concluídas** ou **Canceladas**.
  2. Em OS **ativas**, Gestor e Técnico responsável fazem apontamentos conforme suas permissões e responsabilidades.
  3. Quem **abriu** a OS também pode registrar **observações** enquanto ela estiver ativa.
  4. O autor da abertura **não** recebe automaticamente permissão para horas de reparo, peças, diagnóstico técnico
     ou conclusão do serviço.
  5. Observações e intervenções técnicas são **operações distintas**, ainda que compartilhem um histórico cronológico.
     Autoria, data e tipo de cada registro são preservados.
  6. Uma observação **não altera** o estado da OS.
  7. As regras são verificadas **no servidor**, não só no frontend.
- **Distinções que o domínio deve manter:**

| Conceito | O que é | Quem registra | Altera o status? | Tipo no histórico |
|----------|---------|---------------|------------------|-------------------|
| Observação da OS | Comentário livre sobre a OS | Gestor, Técnico responsável e quem abriu a OS, em OS ativa | Não | Observação |
| Diagnóstico técnico | Parecer inicial e causa-raiz | Técnico responsável | Não | Diagnóstico |
| Apontamento de reparo/intervenção | Horas, intervenção e peças | Técnico responsável | Pode (Atribuída → Em Execução, comportamento do baseline) | Reparo |
| Alteração de status | Transição da máquina de estados | Conforme a transição (técnico, gestor) | Sim | Mudança de status e tipos específicos (conclusão, encerramento etc.) |

- **Testes necessários:** (a) observação e apontamento de reparo em OS Concluída ou Cancelada são recusados;
  (b) o usuário que abriu a OS registra observação em OS ativa e é recusado ao apontar reparo, diagnosticar ou concluir;
  (c) técnico que não é o responsável é recusado nas operações técnicas; (d) a observação não muda o status;
  (e) autor, data e tipo gravados corretamente; (f) as mesmas recusas ocorrem via API, sem depender do frontend.
- **Ponto sem decisão:** o enunciado não pede observação pelo autor da abertura; é uma regra aprovada pela equipe.
  Se o autor da abertura for desativado, a regra dele deixa de ser exercida (ver seção 5.2).

### D-05 — Disponibilidade dos técnicos

- **Baseline:** só uma OS **Em Execução** coloca o técnico em "Em atendimento"; "Aguardando Peça" volta a "Disponível".
  O cálculo só ocorre quando a interface chama `atualizar_disponibilidades()` (`ui/aplicacao.py:101`); antes disso o
  valor fica desatualizado (AUD-13, executado, Apêndice A E).
- **Aprovado:**
  - preservar a regra da Entrega 1: **somente** OS **Em Execução** caracteriza atendimento; OS **Aguardando Peça**, por
    si só, **não** caracteriza "Em atendimento";
  - a disponibilidade operacional é **calculada a partir das ordens de serviço**, sem depender de rotina de atualização
    da interface;
  - a **ausência** continua registrada separadamente e a ausência manual **tem precedência** sobre a disponibilidade
    calculada;
  - **não** introduzir novo SLA nem novas regras de ocupação.
- **Cenários de teste:**

| # | Situação do técnico | Resultado esperado |
|---|---------------------|--------------------|
| 1 | Sem OS ativas, não ausente | Disponível |
| 2 | Uma OS Atribuída | Disponível |
| 3 | Uma OS Em Execução | Em atendimento |
| 4 | Uma OS Aguardando Peça, nenhuma em execução | Disponível |
| 5 | Uma OS Em Execução e outra Aguardando Peça | Em atendimento |
| 6 | Marcado como ausente, com OS Em Execução | Ausente (precedência manual) |
| 7 | Ausência removida com OS Em Execução | Em atendimento (recalculado, sem ação extra) |
| 8 | OS Em Execução passa a Reparo Finalizado | Disponível, sem chamar rotina de atualização |
| 9 | OS reatribuída | O técnico anterior e o novo refletem a mudança imediatamente |
| 10 | Consulta da API logo após uma transição | Valor já correto na mesma resposta |

### D-06 — Diagnóstico obrigatório

- **Baseline:** a transição para Reparo Finalizado exige só intervenção registrada (`ordem_servico.py:133-134`). Com a
  OS finalizada sem diagnóstico, a conclusão técnica é recusada e o diagnóstico também (aceito só em Atribuída, Em
  Execução e Aguardando Peça, `:106`); o técnico precisa voltar a Em Execução (AUD-21, executado, Apêndice A F).
- **Aprovado:** o diagnóstico técnico deve existir **antes** da transição para Reparo Finalizado. A regra é aplicada **no
  domínio**; a ausência produz **erro claro** e impede a transição. As demais transições válidas são preservadas.
- **Testes necessários:** (a) finalizar sem diagnóstico é recusado com mensagem específica e não altera o status nem o
  histórico; (b) com diagnóstico, a transição segue exigindo intervenção; (c) fluxo completo continua passando;
  (d) a transição Reparo Finalizado → Em Execução e o retorno continuam válidos; (e) o caminho indireto do baseline
  deixa de ser necessário.

## 4. Decisões técnicas aprovadas (D-10, D-11, D-13, D-14)

### D-10 — Futuro da CLI e do diretório `app/`

- **Baseline:** a CLI (`main.py`, `ui/`, `models/`, `persistencia/`) é a Entrega 1; `app/` é uma implementação paralela
  não importada e sem ponto de entrada (AUD-18).
- **Aprovado para o planejamento:**
  1. **Preservar** a CLI original e o código legado.
  2. **Não** criar nova CLI nem adaptador JSON de transição na Fase 02.
  3. Desenvolver o novo backend em `backend/src/manutencao/` (D-14), ao lado do legado.
  4. **Não remover** `app/` nem outros módulos legados sem autorização posterior, específica e atual.
  5. A **interface principal da Entrega 2 será web**; a CLI não é adaptador dos novos serviços.
- **Consequências:** a CLI legada serve de referência de comportamento e permanece executável; os testes de
  caracterização usam uma fachada sobre o legado (ADR-0006); os repositórios novos são em memória (Fase 02) e
  SQLAlchemy (Fase 03), sem implementação JSON; a CLI não usa a raiz de composição (ADR-0005).
- **Continua sem decisão:** o destino final de cada módulo legado (manter como referência ou remover) e de `app/`.
  Qualquer remoção depende de testes de caracterização aprovados e de autorização explícita, em fase posterior
  (ADR-0008).
- **Não implementada:** esta decisão apenas orienta o planejamento; nenhum código foi criado nem alterado.

### D-11 — Datas e fuso horário

- **Baseline:** datas são `str` no formato `dd/mm/aaaa hh:mm`, sem fuso (`ordem_servico.py:21-22`, AUD-07).
- **Aprovado:** datas **tipadas e conscientes de fuso**; instantes **armazenados em UTC**; exibição no fuso
  **America/Sao_Paulo**; **sem `datetime` ingênuo** nas novas implementações. A conversão das datas legadas é tratada
  **depois**, antes de qualquer migração de dados. **Nenhuma conversão de dados é executada nesta fase.**
- **Relógio:** a abstração de relógio fica na **camada de aplicação**; o domínio não a importa. A aplicação obtém o
  instante e o **entrega explicitamente** às operações de domínio. Detalhes e justificativa no
  [ADR-0007](adr/0007-datas-fuso-horario-e-relogio.md).
- **Testes necessários:** relógio fixo nos casos de uso; operações de domínio rejeitam `datetime` ingênuo; instante
  gravado em UTC e apresentado em America/Sao_Paulo (incluindo mudança de dia); ordenação do histórico por instante.

### D-13 — Ferramentas de qualidade

- **Aprovado:** introduzir **pytest, ruff e mypy a partir da Fase 02**; usar **testes de caracterização** antes de
  alterar comportamentos existentes; separar testes de **domínio, aplicação e integração**; planejar **verificações de
  contrato** dos repositórios para demonstrar substituibilidade; manter as ferramentas de **frontend** e os testes
  **E2E** para as fases correspondentes.
- **Nesta fase:** nenhuma ferramenta é instalada. Detalhes em [ADR-0006](adr/0006-estrategia-de-testes.md).
- **Ainda em aberto dentro de D-13:** ferramenta E2E, ferramentas de frontend além de Vitest e metas de cobertura,
  decididas nas fases correspondentes.

### D-14 — Estrutura do novo backend

- **Aprovado:** criar futuramente o pacote **`backend/src/manutencao/`**, em camadas, **sem conflito** com o diretório
  legado `app/`. Preservar o código legado enquanto a implementação nova é construída e validada; migrar
  comportamentos gradualmente; preservar a Entrega 1 pela tag `entrega-1`.
- **Nesta fase:** `app/`, `models/`, `ui/`, `persistencia/` e `main.py` **não são excluídos**. Estratégia de convivência
  e destino de cada módulo legado em [ADR-0008](adr/0008-estrutura-do-backend-e-convivencia-com-o-legado.md).

## 5. Melhorias aprovadas (não são comportamento atual)

### 5.1 Validação de entradas

- **Baseline:** só a interface valida (`ui/entrada.py:14-45`). O domínio aceitou falha vazia, 0 h e intervenção vazia
  (AUD-12, executado, Apêndice A B5).
- **Aprovado (mudança de comportamento, não correção do baseline):**
  - rejeitar campos obrigatórios vazios;
  - rejeitar valores inválidos em campos numéricos;
  - rejeitar apontamentos com duração **igual ou inferior a zero** (o baseline aceita zero);
  - entradas inválidas não criam registros inconsistentes;
  - validação **no servidor**, independentemente do frontend.
- **Registro do delta:** como o baseline aceita zero hora e textos vazios, esta mudança deve aparecer como **delta de
  comportamento explícito** na estratégia de caracterização (ADR-0006, seção "Deltas").
- **Testes necessários:** abertura com falha vazia ou só espaços; apontamento com 0, negativo e não numérico; intervenção
  vazia; peça com quantidade zero ou negativa; nenhum registro e nenhuma entrada de histórico criados após a recusa.

### 5.2 Desativação de usuários

- **Baseline:** não existe campo `ativo` em `Usuario`; usuário com histórico não pode ser excluído
  (`persistencia/repositorio.py:131-145`).
- **Aprovado (futuro):** adicionar o campo `ativo`; desativar sem excluir o histórico; **impedir autenticação e novas
  operações** de usuários inativos; preservar referências históricas a técnicos e gestores desativados.
- **Tratamento das OS atribuídas a usuário desativado:** **necessidade registrada, sem política inventada.** É preciso
  decidir (por Gestor, caso a caso, ou por regra automática) o que acontece com OS ainda atribuídas, com OS que ele
  abriu e com seu papel na disponibilidade. Até haver decisão, a implementação não deve reatribuir automaticamente.
  Esta é uma pendência a levar à Fase 06.
- **Testes necessários:** usuário inativo não autentica nem opera; histórico mantém nome e referência; usuário inativo
  não aparece como técnico atribuível; listagens históricas continuam exibindo-o.

## 6. Decisões pendentes

Nenhuma é considerada aprovada. As recomendações abaixo continuam sendo **propostas da equipe**.

| ID | Pergunta | Recomendação documentada | Decidir antes de |
|----|----------|--------------------------|------------------|
| D-01 | Sessão ou token, senha inicial, contas iniciais, recuperação de acesso | Cookie de sessão `HttpOnly` ou token de curta duração com senha em hash de biblioteca consolidada; conta de gestor inicial criada por comando de provisionamento, sem senha no código | Fase 04 |
| D-07 | Incluir fabricante, nº de série, setor e data de aquisição no equipamento | Incluir como campos opcionais do equipamento (evolução aditiva; não bloqueia o domínio da Fase 02) | Fase 03 |
| D-08 | Importar o `dados/dados.json` existente? | Não importar automaticamente; carga de demonstração por *seed*; importação só com plano, *backup*, *dry-run* e autorização específica | Fase 03 |
| D-09 | Hospedagem da API e do PostgreSQL | Decidir após a Fase 09; frontend estático separado; banco gerenciado | Fase 10 |
| D-12 | Provisionamento do PostgreSQL (desenvolvimento, teste e CI) | Contêiner descartável para testes de integração; serviço do provedor no CI | Fase 03 |
| D-15 | Definição de OS "atrasada" | Sem prazo no modelo atual; propor prazo por criticidade somente se a equipe aprovar um SLA | Fase 08 |

### 6.1 Observações sem decisão

- `aprovar_os` é **uma única permissão** que controla aprovar, reprovar e cancelar (`ordem_servico.py:173,180,186`;
  descrição "Aprovar, cancelar e encerrar OS", `models/permissoes.py:21`). No baseline, quem pode aprovar também pode
  cancelar. Separar as permissões **não está decidido**; os testes de caracterização preservam o comportamento atual.
- O baseline trata o Técnico como o único que opera o reparo; a regra de quem **abre** OS (qualquer usuário com
  `abrir_os`) é preservada.

### 6.2 Dependências da Fase 02

Nenhuma decisão pendente bloqueia a Fase 02. A D-10, que era a dependência imediata, foi aprovada para o planejamento
(seção 4): CLI e legado preservados, sem nova CLI nem adaptador JSON. D-07 é aditiva e as demais pertencem a fases
posteriores.

## 7. Deltas técnicos de autorização (DLT-12 a DLT-17)

Aprovados por autorização expressa do usuário em **2026-11-17** (regularização da Operação D, alternativa B:
*preservar as correções de autorização já implementadas, formalizá-las como deltas e corrigir a rastreabilidade e a
caracterização*). Esta seção **não altera** as decisões D-01 a D-15 e **não renumera** os deltas anteriores.

**Convenção.** As decisões de produto e de arquitetura têm identificadores `D-nn` (seções 2 a 6). As diferenças
técnicas entre o legado e o novo backend têm identificadores `DLT-nn`, registrados no código em
`backend/tests/caracterizacao/deltas.py` (fonte de verificação automática) e descritos no
[ADR-0006](adr/0006-estrategia-de-testes.md). Os DLT-12 a DLT-17 não decorrem de uma decisão `D-nn`: nascem dos achados
AUD-02 (autorização desigual) e AUD-09 (regras só na interface) e da autorização citada acima.

| ID | Tema | Origem | Camada | Estado | Aprovação |
|----|------|--------|--------|--------|-----------|
| DLT-12 | Autoproteção do gestor | AUD-09 (CAR-71) | Aplicação | **Implementado** | 2026-11-17 |
| DLT-13 | Autorização para operações de gestão | AUD-02 (CAR-73) | Aplicação | **Implementado** | 2026-11-17 |
| DLT-14 | Autorização para operações de leitura | AUD-02 (CAR-91) | Aplicação | **Implementado** | 2026-11-17 |
| DLT-15 | Alteração manual da disponibilidade de terceiros | AUD-09 (CAR-72) | Aplicação | **Implementado** | 2026-11-17 |
| DLT-16 | Precedência das verificações de autorização | AUD-02 (CAR-93, CAR-64, CAR-65) | Aplicação | **Implementado** | 2026-11-17 |
| DLT-17 | Ator inexistente | AUD-02 (CAR-92) | Aplicação | **Implementado** | 2026-11-17 |

"Implementado" significa que o comportamento existe nos serviços de aplicação da branch `refactor/arquitetura` (local,
sem merge nem push) e tem os testes citados em cada delta. O legado (`models/`, `ui/`, `persistencia/`) **não** foi
alterado e continua com o comportamento antigo, que segue caracterizado por testes.

Em todos os deltas: a autorização é verificada **no serviço, antes de qualquer mutação**; uma operação recusada **não
altera repositórios nem consome identificadores**; **nenhuma permissão nova** foi criada; **não** foi implementada
autenticação (D-01 segue pendente). Os papéis explícitos, o bloqueio de técnico ausente, a política de observações, a
disponibilidade derivada, o diagnóstico obrigatório, as validações e o usuário ativo/inativo foram implementados depois,
na Operação E (seção 8), **sem enfraquecer** nenhum dos DLT-12 a DLT-17.

### DLT-12 — Autoproteção do gestor (CAR-71)

- **Legado:** o gestor pode trocar o próprio cargo por um sem gestão, remover do próprio cargo `gerir_usuarios` ou
  reduzir as permissões do próprio cargo; só a tela da CLI o impedia (AUD-09).
- **Aprovado:** o serviço recusa essas três ações com `AUTOREMOCAO_DE_ACESSO_DE_GESTAO`, sem alterar o estado. Alterações
  que preservam `gerir_usuarios` são permitidas. A proteção é da camada de aplicação e independe da interface.
- **Justificativa:** evita deixar o sistema sem quem gerencie usuários por engano.
- **Evidência:** `aplicacao/test_autorizacao.py::test_dlt12_*`; `caracterizacao/test_autorizacao_servicos.py::test_dlt12_*`.
- **Teste do comportamento legado:** `caracterizacao/test_legado_defeitos.py::test_aud09_dominio_aceita_o_gestor_remover_o_proprio_acesso_de_gestao`.

### DLT-13 — Autorização para operações de gestão (CAR-73)

- **Legado:** equipamentos e exclusão de usuário eram operados sem identidade nem permissão; só o menu da CLI exigia
  `gerir_equipamentos` e `gerir_usuarios`.
- **Aprovado:** o serviço exige `gerir_equipamentos` (gestão de equipamentos) e `gerir_usuarios` (usuários e cargos),
  antes de qualquer mutação.
- **Justificativa:** preserva a permissão efetiva da CLI e a impõe no servidor (ADR-0003).
- **Evidência:** `aplicacao/test_autorizacao.py::test_dlt13_*`; `caracterizacao/test_autorizacao_servicos.py::test_dlt13_*`.
- **Teste do comportamento legado:** `test_aud02_equipamentos_sao_geridos_sem_identidade_nem_permissao` e
  `test_aud02_exclusao_de_usuario_nao_confere_a_permissao_do_solicitante` (`test_legado_defeitos.py`).

### DLT-14 — Autorização para operações de leitura (CAR-91)

- **Legado:** nenhuma consulta verificava permissão; só o menu escondia as telas.
- **Aprovado:** `ver_equipamentos`, `ver_os` e `ver_disponibilidade` nas consultas correspondentes; `gerir_usuarios` nas
  consultas de usuários e cargos (como na CLI). Sem ampliar permissões nem criar regras de visibilidade.
- **Evidência:** `aplicacao/test_autorizacao.py::test_dlt14_*`; `caracterizacao/test_autorizacao_servicos.py::test_dlt14_*`.
- **Teste do comportamento legado:** `test_aud02_consultas_nao_exigem_permissao_de_leitura_no_legado`.

### DLT-15 — Alteração de disponibilidade de terceiros (CAR-72)

- **Legado:** qualquer usuário altera a disponibilidade de qualquer outro (a tela só mostrava "minha disponibilidade").
- **Aprovado:** o usuário altera a própria; quem tem `gerir_usuarios` altera a de outro; quem não tem é recusado sem
  mutação. Trata só de **quem pode** alterar o valor manual: a disponibilidade derivada (D-05) **não** foi implementada.
- **Evidência:** `aplicacao/test_autorizacao.py::test_dlt15_*`; `caracterizacao/test_autorizacao_servicos.py::test_dlt15_*`.
- **Teste do comportamento legado:** `test_aud09_qualquer_usuario_altera_a_disponibilidade_de_qualquer_outro` e
  `test_aud09_o_proprio_usuario_e_o_gestor_tambem_alteram_a_disponibilidade`.

### DLT-16 — Precedência das verificações (CAR-93; CAR-64 e CAR-65 preservados)

- **Legado:** a exclusão de usuário conferia autoexclusão e histórico sem olhar a permissão.
- **Aprovado:** a autorização é a **primeira** verificação funcional dos casos de uso protegidos, antes de procurar o
  recurso e antes de autoexclusão e histórico. A ordem interna das regras de domínio **não muda** (autoexclusão antes
  do histórico, CAR-64).
- **Evidência:** `aplicacao/test_autorizacao.py::test_dlt16_*`; `caracterizacao/test_autorizacao_servicos.py::test_dlt16_*`.
- **Teste do comportamento legado:** `test_aud02_exclusao_confere_autoexclusao_e_historico_sem_olhar_a_permissao`.

### DLT-17 — Ator inexistente (CAR-92)

- **Legado:** as operações de gestão não recebiam nem consultavam o solicitante.
- **Aprovado:** os serviços recusam a operação quando o ator não existe, com o erro tipado `NaoEncontradoError`
  (entidade "Usuário"). Não há administrador padrão nem criação automática de usuário. Não é autenticação (D-01).
- **Evidência:** `aplicacao/test_autorizacao.py::test_dlt17_*`; `caracterizacao/test_autorizacao_servicos.py::test_dlt17_*`.
- **Teste do comportamento legado:** `test_aud02_operacoes_de_gestao_ignoram_quem_pede_inclusive_um_inexistente`.

### Categoria `DEFEITO_CORRIGIDO` eliminada

A categoria `DEFEITO_CORRIGIDO` foi introduzida na Operação D sem estar vinculada a uma decisão aprovada e **deixou de
existir**. Um cenário só é excluído da comparação com os serviços quando há um delta aprovado e implementado que o
liste, o comportamento antigo continua testado no legado, o novo tem teste específico e a divergência é exatamente a
autorizada (verificado por `caracterizacao/test_adaptador_servicos.py`). CAR-71, CAR-72 e CAR-73 passaram de "defeito do
legado" a "modificar por decisão aprovada" (DLT-12, DLT-15, DLT-13), assim como CAR-74 (DLT-11).

### CAR-65 — solicitante da exclusão

O teste da regra `USUARIO_COM_HISTORICO` passou a usar uma segunda gestora (Eva) como solicitante da exclusão da Ana,
porque o técnico Bruno é agora recusado por falta de permissão antes da regra de histórico (DLT-13, DLT-16). O resultado
esperado da regra não mudou. A tentativa do técnico continua documentada e testada: o legado a aceita até a regra de
histórico e os serviços a recusam por permissão
(`test_car65_o_legado_permite_a_tentativa_do_tecnico_e_os_servicos_recusam_por_permissao`).

## 8. Deltas de regras de negócio (Operação E): DLT-01 a DLT-09

Implementam as decisões D-02 a D-06 e as melhorias aprovadas (validação de entradas e usuário ativo), aprovadas em
2026-11-15 (seções 3 e 5; [ADR-0009](adr/0009-papeis-autorizacao-e-regras-da-os.md)) e implementadas depois da autorização
da Operação E, em 2026-11-17. Valem **só no novo backend** (`backend/src/manutencao/`, branch local `refactor/arquitetura`,
sem merge nem push); o legado continua como estava, e o comportamento antigo segue caracterizado por testes. O DLT-07
(datas, Operação C) é anterior e não foi alterado; os DLT-10 a DLT-17 foram preservados.

| ID | Tema | Decisão | Camada | Estado | Implementação |
|----|------|---------|--------|--------|---------------|
| DLT-01 | Papéis Gestor e Técnico | D-02 | Domínio e aplicação | **Implementado** | 2026-11-17 |
| DLT-02 | Atribuição a técnico ausente | D-03 | Domínio e aplicação | **Implementado** | 2026-11-17 |
| DLT-03 | Observação em OS Concluída ou Cancelada | D-04 | Domínio | **Implementado** | 2026-11-17 |
| DLT-04 | Quem observa uma OS ativa | D-04 | Domínio | **Implementado** | 2026-11-17 |
| DLT-05 | Disponibilidade derivada das OS | D-05 | Domínio e aplicação | **Implementado** | 2026-11-17 |
| DLT-06 | Diagnóstico antes de Reparo Finalizado | D-06 | Domínio | **Implementado** | 2026-11-17 |
| DLT-08 | Campos obrigatórios e horas maiores que zero | Melhoria 5.1 (AUD-12) | Domínio e aplicação | **Implementado** | 2026-11-17 |
| DLT-09 | Usuário ativo ou inativo | Melhoria 5.2 (AUD-10, AUD-08) | Domínio e aplicação | **Implementado** | 2026-11-17 |

Cada delta está registrado em `backend/tests/caracterizacao/deltas.py` com o comportamento do legado, o aprovado, a
justificativa, a camada, o teste do legado e as evidências **separadas por camada** (domínio, serviços e comparação com o
legado). Em todos: a recusa não altera a OS, o histórico, os repositórios nem consome identificadores; a autorização
continua sendo a primeira verificação (DLT-16) e um ator inexistente é recusado (DLT-17).

### DLT-01 — Papéis Gestor e Técnico (D-02)

- **Legado:** técnico é quem tem a permissão `apontar_reparo`; retirá-la tira o usuário da lista e da atribuição,
  concedê-la a um gestor o torna atribuível e trocar o cargo move o usuário entre técnicos e gestores (AUD-20).
- **Novo:** `Usuario.papel` (`Papel.GESTOR` ou `Papel.TECNICO`) é obrigatório e **não depende de permissão**. A lista de
  técnicos, a atribuição, a carga e a disponibilidade usam o papel. Um Técnico sem `apontar_reparo` continua listado e
  atribuível, e é negado ao apontar; um Gestor com permissões técnicas não aparece nem recebe atribuição; mudar o cargo
  muda as permissões e não o papel.
- **Mudar o papel:** `ServicoDeUsuarios.alterar_papel`, operação explícita que exige o **papel Gestor e** a permissão
  `gerir_usuarios` (ratificado em REG-E-02, DLT-19). Ninguém deixa de ser Gestor por conta própria (REG-E-03, DLT-20). **Não
  reatribui** as OS do usuário; quem tem OS ativas não deixa o papel Técnico (REG-E-04, DLT-21), e o último gestor
  administrativamente apto não é eliminado (REG-E-01, DLT-18).
- **Não feito:** nenhum papel novo; nenhuma autenticação.

### DLT-02 — Atribuição a técnico ausente (D-03)

- **Legado:** o domínio aceita; só a tela da CLI pede confirmação.
- **Novo:** atribuir ou reatribuir a técnico `Ausente` (ausência manual) é recusado com conflito (`tecnico_ausente`),
  salvo `confirmar_ausente=True`, **dado explícito da operação** validado no caso de uso e que só vale para quem tem
  `atribuir_os`. O histórico registra "(técnico ausente; atribuição confirmada pelo gestor)". A ordem das verificações
  antigas (permissão, estado, é técnico, já atribuída) é preservada; a ausência é verificada por último.

### DLT-03 e DLT-04 — Observações (D-04)

- **Legado:** qualquer usuário com `registrar_apontamento` observa qualquer OS, inclusive Concluída ou Cancelada.
- **Novo:** ordem **permissão → vínculo → estado**. Em OS ativa observam o **Gestor**, o **técnico responsável** e **quem
  abriu** a OS (todos com `registrar_apontamento`); um terceiro é recusado (`sem_vinculo_com_a_os`, 403), inclusive em OS
  encerrada (quem não pode agir não aprende nada sobre o estado). Em OS Concluída ou Cancelada ninguém observa
  (`os_encerrada`). A observação não altera o status e é registrada como `Apontamento` (autor, data e tipo preservados).
  O autor da abertura **não** recebe capacidade técnica: diagnóstico, reparo, status e conclusão seguem exigindo o
  responsável. Diagnóstico e reparo já eram restritos aos status de atendimento.

### DLT-05 — Disponibilidade derivada (D-05)

- **Legado:** valor armazenado, atualizado só por `atualizar_disponibilidades()` (rotina da interface).
- **Novo:** a disponibilidade **é derivada das OS a cada consulta** (`domain/disponibilidade.py`, `Projecoes`): a ausência
  manual prevalece; senão, uma OS `Em Execução` do técnico o põe `Em atendimento`; `Aguardando Peça` não; senão
  `Disponível`. Não há rotina, gravação nem processo em segundo plano (`atualizar_disponibilidades` foi removida do
  serviço). `Usuario.disponibilidade` passou a ser o valor **manual** (a ausência); a autorização para alterá-lo
  continua sendo a do DLT-15. Os dez cenários da decisão têm teste.

### DLT-06 — Diagnóstico obrigatório (D-06)

- **Legado:** finalizar exige só intervenção; sem diagnóstico a OS fica sem saída (AUD-21).
- **Novo:** `alterar_status(Reparo Finalizado)` exige diagnóstico, com erro claro (`sem_diagnostico`) e sem alterar status
  nem histórico. A falta de **intervenção** continua sendo verificada primeiro (preserva as recusas antigas). A verificação
  em `concluir_tecnicamente` permanece como invariante. As demais transições não mudaram.

### DLT-08 — Campos obrigatórios e horas positivas (AUD-12)

Valem **no domínio e nos serviços**, para qualquer interface (os mesmos campos são conferidos campo a campo em
`backend/tests/aplicacao/test_campos_obrigatorios.py`, a partir da lista única `backend/tests/apoio/campos.py`).

| Campo | Situação | Delta |
|-------|----------|-------|
| descrição da falha (abertura da OS) | **Obrigatório** | DLT-08 |
| parecer técnico (diagnóstico) | **Obrigatório** | DLT-08 |
| causa-raiz (diagnóstico) | **Obrigatório** | DLT-08 |
| intervenção realizada (apontamento de reparo) | **Obrigatório** | DLT-08 |
| motivo da reprovação | **Obrigatório** | DLT-08 |
| motivo do cancelamento | **Obrigatório** | DLT-08 |
| nome do usuário | **Obrigatório** | DLT-08 |
| nome do equipamento | **Obrigatório** | DLT-08 |
| texto da observação de OS | **Obrigatório** | DLT-22 (REG-E-05) |
| descrição da peça utilizada | **Obrigatório** | DLT-22 (REG-E-05) |
| modelo do equipamento | Opcional (sem validação) | — |
| teste funcional | Opcional (sem validação) | — |
| e-mail do usuário | Opcional (sem validação) | — |
| escala do usuário | Opcional (sem validação) | — |

- **Regra.** Obrigatório = texto não vazio depois de remover os espaços das extremidades. A recusa é
  `campo_obrigatorio` (422); o texto aceito é guardado **exatamente como informado**.
- **Horas.** `< 0` mantêm a recusa e a mensagem do legado; `0` e valores não finitos são recusados
  (`horas_nao_positivas`). A quantidade de peça positiva é preservada e é verificada **antes** da descrição da peça.
- **Precedência.** A validação vem **depois** da autorização e das regras de estado e **antes** de qualquer mutação:
  uma recusa não cria registro nem inicia a execução da OS. Na observação a ordem é permissão, vínculo, estado e só
  então o conteúdo.
- **Legado.** O legado aceitava todos estes textos vazios (só a tela os exigia): `test_legado_defeitos.py` (CAR-80).

### DLT-09 — Usuário ativo ou inativo (melhoria 5.2)

- **Legado:** não há `ativo`; só se exclui quem não tem histórico.
- **Novo:** `Usuario.ativo` (todos nascem ativos); `desativar` e `reativar` exigem `gerir_usuarios`, são idempotentes e
  **ninguém desativa a si mesmo** (mesma autoproteção do DLT-12). Um usuário **inativo não opera** (recusado como
  `usuario_inativo` antes de qualquer verificação de permissão; um ator inexistente continua `NaoEncontradoError`), não tem
  permissão efetiva, sai da lista de técnicos atribuíveis e não recebe OS. O histórico e as OS que o citam são
  preservados; **nenhuma OS é reatribuída automaticamente** e a exclusão continua recusada para quem tem histórico.
  A desativação é recusada para quem tem OS ativas sob sua responsabilidade (REG-E-04, DLT-21) e para o último gestor
  administrativamente apto (REG-E-01, DLT-18).
- **Não feito:** autenticação (D-01); a política completa de transferência de responsabilidades (ver 8.1).

### 8.1 Pontos que estavam sem decisão

Os pontos abaixo ficaram em aberto ao fim da Operação E e foram decididos na regularização (seção 9). O que segue
pendente está na última linha.

| Ponto | Situação ao fim da Operação E | Decisão |
|-------|-------------------------------|---------|
| OS ativas de quem muda de papel ou é desativado | Nada era reatribuído; o usuário seguia como responsável | **REG-E-04**: bloqueio (recusa), sem reatribuir nem cancelar |
| `alterar_papel` exige papel **e** permissão | Mais restritivo que só a permissão | **REG-E-02**: ratificado |
| Autoproteção em `alterar_papel` e `desativar` | Recusava o próprio gestor; sem regra de "último gestor" | **REG-E-03**: ratificado; **REG-E-01**: último gestor |
| Textos não listados no DLT-08 | Observação, teste funcional, descrição de peça, modelo, e-mail e escala não eram validados | **REG-E-05**: observação e descrição de peça passam a ser obrigatórias; os demais seguem opcionais |
| "Diagnóstico" no DLT-08 | Parecer **e** causa-raiz obrigatórios | **REG-E-05**: os campos já validados são preservados |
| Manual `Em atendimento` | Aceito, mas a consulta mostrava o derivado | **REG-E-06**: só `Disponível` e `Ausente` são aceitos |
| Autenticação | Não implementada | Pendente (D-01) |
| Política completa de transferência de responsabilidades (reatribuição de OS de quem é desativado ou muda de papel) | Não decidida | Pendente (fase planejada) |

## 9. Regularização da Operação E (REG-E-01 a REG-E-08)

Depois da Operação E, uma auditoria de leitura propôs oito decisões para regularizar o que ficara implementado por
interpretação. Foram **aprovadas expressamente pelo usuário em 2026-11-17**
(*AUTORIZAÇÃO DE REGULARIZAÇÃO DA OPERAÇÃO E*), com autorização para implementar só as correções descritas, atualizar
testes e documentação e fazer commits **locais** (sem push nem merge; a Operação F **não** foi autorizada). Valem **só
no novo backend** (`backend/`, branch local `refactor/arquitetura`); o legado não foi alterado.

**Convenção.** Os deltas continuam a numeração DLT sem renumerar os anteriores: REG-E-01 a REG-E-06 têm o registro
definitivo DLT-18 a DLT-23 (em `backend/tests/caracterizacao/deltas.py`, com `Delta.regularizacao`). REG-E-07 e REG-E-08
corrigem a rastreabilidade e **não** mudam comportamento: o registro definitivo de cada uma é o próprio identificador
(`REGULARIZACOES_E`, no mesmo arquivo).

| Decisão | Tema | Registro definitivo | Camada | Situação | Aprovação |
|---------|------|---------------------|--------|----------|-----------|
| REG-E-01 | Proteção do último gestor | DLT-18 | Aplicação (condição de gestor apto no domínio) | **Implementada** | 2026-11-17 |
| REG-E-02 | Alteração de papel (ratificação) | DLT-19 | Aplicação | **Ratificada** (já implementada) | 2026-11-17 |
| REG-E-03 | Autoproteção estendida (ratificação) | DLT-20 | Aplicação | **Ratificada** (já implementada) | 2026-11-17 |
| REG-E-04 | Ordens de serviço ativas | DLT-21 | Aplicação | **Implementada** | 2026-11-17 |
| REG-E-05 | Campos obrigatórios (observação e peça) | DLT-22 | Domínio | **Implementada** | 2026-11-17 |
| REG-E-06 | Disponibilidade manual e derivada | DLT-23 | Domínio e aplicação | **Implementada** | 2026-11-17 |
| REG-E-07 | Rastreabilidade do CAR-37 | REG-E-07 | Testes de caracterização | **Registrada** | 2026-11-17 |
| REG-E-08 | Docstring do CAR-80 | REG-E-08 | Testes de caracterização | **Corrigida** | 2026-11-17 |

Evidência de implementação (commits locais): Bloco A, administração de usuários, `1ec50242b0cbeaef3aae71cb29ca086c428c2bc1`; Bloco B, validações e
disponibilidade, `e2b2a1706e1cc36f4ad55ab5303f359460c4cb8c`; Bloco C, caracterização, rastreabilidade e documentação, o commit que contém esta seção.
Todas as recusas são **sem mutação** (usuários, cargos, OS com histórico e sequências de identificadores intactos), com erro
tipado; as de conflito são `RegraDeAplicacaoError` (409 na borda) e a de valor, `ViolacaoDeRegraError` (422).

### REG-E-01 — Proteção do último gestor (DLT-18)

- **Regra anterior:** nada impedia o sistema de ficar sem quem administre usuários.
- **Regra aprovada:** **gestor administrativamente apto** = papel Gestor, usuário ativo e permissão efetiva
  `gerir_usuarios` (`Usuario.e_gestor_administrativo`). A operação que eliminaria o último apto é recusada com
  `ultimo_gestor` (conflito), sem mutação. Abrange: desativação, alteração de papel, alteração de cargo e alteração das
  permissões de um cargo (o efeito é calculado sobre **todos** os usuários, inclusive os que compartilham o cargo). Não
  cria usuário, não concede permissão e não há recuperação administrativa.
- **Interpretação a confirmar:** a **exclusão** de usuário também é protegida (ela elimina o gestor do mesmo modo e cabe na
  frase "impedir que o sistema fique sem pelo menos um Gestor"); não estava na lista de operações da decisão.
- **Ordem das recusas:** autorização, existência, autoproteção (REG-E-03), último gestor e, por fim, OS ativas (REG-E-04).
  A regra só recusa quando a operação **elimina** a última condição existente: se ninguém era apto antes, nada foi
  eliminado.
- **Justificativa:** sem recuperação administrativa, perder o último gestor seria irreversível.
- **Testes:** `aplicacao/test_regularizacao_e.py` (`test_dlt18_*`), `dominio/test_regularizacao_e.py` e
  `caracterizacao/test_regularizacao_e_servicos.py`.

### REG-E-02 — Alteração de papel (DLT-19, ratificação)

- **Regra anterior:** `alterar_papel` exigia papel Gestor e `gerir_usuarios` (DLT-01), sem decisão expressa.
- **Regra aprovada:** o ator precisa, **simultaneamente**, do papel Gestor, estar ativo e ter `gerir_usuarios`; uma só
  condição não basta. A precedência de autorização (DLT-16, DLT-17) é preservada e a exigência de papel Gestor **não** se
  estende às demais operações de gestão, que dependem só de permissão.
- **Testes:** `test_dlt19_*` e `test_dlt01_alterar_papel_*` (`aplicacao/test_operacao_e.py`).

### REG-E-03 — Autoproteção estendida (DLT-20, ratificação)

- **Regra anterior:** um gestor não se rebaixava e ninguém desativava a própria conta, sem decisão expressa.
- **Regra aprovada:** as duas proteções, que complementam o DLT-12, são ratificadas, com o erro tipado existente
  (`autoremocao_de_acesso_de_gestao`). O código é **adequado**: perder o papel de Gestor ou a conta é perder o próprio
  acesso de gestão; nenhuma correção foi necessária. Nenhuma outra autoproteção foi criada (o gestor segue editando os
  próprios dados e a própria disponibilidade).
- **Testes:** `test_dlt20_*`, `test_dlt01_ninguem_deixa_de_ser_gestor_por_conta_propria` e
  `test_dlt09_ninguem_desativa_a_si_mesmo`.

### REG-E-04 — Ordens de serviço ativas (DLT-21)

- **Regra anterior:** desativar ou mudar o papel de quem tinha OS ativas era aceito, sem reatribuir.
- **Regra aprovada:** OS **ativa** = a que não está em `Concluída` nem `Cancelada` (estados do domínio: `Atribuída`, `Em
  Execução`, `Aguardando Peça`, `Reparo Finalizado` e `Aguardando Aprovação`, com o usuário como técnico atribuído). Quem tem
  OS ativa **não é desativado** nem **deixa o papel Técnico** (`usuario_com_os_ativas`, conflito). A verificação vem antes
  da alteração; usuário, OS, histórico e identificadores ficam intactos. **Não** reatribui nem cancela OS e não altera o
  histórico. A mudança de cargo que preserva o papel Técnico não é impedida. Desativar quem já está inativo continua
  idempotente.
- **Pendente:** a política completa de transferência de responsabilidades (fase planejada).
- **Testes:** `test_dlt21_*` (usuário sem OS, `Atribuída`, `Em Execução`, `Aguardando Peça`, `Aguardando Aprovação`,
  `Concluída`, `Cancelada`; desativação e mudança de papel; recusa sem mutação).

### REG-E-05 — Campos obrigatórios (DLT-22)

- **Regra anterior:** observação e descrição de peça vazias eram aceitas.
- **Regra aprovada:** ampliação do DLT-08 ao texto da observação e à descrição da peça (tabela do DLT-08, seção 8). Modelo
  do equipamento, teste funcional, e-mail e escala **não** se tornam obrigatórios. **Precedência:** na observação,
  permissão, vínculo, estado e só depois o conteúdo; na peça, a quantidade antes da descrição, e as peças antes da OS e das
  horas, como no legado.
- **Testes:** `test_dlt22_*` (domínio, serviços e comparação) e `aplicacao/test_campos_obrigatorios.py`.

### REG-E-06 — Disponibilidade manual e derivada (DLT-23)

- **Regra anterior:** o valor manual aceitava `Em atendimento` e a autorização das duas vias de alteração não era única.
- **Regra aprovada:** a disponibilidade manual aceita **exclusivamente** `Disponível` e `Ausente` (`Usuario.definir_disponibilidade_manual`; recusa `disponibilidade_manual_invalida`, 422, sem mutação). `Em atendimento` é só derivado das
  OS. `ServicoDeUsuarios.definir_disponibilidade` e `ServicoDeDisponibilidade.alterar_disponibilidade` delegam à **mesma
  função** (`politica_de_disponibilidade.py`, DLT-15): o usuário altera a própria; quem tem `gerir_usuarios` altera a de
  terceiros; terceiro sem autorização é recusado antes de procurar o alvo. A ausência manual continua prevalecendo sobre a
  derivada; sem atualização em segundo plano.
- **Limite.** A regra é imposta pelo método `definir_disponibilidade_manual` e pelos serviços; o atributo
  `Usuario.disponibilidade` segue atribuível diretamente (o adaptador de caracterização do domínio reproduz a tela do
  legado atribuindo o valor). Nenhum caminho dos serviços grava `Em atendimento`.
- **Testes:** `test_dlt23_*` (as duas vias decidem igual em todas as combinações de ator, alvo e valor).

### REG-E-07 — Rastreabilidade do CAR-37

- **Regra anterior:** o teste que só roda no legado (`test_tecnico.py::test_conclusao_sem_diagnostico_e_recusada`) não tinha
  o vínculo com o DLT-06 registrado, e a exclusão da variante podia ser lida como a do cenário inteiro.
- **Regra aprovada:** confirmada pela leitura do código, a relação com o **DLT-06**: o teste leva a OS a `Reparo Finalizado`
  sem diagnóstico, e a finalização sem diagnóstico passou a ser recusada (`sem_diagnostico`), então o estado de partida é
  inalcançável no novo código. Só **essa variante** não é comparada diretamente
  (`aplicabilidade.VARIANTES_SOMENTE_NO_LEGADO`); o CAR-37 continua **preservado** e executado nos três adaptadores pelos
  seus outros testes; a invariante segue testada no domínio com a mesma recusa e a mesma mensagem. As expectativas do
  legado não foram alteradas e nenhum `skip` foi criado.
- **Testes:** `test_rastreabilidade.py` (`test_a_variante_so_no_legado_do_car_37_esta_ligada_ao_dlt_06` e correlatos).

### REG-E-08 — Docstring do CAR-80

- **Regra anterior:** o docstring do teste do legado afirmava que o domínio e os serviços recusavam textos que ainda
  aceitavam (observação e descrição de peça).
- **Regra aprovada:** os docstrings e esta documentação listam **exatamente** os campos validados e os não validados (tabela
  do DLT-08), a partir de uma lista única (`backend/tests/apoio/campos.py`) conferida campo a campo nos serviços e contra
  este documento. Nenhum teste foi alterado para esconder divergências.

### 9.1 Políticas ratificadas para documentação

Já implementadas e **não modificadas** pela regularização (nenhuma contradiz REG-E-01 a REG-E-08):

- ator inativo é recusado **antes** da verificação de permissão;
- nas observações, a verificação segue autorização, vínculo e estado;
- o gestor autorizado pode observar OS ativas (D-04);
- desativar e reativar mantêm o comportamento **idempotente**;
- a ordem herdada de validação de peças e horas permanece preservada.

### 9.2 Limites e riscos remanescentes

- Autenticação (D-01) e a política completa de transferência de responsabilidades seguem pendentes; não há recuperação
  administrativa (a decisão não a criou).
- `alterar_papel` não alcança o caso "último gestor" por si só (o ator é, por construção, um gestor apto, e a
  autoproteção impede o autorrebaixamento); a verificação existe como garantia e é exercida pelas demais operações.
- `Usuario.disponibilidade` permanece atribuível diretamente (ver REG-E-06); papel e `ativo` só existem em memória até a
  Fase 03.
