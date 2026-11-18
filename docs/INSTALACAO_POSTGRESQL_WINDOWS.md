# Instalação permanente do PostgreSQL 16 no Windows

Procedimento **manual** (exige interação sua: privilégio de administrador e a senha do superusuário `postgres`).
**Nunca** coloque senhas em comandos, scripts versionados, documentação ou no chat: os passos abaixo as digitam
apenas em prompts sem eco.

> Estado neste computador (verificado em 2026-11-17): sem PostgreSQL instalado, sem serviço `postgres*`, sem `psql`,
> porta 5432 livre, `winget` v1.29 disponível. Os testes do projeto usam o PostgreSQL 16.2 descartável do `pgserver`
> e **não** substituem esta instalação para o uso real.

## 1. Instalar (PowerShell **como administrador**)

```powershell
winget install --id PostgreSQL.PostgreSQL.16 -e
```

- Aceite os termos do `winget`/da fonte quando perguntado.
- O instalador gráfico (EDB) abre: mantenha **PostgreSQL Server**, **Command Line Tools** (traz o `psql`) e,
  opcionalmente, o pgAdmin; porta **5432**; locale padrão.
- Quando pedir a **senha do superusuário `postgres`**, escolha uma senha forte **e guarde-a no seu gerenciador de
  senhas**. Ela é só para administração; a aplicação **não** usa o `postgres`.
- Se o `winget` falhar: baixe o instalador do PostgreSQL 16 em <https://www.postgresql.org/download/windows/> e
  repita as escolhas acima.

## 2. Verificar a instalação

```powershell
Get-Service *postgres*                                              # Status: Running, tipo Automatic
& "C:\Program Files\PostgreSQL\16\bin\psql.exe" --version           # psql (PostgreSQL) 16.x
Get-NetTCPConnection -LocalPort 5432 -State Listen                  # a porta em escuta
```

Por padrão o PostgreSQL escuta em `localhost` (`listen_addresses = 'localhost'` no `postgresql.conf`): **não altere**.
Se a porta 5432 já estiver ocupada por outra instância, o instalador usa outra (ex.: 5433): anote-a e use-a em
`MANUTENCAO_DB_PORT`.

## 3. Criar o papel e o banco da aplicação (sem expor senha)

Conecte como `postgres` (o `psql` pede a senha do passo 1, sem eco):

```powershell
& "C:\Program Files\PostgreSQL\16\bin\psql.exe" -U postgres -h localhost
```

Dentro do `psql`:

```sql
CREATE ROLE manutencao WITH LOGIN;
\password manutencao
CREATE DATABASE manutencao OWNER manutencao ENCODING 'UTF8';
\q
```

`\password manutencao` pede a nova senha **duas vezes, sem eco**, e envia só o hash ao servidor (a senha não vai ao
histórico do `psql` nem aos logs). Defina uma senha **diferente** da do `postgres`. Antes de criar, confira se o
banco/papel já existem (`\du`, `\l`); se existirem, **não** os recrie sem entender o estado.

## 4. Configurar a aplicação

```powershell
cd backend
copy .env.example .env
notepad .env      # edite MANUTENCAO_DB_PASSWORD com a senha do papel "manutencao"
```

`backend/.env` é ignorado pelo Git (nunca o versione nem imprima o conteúdo). Confirme que **não** há uma variável
`MANUTENCAO_DATABASE_URL` no ambiente do Windows, pois ela tem precedência sobre as partes:

```powershell
[Environment]::GetEnvironmentVariable("MANUTENCAO_DATABASE_URL", "User")
[Environment]::GetEnvironmentVariable("MANUTENCAO_DATABASE_URL", "Machine")   # ambos devem estar vazios
```

## 5. Esquema, dados e verificação

```powershell
cd backend
$env:PYTHONPATH = "src"
.\.venv\Scripts\python.exe -m manutencao.composicao.banco migrar        # 0001 e 0002 (Alembic)
.\.venv\Scripts\python.exe -m manutencao.composicao.banco criar-gestor --nome "Seu Nome" --login seu.login
#   ou, para a demonstração fictícia (banco vazio): semear --com-acesso
.\.venv\Scripts\python.exe -m manutencao.composicao.banco estado        # revisão 0002 e contagens
```

Prova de persistência: encerre os processos, **reinicie o serviço** (`Restart-Service postgresql-x64-16`) ou o
computador e rode `estado` de novo: as contagens permanecem, e o banco não depende do `pgserver` dos testes.

## 6. Backup

```powershell
& "C:\Program Files\PostgreSQL\16\bin\pg_dump.exe" -U manutencao -h localhost -Fc manutencao -f backup.dump
```

(o `pg_dump` pede a senha; guarde o arquivo fora do repositório).
