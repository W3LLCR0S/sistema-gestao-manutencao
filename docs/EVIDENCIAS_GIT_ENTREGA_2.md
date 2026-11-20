# Evidências de versionamento — Entrega 2

Dados extraídos do repositório local em 2026-11-20 com os comandos da seção 7. Nenhum commit, tag ou publicação foi
criado para esta documentação. Remoto: `origin` → `https://github.com/W3LLCR0S/sistema-gestao-manutencao.git`.

## 1. Resumo

| Item | Valor |
|---|---|
| Branch principal | `main` (`8427977`, igual a `origin/main`) |
| Commits alcançáveis a partir de `main` | 97 |
| Autoria | 1 autor no histórico (`git shortlog -sn --all`) |
| Tags | `entrega-1` → `e6f7354` (2026-11-15); `entrega-2` → `8427977` (2026-11-18). Ambas **anotadas** e já presentes em `origin` |
| Merges (3) | `6852901`, `cfc4694`, `8427977` |
| Fluxo | Uma branch por fase, integrada em `main` com merge `--no-ff` (ver `FLUXO_DE_DESENVOLVIMENTO.md`) |

## 2. Branches e relação com as fases

Todas as branches abaixo existem localmente e em `origin`, e **estão integradas** em `main` (`git rev-list --count
main..<branch>` = 0). As fases foram encadeadas: cada branch partiu do topo da anterior.

| Branch | Topo | Data do topo | Conteúdo (fase) |
|---|---|---|---|
| `setup/repositorio` | `b9a6879` | 2026-11-15 | Fase 00: documentação do baseline da Entrega 1 |
| `docs/auditoria` | `2c51e01` | 2026-11-15 | Fase 01: auditoria arquitetural, ADRs, decisões, matriz, diagramas e plano (22 commits) |
| `refactor/arquitetura` | `d8d7a89` | 2026-11-17 | Fase 02: backend em camadas, caracterização do legado, domínio, serviços, portas, composição (41 commits) |
| `feat/persistencia` | `c8435d1` | 2026-11-17 | Fase 03: PostgreSQL, SQLAlchemy, Alembic, contrato dos repositórios (9 commits) |
| `feat/api` | `3d4e1d9` | 2026-11-17 | Fase 04: API FastAPI, autenticação (Argon2id, sessão, CSRF) e testes (4 commits) |
| `feat/frontend` | `f556d93` | 2026-11-18 | Fase 05: frontend React e validação ponta a ponta (9 commits) |
| `feat/autenticacao-matricula` | `015a099` | 2026-11-18 | Login por matrícula (ADR-0011), migração 0003, ajustes do frontend e README (6 commits) |

## 3. Merges

| Merge | Data | Pais | Efeito |
|---|---|---|---|
| `6852901` Merge branch `setup/repositorio` | 2026-11-15 | `e6f7354` (entrega-1) + `b9a6879` | Fase 00 em `main` |
| `cfc4694` merge: integrate phase 01 architectural audit and documentation | 2026-11-15 | `6852901` + `2c51e01` | Fase 01 em `main` |
| `8427977` merge: integrate entrega 2 (PostgreSQL, API FastAPI, frontend React, login por matricula) | 2026-11-18 | `cfc4694` + `015a099` | Fases 02 a 05 e login por matrícula em `main`; recebe a tag `entrega-2` |

Do merge `cfc4694` ao `8427977` entram 70 commits (`git rev-list --count cfc4694..8427977`). A diferença entre as
tags (`git diff --stat entrega-1 entrega-2`) é de 271 arquivos, +44556 / −7 linhas.

## 4. Commits representativos

| Commit | Data | Mensagem | Fase |
|---|---|---|---|
| `e6f7354` | 2026-11-15 | chore: import initial CLI maintenance system | Entrega 1 (tag) |
| `0007e37` | 2026-11-15 | docs: add architectural audit of the entrega-1 baseline | 01 |
| `8dcfd4d` | 2026-11-15 | docs: add architecture decision records | 01 |
| `e3520bc` | 2026-11-16 | test(backend): add legacy characterization facade and fixtures | 02 |
| `6c9725d` | 2026-11-16 | refactor(domain): add OrdemServico entity preserving legacy rules | 02 |
| `9373d23` | 2026-11-17 | feat(application): add repository ports and application errors | 02 |
| `cade04e` | 2026-11-17 | feat(composicao): add explicit composition root and DI contracts | 02 |
| `d32d7e1` | 2026-11-17 | feat(infra): PostgreSQL repositories, SQLAlchemy models and the initial Alembic migration | 03 |
| `8bcad43` | 2026-11-17 | test(backend): run the repository contract suite against a real PostgreSQL | 03 (LSP) |
| `688ffa4` | 2026-11-17 | feat(auth): D-01 authentication with Argon2id, server sessions and CSRF | 04 |
| `fb4a81f` | 2026-11-17 | test(api): auth, users, equipment, work orders, panel and contract suites | 04 |
| `fa15312` | 2026-11-18 | feat(frontend): estrutura inicial, cliente HTTP e navegação | 05 |
| `e546db9` | 2026-11-18 | feat(frontend): fluxo de ordens de serviço e rotas | 05 |
| `721fe04` | 2026-11-18 | feat(auth): matricula AA999999 como identificador de login | matrícula |
| `82b3d5b` | 2026-11-18 | test(db): migracao 0003 com dados na revisao 0002, idempotencia e reversao | matrícula |
| `015a099` | 2026-11-18 | docs: README com instalacao e execucao da Entrega 2 | matrícula |

## 5. Alterações posteriores à tag `entrega-2` (na análise)

Não fazem parte da tag `entrega-2`. Foram commitadas depois da análise e publicadas com a tag `entrega-2-final` (a `entrega-2` não foi movida).

| Arquivo | Estado | Origem |
|---|---|---|
| `models/permissoes.py` | modificado **antes** desta auditoria (já aparecia no `git status` inicial) | Código da Entrega 1: `Permissoes.from_dict` passa a aceitar também uma lista (formato antigo do JSON). É alteração do autor do projeto e foi **preservada**; validada (aditiva, restrita à Entrega 1, sem uso pelo pacote novo) e commitada como `fix: preserve legacy permission list compatibility` |
| `docs/RELATORIO_TECNICO_ENTREGA_2.md` | novo | Esta auditoria |
| `docs/DIAGRAMAS.md` | modificado | Esta auditoria (Parte A implementada; Parte B histórica) |
| `docs/MATRIZ_RASTREABILIDADE.md` | modificado | Esta auditoria |
| `docs/EVIDENCIAS_GIT_ENTREGA_2.md` | novo | Esta auditoria |
| `docs/VALIDACAO_FINAL_ENTREGA_2.md` | novo | Esta auditoria |
| `README.md`, `docs/README.md`, `docs/EXECUCAO_LOCAL.md` | modificados | Correção de caminho do README e índice (ver validação final) |

Arquivos ignorados pelo Git e presentes no diretório de trabalho (`backend/.env`, `backend/.venv/`, `frontend/node_modules/`,
`api.log`, `front.log`, caches) **não** vão para o pacote de entrega (ver `VALIDACAO_FINAL_ENTREGA_2.md`).

## 6. Observações

- A tag `entrega-2` aponta para `8427977`; as alterações da seção 5 ficam depois dela. Para entregar a documentação
  atualizada no repositório remoto, é preciso commitá-la e (se desejado) mover ou criar outra tag. **Essa decisão e a
  publicação dependem de autorização do autor** e não foram feitas.
- O histórico das fases 03 a 05 tem granularidade de 4 a 9 commits por fase, em linha com as mensagens
  (convenção `feat`, `test`, `docs`, `fix`, `chore`, `refactor`, `style`).

## 7. Comandos para reproduzir

```bash
git status --short
git branch -a
git log --oneline --decorate --graph -40
git log --merges --format='%h %ad %p %s' --date=short
git tag -n
git cat-file -t entrega-2 && git rev-parse entrega-1 entrega-2
git for-each-ref refs/heads --format='%(refname:short) %(objectname:short) %(committerdate:short)'
for b in setup/repositorio docs/auditoria refactor/arquitetura feat/persistencia feat/api feat/frontend feat/autenticacao-matricula; do git rev-list --count main..$b; done
git rev-list --count 6852901..cfc4694; git rev-list --count cfc4694..8427977
git diff --stat entrega-1 entrega-2 | tail -1
git shortlog -sn --all
git remote -v
```
