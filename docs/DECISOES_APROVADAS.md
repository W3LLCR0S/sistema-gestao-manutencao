# Decisões aprovadas e pendentes

Registro das decisões funcionais e arquiteturais da Fase 01. Fonte única para os identificadores `D-nn` citados na
[auditoria](AUDITORIA_ARQUITETURAL.md), na [matriz](MATRIZ_RASTREABILIDADE.md), nos [ADRs](adr/README.md) e no
[plano de migração](PLANO_DE_MIGRACAO.md).

> **Aprovar uma decisão não é implementá-la.** Tudo o que está marcado como "aprovada" abaixo orienta fases futuras e
> **não existe no código**. O baseline (`e6f7354`, tag `entrega-1`) continua com o comportamento descrito na coluna
> "Baseline". Nenhum código foi alterado por esta documentação.

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
| D-02 | Definição de Técnico | **Aprovada** | AUD-20 | 02 |
| D-03 | Atribuição a Técnico Ausente | **Aprovada** | AUD-09 | 02 |
| D-04 | Apontamentos e observações em OS | **Aprovada** | AUD-11 | 02 |
| D-05 | Disponibilidade dos técnicos | **Aprovada** | AUD-13 | 02 |
| D-06 | Diagnóstico obrigatório antes de Reparo Finalizado | **Aprovada** | AUD-21 | 02 |
| D-07 | Campos extras de equipamento | **Pendente** | OPC-06 | Decidir antes da 03 |
| D-08 | Importação dos dados JSON existentes | **Pendente** | OPC-07, AUD-06 | Decidir antes da 03 |
| D-09 | Hospedagem da API e do banco | **Pendente** | ADR-0001 | Decidir antes da 10 |
| D-10 | Futuro da CLI e do diretório `app/` | **Pendente** (dependência imediata, ver 6.2) | AUD-18 | Decidir antes da 02 (CLI) e após a 04 (remoções) |
| D-11 | Datas e fuso horário | **Aprovada** | AUD-07 | 02 (tipos); conversão de dados legados depois |
| D-12 | Provisionamento do PostgreSQL | **Pendente** | ADR-0006 | Decidir antes da 03 |
| D-13 | Ferramentas de qualidade | **Aprovada** (backend) | AUD-17 | 02 |
| D-14 | Estrutura do novo backend | **Aprovada** | ADR-0002 | 02 |
| D-15 | OS atrasada e prazos | **Pendente** | E2-FRT-03 | Decidir antes da 08 |
| — | Validação de entradas | **Aprovada** (melhoria) | AUD-12 | 02 (domínio), 04 (API) |
| — | Desativação de usuários | **Aprovada** (melhoria) | AUD-10, AUD-08 | 02 (modelo), 03 (persistência), 06 (cadastro) |

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

## 4. Decisões técnicas aprovadas (D-11, D-13, D-14)

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
| D-10 | Futuro da CLI e de `app/` | Ver 6.2 | Antes da Fase 02 (CLI) e após a 04 (remoções) |
| D-12 | Provisionamento do PostgreSQL (desenvolvimento, teste e CI) | Contêiner descartável para testes de integração; serviço do provedor no CI | Fase 03 |
| D-15 | Definição de OS "atrasada" | Sem prazo no modelo atual; propor prazo por criticidade somente se a equipe aprovar um SLA | Fase 08 |

### 6.1 Observações sem decisão

- `aprovar_os` é **uma única permissão** que controla aprovar, reprovar e cancelar (`ordem_servico.py:173,180,186`;
  descrição "Aprovar, cancelar e encerrar OS", `models/permissoes.py:21`). No baseline, quem pode aprovar também pode
  cancelar. Separar as permissões **não está decidido**; os testes de caracterização preservam o comportamento atual.
- O baseline trata o Técnico como o único que opera o reparo; a regra de quem **abre** OS (qualquer usuário com
  `abrir_os`) é preservada.

### 6.2 Dependência imediata de decisão pendente para a Fase 02

**D-10 (parcial)** afeta o plano da Fase 02: manter ou não a CLI como adaptador dos novos serviços e, em consequência,
se será criado um adaptador JSON de transição. Recomendação documentada: **não** criar o adaptador JSON nem adaptar a
CLI na Fase 02; manter `main.py` e o código legado intactos e executáveis, servindo como referência de comportamento
(D-14), e construir o novo pacote ao lado. A alternativa (CLI sobre os novos serviços) é viável, mas amplia o escopo da
Fase 02. As demais decisões pendentes não bloqueiam a Fase 02 (D-07 é aditiva e as demais pertencem a fases posteriores).
