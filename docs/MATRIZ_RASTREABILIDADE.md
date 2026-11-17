# Matriz de rastreabilidade de requisitos

Relaciona cada requisito dos enunciados da **Entrega 1** e da **Entrega 2** à implementação existente, à lacuna
encontrada, à fase planejada e ao critério de aceitação. Baseline: commit `e6f7354` (tag `entrega-1`).

As descrições abaixo são resumos para rastreio; os enunciados oficiais prevalecem. Os achados `AUD-nn` estão em
[`AUDITORIA_ARQUITETURAL.md`](AUDITORIA_ARQUITETURAL.md).

## 1. Convenções

**Identificadores:** `E1-<grupo>-nn` (Entrega 1), `E2-<grupo>-nn` (Entrega 2) e `OPC-nn` (melhorias não exigidas
pelos enunciados). Grupos: `OBJ` objetivo, `EQP` equipamentos, `USR` usuários/perfis, `CMP` funções compartilhadas,
`TEC` técnico, `GES` gestor, `OS` ordens de serviço, `RNF` requisitos técnicos mínimos, `ARQ` arquitetura,
`SOL` SOLID, `PAD` padrões, `FRT` front-end, `PER` persistência, `EXE` execução, `ENT` entregáveis, `DOC` relatório.

**Classificação dos itens** (nunca misturar as quatro):

| Classe | Onde aparece | Significado |
|--------|--------------|-------------|
| **Requisito oficial** | Seções 2 e 3 (`E1-*`, `E2-*`, tipo *Obrigatório*) | Consta nos enunciados das Entregas 1 e 2 |
| **Decisão técnica ou funcional aprovada** | Seção 5 e [`DECISOES_APROVADAS.md`](DECISOES_APROVADAS.md) (`D-nn`) | Decidida pela equipe; orienta a implementação |
| **Melhoria recomendada** | Seção 4 (`OPC-nn`) | Proposta da equipe; não exigida pelos enunciados |
| **Funcionalidade ainda não implementada** | Coluna "Situação" | Qualquer item, de qualquer classe, sem código e teste que o comprovem |

**Tipo:** *Obrigatório* = requisito oficial, consta no enunciado. *Opcional* = melhoria derivada da auditoria ou de
proposta da equipe, não exigida pelos enunciados (seção 4). Autenticação e integridade dos dados (OPC-01, OPC-02) são
tratadas como **necessárias para a solução web proposta**, não como exigências literais dos enunciados.

**Situação atual** (referente ao baseline):
- **Atendido**: comportamento presente na CLI, sem defeito relevante encontrado.
- **Atendido com ressalva**: comportamento presente, mas a auditoria encontrou defeito ou limite a corrigir na migração.
- **Parcial**: existe parte do que o requisito pede.
- **Não atendido**: inexistente ou ainda não demonstrado.
- **Não verificado**: sem evidência de execução nesta auditoria.

**Evidência:** caminhos relativos à raiz do repositório (`models/`, `ui/`, `persistencia/`, `app/`). "Executado" indica
resultado observado na auditoria (ver método em `AUDITORIA_ARQUITETURAL.md`); as demais referências são leitura de código.

**Fases** (nomes e branches em [`ORGANIZACAO_DO_REPOSITORIO.md`](ORGANIZACAO_DO_REPOSITORIO.md), seção 7): 02 domínio e
SOLID; 03 persistência; 04 API e autenticação; 05 front-end base; 06 cadastros; 07 ordens de serviço; 08 dashboard e
histórico; 09 testes e segurança; 10 publicação; 11 documentação final. "02 → 06" significa: regra protegida por teste e
refatorada na Fase 02, entregue na interface web na Fase 06.

## 2. Entrega 1

### 2.1 Objetivo e módulos de cadastro

| ID | Tipo | Fonte e seção | Descrição | Situação | Evidência | Lacuna | Fase | Critério de aceitação |
|----|------|---------------|-----------|----------|-----------|--------|------|-----------------------|
| E1-OBJ-01 | Obrigatório | E1, Objetivo Geral | Gerenciar o ciclo completo de manutenção: abertura da OS, diagnóstico, alocação, acompanhamento de status, intervenções e histórico | Atendido com ressalva | `models/ordem_servico.py:88-192`; ciclo completo executado (11 serviços) | AUD-09, AUD-11, AUD-13 | 02 → 07 | Cenário ponta a ponta (abrir → atribuir → diagnosticar → reparar → concluir → aprovar) automatizado e passando na API e na interface web |
| E1-EQP-01 | Obrigatório | E1, Escopo > Gestão de Equipamentos | Cadastrar equipamentos | Atendido | `ui/tela_equipamentos.py:62-70`; `persistencia/repositorio.py:125` | Só nome e modelo (+ativo); campos extras existem em `app/` (decisão pendente D-07, OPC-06) | 03, 06 | Equipamento criado via API e tela, persistido no banco, com validação de campos obrigatórios |
| E1-EQP-02 | Obrigatório | E1, Escopo > Gestão de Equipamentos | Listar equipamentos | Atendido | `ui/tela_base.py:27-35` | Sem busca nem paginação (não exigidas) | 06 | Listagem com busca e filtro por situação, responsiva |
| E1-EQP-03 | Obrigatório | E1, Escopo > Gestão de Equipamentos | Visualização detalhada do equipamento | Atendido com ressalva | `ui/tela_equipamentos.py:20-31` mostra modelo, situação, OS e histórico | "Detalhes técnicos" mínimos (nome, modelo, situação) | 06 | Tela de detalhe com dados do equipamento, suas OS e linha do tempo de intervenções |
| E1-USR-01 | Obrigatório | E1, Escopo > Controle de Usuários e Perfis | Definir e persistir perfis de acesso e dados cadastrais | Atendido com ressalva | `models/usuario.py:12-19`, `models/cargo.py`, `models/permissoes.py`; `repositorio.py:45-56` | Sem credencial (AUD-01); permissões por string (AUD-03) | 02, 03, 04 | Usuário e perfil persistidos no banco; senha armazenada só como hash; permissões tipadas |
| E1-USR-02 | Obrigatório | E1, Escopo > Controle de Usuários e Perfis | Pelo menos dois tipos de usuário: Técnico e Gestor | Atendido | Cargos fixos Gestor e Técnico: `repositorio.py:58-62` | "Técnico" é derivado de permissão editável no baseline (AUD-20); **D-02 aprovada**: papéis explícitos no domínio (não implementado) | 02, 06 | Papel explícito e independente das permissões: técnico sem a permissão de apontar continua técnico e atribuível; gestor com permissão técnica não vira técnico; teste de acesso indevido entre papéis |

### 2.2 Funções compartilhadas (Gestor e Técnico)

| ID | Tipo | Fonte e seção | Descrição | Situação | Evidência | Lacuna | Fase | Critério de aceitação |
|----|------|---------------|-----------|----------|-----------|--------|------|-----------------------|
| E1-CMP-01 | Obrigatório | E1, Funções Compartilhadas | Visualizar lista e detalhes técnicos dos equipamentos | Atendido com ressalva | `ui/tela_equipamentos.py:10-31`; permissão `ver_equipamentos` só no menu (`ui/aplicacao.py:31`) | Permissão de leitura não imposta no domínio (AUD-02) | 04, 06 | Rotas de leitura exigem usuário autenticado e permissão; teste 401/403 |
| E1-CMP-02 | Obrigatório | E1, Funções Compartilhadas | Consultar OS: filtrar e ver histórico completo e detalhes de OS abertas ou concluídas | Atendido | Filtros: todas, em aberto, encerradas, status, equipamento, técnico, criticidade (`ui/tela_ordens.py:22-43`); detalhe com serviços (`ui/tela_base.py:61-86`) | Sem filtros combinados nem paginação (não exigidos) | 07, 08 | Listagem com os mesmos filtros (e combinados) e detalhe com histórico completo |
| E1-CMP-03 | Obrigatório | E1, Funções Compartilhadas | Abrir chamado apontando falha, criticidade e equipamento afetado | Atendido com ressalva | `models/ordem_servico.py:88-96`; `ui/tela_ordens.py:45-58`; recusa equipamento inativo | Domínio aceitou falha vazia (AUD-12, executado); **validação de entradas aprovada** (mudança de comportamento, não implementada) | 02 → 07 | Abertura exige falha não vazia (nem só espaços), criticidade válida e equipamento ativo; entrada inválida não cria OS nem histórico; erros devolvem 422/409; regra vale na API, independentemente do frontend |
| E1-CMP-04 | Obrigatório | E1, Funções Compartilhadas | Consultar escala e status atual dos técnicos (disponível, em atendimento, ausente) | Atendido com ressalva | `ui/tela_ordens.py:68-74`; `repositorio.py:112-119`; escala é texto livre (`models/usuario.py:12`) | Recalculo só pelo laço da UI (AUD-13, executado); **D-05 aprovada** (só "Em Execução" caracteriza atendimento; não implementada) | 02, 06 | Tela e rota exibem, para cada técnico, a **escala** e o **status** (Disponível, Em atendimento, Ausente) e a carga; status calculado a partir das OS sem rotina de atualização; "Ausente" manual prevalece; os 10 cenários de D-05 passam; acessível a Gestor e Técnico |

### 2.3 Funções exclusivas do Técnico

| ID | Tipo | Fonte e seção | Descrição | Situação | Evidência | Lacuna | Fase | Critério de aceitação |
|----|------|---------------|-----------|----------|-----------|--------|------|-----------------------|
| E1-TEC-01 | Obrigatório | E1, Funções Exclusivas do Técnico | Registrar diagnóstico (parecer inicial e causa-raiz) | Atendido | `models/ordem_servico.py:103-109`; `ui/tela_tecnico.py:15-23`; exige permissão, OS do técnico e status válido | — | 02 → 07 | Só o técnico atribuído registra; status inválido ou OS de outro técnico recusados; entrada no histórico |
| E1-TEC-02 | Obrigatório | E1, Funções Exclusivas do Técnico | Apontar horas, intervenções e peças/materiais | Atendido com ressalva | `ordem_servico.py:111-123`; `models/peca_material.py` valida quantidade > 0 | Domínio aceita 0 h e intervenção vazia (AUD-12, executado); **validação aprovada** (duração > 0; mudança de comportamento, não implementada) | 02 → 07 | Duração estritamente maior que zero e intervenção obrigatória, validadas no servidor; totais da OS somam os apontamentos; histórico registra horas e peças |
| E1-TEC-03 | Obrigatório | E1, Funções Exclusivas do Técnico | Atualizar status para Em Execução, Aguardando Peça ou Reparo Finalizado | Atendido | `ordem_servico.py:125-135`; recusa finalizar sem intervenção | — | 02 → 07 | Tabela de transições testada, positivos e negativos; bloqueio de "Reparo Finalizado" sem intervenção |
| E1-TEC-04 | Obrigatório | E1, Funções Exclusivas do Técnico | Conclusão técnica após testes funcionais, submetendo a OS ao encerramento | Atendido com ressalva | `ordem_servico.py:137-150`; exige diagnóstico; teste reprovado não avança (executado) | Finalizar sem diagnóstico bloqueia diagnóstico e conclusão até voltar o status (AUD-21, executado); **D-06 aprovada** (diagnóstico antes de Reparo Finalizado; não implementada) | 02 → 07 | Reparo Finalizado exige diagnóstico, recusado com erro claro; conclusão exige diagnóstico e resultado de teste; reprovação mantém "Reparo Finalizado"; aprovação leva a "Aguardando Aprovação" |

### 2.4 Funções exclusivas do Gestor

| ID | Tipo | Fonte e seção | Descrição | Situação | Evidência | Lacuna | Fase | Critério de aceitação |
|----|------|---------------|-----------|----------|-----------|--------|------|-----------------------|
| E1-GES-01 | Obrigatório | E1, Funções Exclusivas do Gestor | Cadastrar, editar, inativar ou excluir equipamentos | Atendido com ressalva | `ui/tela_equipamentos.py:34-75`; exclusão bloqueada se houver OS (`repositorio.py:131-134`) | Permissão só na tela e regra de exclusão no repositório (AUD-02, AUD-10, executado) | 02 → 06 | Casos de uso com permissão central; exclusão recusada com OS vinculada (inativar preserva histórico); técnico recebe 403 |
| E1-GES-02 | Obrigatório | E1, Funções Exclusivas do Gestor | Criar, editar e definir níveis de acesso de técnicos e gestores | Atendido com ressalva | `ui/tela_usuarios.py:16-107`; `Permissoes.definir` (`models/permissoes.py:62-65`) | Sem senha; regra "não remover o próprio acesso" só na UI (AUD-01, AUD-09); papel × permissão (AUD-20) | 04, 06 | Gestão de usuários e permissões por API; autoproteção do gestor aplicada no servidor; senha com hash |
| E1-GES-03 | Obrigatório | E1, Funções Exclusivas do Gestor | Atribuir e reatribuir chamados a técnicos, balanceando carga | Atendido com ressalva | `ordem_servico.py:153-170`; `ui/tela_gestor.py:10-31` (ordena por carga) | Alerta de técnico Ausente só na UI (AUD-09, executado); **D-03 aprovada** (recusa por padrão, confirmação explícita no servidor; não implementada) | 02 → 07 | Reatribuição registra "de → para"; atribuir a Ausente sem confirmação é recusado inclusive por chamada direta à API; com confirmação explícita é aceito e registrado; carga exibida |
| E1-GES-04 | Obrigatório | E1, Funções Exclusivas do Gestor | Validar o reparo, cancelar OS indevidas e fechar formalmente | Atendido | `ordem_servico.py:172-192`; `ui/tela_gestor.py:33-63`; reprovação devolve a "Em Execução"; aprovar, reprovar e cancelar usam a **mesma permissão** `aprovar_os` (`:173,180,186`) | Permissão compartilhada entre aprovação e cancelamento (separação não decidida, ver `DECISOES_APROVADAS.md` 6.1) | 02 → 07 | Aprovar, reprovar e cancelar com motivo, só pelo gestor e nos status permitidos; comportamento atual da permissão preservado na caracterização; data de encerramento registrada |

### 2.5 Ordens de serviço

| ID | Tipo | Fonte e seção | Descrição | Situação | Evidência | Lacuna | Fase | Critério de aceitação |
|----|------|---------------|-----------|----------|-----------|--------|------|-----------------------|
| E1-OS-01 | Obrigatório | E1, Ordens de Serviço | Abertura de chamados/OS e detalhamento do problema | Atendido com ressalva | `models/ordem_servico.py:26-58,88-96` | Mesma lacuna de E1-CMP-03 (AUD-12) | 02 → 07 | Idem E1-CMP-03 |
| E1-OS-02 | Obrigatório | E1, Ordens de Serviço | Alocação e atribuição a técnicos disponíveis | Atendido com ressalva | `ui/tela_gestor.py:16,27-29`; `repositorio.py:101-109` | Disponibilidade não verificada no domínio (AUD-09); D-03 e D-05 aprovadas | 02 → 07 | Idem E1-GES-03; regra de disponibilidade (D-05) testada |
| E1-OS-03 | Obrigatório | E1, Ordens de Serviço | Fluxo de alteração e acompanhamento de status | Atendido | `models/enums.py:6-14` (8 status); transições nos métodos de `ordem_servico.py`; documentado em `DOCUMENTACAO.md` §5 | O enunciado cita status de exemplo (Aberto, Em Andamento, Concluído, Cancelado); a implementação usa 8, mais detalhados | 02 → 07 | Máquina de estados explícita, com todas as transições válidas e inválidas cobertas por testes |
| E1-OS-04 | Obrigatório | E1, Ordens de Serviço | Listagem geral e visualização detalhada de cada OS | Atendido | `ui/tela_base.py:38-86`; `ui/tela_ordens.py:11-20` | — | 07 | Listagem e detalhe na API e na tela, com paginação |
| E1-OS-05 | Obrigatório | E1, Ordens de Serviço | Histórico sequencial das intervenções realizadas em cada equipamento/OS e inclusão de novos apontamentos | Atendido com ressalva | `models/servico.py`; `ordem_servico.py:69-73,98-100`; histórico por OS numerado 1..N preservado após recarga (executado); histórico por equipamento em `ui/tela_equipamentos.py:20-31` | Apontamento aceito em OS encerrada e por não dono (AUD-11, executado); **D-04 aprovada** (não implementada); sem consulta de histórico por equipamento na API | 02 → 08 | (a) **Consulta cronológica do histórico de cada OS**, ordenada pelo instante e pelo número sequencial, sem lacunas nem duplicidade; (b) **acesso ao histórico de OS de cada equipamento**; (c) histórico imutável, com autor, data e tipo de cada registro; (d) novos apontamentos bloqueados em OS Concluída ou Cancelada e observação permitida ao autor da abertura (D-04), verificados na API |

### 2.6 Requisitos técnicos mínimos

| ID | Tipo | Fonte e seção | Descrição | Situação | Evidência | Lacuna | Fase | Critério de aceitação |
|----|------|---------------|-----------|----------|-----------|--------|------|-----------------------|
| E1-RNF-01 | Obrigatório | E1, Requisitos Técnicos Mínimos | Persistência de dados obrigatória (banco ou arquivos) | Atendido com ressalva | JSON em `dados/dados.json` (`repositorio.py:45-56`); recarga preserva os dados (executado) | Perda de atualização, colisão de números e formatos conflitantes (AUD-04 a AUD-08) | 03 | Dados no PostgreSQL com migrações; sobrevivem a reinício; testes de integração em banco de teste |
| E1-RNF-02 | Obrigatório | E1, Requisitos Técnicos Mínimos | Entregar o software funcional e executável, demonstrando os fluxos essenciais | Não verificado | Domínio e persistência foram executados por script; a CLI interativa não foi exercitada | Execução da CLI não verificada nesta auditoria | 02 | Teste de fumaça da CLI no baseline antes da refatoração; guia de execução validado do zero (Fase 11) |
| E1-RNF-03 | Obrigatório | E1, Requisitos Técnicos Mínimos | Interface livre: CLI, Web ou Desktop | Atendido | CLI em `ui/` e `main.py` | A Entrega 2 exige interface web (E2-FRT-01) | 05 | Ver E2-FRT-01 |

## 3. Entrega 2

| ID | Tipo | Fonte e seção | Descrição | Situação | Evidência | Lacuna | Fase | Critério de aceitação |
|----|------|---------------|-----------|----------|-----------|--------|------|-----------------------|
| E2-OBJ-01 | Obrigatório | E2, 1. Contexto e Objetivo | Evoluir a Entrega 1 com foco em arquitetura, SOLID, padrões de projeto, coesão, baixo acoplamento, testabilidade e manutenibilidade, mais front-end web | Não atendido | Fase 01 produz apenas a documentação do plano | Implementação inexistente | 02 a 09 | Todos os requisitos E2 abaixo atendidos e evidenciados |
| E2-ARQ-01 | Obrigatório | E2, 2.A | Incorporar os feedbacks da avaliação da Entrega 1 e implementar melhoria significativa de arquitetura | Não atendido | Feedback informado: avaliação positiva, sem correções específicas adicionais (os achados desta auditoria são da equipe) | Melhoria arquitetural ainda não implementada | 02, 03, 04 | Arquitetura em camadas implementada, com testes e ADRs aprovados; registro de qualquer novo feedback recebido |
| E2-SOL-01 | Obrigatório | E2, 2.A | Aplicar Responsabilidade Única (SRP) | Parcial | Separação em `models/`, `ui/`, `persistencia/`; violações em `OrdemServico` e `Repositorio` (AUD-15, AUD-10) | Responsabilidades acumuladas | 02 | Entidades sem serialização nem persistência; repositório sem regra; casos de uso em serviços (ver `PRINCIPIOS_SOLID_E_PADROES.md`) |
| E2-SOL-02 | Obrigatório | E2, 2.A | Aplicar Aberto/Fechado (OCP) | Não atendido | Nova permissão exige editar 3 pontos de `Permissoes` (AUD-03) | Sem pontos de extensão | 02 | Nova permissão ou transição adicionada sem alterar o código existente de controle (demonstrado em teste) |
| E2-SOL-03 | Obrigatório | E2, 2.A | Aplicar Substituição de Liskov (LSP) | Não atendido | Sem hierarquia ou contrato substituível no domínio; **não demonstrado** | Nenhum exemplo concreto; `pytest` e `mypy` só entram na Fase 02 (D-13) | 02, 03 | Suíte de contrato aprovada por duas implementações do repositório (em memória e SQLAlchemy) e `mypy` aprovando ambas contra o `Protocol` |
| E2-SOL-04 | Obrigatório | E2, 2.A | Aplicar Segregação de Interfaces (ISP) | Não atendido | `Repositorio` único e amplo (`repositorio.py`) | Interface única para todos os clientes; **não demonstrado** | 02 | Portas por agregado e por tipo de uso; cada serviço depende só do que usa, verificado por `mypy` e pelos dublês de teste enxutos |
| E2-SOL-05 | Obrigatório | E2, 2.A | Aplicar Inversão de Dependências (DIP) | Parcial | Domínio não importa infraestrutura; `Aplicacao` cria `Repositorio()` direto (`ui/aplicacao.py:19`) | UI e regras dependem do concreto; **não demonstrado** | 02, 04 | Serviços recebem portas por injeção e a raiz de composição é o único ponto que importa as implementações; domínio sem importar `application`, FastAPI ou SQLAlchemy (teste de arquitetura e `mypy`) |
| E2-PAD-01 | Obrigatório | E2, 2.A | Implementar pelo menos 1 padrão de projeto, justificando no relatório a escolha e o problema resolvido | Não atendido | `Repositorio` atual não tem contrato nem implementação alternativa; não conta como padrão demonstrado | Padrão formal inexistente | 02, 03 | Repository (e injeção de dependências) implementados com ao menos duas implementações; relatório com, para cada padrão, **o problema que resolve** (com o achado `AUD-nn` correspondente), **a justificativa da escolha** e **as alternativas consideradas e descartadas** (ver ADR-0004, ADR-0005 e `PRINCIPIOS_SOLID_E_PADROES.md`) |
| E2-ARQ-02 | Obrigatório | E2, 2.A | Aplicar um tipo de arquitetura e apresentar evidências e documentação | Parcial | Três camadas descritas em `DOCUMENTACAO.md` §2; limites não verificados automaticamente | Sem evidência verificável nem limites aplicados | 02 | Arquitetura em camadas documentada (ADR-0002, 0003, 0008) com raiz de composição e verificada por teste de dependências |
| E2-FRT-01 | Obrigatório | E2, 2.B | Interface gráfica web (front-end) totalmente funcional | Não atendido | Inexistente | Todo o front-end | 05 a 08 | Frontend React integrado à API cobrindo os fluxos de Gestor e Técnico |
| E2-FRT-02 | Obrigatório (responsividade); meta técnica da equipe (acessibilidade) | E2, 2.B | Interface responsiva em dispositivos móveis e desktop, com visualização clara, intuitiva e acessível. **Acessibilidade:** a equipe adota **WCAG 2.1 nível AA como meta técnica própria**; o enunciado pede interface "acessível", mas **não cita** WCAG | Não atendido | Inexistente | — | 05, 09 | (a) **Responsividade:** verificada nas larguras 320, 375, 768, 1024 e 1440 px, sem rolagem horizontal. (b) **Acessibilidade (meta WCAG 2.1 AA, ainda não comprovada):** teste de **teclado** (todo fluxo operável sem mouse, sem armadilha de foco); **foco** visível e ordem lógica; **contraste** mínimo 4,5:1 para texto normal e 3:1 para texto grande e componentes; **rótulos** associados a todos os campos e nomes acessíveis nos controles; **verificação automatizada complementar** (ferramenta a definir, parte de D-13), sem substituir os testes manuais; resultados registrados com limitações |
| E2-FRT-03 | Obrigatório | E2, 2.B | Visualização clara, intuitiva e acessível de painéis (Dashboard), listagens de OS e formulários de cadastro | Não atendido | Inexistente | — | 05, 06, 07, 08 | **Painel mínimo funcional** com: (1) contagem de OS **por status**; (2) contagem de OS **por criticidade**; (3) **OS atribuídas ao técnico** que consulta (visão do Técnico); (4) **visão de carga de trabalho dos técnicos** para o Gestor (OS ativas e status de disponibilidade de cada técnico). Valores calculados no servidor e coerentes com os dados persistidos; estado vazio tratado; painel legível em 320 px. Listagens e formulários atendem aos critérios de acessibilidade de E2-FRT-02. O conceito de OS "atrasada" **não** faz parte do painel mínimo (D-15 pendente) |
| E2-PER-01 | Obrigatório | E2, 2.C | Persistência mantida e desacoplada da regra de negócio (ex.: Repository ou camadas definidas) | Parcial | `Repositorio` isola o arquivo, mas contém regras e é instanciado pela UI (AUD-10, AUD-16) | Acoplamento e regras no repositório | 02, 03 | Regras fora do repositório; troca JSON → PostgreSQL sem alterar domínio nem serviços |
| E2-EXE-01 | Obrigatório | E2, 2.C | Software totalmente funcional e executável, com instruções claras de execução e acesso à interface | Parcial | `README.md` cobre apenas a CLI | Guia para backend, banco e frontend | 11 (validado em 09) | Comandos do guia executados do zero em ambiente limpo, com resultado registrado |
| E2-ENT-01 | Obrigatório | E2, 3.1 | Código-fonte completo e organizado, com camadas separadas | Parcial | Estrutura atual: `ORGANIZACAO_DO_REPOSITORIO.md` | Camadas atuais misturam regras (AUD-09, AUD-10) | 02 a 06 | Estrutura de diretórios por camada, sem dependências invertidas |
| E2-DOC-01 | Obrigatório | E2, 3.2 | Relatório: arquitetura utilizada e justificativa técnica | Parcial | ADRs desta fase (`docs/adr/`) | Relatório final consolidado | 11 | `docs/RELATORIO_TECNICO.md` com arquitetura e justificativa |
| E2-DOC-02 | Obrigatório | E2, 3.2 | Relatório: onde e como SOLID e padrões foram aplicados, com trechos ou diagramas | Não atendido | Plano em `PRINCIPIOS_SOLID_E_PADROES.md` (intenção, não implementação) | Aplicação real inexistente | 11 (após 02 a 04) | Cada princípio e padrão com arquivo, linha e teste reais; para cada padrão adotado, a **justificativa da escolha**, o **problema do sistema que resolve** e as **alternativas consideradas** (inclusive as descartadas: State, Strategy, Observer); nenhum princípio declarado sem a evidência listada na seção 3 de `PRINCIPIOS_SOLID_E_PADROES.md` |
| E2-DOC-03 | Obrigatório | E2, 3.2 | Relatório: o que foi implementado (melhorias, módulos, novo front-end) | Não atendido | — | — | 11 | Comparativo Entrega 1 × Entrega 2 por requisito, com capturas reais |
| E2-DOC-04 | Obrigatório | E2, 3.2 | Relatório: versionamento (branches, commits, evidências) | Parcial | Fluxo em `FLUXO_DE_DESENVOLVIMENTO.md`; fases com merge `--no-ff`; tag `entrega-1` | Histórico completo só ao final | 11 | Lista de branches, SHAs de merge e convenções, conferida com `git log` |
| E2-DOC-05 | Obrigatório | E2, 3.2 | Relatório: guia de execução passo a passo | Não atendido | — | — | 11 | Ver E2-EXE-01 |

## 4. Melhorias opcionais (não exigidas pelos enunciados)

Propostas da equipe, derivadas da auditoria. Podem ser ajustadas sem descumprir os enunciados, mas várias são
pré-condição técnica para a aplicação web (por exemplo, não é possível expor a API com segurança sem autenticação):
OPC-01 e OPC-02 são **necessárias para a solução web proposta**, e não exigências literais dos enunciados.

| ID | Tipo | Origem | Descrição | Situação | Lacuna | Fase | Critério de aceitação |
|----|------|--------|-----------|----------|--------|------|-----------------------|
| OPC-01 | Opcional (necessária para a solução web) | AUD-01, AUD-02, D-01 pendente | Autenticação com senha em hash, sessão com expiração e autorização no servidor | Não atendido | Login por ID | 04 | 401/403 testados; senhas só em hash; nenhum segredo em log |
| OPC-02 | Opcional (necessária para a solução web) | AUD-04, AUD-05 | Concorrência e integridade transacional (controle otimista, sequências do banco) | Não atendido | Perda de atualização e colisão (executados) | 03, 07 | Teste de duas escritas concorrentes: a segunda recebe conflito, nenhum dado é perdido |
| OPC-03 | Opcional (recomendada) | AUD-17, D-13; E2-OBJ-01 (testabilidade) | Testes automatizados, análise estática e integração contínua | Não atendido | Nenhum teste versionado; ferramentas não instaladas | 02, 09 | `pytest`, `ruff` e `mypy` e testes de caracterização na Fase 02; pipeline verde na Fase 09 |
| OPC-04 | Opcional | Arquitetura aprovada | API REST versionada com documentação OpenAPI | Não atendido | Inexistente | 04 | Contrato OpenAPI gerado e coberto por testes |
| OPC-05 | Opcional | Proposta da equipe | Trilha de auditoria imutável e indicadores calculados no backend | Não atendido | Histórico existe só por OS | 08 | Linha do tempo sem duplicidade; fórmulas dos indicadores documentadas e testadas |
| OPC-06 | Opcional | `app/`, D-07 pendente | Campos extras de equipamento (fabricante, nº de série, setor, data de aquisição) | Não atendido | Decisão pendente | Decidir antes da 03; implementar na 03 ou 06 | Decisão registrada; se adotado, campos opcionais no modelo, API e tela |
| OPC-07 | Opcional | Proposta da equipe, D-08 pendente | Importação dos dados JSON existentes para o banco | Não atendido | Decisão e autorização pendentes | 03 | Importação idempotente com dry-run, contagens e reversão, executada **somente com autorização específica** |
| OPC-08 | Opcional | Proposta da equipe, D-09 pendente | Publicação em ambiente de produção | Não atendido | Hospedagem não decidida | 10 | URLs verificadas e persistência real, **somente com autorização específica** |
| OPC-09 | Opcional (melhoria aprovada) | AUD-12 | Validação de entradas no servidor: campos obrigatórios, números válidos, duração > 0 | Não atendido | O baseline aceita entradas vazias e zero hora (executado) | 02, 04 | Entrada inválida recusada sem criar registro nem histórico, pela API e pelo domínio; delta de comportamento registrado |
| OPC-10 | Opcional (melhoria aprovada) | AUD-08, AUD-10 | Desativação de usuários (`ativo`), sem excluir o histórico; inativos não autenticam nem operam | Não atendido | Campo inexistente; política para OS atribuídas a inativos **não decidida** | 02, 03, 06 | Usuário inativo recusado em login e operações; referências históricas preservadas; nenhuma reatribuição automática |

## 5. Decisões aprovadas e requisitos que elas afetam

Referência: [`DECISOES_APROVADAS.md`](DECISOES_APROVADAS.md). Todas **aprovadas**. D-02 a D-06, a validação de entradas e a
desativação de usuários foram **implementadas no novo backend** na Operação E (DLT-01 a DLT-06, DLT-08 e DLT-09, seção 8
daquele documento); as demais seguem não implementadas. A coluna "Situação" das seções 1 a 4 continua descrevendo o
**baseline** (a CLI legada não foi alterada).

| Decisão | Requisitos afetados | Fase |
|---------|---------------------|------|
| D-02 Papéis | E1-USR-02, E1-GES-02 | 02 (**DLT-01** implementado) |
| D-03 Técnico Ausente | E1-GES-03, E1-OS-02 | 02 (**DLT-02** implementado) |
| D-04 Apontamentos e observações | E1-OS-05, E1-TEC-02 | 02 (**DLT-03** e **DLT-04** implementados) |
| D-05 Disponibilidade | E1-CMP-04, E1-OS-02 | 02 (**DLT-05** implementado) |
| D-06 Diagnóstico | E1-TEC-04, E1-TEC-03 | 02 (**DLT-06** implementado) |
| D-11 Datas e fuso | E1-RNF-01, E1-OS-05 | 02 |
| D-13 Ferramentas de qualidade | E2-SOL-03, E2-SOL-04, E2-SOL-05, OPC-03 | 02 |
| D-14 Estrutura do backend | E2-ENT-01, E2-ARQ-02 | 02 |
| D-10 CLI e legado preservados; interface principal web | E2-ENT-01, E2-FRT-01, E1-RNF-03 | 02 (convivência) |
| Validação de entradas | E1-CMP-03, E1-TEC-02, OPC-09 | 02 (**DLT-08** implementado no domínio e nos serviços), 04 |
| Desativação de usuários | E1-GES-02, OPC-10 | 02 (**DLT-09** implementado no modelo e nos serviços), 03, 06 |

Pendentes (sem efeito sobre a situação dos requisitos até serem decididas): D-01 (OPC-01), D-07 (OPC-06), D-08 (OPC-07),
D-09 (OPC-08), D-12 (E1-RNF-01, OPC-02), D-15 (E2-FRT-03).

## 6. Resumo da cobertura (baseline)

| Grupo | Total | Atendido | Atendido com ressalva | Parcial | Não atendido | Não verificado |
|-------|-------|----------|-----------------------|---------|--------------|----------------|
| Entrega 1 (obrigatórios) | 26 | 10 | 15 | 0 | 0 | 1 |
| Entrega 2 (obrigatórios) | 20 | 0 | 0 | 8 | 12 | 0 |
| Opcionais | 10 | — | — | — | 10 | — |

Leitura: a Entrega 1 está funcionalmente presente na CLI, com 15 requisitos que exigem correção durante a migração
(`ressalva`) e um sem verificação de execução da CLI; a Entrega 2 está essencialmente por fazer, como esperado no início
da Fase 01. Esta tabela descreve o **estado do baseline**, não o resultado das fases futuras.
