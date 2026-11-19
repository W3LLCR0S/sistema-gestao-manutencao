# Relatório final da Fase 02 — Refatoração do domínio e SOLID

- **Branch:** `refactor/arquitetura` (local, não publicada; criada de `main` = `cfc4694`).
- **Data de encerramento:** 2026-11-17.
- **Escopo:** novo backend em `backend/src/manutencao/`, ao lado do legado. A CLI da Entrega 1 foi preservada e **não** foi
  conectada à nova arquitetura (D-10).
- **Situação:** Operações A a F concluídas. **Merge e push não foram feitos** e exigem autorização própria
  (`AUTORIZO MERGE FASE 02`).

Este relatório descreve o que existe e foi executado. O que não existe está na seção 7.

## 1. O que foi implementado

| Operação | Entrega |
|----------|---------|
| A | Estrutura `backend/` (pyproject, `pytest`, `ruff`, `mypy` estrito, pacotes por camada), guardas de ambiente e testes de arquitetura |
| B | 1.176 testes de caracterização do legado (fachada estável, teste de fumaça da CLI), com cenários classificados (`CAR-nn`) |
| C | Domínio sem serialização: entidades, permissões tipadas, tabela de transições, hierarquia de erros, instantes UTC, porta `Relogio` |
| D | Portas de repositório (`Protocol`), repositórios em memória com IDs monotônicos, serviços de aplicação, raiz de composição |
| E | Regras de negócio aprovadas, uma por vez, com delta registrado (DLT-01 a DLT-09), e sua regularização (DLT-18 a DLT-23) |
| F | Auditoria final, evidências SOLID/Repository, revisão dos ADRs, esta documentação; teste de precedência da exclusão (REG-E-01) e testes de extensibilidade (OCP) |

Código de produção: ≈2.580 linhas em quatro camadas (`domain`, `application`, `infrastructure`, `composicao`) mais `api/`,
que continua vazio (Fase 04). O pacote não tem dependência de terceiros (`dependencies = []`).

### Deltas em relação ao legado (23, todos com teste e registro)

| Delta | Tema |
|-------|------|
| DLT-01 | Papéis explícitos Gestor e Técnico (D-02) |
| DLT-02 | Atribuição a técnico ausente recusada, com confirmação explícita (D-03) |
| DLT-03, DLT-04 | Observações em OS encerrada e quem pode observar (D-04) |
| DLT-05 | Disponibilidade derivada das OS; ausência manual prevalece (D-05) |
| DLT-06 | Diagnóstico antes de Reparo Finalizado (D-06) |
| DLT-07 | Datas com fuso, em UTC, relógio fornecido pela aplicação (D-11) |
| DLT-08 | Campos obrigatórios e horas maiores que zero |
| DLT-09 | Usuário ativo ou inativo |
| DLT-10 | Identificadores monotônicos (AUD-05) |
| DLT-11 | Permissões tipadas (AUD-03) |
| DLT-12 a DLT-17 | Autoproteção do gestor, autorização de gestão e leitura, disponibilidade de terceiros, precedência das verificações, ator inexistente |
| DLT-18 | Último gestor administrativamente apto protegido ao desativar, rebaixar, trocar cargo, alterar permissões do cargo **e excluir** |
| DLT-19, DLT-20 | Alteração de papel e autoproteção estendida (ratificações) |
| DLT-21 | OS ativa impede desativar e deixar o papel Técnico |
| DLT-22 | Observação e descrição de peça obrigatórias |
| DLT-23 | Disponibilidade manual só `Disponível` e `Ausente`; política única |

Fonte de verificação automática: `backend/tests/caracterizacao/deltas.py`. Descrição e justificativa em
[`DECISOES_APROVADAS.md`](DECISOES_APROVADAS.md).

### Decisão complementar ratificada na Operação F

A proteção do último gestor também vale para a **exclusão** de usuários (REG-E-01 / DLT-18). O código já a tinha
(`ServicoDeUsuarios.excluir`); a Operação F ratificou a decisão na documentação e acrescentou o teste de precedência
(autorização → existência → autoexclusão → histórico → último gestor), com prova de ausência de mutação. Uma mutação
temporária (guarda removida) fez dois testes falharem e foi revertida.

## 2. Requisitos atendidos

Detalhe em [`MATRIZ_RASTREABILIDADE.md`](MATRIZ_RASTREABILIDADE.md), seção 7.

| Requisito | Situação ao fim da Fase 02 |
|-----------|----------------------------|
| E2-SOL-01 SRP | Atendido (backend) |
| E2-SOL-02 OCP | Atendido com ressalva |
| E2-SOL-03 LSP | **Parcial** (relógio demonstrado; repositórios aguardam a segunda implementação) |
| E2-SOL-04 ISP | Atendido |
| E2-SOL-05 DIP | Atendido (backend) |
| E2-PAD-01 Padrão de projeto | Atendido (Repository, Dependency Injection, Service Layer); critério de duas implementações do Repository pendente |
| E2-ARQ-02 Arquitetura | Atendido (camadas, verificada por teste) |
| E2-PER-01 Persistência desacoplada | Parcial |
| E2-DOC-02 SOLID e padrões documentados | Parcial (falta o relatório técnico final) |

Não atendidos, por pertencerem a fases seguintes: interface web (E2-FRT-01 a 03), guia de execução (E2-EXE-01,
E2-DOC-05), relatório técnico final (E2-DOC-01, 03, 04).

## 3. Padrões e princípios aplicados

Evidência completa, com arquivo, linha e teste, em
[`PRINCIPIOS_SOLID_E_PADROES.md`](PRINCIPIOS_SOLID_E_PADROES.md#4-evidências-ao-encerrar-a-fase-02). Resumo:

- **Arquitetura em camadas** (ADR-0002): `domain` ← `application` ← `infrastructure`/`composicao`; `domain` importa só a
  biblioteca-padrão; `application` não importa infraestrutura.
- **Repository:** quatro `Protocol` por agregado (`application/portas/repositorios.py`), implementação em memória
  (`infrastructure/memoria/`), suíte de contrato (`tests/contrato/`, 82 testes). **Uma** implementação hoje.
- **Dependency Injection:** por construtor, sem biblioteca; só `composicao/fabrica.py` importa implementações concretas.
- **Service Layer:** `ServicoDeOrdens`, `ServicoDeUsuarios`, `ServicoDeEquipamentos`, `ServicoDeDisponibilidade`.

## 4. Testes que comprovam os resultados

Executados em 2026-11-17, a partir de `backend/`, com o ambiente virtual local.

| Verificação | Resultado |
|-------------|-----------|
| `pytest` completo (duas execuções) | **2477 passed, 46 skipped**, nas duas |
| Domínio | 534 passed |
| Aplicação | 405 passed |
| Contrato | 82 passed |
| Integração | 13 passed |
| Arquitetura | 234 passed |
| Caracterização | 1176 passed, 46 skipped |
| Guardas do ambiente | 33 passed |
| `ruff check` | sem erros |
| `ruff format --check` | 127 arquivos formatados |
| `mypy` (estrito) | sem erros em 127 arquivos |

Os 46 *skipped* são cenários de caracterização que não se aplicam ao domínio ou aos serviços por conta de um delta ou de
uma limitação, cada um com a justificativa registrada em `tests/caracterizacao/`. Baseline recebido pela Operação F:
2460 passed, 46 skipped. A Operação F acrescentou 1 teste de aplicação (precedência da exclusão) e 16 de domínio (OCP),
sem remover, renomear nem alterar expectativa de teste algum.

Integridade do legado: `git diff entrega-1 HEAD` em `main.py models ui persistencia app dados README.md DOCUMENTACAO.md`
vazio; `dados/dados.json` não foi lido; a CLI interativa não foi executada.

## 5. ADRs

Os nove ADRs foram revisados (seção "Revisão ao encerrar a Fase 02" em cada um e tabela em [`adr/README.md`](adr/README.md)).
Nenhuma decisão foi alterada; mudaram os status (de "aceita para documentação" para implementada, parcial ou
planejada) e foram registrados os pontos ainda abertos (ADR-0004: unidade de trabalho, mapeamento do ORM e controle de versão).

## 6. Rastreabilidade

- Os 23 deltas têm registro em `deltas.py`, descrição em `DECISOES_APROVADAS.md` e ao menos um teste (conferido por busca
  cruzada em código, testes e documentos).
- Os requisitos E1 e E2 afetados estão na seção 7 de `MATRIZ_RASTREABILIDADE.md`.
- Apenas `backend/` e `docs/` foram alterados na Fase 02. Nenhum arquivo de planejamento está no Git.

## 7. Limitações que permanecem

1. **Repository com uma só implementação.** O critério "duas implementações" depende da Fase 03.
2. **Nada é persistido.** Os repositórios são em memória; papel e `ativo` só existem na memória.
3. **Sem API, sem interface web, sem autenticação** (D-01 pendente). A CLI legada continua sendo a única interface
   executável e usa o modelo antigo (sem papéis, sem `ativo`, sem as regras novas).
4. **Sem recuperação administrativa:** a regra impede eliminar o último gestor apto, mas nada cria ou restaura um gestor se o sistema já estiver sem nenhum.
5. **Não há reatribuição automática de OS.** Quem tem OS ativa não é desativado nem deixa o papel Técnico; o gestor
   resolve à mão.
6. `alterar_papel` não alcança sozinho o caso "último gestor" (o ator é, por construção, gestor apto; o autorrebaixamento
   é barrado pela autoproteção).
7. `Usuario.disponibilidade` continua atribuível diretamente; a regra está no método e nos serviços.
8. Conversão para `America/Sao_Paulo`, concorrência otimista e transação não foram implementadas.
9. Não verificados: Python 3.8, execução interativa da CLI, renderização dos diagramas Mermaid.
10. Os pontos de interpretação da seção 8.1 de `DECISOES_APROVADAS.md` seguem registrados; não geraram funcionalidade nova.

## 8. Transição para a próxima fase

A Fase 03 (`feat/persistencia`, plano e autorização próprios) é a próxima no planejamento. Não foi iniciada.
Dependências já prontas para ela: portas estáveis, suíte de contrato parametrizada por implementação
(`tests/contrato/implementacoes.py`), raiz de composição e relógio injetável.

Ponto de decisão para o usuário (não decidido aqui): o planejamento prevê PostgreSQL com SQLAlchemy e Alembic. O
enunciado da Entrega 2 aceita "banco de dados relacional/não relacional ou arquivos estruturados" desde que desacoplado
da regra de negócio. Com a entrega prevista para 2026-11-20, o escopo mínimo da próxima fase e a escolha do meio de
persistência precisam ser fixados antes de iniciá-la.
