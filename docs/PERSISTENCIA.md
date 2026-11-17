# Persistência em PostgreSQL (Fase 03)

O novo backend grava num **PostgreSQL** (decisão do responsável, 2026-11-17; D-12) por meio de
**SQLAlchemy 2.0** (psycopg 3), com o esquema versionado por **Alembic**. Os repositórios concretos
implementam as portas da Fase 02 (`application/portas/repositorios.py`) e **não contêm regra de
negócio**: só traduzem entre linhas e entidades. O legado (CLI, `app/`, `dados/`) não foi tocado.

## Estrutura

```text
backend/
├── alembic.ini                               # sem URL nem credencial
├── migrations/
│   ├── env.py                                # URL vem do ambiente (mesma config da aplicação)
│   └── versions/0001_esquema_inicial.py      # DDL explícita, independente do código atual
├── .env.example                              # modelo de configuração (sem segredos)
├── requirements.txt / requirements-dev.txt   # versões exatas
└── src/manutencao/
    ├── infrastructure/postgres/
    │   ├── configuracao.py   # variáveis de ambiente, senha oculta, leitor de .env
    │   ├── banco.py          # Engine e transações (rollback, transação externa participável)
    │   ├── modelos.py        # modelos SQLAlchemy (o esquema)
    │   ├── sequencia.py      # identificadores monotônicos persistidos
    │   ├── cargos.py · usuarios.py · equipamentos.py · ordens.py   # repositórios concretos
    │   └── migracoes.py      # Alembic por código (usada pelo comando e pelos testes)
    └── composicao/
        ├── fabrica.py        # criar_container_postgres(banco): liga as portas aos adaptadores
        ├── demonstracao.py   # dados fictícios de demonstração (pelos serviços)
        └── banco.py          # comando: estado | migrar | semear | reverter
```

Camadas: `domain` e `application` não importam SQLAlchemy (testes de arquitetura); só a raiz de
composição (`fabrica.py` e `banco.py`) importa a infraestrutura. Trocar memória por PostgreSQL é
trocar a função de composição; **nenhum serviço mudou**.

## Modelo de dados

| Tabela | Conteúdo | Observações |
|---|---|---|
| `sequencias` | maior identificador já emitido por agregado | nunca recua (DLT-10); `UPDATE ... WHERE ultimo < :id` serializa emissões concorrentes |
| `cargos`, `cargo_permissoes` | cargos e suas permissões | permissões como relação, com `CHECK` nos valores |
| `usuarios` | nome, cargo (FK `RESTRICT`), e-mail, escala, disponibilidade **manual**, papel, ativo | papel e ativo persistidos (DLT-01, DLT-09) |
| `equipamentos` | nome, modelo, ativo | |
| `ordens_servico` | OS (agregado) | status, criticidade, diagnóstico, causa-raiz, teste, cancelamento, datas (`timestamptz`) |
| `servicos_os` | histórico da OS (PK `os_numero`+`numero`, `ON DELETE CASCADE`) | tipo, descrição, responsável, instante, horas |
| `pecas_servico` | peças de cada registro de reparo | quantidade `> 0` |

Decisões e justificativas:

- **Identificadores vêm do domínio/aplicação** (não há `SERIAL`): `proximo_id()` consulta e
  `adicionar` consome. Excluir não libera número; reiniciar a aplicação não o recua.
- **Horas, intervenções e peças da OS não são colunas**: derivam dos registros de reparo do
  histórico (`OrdemServico.restaurar`), a única origem delas no domínio. Sem duplicação.
- **Referências da OS a usuários e equipamento são cópias (`*_snapshot`, JSONB) + o id em coluna
  indexada, sem chave estrangeira.** É o contrato da porta (a OS guarda como estavam quando foi
  salva) e ele é exercitado pela suíte de contrato, cujos testes criam OS sem cadastrar antes
  usuários e equipamentos. A integridade vem da aplicação (`usuario_tem_participacao`,
  `equipamento_com_os` barram a exclusão) e o histórico nunca perde quem agiu. Limitação
  conhecida: nomes embutidos na OS ficam defasados após uma edição do usuário/equipamento.
- **Enumerações** são texto com `CHECK` (valores idênticos aos do domínio); a migração os repete
  literalmente para que uma migração antiga continue reproduzindo o mesmo esquema.
- **Instantes** são `timestamptz` e o domínio os normaliza para UTC (D-11).
- **Transações:** cada operação de repositório é atômica (commit, ou rollback em qualquer erro).
  Um caso de uso que grave em mais de um repositório envolve as chamadas em
  `with banco.transacao():` e obtém tudo-ou-nada (as chamadas internas participam da transação
  externa). Hoje cada caso de uso grava em um só agregado, então nenhum precisou disso.
- **Concorrência:** a sequência é segura (testada com 4 fluxos disputando o mesmo id). **Não há**
  controle de versão otimista na OS (duas edições simultâneas da mesma OS: vale a última) —
  pendência registrada.

## Configuração (variáveis de ambiente)

| Variável | Uso |
|---|---|
| `MANUTENCAO_DATABASE_URL` | URL completa `postgresql://usuario:senha@host:5432/banco` (precede as partes) |
| `MANUTENCAO_DB_NAME`, `MANUTENCAO_DB_USER` | obrigatórias se não houver URL |
| `MANUTENCAO_DB_HOST` (`localhost`), `MANUTENCAO_DB_PORT` (`5432`), `MANUTENCAO_DB_PASSWORD` | opcionais |
| `MANUTENCAO_ENV_FILE` | outro arquivo `.env` (vazio = não ler nenhum) |
| `MANUTENCAO_TEST_SERVER_URL` | só testes: servidor existente que possa criar bancos |

O arquivo `backend/.env` (ignorado pelo Git) é lido se existir e **nunca sobrescreve** variáveis já
definidas. Use `backend/.env.example` como modelo. A senha não aparece em `repr`, mensagens de erro
nem na saída do comando.

## Como configurar e executar (a partir de `backend/`)

### 1. PostgreSQL

O projeto precisa de um servidor PostgreSQL 14+ acessível (**o computador de desenvolvimento deste
trabalho não tinha PostgreSQL nem Docker**; os testes usam o `pgserver`, ver abaixo). O caminho mais
rápido para uso real:

- **Windows (instalador):** `winget install PostgreSQL.PostgreSQL.16` (ou o instalador oficial em
  postgresql.org). Guarde a senha do usuário `postgres` que o instalador pede.
- **Docker (alternativa, se instalado):**
  `docker run --name manutencao-pg -e POSTGRES_PASSWORD=<senha> -e POSTGRES_DB=manutencao -p 5432:5432 -d postgres:16`

Depois crie o banco e um papel dedicado (uma vez), no `psql` ou no pgAdmin:

```sql
CREATE ROLE manutencao LOGIN PASSWORD '<senha-local>';
CREATE DATABASE manutencao OWNER manutencao ENCODING 'UTF8';
```

### 2. Ambiente Python, configuração, esquema e dados

```powershell
cd backend
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements-dev.txt     # ou requirements.txt (só execução)
copy .env.example .env                                           # edite a senha em .env
.venv\Scripts\python -m manutencao.composicao.banco migrar       # cria o esquema (Alembic)
.venv\Scripts\python -m manutencao.composicao.banco semear       # dados fictícios (banco vazio)
.venv\Scripts\python -m manutencao.composicao.banco estado       # revisão e contagens
```

(O comando funciona com `PYTHONPATH=src`; os testes do `pyproject.toml` já a configuram. Para
executar o comando direto, use `set PYTHONPATH=src` antes, ou `pip install -e .` quando a API
chegar.)

`semear` cria 2 cargos, 3 usuários, 3 equipamentos e 5 OS (aberta, atribuída, em execução,
concluída e cancelada), **todos fictícios e separados do legado**; recusa-se a rodar em banco que
já tem dados. Os dados do legado (`dados/`) **nunca** são lidos nem importados (D-08: importar só com
plano, backup, dry-run e autorização específica; nada disso foi feito).

### 3. Backup e reversão

- Backup antes de qualquer reversão ou experimento: `pg_dump -Fc -U manutencao manutencao > backup.dump`;
  restauração: `pg_restore -c -d manutencao backup.dump`.
- Reverter o esquema: `python -m manutencao.composicao.banco reverter [destino] --confirmo`
  (`-1` = uma revisão; `base` = tudo). **Apaga os dados das tabelas desfeitas**; sem `--confirmo` o
  comando recusa. Reaplicar com `migrar`.
- Nova migração (quando o modelo mudar): `alembic revision -m "..."` e escrever a DDL à mão; o teste
  `test_os_modelos_e_as_migracoes_descrevem_o_mesmo_esquema` falha se modelos e migrações divergirem.

## Testes

```powershell
.venv\Scripts\python -m pytest                       # tudo (usa o PostgreSQL embutido do pgserver)
.venv\Scripts\python -m pytest tests\contrato        # contrato dos repositórios: memória e PostgreSQL
.venv\Scripts\python -m pytest tests\integracao      # migrações, persistência, reinício, transações
```

- **Contrato:** a mesma suíte (`tests/contrato`) roda contra a implementação em memória **e** a do
  PostgreSQL, sem alteração dos testes. É a demonstração do LSP que ficou pendente na Fase 02
  (duas implementações da porta de repositório).
- **Servidor dos testes:** `MANUTENCAO_TEST_SERVER_URL` (servidor existente) ou, na ausência, o
  `pgserver` (PostgreSQL 16 real e descartável, pasta temporária; só desenvolvimento). Cada sessão
  cria um banco `manutencao_teste_*`, aplica as migrações e o remove ao final. O pacote embutido para
  Windows **não traz a base de fusos horários do PostgreSQL**: por isso a aplicação não fixa o fuso da
  sessão (`timestamptz` guarda o instante; o domínio normaliza para UTC).
- **Reinício:** `tests/integracao/test_persistencia_postgres.py` descarta conexões e contêiner e
  monta outros sobre o mesmo banco; `test_comando_do_banco.py` faz o mesmo com **processos
  separados** (`migrar`, `semear`, `estado`).
- **Paridade:** a demonstração semeada em memória e no PostgreSQL produz o mesmo estado
  (cadastros, OS, históricos, peças) e as mesmas recusas.

## Limitações e pendências

- Sem chave estrangeira da OS para usuários/equipamentos e com cópias embutidas (acima).
- Sem controle de concorrência otimista nas OS; sem recuperação de reservas de sequência (um número
  consumido e abandonado por falha posterior fica de fora; nunca é reutilizado).
- D-07 (campos extras do equipamento) **não** implementada: não estava na lista da fase.
- Importação do JSON legado: **não** implementada (D-08).
- O comando exige o repositório inteiro (as migrações ficam em `backend/migrations`); não é um pacote
  instalável isolado.
- Não verificado: PostgreSQL instalado como serviço do Windows (os testes rodaram no `pgserver`,
  PostgreSQL 16.2 real) e execução em outro computador; os comandos acima são a receita.
