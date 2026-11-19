# Sistema de Gestão de Manutenção de Equipamentos

Gerencia o ciclo de vida da manutenção: abertura de OS, atribuição, diagnóstico, reparo, conclusão técnica,
aprovação e histórico de serviços.

| Entrega | O que é | Onde está |
|---------|---------|-----------|
| **Entrega 2** (atual) | Backend em camadas (FastAPI + SQLAlchemy + PostgreSQL) e frontend React, com login por matrícula | `backend/`, `frontend/`, tag `entrega-2` |
| **Entrega 1** | Aplicação Python orientada a objetos com CLI e persistência em JSON | `main.py`, `models/`, `persistencia/`, `ui/`, tag `entrega-1` |

Documentação técnica: [`docs/README.md`](docs/README.md). Decisões de projeto da Entrega 1: **DOCUMENTACAO.md**.

## Entrega 2: instalação e execução

Guia completo (Windows, com acesso pelo celular): [`docs/EXECUCAO_LOCAL.md`](docs/EXECUCAO_LOCAL.md).

**Requisitos:** Python 3.11, Node.js e PostgreSQL 16 (instalação em
[`docs/INSTALACAO_POSTGRESQL_WINDOWS.md`](docs/INSTALACAO_POSTGRESQL_WINDOWS.md)).

**1. Banco e configuração (uma vez).** Crie o papel e o banco `manutencao` no PostgreSQL, copie
`backend/.env.example` para `backend/.env` (ignorado pelo Git) e preencha `MANUTENCAO_DB_PASSWORD`.
Nunca versione o `.env`.

**2. Dependências (uma vez).**

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
cd ..rontend
npm install
```

**3. Esquema e primeiro acesso (uma vez).**

```powershell
cd backend
$env:PYTHONPATH = "src"
.\.venv\Scripts\python.exe -m manutencao.composicao.banco migrar
.\.venv\Scripts\python.exe -m manutencao.composicao.banco criar-gestor --nome "Seu Nome"   # imprime a matrícula
```

A senha é pedida sem eco. O login usa a **matrícula** (formato `AA999999`) e a senha. Para dados fictícios de
demonstração em banco vazio, use `banco semear --com-acesso`.

**4. Execução.**

```powershell
# terminal 1 (backend/)
$env:PYTHONPATH = "src"; .\.venv\Scripts\python.exe -m manutencao.composicao.servidor
# terminal 2 (frontend/)
npm run dev
```

Abra <http://localhost:5173>. API e Swagger: <http://127.0.0.1:8000/docs>.

**5. Verificação.**

```powershell
cd backend;  .\.venv\Scripts\python.exe -m pytest -q ; ruff check . ; ruff format --check . ; mypy
cd frontend; npm run typecheck; npm run lint; npm test; npm run build
```

Os testes do backend usam um PostgreSQL embutido e descartável; não tocam no banco `manutencao`.

## Entrega 1: CLI legada

```bash
python main.py
```

Requer Python 3.8+ e nenhuma biblioteca externa. Na primeira execução é criado
`dados/dados.json` com dados de exemplo. Para recomeçar do zero, apague esse arquivo.

Usuários de exemplo: **1 – Ana Souza (Gestor)**, **2 – Bruno Lima (Técnico)**,
**3 – Carla Mendes (Técnico)**.

## Estrutura da Entrega 1

```
sistema_manutencao/
├── main.py
├── models/                  # classes do domínio (regras de negócio)
│   ├── permissoes.py        # Permissoes
│   ├── cargo.py             # Cargo
│   ├── usuario.py           # Usuario
│   ├── ordem_servico.py     # OrdemServico
│   ├── servico.py           # Servico (serviços executados na OS)
│   ├── peca_material.py     # PecaMaterial
│   ├── equipamento.py       # Equipamento
│   ├── enums.py             # StatusOS, Criticidade, Disponibilidade, TipoServico
│   └── excecoes.py          # RegraNegocioError
├── persistencia/
│   └── repositorio.py       # Repositorio: guarda os objetos e salva/carrega o JSON
├── ui/                      # telas do terminal
│   ├── aplicacao.py         # Aplicacao: login e menu por permissão
│   ├── tela_base.py
│   ├── tela_equipamentos.py
│   ├── tela_usuarios.py
│   ├── tela_ordens.py
│   ├── tela_tecnico.py
│   ├── tela_gestor.py
│   └── entrada.py
└── dados/dados.json         # gerado automaticamente
```

## Classes

```
Usuario ──── cargo ────► Cargo ──── permissoes ────► Permissoes
  id                       id                          ver_equipamentos, ver_os, abrir_os,
  nome                     nome                        ver_disponibilidade, registrar_apontamento,
  cargo                    permissoes                  diagnosticar, apontar_reparo,
  email, escala,                                       atualizar_status, concluir_os,
  disponibilidade                                      gerir_equipamentos, gerir_usuarios,
                                                       atribuir_os, aprovar_os

OrdemServico ──── servicos ────► Servico (1..N)
  numero                           numero (sequencial na OS)
  status                           tipo, descricao, data
  diagnostico                      responsavel (Usuario)
  horas_trabalhadas                horas
  intervencoes_realizadas          pecas (PecaMaterial)
  pecas_utilizadas (PecaMaterial)
  tecnico_atribuido (Usuario)
  equipamento, falha, criticidade, causa_raiz, ...

Equipamento
  id
  nome
  modelo
  ativo (para inativar/reativar)
```

As regras ficam nos métodos das classes. Por exemplo, `OrdemServico.apontar_reparo()`
confere se o usuário tem permissão, se a OS é dele e se o status permite, e então
soma as horas, adiciona a intervenção e as peças e registra um `Servico` no histórico.

## Fluxo de status da OS

Aberta → Atribuída → Em Execução ⇄ Aguardando Peça → Reparo Finalizado
→ Aguardando Aprovação → Concluída  (Cancelada a qualquer momento antes do fim)
