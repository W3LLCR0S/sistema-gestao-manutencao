# Plano de migração incremental

Roteiro para evoluir a Entrega 1 (CLI com JSON) até a aplicação web da Entrega 2, alinhado às fases já definidas no
repositório (ver [`ORGANIZACAO_DO_REPOSITORIO.md`](ORGANIZACAO_DO_REPOSITORIO.md), seção 7). É um **plano**: nada aqui
está implementado, e cada fase só começa após plano aprovado e termina com merge autorizado, conforme
[`FLUXO_DE_DESENVOLVIMENTO.md`](FLUXO_DE_DESENVOLVIMENTO.md).

Base do plano: [`AUDITORIA_ARQUITETURAL.md`](AUDITORIA_ARQUITETURAL.md),
[`MATRIZ_RASTREABILIDADE.md`](MATRIZ_RASTREABILIDADE.md), [`adr/`](adr/README.md),
[`PRINCIPIOS_SOLID_E_PADROES.md`](PRINCIPIOS_SOLID_E_PADROES.md), [`DIAGRAMAS.md`](DIAGRAMAS.md) e
[`DECISOES_APROVADAS.md`](DECISOES_APROVADAS.md). Não há datas: o cronograma depende do prazo de entrega, que não
consta nesta documentação. Os prazos das decisões são expressos como **fase antes da qual** cada uma deve estar
resolvida (seção 5).

## 1. Princípios da migração

1. **Preservar antes de mudar.** Testes de caracterização do comportamento da Entrega 1 vêm antes de qualquer
   refatoração (ADR-0006).
2. **Uma camada por vez, sempre executável.** A CLI legada continua intacta e executável durante a Fase 02; seu
   descarte é decisão posterior (D-10). O código novo nasce em `backend/src/manutencao/` (D-14) sem alterar o legado.
3. **Regra em um só lugar.** Cada regra que hoje está na UI ou no repositório (AUD-09, AUD-10) é movida para domínio
   ou aplicação, com teste, antes de ser exposta na API.
4. **Sem dados reais em testes ou migração automática.** Importação de dados reais exige plano idempotente, *backup*,
   simulação e autorização específica (OPC-07).
5. **Intocáveis nesta documentação:** a tag `entrega-1`, o diretório `app/` e o formato de `dados/dados.json` local.
6. **Mudança funcional separada de refatoração.** Cada decisão aprovada (D-02 a D-06, validações, desativação) é
   aplicada em passo próprio, depois de a refatoração preservar o comportamento caracterizado.
7. **Datas:** novas implementações usam datas com fuso em UTC (D-11, já aprovada); a conversão de dados legados é
   futura e só ocorre antes da migração de dados, com autorização específica.

### Destino futuro dos módulos legados

| Módulo | Situação durante a migração | Destino proposto | Condição |
|--------|-----------------------------|------------------|----------|
| `main.py`, `ui/` | Preservados e executáveis | Remover ou manter como referência | D-10 e autorização específica |
| `models/` | Preservado como referência de comportamento | Substituído por `domain/` | Paridade comprovada por caracterização |
| `persistencia/` | Preservado | Não vira implementação final | D-10 |
| `app/` | Preservada, não utilizada | Avaliar aproveitamento (OPC-06); remoção só com autorização | D-10 |
| `dados/` | Local, ignorado pelo Git | Nunca versionado nem usado em testes | — |

Detalhes e justificativa em [ADR-0008](adr/0008-estrutura-do-backend-e-convivencia-com-o-legado.md).

## 2. Visão geral

| Fase | Branch | Entrega principal | Depende de |
|------|--------|-------------------|------------|
| 01 | `docs/auditoria` | Auditoria, matriz, ADRs, diagramas e este plano (documentação) | Fase 00 |
| 02 | `refactor/arquitetura` | `pytest`, `ruff` e `mypy`; testes de caracterização; novo pacote `manutencao`; portas; serviços; domínio sem acoplamentos; SOLID; decisões D-02 a D-06 | 01 aprovada |
| 03 | `feat/persistencia` | PostgreSQL, SQLAlchemy, Alembic, repositórios concretos, plano de importação | 02 |
| 04 | `feat/api-autenticacao` | API FastAPI `/api/v1`, autenticação com hash, autorização no servidor | 02, 03 |
| 05 | `feat/frontend-base` | SPA React, login, estrutura, componentes, responsividade e acessibilidade base | 04 |
| 06 | `feat/gestao-cadastros` | Equipamentos, usuários, papéis/permissões e disponibilidade | 04, 05 |
| 07 | `feat/ordens-servico` | Ciclo completo da OS, máquina de estados, concorrência | 04, 05, 06 |
| 08 | `feat/dashboard-historico` | Dashboard, filtros combinados, paginação, linha do tempo imutável | 07 |
| 09 | `test/qualidade` | Testes E2E, análise estática, CI, revisão de segurança e acessibilidade | 02 a 08 |
| 10 | `deploy/producao` | Publicação e validação em produção (**opcional**, exige autorização) | 09 |
| 11 | `docs/entrega-final` | README, relatório técnico, evidências e checklist de entrega | 02 a 09 |

A **integração** entre frontend e API acontece de forma contínua nas Fases 05 a 08 (cada tela consome rotas reais; sem
dados simulados como se fossem de produção) e é validada de ponta a ponta na Fase 09.

## 3. Detalhamento por fase

### Fase 02 — Testes de caracterização e domínio (`refactor/arquitetura`)

**Objetivo:** estruturar o domínio e a aplicação conforme ADR-0002, 0003, 0004 e 0005, em `backend/src/manutencao/`
(D-14), preservando o comportamento exigido pela Entrega 1 e aplicando, **depois e em separado**, as mudanças aprovadas.

**Atividades (nesta ordem):**
1. **Ferramentas (D-13):** introduzir `pytest`, `ruff` e `mypy` e um manifesto mínimo de dependências. Nenhuma ferramenta é
   instalada antes da Fase 02.
2. **Caracterizar** o comportamento atual (ADR-0006, seção 3): cada transição de status válida e inválida, permissões por
   cargo, posse da OS pelo técnico, histórico sequencial, regras de inativação e exclusão de equipamento e usuário,
   disponibilidade, aprovação, reprovação e cancelamento. Converter o script de verificação da auditoria em testes. Usar
   uma **fachada estável** para que os mesmos testes valham para o legado e para o novo domínio. Marcar explicitamente
   como **comportamento atual** as divergências AUD-09, AUD-11, AUD-12, AUD-13 e AUD-21. Incluir um teste de fumaça da CLI
   (E1-RNF-02).
3. **Refatorar preservando comportamento:** novo domínio sem serialização; permissões tipadas, tabela de transições,
   hierarquia de erros e datas com fuso (D-11); porta `Relogio` na aplicação, com o instante entregue ao domínio;
   comparação de entidades por ID.
4. **Portas de repositório** (`Protocol`) por agregado e implementação **em memória**. O adaptador JSON de transição é
   **condicional** a D-10 (ver seção 5): só será criado se a CLI passar a usar os novos serviços.
5. **Serviços de aplicação** com autorização central e **raiz de composição** separada (ADR-0005).
6. **Aplicar as mudanças aprovadas, uma por vez**, cada uma com seu teste substituindo o de caracterização e registrada
   como delta: D-02 (papéis), D-03 (técnico ausente), D-04 (observações e apontamentos), D-05 (disponibilidade),
   D-06 (diagnóstico), validação de entradas (AUD-12, **mudança de comportamento aprovada**) e campo `ativo` do usuário.
7. **Teste de arquitetura** de importações e **suíte de contrato** dos repositórios.

**Critérios de aceitação:** testes de caracterização passam no baseline **antes** da refatoração e depois dela; cada
mudança aprovada tem teste próprio e delta registrado; `ruff` e `mypy` sem erros nos pacotes novos; o legado continua
executável; `domain` e `application` sem importar *frameworks* nem persistência concreta e `domain` sem importar
`application`; evidência de SRP, ISP, DIP e do padrão Repository conforme `PRINCIPIOS_SOLID_E_PADROES.md`.

**Riscos:** regressão silenciosa de regra (mitigação: caracterização prévia e mudanças separadas); refatoração excessiva
(mitigação: só abstrair com problema concreto); testes acoplados ao legado perderem validade (mitigação: fachada estável,
ADR-0006); escopo ampliado se a CLI for adaptada (mitigação: decisão D-10 antes de iniciar).

**Decisões que condicionam esta fase:** D-10 (CLI e adaptador JSON). As demais pendências não a bloqueiam.

### Fase 03 — Persistência (`feat/persistencia`)

**Objetivo:** substituir o JSON por PostgreSQL atrás das mesmas portas.

**Atividades:** modelar tabelas (usuários, cargos/permissões, equipamentos, OS, serviços, peças); mapeamento
SQLAlchemy 2 com mapeadores explícitos; migrações Alembic; repositórios concretos; transações e controle otimista de
versão (ADR-0004); configuração por variáveis de ambiente (nenhuma URL ou senha no código; modelo `.env.example` sem
valores); *seeds* de demonstração isolados; **plano** de importação idempotente e reversível do JSON existente, com
*dry-run* e contagens, sem executá-lo sobre dados reais.

**Critérios de aceitação:** migrações aplicáveis em banco de teste; suíte de contrato passando para memória **e**
SQLAlchemy; teste de duas escritas concorrentes sem perda de dados; *rollback* de migração documentado.

**Riscos:** perda de dados reais (mitigação: importação só com autorização, *backup* confirmado e simulação); diferenças
entre ambiente local e produção (mitigação: testar contra PostgreSQL, não outro banco); datas legadas sem fuso.

**Datas:** o tipo de data já está decidido (D-11: instantes em UTC, exibição em America/Sao_Paulo) e o esquema nasce com
`timestamp with time zone`. A **conversão dos dados legados** (`dd/mm/aaaa hh:mm`, sem fuso) permanece futura: antes de
qualquer importação é preciso definir o fuso presumido das datas existentes e o tratamento de horários ambíguos; **nenhuma
conversão é executada** sem a autorização específica de migração de dados.

**Dependências:** decidir D-07 (campos extras de equipamento), D-08 (importação dos dados) e D-12 (provisionamento do
PostgreSQL de desenvolvimento e de teste) antes do início da fase.

### Fase 04 — API e autenticação (`feat/api-autenticacao`)

**Objetivo:** expor os casos de uso por API versionada, com identidade verificada e autorização no servidor.

**Atividades:** FastAPI em `/api/v1`; esquemas Pydantic; tradução de erros conforme ADR-0003 (401/403/404/409/422);
OpenAPI; login com **senha em hash seguro**, sessão ou token com expiração; autorização por papel e permissão nos
serviços; CORS restrito por ambiente; nada de senhas ou tokens em *logs*; rotas de equipamentos, usuários,
disponibilidade e OS usando serviços (nunca o ORM direto).

**Critérios de aceitação:** contrato OpenAPI gerado; testes de 401/403, isolamento de papéis, entrada inválida e fluxos
principais; nenhuma rota administrativa sem autenticação.

**Riscos:** falhas de segurança de autenticação (mitigação: revisão na Fase 09, sem implementar criptografia própria);
política de contas iniciais indefinida (D-01).

**Aprovação específica necessária antes da fase:** política de contas iniciais, redefinição de senha e formato da sessão
(D-01). Usuários inativos não autenticam (desativação aprovada). Autenticação e controle de integridade são necessários
para a solução web proposta; não são exigências literais do enunciado.

### Fase 05 — Frontend base (`feat/frontend-base`)

**Objetivo:** SPA responsiva e acessível, integrada à autenticação.

**Atividades:** projeto React + TypeScript + Vite + Tailwind; rotas; cliente HTTP tipado; estados de carregamento, erro e
vazio; login, estrutura de navegação (desktop e mobile), componentes reutilizáveis e *tokens* visuais; proposta de
*wireframes* para aprovação visual antes de codificar.

**Critérios de aceitação:** funciona nas larguras 320, 375, 768, 1024 e 1440 px sem rolagem horizontal; foco visível,
navegação por teclado, rótulos e contraste verificados; login integrado; rotas protegidas.

**Riscos:** retrabalho visual (mitigação: aprovação dos *wireframes*); dados simulados confundidos com reais (mitigação:
sinalizar *placeholders*).

### Fase 06 — Cadastros (`feat/gestao-cadastros`)

**Atividades:** equipamentos (listar, buscar, detalhar, criar, editar, inativar), usuários, papéis fixos Gestor e Técnico
com edição de permissões, disponibilidade e carga dos técnicos (preservando "Ausente" manual); confirmação antes de
exclusão e bloqueio de remoção de registros referenciados.

**Critérios de aceitação:** fluxos completos com testes de permissão (técnico acessando rotas de gestor recebe 403) e
layout responsivo; histórico íntegro após inativações.

**Atividades adicionais aprovadas:** desativar e reativar usuários sem excluir o histórico (campo `ativo`); decidir a
política para OS ainda atribuídas a usuário desativado, **sem reatribuição automática inventada** (pendência registrada em
`DECISOES_APROVADAS.md`, seção 5.2).

**Riscos:** persistência do papel definido em D-02 (aprovada) e sua migração; campos extras de equipamento (D-07, decidir
antes da Fase 03); OS atribuídas a usuário desativado.

### Fase 07 — Ordens de serviço (`feat/ordens-servico`)

**Atividades:** abertura, listagem, filtros e detalhe; atribuição e reatribuição; diagnóstico, horas, peças,
intervenções e status; conclusão técnica separada da aprovação administrativa; reprovação devolvendo à execução;
cancelamento; registro de autor e instante de cada transição; testes de concorrência, requisições duplicadas e integridade
transacional.

**Critérios de aceitação:** fluxo Gestor/Técnico ponta a ponta, com testes positivos e negativos para cada transição da
tabela de estados; reparo sem atribuição válida, finalização sem intervenção, conclusão sem diagnóstico e avanço após
teste reprovado impedidos; conflito de versão devolve 409 sem perda de dados.

**Riscos:** regressão das regras D-03 a D-06, já **aprovadas** e previstas para a Fase 02, ao expô-las na API
(mitigação: testes de API que repetem os cenários de `DECISOES_APROVADAS.md`, inclusive chamadas sem a confirmação de
técnico ausente e observações em OS encerrada).

### Fase 08 — Dashboard e histórico (`feat/dashboard-historico`)

**Atividades:** painel por perfil (OS abertas, atrasadas, por criticidade e status; técnicos e carga); linha do tempo
imutável sem duplicidade; filtros combinados, paginação e indicadores calculados no backend; fórmulas documentadas e
testadas com dados conhecidos; tratamento de base vazia; gráficos e tabelas legíveis em tela pequena.

**Critérios de aceitação:** indicadores coerentes com os dados persistidos; histórico íntegro; painel responsivo e testado.

**Riscos:** definição de "atrasada" sem regra existente (D-15, pendente: decidir antes da fase; não há prazo/SLA no modelo
atual e nenhum será introduzido sem decisão); datas como texto (tipos com fuso definidos pela D-11 e implementados a partir
da Fase 02).

### Fase 09 — Testes e qualidade (`test/qualidade`)

**Atividades:** testes de integração e ponta a ponta dos fluxos Gestor e Técnico (os testes unitários, de aplicação,
`ruff` e `mypy` já existem desde a Fase 02); integração contínua com jobs separados para API e frontend; auditoria de
segredos, dependências, CORS, *logs*, validação de entrada, sessões e migrações; verificação de responsividade e de
acessibilidade (teclado, foco, contraste, rótulos e verificação automatizada complementar, meta WCAG 2.1 AA da equipe).

**Critérios de aceitação:** CI verde; testes reproduzíveis; checklist de qualidade e segurança com evidências e
limitações reais.

**Riscos:** ferramenta E2E, ferramentas de frontend além de Vitest, verificação automatizada de acessibilidade e metas de
cobertura ainda indefinidas (parte de D-13, a decidir nas fases correspondentes); correção de defeitos descobertos sem
ampliar escopo.

### Fase 10 — Publicação (`deploy/producao`) — opcional

**Atividades:** frontend (Vercel é uma opção) com variável pública de URL da API; hospedagem compatível com FastAPI e
PostgreSQL gerenciado; CORS, HTTPS, verificação de saúde, migrações de produção, observabilidade básica; teste de fumaça
real de login, OS e persistência entre sessões.

**Critérios de aceitação:** URLs verificadas, persistência real, fluxo crítico em produção e guia de reversão.

**Aprovações específicas necessárias:** provedores, planos e custos (D-09); qualquer criação de recurso pago, publicação
e migração no banco de produção.

**Riscos:** custos, limites de execução do provedor (não presumir processo persistente em plataformas *serverless*),
vazamento de segredos.

### Fase 11 — Documentação final (`docs/entrega-final`)

**Atividades:** `README.md` com stack real, pré-requisitos, *setup*, variáveis, testes e execução; relatório técnico com
arquitetura, SOLID demonstrado por arquivo e linha reais, Repository, diagramas e decisões; comparativo Entrega 1 × 2 por
requisito (com capturas reais); registro de *branches*, SHAs de merge e convenções; todos os comandos do guia executados
do zero; checklist de entrega e limitações sem omissões.

**Critérios de aceitação:** README reproduzível, relatório completo, histórico Git verificável e nenhuma afirmação não
verificada.

## 4. Riscos transversais

| ID | Risco | Probabilidade | Impacto | Mitigação |
|----|-------|---------------|---------|-----------|
| R-01 | Regressão funcional na refatoração | Média | Alto | Caracterização antes de mudar; CI |
| R-02 | Perda ou corrupção de dados reais | Baixa | Alto | Sem migração automática; *backup*, *dry-run* e autorização específica |
| R-03 | Escopo grande (backend, frontend, banco, CI, deploy) para o prazo | Alta | Alto | Fases curtas e verticais; deploy opcional; priorizar requisitos obrigatórios da matriz |
| R-04 | Abstração excessiva ("padrões para aumentar quantidade") | Média | Médio | Só adotar padrão com problema concreto (seção 2.2 de `PRINCIPIOS_SOLID_E_PADROES.md`) |
| R-05 | Falha de segurança na autenticação | Média | Alto | Bibliotecas consolidadas, sem criptografia própria; testes 401/403; revisão na Fase 09 |
| R-06 | Concorrência e integridade na API | Média | Alto | Versão otimista e transações; teste de escritas concorrentes |
| R-07 | Decisões pendentes (D-10, D-07, D-08, D-12, D-01, D-15) retardando fases | Média | Médio | Cada decisão tem fase-limite na seção 5.2; D-10 precisa ser resolvida antes da Fase 02 |
| R-08 | Ambiente PostgreSQL inconsistente entre máquinas e CI | Média | Médio | Decidir D-12 antes da Fase 03 |
| R-09 | Legado (`main.py`, `models/`, `app/`) e novo pacote confundirem a manutenção | Média | Médio | Manter o legado intocado até decisão (D-10); todo código novo vai para `backend/src/manutencao/` (ADR-0008) |
| R-10 | Documentação diverge do código | Média | Médio | Marcar tudo como planejado ou implementado; validar comandos na Fase 11 |
| R-11 | Custos e limites de hospedagem | Média | Médio | Decisão e aprovação prévia (Fase 10 é opcional) |

## 5. Decisões: aprovadas e pendentes

Fonte detalhada: [`DECISOES_APROVADAS.md`](DECISOES_APROVADAS.md). Aprovar uma decisão **não** é implementá-la: as
aprovadas orientam as fases indicadas. Cada decisão pendente tem uma fase **antes da qual** deve estar resolvida; a coluna
considera a fase em que o primeiro artefato dependente nasce, e não a fase em que a decisão é usada por último.

### 5.1 Aprovadas

| ID | Decisão | Implementação |
|----|---------|---------------|
| D-02 | Gestor e Técnico são papéis explícitos; permissões continuam configuráveis | Fase 02 |
| D-03 | Atribuição a Técnico Ausente recusada por padrão; confirmação explícita validada na aplicação | Fase 02 (regra), 04 (API) |
| D-04 | Bloquear apontamentos em OS Concluída ou Cancelada; observações pelo autor da abertura; operações distintas | Fase 02 |
| D-05 | Disponibilidade calculada a partir das OS Em Execução; ausência manual separada e prevalecente | Fase 02 |
| D-06 | Diagnóstico obrigatório antes de Reparo Finalizado | Fase 02 |
| D-11 | Datas com fuso, UTC no armazenamento, America/Sao_Paulo na exibição; conversão de dados legados futura | Fase 02 (tipos); conversão antes da migração de dados |
| D-13 | `pytest`, `ruff` e `mypy` a partir da Fase 02; frontend e E2E nas fases correspondentes | Fase 02 |
| D-14 | Pacote `backend/src/manutencao/`; legado preservado; migração gradual | Fase 02 |
| — | Validação de entradas no servidor (mudança de comportamento aprovada, AUD-12) | Fases 02 e 04 |
| — | Campo `ativo` e desativação de usuários, sem política automática de reatribuição | Fases 02, 03 e 06 |

### 5.2 Pendentes

Nenhuma é considerada aprovada. As recomendações são propostas da equipe.

| ID | Decisão | Origem | Necessária antes de | Observação |
|----|---------|--------|---------------------|------------|
| D-10 | CLI sobre os novos serviços e adaptador JSON de transição? Futuro de `app/` | AUD-18 | **Fase 02** (parte CLI); após a Fase 04 (remoções) | **Dependência imediata** da Fase 02. Recomendação: legado intacto, sem adaptador JSON nem CLI nova |
| D-07 | Incluir campos extras de equipamento (fabricante, nº de série, setor, data de aquisição) | OPC-06 | Fase 03 (esquema do banco) | Evolução aditiva; não bloqueia a Fase 02 |
| D-08 | Importar os dados JSON existentes? Destino do `dados/dados.json` local | OPC-07, AUD-06 | Fase 03 | Exige autorização específica e a conversão de datas |
| D-12 | Provisionamento do PostgreSQL de desenvolvimento, teste e CI | ADR-0006 | Fase 03 | Fase 02 usa só repositórios em memória |
| D-01 | Sessão ou token, política de senha inicial, contas iniciais, recuperação | AUD-01 | Fase 04 | Aprovação específica |
| D-15 | Definição de OS "atrasada" e prazos | Dashboard (E2-FRT-03) | Fase 08 | Sem prazo no modelo atual |
| D-09 | Hospedagem da API e do PostgreSQL, plano e custos | ADR-0001 | Fase 10 | Fase opcional |

Decisões ainda abertas **dentro** de D-13: ferramenta E2E, ferramentas de frontend além de Vitest, verificação
automatizada de acessibilidade e metas de cobertura (Fases 05 e 09).

Pontos sem identificador, também **não decididos**: separação das permissões de aprovar e cancelar
(`DECISOES_APROVADAS.md`, seção 6.1) e política para OS atribuídas a usuários desativados (seção 5.2 do mesmo documento).

## 6. Rastreio de fases e requisitos

Cada requisito obrigatório está associado a uma ou mais fases na [matriz](MATRIZ_RASTREABILIDADE.md). Uma fase só é
considerada concluída quando os critérios de aceitação acima forem cumpridos **e** a matriz for atualizada com a situação
real e a evidência (arquivo, linha e teste) de cada requisito tocado.
