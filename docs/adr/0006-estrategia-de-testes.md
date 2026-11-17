# ADR-0006 — Estratégia de testes e ferramentas de qualidade

- **Status:** Aceita para documentação (Fase 01); atualizada com a decisão D-13 e com a estratégia de caracterização.
  Ferramentas além das aprovadas dependem de justificativa. **Nenhuma ferramenta foi instalada nesta fase.**
- **Data:** 2026-11-15
- **Relacionados:** ADR-0001 a ADR-0005, ADR-0007 a ADR-0009; AUD-17; E2-OBJ-01 (testabilidade), E2-SOL-03, E2-SOL-04,
  E2-SOL-05, E2-DOC-02; [`DECISOES_APROVADAS.md`](../DECISOES_APROVADAS.md) (D-13)

## Contexto

O baseline não tem testes automatizados, manifesto de dependências nem integração contínua (AUD-17). A refatoração
exigida pela Entrega 2 altera estrutura e persistência, mas **deve preservar** o comportamento da Entrega 1, exceto nos
pontos em que uma mudança foi aprovada (D-02 a D-06, validações, desativação de usuários). Sem testes anteriores à
mudança, não há como provar a preservação. A auditoria executou verificações ad hoc que revelaram defeitos reais, mas o
script não é versionado.

Os testes de caracterização escritos hoje seriam acoplados diretamente a `models/` e `persistencia/`. Esses módulos
serão substituídos gradualmente (ADR-0008), então **não se pode assumir** que tais testes continuarão válidos sem
adaptação depois da refatoração.

## Alternativas consideradas

| Alternativa | Avaliação |
|-------------|-----------|
| Teste manual da CLI e da interface | Não reproduzível nem auditável; não detecta regressões |
| Apenas testes de ponta a ponta | Lentos, frágeis e pouco precisos para localizar falhas de regra |
| `unittest` da biblioteca padrão | Funcional, porém com menos recursos de parametrização e *fixtures* que o `pytest` |
| Refatorar primeiro e testar depois | Impossibilita separar regressão de mudança intencional |
| Aplicar as mudanças aprovadas junto da refatoração | Mistura regressão com mudança intencional; impede saber o que quebrou |
| **Pirâmide de testes; caracterização antes da refatoração; mudanças funcionais aplicadas em separado** (escolhida) | Protege o comportamento e dá retorno rápido |

## Decisão

### 1. Ferramentas (D-13)

| Ferramenta | Uso | Introdução |
|------------|-----|------------|
| `pytest` | Testes de caracterização, domínio, aplicação, contrato, integração e arquitetura | **Fase 02** |
| `ruff` | Verificação de estilo e erros estáticos (*lint*) e formatação | **Fase 02** |
| `mypy` | Verificação estática de tipos, incluindo a conformidade das implementações aos `Protocol` | **Fase 02** |
| `Vitest` | Testes de componentes e do cliente HTTP do frontend | Fase do frontend (05 em diante) |
| Ferramenta E2E | Fluxos Gestor e Técnico | A definir e justificar (Fase 09); **não escolhida** |
| Verificação automatizada de acessibilidade | Complementa os testes manuais de teclado, foco, contraste e rótulos | A definir (Fases 05 e 09) |

Configuração mínima (manifesto de dependências, `pyproject.toml`) será criada na Fase 02, **não agora**. Metas
numéricas de cobertura **não foram definidas** (proposta na Fase 09).

### 2. Níveis de teste

| Nível | Escopo | Depende de |
|-------|--------|------------|
| **Caracterização** (Fase 02, **antes** de alterar regras) | Fixa o comportamento atual da Entrega 1 | Código legado |
| **Domínio** | Máquina de estados (tabela de transições, casos válidos e inválidos), invariantes, permissões | Só `domain` |
| **Aplicação** | Casos de uso, autorização, orquestração e erros, com repositórios em memória e relógio fixo | `application` + dublês |
| **Contrato de repositório** | A mesma suíte roda contra todas as implementações de cada porta | Em memória; SQLAlchemy (Fase 03) |
| **Integração** | Repositórios reais, migrações, concorrência e rotas da API (401/403/404/409/422) | PostgreSQL de teste (D-12, pendente) |
| **Arquitetura** | Falha se `domain` importar `application`, `infrastructure`, `api` ou *frameworks*; se `application` importar `infrastructure`, `api` ou *frameworks*; se `api` importar `infrastructure` | Análise de importações |
| **Frontend** | `Vitest` | Fases do frontend |
| **Ponta a ponta** | Fluxos Gestor e Técnico | Ferramenta a definir |

Os testes de **domínio, aplicação e integração** ficam em diretórios separados (`tests/dominio`, `tests/aplicacao`,
`tests/integracao`), como no esboço do [ADR-0008](0008-estrutura-do-backend-e-convivencia-com-o-legado.md).

### 3. Estratégia de caracterização e refatoração

Sequência obrigatória para cada regra tocada:

1. **Caracterizar** o comportamento atual do legado (inclusive os defeitos conhecidos, marcados como tal: AUD-09, AUD-11,
   AUD-12, AUD-13, AUD-21), de modo que o teste **descreva** e não **julgue** o comportamento.
2. **Refatorar preservando** esses comportamentos (mudar estrutura, não regra), com a mesma suíte passando antes e
   depois.
3. **Aplicar separadamente** cada mudança funcional aprovada (D-02 a D-06, validações, desativação), em commit próprio,
   cujo teste substitui explicitamente o de caracterização correspondente.
4. **Executar** os testes após cada etapa e registrar o resultado real.
5. **Registrar o delta de comportamento** de cada mudança (ver abaixo).

**Reduzir o acoplamento dos testes à implementação.** Como os testes acoplados a `models/` e `persistencia/` não
sobreviverão intactos:

- sempre que possível, escrever a caracterização contra uma **fachada estável** pequena (por exemplo, um adaptador de
  teste com operações como `abrir_os`, `atribuir`, `apontar`, `alterar_status`, `aprovar`), em vez de chamar classes
  internas diretamente;
- a mesma suíte de caracterização é executada primeiro contra a fachada do **legado** e, depois, contra a fachada do
  **novo domínio**; as diferenças aprovadas aparecem como deltas explícitos e não como falhas;
- testes que dependam de detalhes internos (formato do JSON, ordem de atributos) são marcados como **descartáveis** e
  removidos junto com o módulo que testam;
- a tag `entrega-1` preserva o código de referência caso o legado seja removido.

**Deltas de comportamento.** Cada mudança aprovada é registrada com: regra, comportamento anterior (com o teste de
caracterização), comportamento novo (com o teste substituto), decisão que a autorizou e fase. Lista inicial:

| Delta | Anterior | Novo | Decisão |
|-------|----------|------|---------|
| Atribuir a técnico Ausente | Aceito pelo domínio | Recusado sem confirmação explícita | D-03 |
| Observação em OS Concluída ou Cancelada | Aceita de qualquer usuário com permissão | Recusada | D-04 |
| Observação pelo autor da abertura | Aceita só com a permissão geral | Aceita em OS ativa, sem conferir capacidade técnica | D-04 |
| Disponibilidade | Atualizada só pela rotina da UI | Derivada, sem rotina | D-05 |
| Finalizar reparo sem diagnóstico | Aceito (e bloqueava o diagnóstico depois) | Recusado com erro claro | D-06 |
| Identidade de técnico | Por permissão | Por papel | D-02 |
| Entradas vazias, zero hora, valores inválidos | Aceitos pelo domínio | Rejeitados | Validação |
| Datas | Texto sem fuso | Instante com fuso em UTC | D-11 |
| Usuário inativo | Inexistente | Não autentica nem opera | Desativação |

**Registro dos deltas.** Cada delta tem um identificador `DLT-nn` em `backend/tests/caracterizacao/deltas.py`, com o
comportamento do legado, o aprovado, os cenários CAR-nn que caracterizam o antigo, o estado e as evidências
(`arquivo::teste`); `test_rastreabilidade.py` confere o estado esperado de cada um e a existência das evidências.
`DLT-01` a `DLT-09` correspondem, em outra ordem, às linhas da lista inicial acima; `DLT-10` (IDs monotônicos) e `DLT-11` (permissões tipadas) foram acrescentados nas Operações C e D. Todos os deltas estão **implementados**: `DLT-07`, `DLT-10` e `DLT-11` (Operações C e D), os de autorização abaixo
(`DLT-12` a `DLT-17`) e os de regras de negócio da Operação E (`DLT-01` a `DLT-06`, `DLT-08` e `DLT-09`, tabela a seguir). A
**regularização da Operação E** acrescenta `DLT-18` a `DLT-23` (decisões `REG-E-01` a `REG-E-06`) sem renumerar os
anteriores; `REG-E-07` e `REG-E-08` são correções de rastreabilidade e seu registro definitivo é o próprio identificador.

**Deltas de autorização (regularização da Operação D, aprovados em 2026-11-17).** Detalhados na
[seção 7 de `DECISOES_APROVADAS.md`](../DECISOES_APROVADAS.md); todos da camada de aplicação e **implementados**:

| Delta | Anterior (legado) | Novo (serviços) | Cenários do legado |
|-------|-------------------|-----------------|--------------------|
| DLT-12 | Gestor retira de si o próprio acesso de gestão | Recusado (autoproteção), sem mutação | CAR-71 |
| DLT-13 | Gestão de equipamentos, usuários e cargos sem permissão | Exige `gerir_equipamentos` / `gerir_usuarios` antes de mutar | CAR-73 |
| DLT-14 | Consultas sem permissão | Exige `ver_equipamentos`, `ver_os`, `ver_disponibilidade` (e `gerir_usuarios` para usuários e cargos) | CAR-91 |
| DLT-15 | Qualquer um altera a disponibilidade de qualquer um | Própria: livre; de outro: só com `gerir_usuarios` | CAR-72 |
| DLT-16 | Autoexclusão e histórico conferidos sem olhar a permissão | Autorização é a primeira verificação | CAR-93, CAR-64, CAR-65 |
| DLT-17 | Solicitante inexistente é indiferente | Recusado com `NaoEncontradoError`; sem administrador padrão | CAR-92 |

**Deltas de regras de negócio (Operação E).** Detalhados na
[seção 8 de `DECISOES_APROVADAS.md`](../DECISOES_APROVADAS.md#8-deltas-de-regras-de-negócio-operação-e-dlt-01-a-dlt-09);
todos **implementados** no domínio e/ou na aplicação, com evidências separadas por camada:

| Delta | Anterior (legado) | Novo | Cenários do legado |
|-------|-------------------|------|--------------------|
| DLT-01 | Técnico é quem tem `apontar_reparo`; o cargo move o usuário | Papel explícito; permissão não muda o papel; `alterar_papel` restrito ao Gestor | CAR-18, 60, 63, 82 |
| DLT-02 | Atribuição a ausente aceita (só a tela confirma) | Recusada; aceita com `confirmar_ausente` e registrada no histórico | CAR-17, 89 |
| DLT-03 | Observação em OS encerrada aceita | Recusada para todos | CAR-79 |
| DLT-04 | Qualquer um com permissão observa | Gestor, responsável e quem abriu, em OS ativa | CAR-39, 79 |
| DLT-05 | Disponibilidade gravada por rotina da UI | Derivada das OS a cada consulta; ausência manual prevalece | CAR-43, 47 a 52, 81 |
| DLT-06 | Finalizar sem diagnóstico aceito | Diagnóstico exigido antes de Reparo Finalizado | CAR-34, 83 |
| DLT-08 | Textos vazios e zero hora aceitos | Obrigatórios e horas maiores que zero | CAR-80 |
| DLT-09 | Sem `ativo`; só se exclui sem histórico | Usuário inativo não opera nem é atribuível; histórico preservado | CAR-64, 65 |

**Regularização da Operação E (aprovada em 2026-11-17).** Detalhada na
[seção 9 de `DECISOES_APROVADAS.md`](../DECISOES_APROVADAS.md#9-regularização-da-operação-e-reg-e-01-a-reg-e-08);
todos **implementados** (`REG-E-02` e `REG-E-03` ratificam regras já implementadas):

| Decisão | Delta | Anterior (legado) | Novo | Cenários do legado |
|---------|-------|-------------------|------|--------------------|
| REG-E-01 | DLT-18 | Nada impede ficar sem gestor | Recusa que elimina o último gestor administrativamente apto (`ultimo_gestor`) | CAR-71 |
| REG-E-02 | DLT-19 | O papel era a permissão; sem operação de papel | `alterar_papel` exige Gestor ativo com `gerir_usuarios` (ratificada) | CAR-63 |
| REG-E-03 | DLT-20 | Só a tela impedia a autoexclusão | Ninguém se rebaixa de Gestor nem desativa a própria conta (ratificada) | CAR-71, CAR-64 |
| REG-E-04 | DLT-21 | Mudança de cargo sem relação com as OS | OS ativa impede desativar e deixar o papel Técnico (`usuario_com_os_ativas`) | CAR-63 |
| REG-E-05 | DLT-22 | Observação e descrição de peça vazias aceitas | Ambas obrigatórias (ampliação do DLT-08) | CAR-80 |
| REG-E-06 | DLT-23 | `Em atendimento` manual aceito; duas políticas | Só `Disponível` e `Ausente`; política única (DLT-15) | CAR-51, CAR-52 |
| REG-E-07 | REG-E-07 | Variante do CAR-37 sem vínculo com o DLT-06 | Registrada em `VARIANTES_SOMENTE_NO_LEGADO` | CAR-37 |
| REG-E-08 | REG-E-08 | Docstring do CAR-80 inexato | Campos validados listados exatamente | CAR-80 |

Nas comparações lado a lado (`test_adaptador_dominio.py`, `test_adaptador_servicos.py`) cada par (estado, operação) que muda
por estes deltas está **nomeado** em `tests/caracterizacao/divergencias.py`, com o delta e a recusa exata; a tabela não admite
entrada sobrando e todo outro par continua exigindo igualdade total.

**Regra de exclusão da comparação.** Um cenário só deixa de ser executado contra os serviços (`NAO_REPRODUZIDOS_PELOS_SERVICOS`)
quando (1) há um delta aprovado e implementado; (2) o cenário está vinculado a ele; (3) o comportamento antigo continua
testado no legado; (4) o novo comportamento tem teste específico; e (5) a divergência é exatamente a autorizada.
Não existe exclusão genérica por "defeito do legado".

**Variante só do legado (`REG-E-07`).** Quando é só **um teste** de um cenário que não pode rodar contra o novo código
(o estado de partida deixou de existir por um delta), o cenário **não** é excluído nem classificado como divergente: a
variante é registrada em `VARIANTES_SOMENTE_NO_LEGADO` (`aplicabilidade.py`) com o delta, a justificativa e as evidências
da invariante, e `test_rastreabilidade.py` confere que o teste existe, usa a fixture `legado`, que o delta está
implementado e que o cenário segue executado nos três adaptadores. Hoje: CAR-37 (`DLT-06`).

### 4. Evidências de LSP, ISP e DIP (futuras, nenhuma existe hoje)

Estes princípios **não estão demonstrados** no baseline. As evidências concretas que serão exigidas, a partir da
Fase 02, são:

| Princípio | Evidência concreta futura |
|-----------|---------------------------|
| LSP | Suíte de **contrato** parametrizada executada contra a implementação em memória e a SQLAlchemy (e a JSON, se existir); `mypy` confirmando que cada implementação satisfaz o `Protocol` |
| ISP | Construtores dos serviços recebendo apenas as portas de que usam; dublês de teste com só essas operações; `mypy` rejeitando uso de método fora da porta declarada |
| DIP | Teste de arquitetura de importações; serviços executados com repositórios em memória e SQLAlchemy sem alterar `domain` nem `application` |

### 5. Regras adicionais

- **Testes de caracterização antes da refatoração**: nenhuma regra é movida sem teste que a cubra.
- **Testes nunca usam dados reais**: apenas *fixtures* e bancos de teste isolados; nada de `dados/dados.json` local.
- **Relógio fixo** nos testes de aplicação; operações de domínio recebem o instante (ADR-0007).
- **Resultados reais**: relatórios de fase registram comandos executados e saídas; nunca se declara um teste como
  executado sem evidência.
- Integração contínua com jobs separados para API e frontend na Fase 09; `ruff` e `mypy` rodam localmente desde a Fase 02.

## Justificativa

- Protege o contrato funcional da Entrega 1 durante a migração, sem confundir regressão com mudança aprovada.
- A suíte de contrato e o `mypy` são o meio concreto de demonstrar substituibilidade e segregação de interfaces.
- O teste de arquitetura transforma a regra de dependência (ADR-0002) em verificação automática.
- Fachadas estáveis reduzem o retrabalho quando os módulos legados forem substituídos.

## Consequências

- Esforço inicial concentrado na Fase 02, antes de qualquer ganho visível ao usuário.
- É necessário um PostgreSQL para os testes de integração; **como provê-lo localmente e no CI não está decidido** (D-12;
  nenhuma instalação é feita nesta fase).
- Metas de cobertura, ferramenta E2E e ferramentas adicionais de frontend continuam pendentes.
- O script de verificação da auditoria deve ser convertido em testes versionados, e não reutilizado como está.
