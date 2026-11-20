# Relatório Técnico — Entrega 2: Sistema de Gestão de Manutenção de Equipamentos

Documento principal de avaliação. Tudo o que está aqui foi conferido no código do repositório (commit `8427977`,
tag `entrega-2`, mais as alterações locais descritas em [`EVIDENCIAS_GIT_ENTREGA_2.md`](EVIDENCIAS_GIT_ENTREGA_2.md)).
Resultados de testes: [`VALIDACAO_FINAL_ENTREGA_2.md`](VALIDACAO_FINAL_ENTREGA_2.md). Requisito a requisito:
[`MATRIZ_RASTREABILIDADE.md`](MATRIZ_RASTREABILIDADE.md). Diagramas: [`DIAGRAMAS.md`](DIAGRAMAS.md).

Onde a documentação histórica (planejamentos, ADRs, auditoria) diverge do código, vale o código. Os documentos
históricos foram preservados como registro das decisões.

## 1. Introdução

**Sistema.** Gerencia o ciclo de vida da manutenção de equipamentos: cadastro de equipamentos e usuários (com cargos e
permissões), abertura de ordens de serviço (OS), diagnóstico, atribuição a técnicos, execução (horas, intervenções,
peças), conclusão técnica, aprovação pelo gestor e histórico.

**Contexto acadêmico.** Projeto em duas entregas. A Entrega 1 é uma aplicação Python orientada a objetos com
interface de terminal e persistência em JSON (tag `entrega-1`). A Entrega 2 exige evolução com foco em arquitetura,
SOLID, padrões de projeto, baixo acoplamento, testabilidade e uma interface web responsiva (tag `entrega-2`).

**Objetivos da Entrega 2 (o que foi feito).**

1. Novo backend em camadas (`backend/src/manutencao/`): domínio, aplicação, infraestrutura, API e composição.
2. Persistência em **PostgreSQL** (SQLAlchemy + Alembic) atrás de portas (`Protocol`), com uma segunda implementação
   em memória usada pelos testes.
3. **API REST** FastAPI (`/api/v1`) com autenticação por sessão, CSRF e autorização por permissão.
4. **Frontend React + TypeScript + Vite** (`frontend/`) consumindo a API real.
5. **Login por matrícula** (`AA999999`) com senha Argon2id (ADR-0010 e ADR-0011).
6. Suíte automatizada (3264 testes de backend coletados e 35 de frontend) e verificações estáticas (ruff, mypy strict).

**Preservação da Entrega 1.** O código legado (`main.py`, `models/`, `persistencia/`, `ui/`, `app/`) continua no
repositório, sem alteração funcional, e é usado como referência pelos testes de caracterização
(`backend/tests/caracterizacao/`). A implementação paralela `app/` nunca foi importada pelo `main.py`
(achado AUD da Fase 01); foi mantida.

## 2. Arquitetura de software

### 2.1 Estilo adotado

**Arquitetura em camadas com portas e adaptadores (Ports & Adapters / Hexagonal simplificada)**, com a regra de
dependência apontando para o domínio (ADR-0002, ADR-0003, ADR-0005, ADR-0008). Há **um único backend** e **uma SPA**
separada que o consome por HTTP.

| Camada (pacote real) | Responsabilidade | Depende de |
|---|---|---|
| `domain/` | Entidades e regras de negócio: `OrdemServico`, `Usuario`, `Equipamento`, `Cargo`, `Permissoes`, `Matricula`, tabela de transições de status, erros tipados. Sem E/S, sem relógio, sem frameworks | nada do projeto |
| `application/` | Casos de uso (`servicos/`: `ServicoDeOrdens`, `ServicoDeUsuarios`, `ServicoDeEquipamentos`, `ServicoDeAutenticacao`, `ServicoDePainel`...), **portas** (`portas/`: repositórios, `Relogio`, `HasherDeSenha`, sessões), DTOs e erros de aplicação | `domain` |
| `infrastructure/` | Adaptadores das portas: `postgres/` (SQLAlchemy), `memoria/`, `relogio.py` (`RelogioDeSistema`), `seguranca.py` (`HasherArgon2`) | `application`, `domain` |
| `api/` | Borda HTTP (FastAPI): rotas, esquemas Pydantic, mapeamento para DTOs, tradução de erros, segurança (sessão, CSRF, `Origin`). **Sem regra de negócio** | `application`, `domain` |
| `composicao/` | **Raiz de composição**: único lugar que escolhe as implementações e liga serviços (`container.py`, `fabrica.py`, `aplicacao.py`), além dos comandos `banco` (administração) e `servidor` (uvicorn) | todas |
| `frontend/` (React) | Apresentação: páginas, componentes, cliente HTTP e regras de exibição | só a API HTTP |

Estrutura de diretórios (resumo):

```
backend/src/manutencao/{domain,application,infrastructure,api,composicao}/
backend/migrations/versions/   # 0001 esquema, 0002 autenticação, 0003 matrícula
backend/tests/{dominio,aplicacao,contrato,integracao,api,arquitetura,caracterizacao}/
frontend/src/{api,auth,componentes,paginas,utilitarios,testes}/
main.py, models/, persistencia/, ui/, app/    # Entrega 1 (CLI), preservada
```

### 2.2 Justificativa técnica

- **Manutenção e evolução.** A regra de negócio vive só em `domain/` (a máquina de estados da OS está numa tabela em
  `domain/transicoes.py`; as permissões, num `StrEnum`). Trocar o banco, a API ou a interface não toca nessas regras.
  A prova prática: o JSON da Entrega 1 foi trocado por PostgreSQL sem alterar `domain/` nem `application/servicos/`.
- **Testabilidade.** Os serviços recebem portas pelo construtor; os testes de aplicação usam repositórios em
  memória e relógio fixo. A mesma suíte de contrato roda contra todas as implementações de repositório.
- **Baixo acoplamento verificado.** `tests/arquitetura/` analisa os imports e falha se uma camada importar outra na
  direção errada (ex.: `domain` importar `application`, `infrastructure` ou FastAPI/SQLAlchemy), ou se algo fora da
  composição importar implementações concretas.
- **Segurança por desenho.** O ator de cada operação vem da sessão; nenhum corpo de requisição nomeia o ator
  (`api/seguranca.py`). Há teste de contrato que lê o OpenAPI e garante isso para todas as rotas.

### 2.3 Fluxo de uma requisição

`React (páginas → api/cliente.ts) → proxy Vite /api → FastAPI (rota + dependência de segurança) → serviço de aplicação
→ entidade de domínio (valida e muda estado) → repositório (porta) → implementação PostgreSQL`. Diagramas em
[`DIAGRAMAS.md`](DIAGRAMAS.md).

### 2.4 Tecnologias (versões verificadas em `requirements*.txt` e `package.json`)

| Componente | Versão |
|---|---|
| Python | 3.11 (`requires-python >=3.11,<3.12`); ambiente de validação 3.11.9 |
| FastAPI / Uvicorn / Pydantic | 0.163.2 / 0.54.0 / 2.14.3 |
| SQLAlchemy / Alembic / psycopg | 2.0.58 / 1.20.1 / 3.3.9 |
| argon2-cffi | 25.1.0 |
| PostgreSQL | 16 (serviço `postgresql-x64-16` do Windows) |
| Testes e qualidade (backend) | pytest 9.2.0, ruff 0.17.5, mypy 2.4.1 (strict), `pgserver` 0.1.4 (PostgreSQL embutido para testes) |
| Frontend | React 18.3, react-router-dom 6.30, TypeScript 6.0, Vite 8.3, Vitest 5.1, Testing Library, ESLint 10 |
| Node.js / npm (validação) | 24.14.1 / 11.11.0 |

## 3. Princípios SOLID

Os testes citados existem em `backend/tests/` e foram executados (ver a validação final).

### 3.1 SRP — Responsabilidade Única

*Uma unidade deve ter um único motivo para mudar.*

- **Arquivos:** `domain/ordem_servico.py` (regras da OS), `application/servicos/ordens.py` (orquestração),
  `infrastructure/postgres/ordens.py` (persistência), `api/rotas/ordens.py` (HTTP), `api/mapeamento.py` (conversão).
- **Trecho** (`application/servicos/ordens.py`): o caso de uso apenas carrega, delega e salva.

  ```python
  def aprovar(self, ator_id: int, numero: int) -> None:
      gestor = self._autorizar(ator_id, Permissao.APROVAR_OS)
      ordem = self._carregar(numero)
      ordem.aprovar(gestor, quando=self._relogio.agora())
      self._ordens.salvar(ordem)
  ```
- **Como atende:** a regra (`OrdemServico.aprovar`) não sabe de banco nem de HTTP; o serviço não reimplementa a regra;
  o repositório não tem regra; a rota não tem regra. Na Entrega 1, `OrdemServico` serializava a si mesma e o
  `Repositorio` continha regras.
- **Benefício:** mudar o formato do JSON de resposta, o banco ou uma regra de aprovação afeta um só lugar.
- **Evidência:** `tests/arquitetura/test_camadas.py`.

### 3.2 OCP — Aberto/Fechado

*Aberto para extensão, fechado para modificação.*

- **Arquivos:** `domain/transicoes.py` (tabela `_TABELA`), `domain/permissoes.py` (`Permissao` e `Permissoes`).
- **Trecho:** `transicao_permitida(origem, destino)` consulta a tabela; `Permissoes.tem()` não tem um `if` por permissão.
- **Como atende:** acrescentar uma transição é uma entrada na tabela; acrescentar uma permissão é um membro do enum, e
  o controle existente passa a tratá-la. `tests/dominio/test_extensibilidade.py` demonstra isso por parametrização.
- **Ressalva (honesta):** uma nova permissão ainda exige declarar o membro em `Permissao` (e sua descrição); o
  OCP é atendido para a lógica de controle, não para o catálogo.

### 3.3 LSP — Substituição de Liskov

*Subtipos devem poder substituir seus tipos base sem alterar a correção.*

- **Arquivos:** portas em `application/portas/repositorios.py`; implementações `infrastructure/memoria/*` e
  `infrastructure/postgres/*`; `tests/contrato/implementacoes.py`.
- **Como atende:** a **mesma suíte de contrato** (`tests/contrato/test_contrato_*.py`) roda contra a implementação em
  memória e contra a do PostgreSQL. A semântica (cópias independentes, `None` para ausência, ids monotônicos que nunca
  são reutilizados) está escrita na docstring da porta e verificada nas duas. O PostgreSQL foi acrescentado à suíte
  sem alterar nenhum teste.
- **Benefício:** o serviço funciona igual com qualquer implementação; os testes rápidos usam memória e a produção usa
  PostgreSQL com o mesmo comportamento.
- **Limite:** não há hierarquia de herança no domínio; a substituição é por contrato de `Protocol` (e `Relogio`, com
  `RelogioDeSistema` e relógios fixos de teste, `tests/contrato/test_contrato_relogio.py`).

### 3.4 ISP — Segregação de Interfaces

*Clientes não devem depender de métodos que não usam.*

- **Arquivos:** `application/portas/repositorios.py` (`EquipamentoRepository`, `CargoRepository`, `UsuarioRepository`,
  `OrdemServicoRepository`), `portas/autenticacao.py` (`CredencialRepository`, `SessaoRepository`, `HasherDeSenha`,
  `UnidadeDeTrabalho`), `portas/relogio.py` (`Relogio`).
- **Como atende:** um `Protocol` por agregado, sem repositório genérico; cargos não têm `remover` (são fixos); OS não
  tem exclusão; `Relogio` tem um único método. Cada serviço recebe só as portas de que precisa (ex.:
  `ServicoDeOrdens(ordens, usuarios, equipamentos, relogio)`).
- **Evidência:** `tests/aplicacao/test_injecao_de_dependencias.py`.
- **Observação:** `UsuarioRepository` é a porta mais ampla (inclui consulta por matrícula); mantida por coesão do agregado.

### 3.5 DIP — Inversão de Dependências

*Módulos de alto nível dependem de abstrações.*

- **Arquivos:** `application/servicos/*` dependem de `application/portas/*`; implementações são escolhidas em
  `composicao/fabrica.py` e `composicao/aplicacao.py`.
- **Trecho** (`composicao/container.py`): `montar(...)` recebe **apenas portas** e devolve o `Container`.
- **Como atende:** `domain` não importa nada do projeto; `application` não importa `infrastructure`; `api` recebe um
  `ContextoDaApi` pronto (não importa `infrastructure` nem `composicao`). Só `composicao/` importa implementações.
- **Evidência:** `tests/arquitetura/test_camadas.py` e `test_injecao_de_dependencias.py` (inclui casos sintéticos que
  provam que o analisador *detecta* violações).

## 4. Design Patterns

| Padrão | Situação | Onde está | Finalidade / problema resolvido |
|---|---|---|---|
| **Repository** | Implementado | portas em `application/portas/repositorios.py`; `infrastructure/postgres/{equipamentos,usuarios,ordens,cargos}.py`; `infrastructure/memoria/*` | Isola a persistência da regra de negócio; permite trocar JSON por PostgreSQL e testar em memória. Resolve o `Repositorio` único da Entrega 1, que misturava regra e arquivo |
| **Dependency Injection** (por construtor, manual) | Implementado | `composicao/container.py` (`montar`), `fabrica.py`, `aplicacao.py`; construtores dos serviços | Baixo acoplamento e testabilidade. Sem framework de DI nem localizador de serviços |
| **Service Layer** | Implementado | `application/servicos/*` | Casos de uso em um só lugar, usados pela API; rotas ficam finas |
| **Factory** (funções-fábrica) | Implementado | `composicao/fabrica.py` (`criar_container_em_memoria`, `criar_container_postgres`), `composicao/aplicacao.py`, `api/app.py` (`criar_app`), `composicao/servidor.py` (`criar`) | Escolhe e monta implementações concretas sem que quem usa saiba qual. Não é o padrão Factory Method/Abstract Factory de classes; são fábricas simples |
| **Adapter** | Implementado (forma ampla) | `infrastructure/seguranca.py` (`HasherArgon2` adapta `argon2.PasswordHasher` à porta `HasherDeSenha`); repositórios PostgreSQL adaptam SQLAlchemy às portas; `api/mapeamento.py` converte domínio em DTOs HTTP | Adaptar uma API externa a uma interface própria. Os testes de caracterização também têm `adaptador_legado.py`, que adapta a CLI da Entrega 1 (apenas teste) |
| **Strategy** | **Não implementado como padrão formal** | — | Há comportamento intercambiável por porta (`HasherDeSenha`, `Relogio`, repositórios), que lembra Strategy, mas não existe hierarquia de estratégias escolhidas em tempo de execução. O planejamento (`PRINCIPIOS_SOLID_E_PADROES.md` §2.2) descartou State, Strategy e Observer deliberadamente |
| **Unit of Work** (transação) | Implementado de forma simples | `infrastructure/postgres/banco.py` (`Banco.transacao`, que participa de transação externa) e porta `UnidadeDeTrabalho` | Atomicidade quando um caso de uso grava em mais de um repositório (ex.: cadastrar usuário com senha) |

## 5. Melhorias da Entrega 1 para a Entrega 2

| Aspecto | Entrega 1 | Entrega 2 | Evidência |
|---|---|---|---|
| Arquitetura | `models/`, `ui/`, `persistencia/`; `Aplicacao` instancia `Repositorio()` direto; `OrdemServico` serializa a si mesma; pacote `app/` paralelo e não usado | Camadas `domain`/`application`/`infrastructure`/`api`/`composicao`, portas `Protocol`, raiz de composição, dependências verificadas por teste | `backend/src/manutencao/`, `tests/arquitetura/`, ADR-0002/0005/0008 |
| Interface | CLI de terminal (`ui/`, `main.py`) | SPA React responsiva (painel, equipamentos, usuários, cargos, OS) + Swagger da API | `frontend/src/paginas/`, `docs/FRONTEND.md` |
| Persistência | Arquivo `dados/dados.json` regravado inteiro, sem concorrência | PostgreSQL 16, SQLAlchemy, migrações Alembic 0001-0003, transações | `backend/migrations/versions/`, `infrastructure/postgres/`, `docs/PERSISTENCIA.md` |
| Autenticação | Login por ID, sem senha | Matrícula `AA999999` + senha Argon2id, sessão no servidor (cookie `HttpOnly`), CSRF, limitador de tentativas, `Origin`/CORS restritos | `application/servicos/autenticacao.py`, `api/seguranca.py`, ADR-0010, ADR-0011 |
| Autorização | Permissões como texto livre | Permissões tipadas (`Permissao`), verificadas antes de qualquer busca (DLT-16) | `domain/permissoes.py`, `application/servicos/ordens.py` |
| Datas | Relógio lido dentro da entidade | Porta `Relogio`, instantes em UTC, conversão para America/Sao_Paulo na interface | ADR-0007, `application/portas/relogio.py` |
| Testes | Nenhum | 3264 testes de backend coletados (domínio, aplicação, contrato, integração, API, arquitetura, caracterização) e 35 de frontend | `backend/tests/`, `frontend/src/testes/` |
| Qualidade estática | Nenhuma | ruff (check e format) e mypy `strict` | `backend/pyproject.toml` |
| Documentação | `README`, `DOCUMENTACAO.md` | ADRs 0001-0011, decisões aprovadas, auditoria, API, frontend, persistência, este relatório | `docs/` |

Regras de negócio alteradas por decisão aprovada na Entrega 2 (documentadas em `DECISOES_APROVADAS.md` e
`tests/caracterizacao/deltas.py`): atribuição a técnico ausente exige confirmação (D-03), observações só em OS ativa
(D-04), diagnóstico exigido antes de `Reparo Finalizado` (D-06), validação de campos obrigatórios e horas > 0, usuário
inativo não opera.

## 6. Funcionalidades implementadas

Listas conferidas nas rotas de `backend/src/manutencao/api/rotas/` e nas páginas de `frontend/src/paginas/`
(44 operações HTTP, descritas em [`API.md`](API.md)).

| Módulo | Backend (`/api/v1`) | Frontend |
|---|---|---|
| Autenticação e perfis | `POST /auth/login`, `/auth/logout`, `GET /auth/me`, `POST /auth/alterar-senha`; papéis Gestor/Técnico; cargos com permissões editáveis | `Login`, `AlterarSenha`, `Cargos`, rota protegida por permissão |
| Equipamentos | CRUD, inativar/reativar (não exclui equipamento com OS) | `Equipamentos` |
| Usuários | CRUD, matrícula gerada pelo sistema, cargo, papel, credencial, desativar/reativar (protege o último gestor) | `Usuarios` |
| Disponibilidade | `GET /disponibilidade`, `PUT /me/disponibilidade` (Disponível/Ausente; "Em atendimento" é derivado das OS) | Painel e Usuários |
| Abertura de OS | `POST /ordens` | `NovaOrdem` |
| Diagnóstico | `POST /ordens/{n}/diagnostico` | `OrdemDetalhe` |
| Atribuição de técnicos | `POST /ordens/{n}/atribuicao` (confirmação para técnico ausente) | `OrdemDetalhe` |
| Execução | `POST /ordens/{n}/reparos` (horas, intervenção, peças), `/status`, `/apontamentos` | `OrdemDetalhe` |
| Encerramento | `POST /ordens/{n}/conclusao-tecnica`, `/aprovacao`, `/reprovacao`, `/cancelamento` | `OrdemDetalhe` |
| Histórico e consultas | `GET /ordens` (filtros, paginação), `/ordens/{n}`, `/ordens/{n}/historico`, `GET /painel` | `Ordens`, `OrdemDetalhe`, `Painel` |

Fluxo de status: Aberta → Atribuída → Em Execução ⇄ Aguardando Peça → Reparo Finalizado → Aguardando Aprovação →
Concluída (Cancelada antes do fim; reprovação volta a Em Execução). Fonte: `domain/transicoes.py`.

## 7. Versionamento

Resumo (detalhes e comandos em [`EVIDENCIAS_GIT_ENTREGA_2.md`](EVIDENCIAS_GIT_ENTREGA_2.md)):

- Branch principal `main`; branches de trabalho por fase: `setup/repositorio`, `docs/auditoria`,
  `refactor/arquitetura`, `feat/persistencia`, `feat/api`, `feat/frontend`, `feat/autenticacao-matricula`.
- Tags anotadas `entrega-1` (`e6f7354`, 2026-11-15) e `entrega-2` (`8427977`, 2026-11-18).
- Merges em `main`: `6852901` (Fase 00), `cfc4694` (Fase 01) e `8427977` (Fases 02 a 06).
- 97 commits no histórico; repositório remoto `origin` no GitHub.

## 8. Guia de execução

Guia completo: [`EXECUCAO_LOCAL.md`](EXECUCAO_LOCAL.md) e README da raiz. Resumo para Windows/PowerShell:

```powershell
# Pré-requisitos: Python 3.11, Node.js (validado com 24.14.1), PostgreSQL 16 em 127.0.0.1:5432
# 1. Banco: crie o papel e o banco "manutencao" (docs/INSTALACAO_POSTGRESQL_WINDOWS.md) e
#    copie backend\.env.example para backend\.env, preenchendo MANUTENCAO_DB_PASSWORD (não versione)

# 2. Dependências
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
cd ..\frontend
npm install

# 3. Esquema e primeiro gestor (a senha é pedida sem eco; a matrícula é impressa)
cd ..\backend
$env:PYTHONPATH = "src"
.\.venv\Scripts\python.exe -m manutencao.composicao.banco migrar
.\.venv\Scripts\python.exe -m manutencao.composicao.banco criar-gestor --nome "Seu Nome"

# 4. Execução (dois terminais)
.\.venv\Scripts\python.exe -m manutencao.composicao.servidor     # API: http://127.0.0.1:8000  (Swagger: /docs)
cd ..\frontend; npm run dev                                       # Frontend: http://localhost:5173
```

Entrar em `http://localhost:5173` com a matrícula e a senha do gestor. O Gestor cadastra os demais usuários em
**Usuários** (a matrícula é gerada e exibida na confirmação) e define as senhas. Dados de demonstração em banco vazio:
`banco semear --com-acesso`.

## 9. Testes e qualidade

Comandos e resultados reais (ambiente, data, contagens e falhas) estão em
[`VALIDACAO_FINAL_ENTREGA_2.md`](VALIDACAO_FINAL_ENTREGA_2.md). Comandos:

```powershell
cd backend;  .\.venv\Scripts\python.exe -m pytest -q; ruff check .; ruff format --check .; mypy
cd frontend; npm run typecheck; npm run lint; npm test; npm run build
```

Os testes de backend usam um PostgreSQL embutido e descartável (`pgserver`) e **não tocam** no banco `manutencao`.
Não há cobertura de código configurada (nenhum percentual é informado). Não há teste automatizado em navegador real
no repositório; a verificação em navegador está descrita na validação final.

## 10. Conclusão

A Entrega 2 atende aos requisitos do enunciado: código em camadas com separação verificável, SOLID analisado com
evidência (o OCP e o ISP com as ressalvas indicadas), padrões Repository, Dependency Injection, Service Layer,
Factory e Adapter, frontend web integrado, persistência em PostgreSQL, documentação técnica e histórico Git
verificável. A matriz de rastreabilidade registra o estado de cada requisito.

**Limitações conhecidas** (preservadas dos documentos de fase e conferidas):

- Strategy não foi implementado como padrão formal.
- Sem testes automatizados em navegador real e sem medição de cobertura.
- HTTP local sem criptografia; o limitador de tentativas é por processo; não há controle de versão otimista nas OS.
- Sem paginação na interface (a API limita a 200 itens); sem "esqueci a senha" (o Gestor redefine).
- Acessibilidade WCAG 2.1 AA é meta técnica da equipe, não comprovada por auditoria formal.
- A CLI da Entrega 1 permanece sem senha (comportamento original preservado).
