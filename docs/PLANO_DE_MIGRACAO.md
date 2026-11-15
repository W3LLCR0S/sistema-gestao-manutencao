# Plano de migração incremental

Roteiro para evoluir a Entrega 1 (CLI com JSON) até a aplicação web da Entrega 2, alinhado às fases já definidas no
repositório (ver [`ORGANIZACAO_DO_REPOSITORIO.md`](ORGANIZACAO_DO_REPOSITORIO.md), seção 7). É um **plano**: nada aqui
está implementado, e cada fase só começa após plano aprovado e termina com merge autorizado, conforme
[`FLUXO_DE_DESENVOLVIMENTO.md`](FLUXO_DE_DESENVOLVIMENTO.md).

Base do plano: [`AUDITORIA_ARQUITETURAL.md`](AUDITORIA_ARQUITETURAL.md),
[`MATRIZ_RASTREABILIDADE.md`](MATRIZ_RASTREABILIDADE.md), [`adr/`](adr/README.md),
[`PRINCIPIOS_SOLID_E_PADROES.md`](PRINCIPIOS_SOLID_E_PADROES.md) e [`DIAGRAMAS.md`](DIAGRAMAS.md). Não há datas: o
cronograma depende do prazo de entrega, que não consta nesta documentação.

## 1. Princípios da migração

1. **Preservar antes de mudar.** Testes de caracterização do comportamento da Entrega 1 vêm antes de qualquer
   refatoração (ADR-0006).
2. **Uma camada por vez, sempre executável.** A CLI continua funcionando durante a Fase 02; seu descarte é decisão
   posterior (D-10).
3. **Regra em um só lugar.** Cada regra que hoje está na UI ou no repositório (AUD-09, AUD-10) é movida para domínio
   ou aplicação, com teste, antes de ser exposta na API.
4. **Sem dados reais em testes ou migração automática.** Importação de dados reais exige plano idempotente, *backup*,
   simulação e autorização específica (OPC-07).
5. **Intocáveis nesta documentação:** a tag `entrega-1`, o diretório `app/` e o formato de `dados/dados.json` local.

## 2. Visão geral

| Fase | Branch | Entrega principal | Depende de |
|------|--------|-------------------|------------|
| 01 | `docs/auditoria` | Auditoria, matriz, ADRs, diagramas e este plano (documentação) | Fase 00 |
| 02 | `refactor/arquitetura` | Testes de caracterização; portas; serviços; domínio sem acoplamentos; SOLID | 01 aprovada |
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

**Objetivo:** estruturar o domínio e a aplicação conforme ADR-0002, 0003, 0004 e 0005 sem alterar o comportamento exigido
pela Entrega 1.

**Atividades:**
1. **Testes de caracterização primeiro** (`pytest`), cobrindo: cada transição de status válida e inválida, permissões por
   cargo, posse da OS pelo técnico, histórico sequencial, regras de inativação e exclusão de equipamento e usuário,
   disponibilidade, aprovação, reprovação e cancelamento. Converter o script de verificação da auditoria em testes.
   Incluir um teste de fumaça da CLI (E1-RNF-02).
2. Registrar como **comportamento atual** (marcado e explícito) as divergências AUD-09, AUD-11, AUD-12, AUD-13 e AUD-21,
   até que as decisões D-03 a D-06 sejam tomadas.
3. Extrair serialização do domínio; introduzir permissões tipadas, tabela de transições, hierarquia de erros e porta de
   relógio; comparar entidades por ID.
4. Definir portas de repositório (`Protocol`) por agregado e implementar a versão em memória e um adaptador JSON de
   transição para manter a CLI.
5. Criar serviços de aplicação com autorização central; reduzir a CLI a um adaptador dos serviços.
6. Teste de arquitetura de importações e suíte de contrato dos repositórios.

**Critérios de aceitação:** testes de caracterização passam no baseline **antes** da refatoração e depois dela; CLI
funcional; `domain` e `application` sem importar *frameworks* nem persistência concreta; evidência de SRP, ISP, DIP e do
padrão Repository conforme `PRINCIPIOS_SOLID_E_PADROES.md`.

**Riscos:** regressão silenciosa de regra (mitigação: caracterização prévia); refatoração excessiva (mitigação: só
abstrair com problema concreto); decisões de regra pendentes bloqueando testes (mitigação: registrar comportamento atual
e corrigir só após decisão).

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
entre ambiente local e produção (mitigação: testar contra PostgreSQL, não outro banco); datas legadas sem fuso (D-11).

**Dependências:** definir como provisionar o PostgreSQL de desenvolvimento e de teste (D-12).

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

**Aprovação específica necessária:** política de contas iniciais, redefinição de senha e formato da sessão (D-01).

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

**Riscos:** conflito entre "técnico = permissão" e papel fixo (D-02); campos extras de equipamento (D-07).

### Fase 07 — Ordens de serviço (`feat/ordens-servico`)

**Atividades:** abertura, listagem, filtros e detalhe; atribuição e reatribuição; diagnóstico, horas, peças,
intervenções e status; conclusão técnica separada da aprovação administrativa; reprovação devolvendo à execução;
cancelamento; registro de autor e instante de cada transição; testes de concorrência, requisições duplicadas e integridade
transacional.

**Critérios de aceitação:** fluxo Gestor/Técnico ponta a ponta, com testes positivos e negativos para cada transição da
tabela de estados; reparo sem atribuição válida, finalização sem intervenção, conclusão sem diagnóstico e avanço após
teste reprovado impedidos; conflito de versão devolve 409 sem perda de dados.

**Riscos:** decisões pendentes D-03 a D-06 alterando regras já testadas (mitigação: tomar essas decisões antes da Fase 07).

### Fase 08 — Dashboard e histórico (`feat/dashboard-historico`)

**Atividades:** painel por perfil (OS abertas, atrasadas, por criticidade e status; técnicos e carga); linha do tempo
imutável sem duplicidade; filtros combinados, paginação e indicadores calculados no backend; fórmulas documentadas e
testadas com dados conhecidos; tratamento de base vazia; gráficos e tabelas legíveis em tela pequena.

**Critérios de aceitação:** indicadores coerentes com os dados persistidos; histórico íntegro; painel responsivo e testado.

**Riscos:** definição de "atrasada" sem regra existente (decisão a tomar na fase; não há prazo/SLA no modelo atual);
datas como texto (resolvido na Fase 02/03).

### Fase 09 — Testes e qualidade (`test/qualidade`)

**Atividades:** testes unitários, de integração e ponta a ponta dos fluxos Gestor e Técnico; análise estática,
formatação e verificação de tipos; integração contínua com jobs separados para API e frontend; auditoria de segredos,
dependências, CORS, *logs*, validação de entrada, sessões e migrações; verificação de responsividade, teclado e contraste.

**Critérios de aceitação:** CI verde; testes reproduzíveis; checklist de qualidade e segurança com evidências e
limitações reais.

**Riscos:** ferramentas E2E, de análise e metas de cobertura ainda indefinidas (D-13); correção de defeitos descobertos
sem ampliar escopo.

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
| R-07 | Decisões de regra pendentes retardando testes | Média | Médio | Registrar comportamento atual e decidir antes da Fase 07 |
| R-08 | Ambiente PostgreSQL inconsistente entre máquinas e CI | Média | Médio | Definir provisionamento em D-12 antes da Fase 03 |
| R-09 | Duas implementações (`main.py` e `app/`) confundirem manutenção | Média | Médio | Manter `app/` intocada até decisão; não criar um terceiro conjunto paralelo |
| R-10 | Documentação diverge do código | Média | Médio | Marcar tudo como planejado ou implementado; validar comandos na Fase 11 |
| R-11 | Custos e limites de hospedagem | Média | Médio | Decisão e aprovação prévia (Fase 10 é opcional) |

## 5. Decisões pendentes

Nenhuma é tomada por esta documentação. Cada uma precisa de decisão explícita antes da fase indicada.

| ID | Decisão | Origem | Necessária antes de |
|----|---------|--------|---------------------|
| D-01 | Mecanismo de sessão ou token, política de senha inicial, contas iniciais e recuperação de acesso | AUD-01 | Fase 04 |
| D-02 | "Técnico" é definido por cargo/papel ou por permissão editável? | AUD-20 | Fase 02 (modelo) |
| D-03 | Atribuir a técnico **Ausente**: bloquear, avisar ou permitir? Onde a regra reside | AUD-09 | Fase 02 |
| D-04 | Permitir apontamento em OS **encerrada** e por quem (hoje qualquer usuário com permissão) | AUD-11 | Fase 02 |
| D-05 | "Aguardando Peça" conta como "Em atendimento"? (hoje só "Em Execução") | AUD-13 | Fase 02 |
| D-06 | Diagnóstico obrigatório para finalizar o reparo, ou aceito em "Reparo Finalizado"? | AUD-21 | Fase 02 |
| D-07 | Incluir campos extras de equipamento (fabricante, nº de série, setor, data de aquisição)? | OPC-06 | Fase 03 |
| D-08 | Importar os dados JSON existentes? Destino do `dados/dados.json` local (formato incompatível com `app/`) | OPC-07, AUD-06 | Fase 03 |
| D-09 | Hospedagem da API e do PostgreSQL, plano e custos | ADR-0001 | Fase 10 |
| D-10 | Quando descontinuar a CLI e o que fazer com `app/` (remoção exige autorização) | AUD-18 | Após Fase 04 |
| D-11 | Fuso e conversão das datas legadas (`dd/mm/aaaa hh:mm`, sem fuso) | AUD-07 | Fase 03 |
| D-12 | Como provisionar o PostgreSQL de desenvolvimento, teste e CI | ADR-0006 | Fase 03 |
| D-13 | Ferramentas E2E, de análise estática e de tipos, e metas de cobertura | ADR-0006 | Fase 09 |
| D-14 | Nome do pacote do backend e estrutura de diretórios definitiva (sem conflitar com `app/`) | ADR-0002 | Fase 02 |
| D-15 | Definição de OS "atrasada" e regras de prazo, inexistentes no modelo atual | Dashboard (E2-FRT-03) | Fase 08 |

## 6. Rastreio de fases e requisitos

Cada requisito obrigatório está associado a uma ou mais fases na [matriz](MATRIZ_RASTREABILIDADE.md). Uma fase só é
considerada concluída quando os critérios de aceitação acima forem cumpridos **e** a matriz for atualizada com a situação
real e a evidência (arquivo, linha e teste) de cada requisito tocado.
