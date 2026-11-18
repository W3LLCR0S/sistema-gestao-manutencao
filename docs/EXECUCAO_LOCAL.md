# Execução local (Windows): PostgreSQL + API + frontend

Guia único para subir o sistema no computador e abrir no navegador ou no celular. Instalação do PostgreSQL:
[`INSTALACAO_POSTGRESQL_WINDOWS.md`](INSTALACAO_POSTGRESQL_WINDOWS.md).

## 1. Banco (uma vez)

1. O serviço `postgresql-x64-16` deve estar em execução (`Get-Service postgresql-x64-16`), escutando só em
   `127.0.0.1:5432`. **Não** use `trust` no `pg_hba.conf` e **não** abra a porta 5432 no firewall.
2. Crie o usuário e o banco `manutencao` com o administrador `postgres` (pede as senhas sem eco), por exemplo:

   ```powershell
   & "C:\Program Files\PostgreSQL\16\bin\psql.exe" -h 127.0.0.1 -U postgres
   ```
   ```sql
   CREATE ROLE manutencao LOGIN PASSWORD 'SUA-SENHA';   -- digite você mesmo; não a versione
   CREATE DATABASE manutencao OWNER manutencao;
   REVOKE CONNECT ON DATABASE manutencao FROM PUBLIC;
   ```
3. Copie `backend/.env.example` para `backend/.env` (ignorado pelo Git) e preencha `MANUTENCAO_DB_PASSWORD`
   (host `127.0.0.1`, porta `5432`, banco e usuário `manutencao`).

## 2. Esquema e primeiro acesso (uma vez)

```powershell
cd backend
$env:PYTHONPATH = "src"
.\.venv\Scripts\python.exe -m manutencao.composicao.banco migrar        # 0001 a 0003
.\.venv\Scripts\python.exe -m manutencao.composicao.banco criar-gestor --nome "Seu Nome"   # imprime a matrícula gerada
#   a senha é pedida sem eco. Para dados fictícios de demonstração (banco vazio):
#   .\.venv\Scripts\python.exe -m manutencao.composicao.banco semear --com-acesso
```

**Login inicial:** a **matrícula** impressa por `criar-gestor` (ou, na demonstração, `KM482731` Ana, `RT095624` Bruno
e `VX716309` Carla, com a senha digitada no `semear`). Consulte as matrículas com `banco usuarios`. Depois, o Gestor cadastra os demais usuários em **Usuários**.

## 3. Todo dia

```powershell
# terminal 1 (backend/)
$env:PYTHONPATH = "src"; .\.venv\Scripts\python.exe -m manutencao.composicao.servidor
# terminal 2 (frontend/)
npm run dev
```

Abra <http://localhost:5173>. API/Swagger: <http://127.0.0.1:8000/docs>.

## 4. Celular na mesma rede Wi-Fi

1. No PowerShell: `ipconfig` e anote o IPv4 do adaptador Wi-Fi (ex.: `192.168.0.25`). O `npm run dev` também
   imprime as URLs "Network".
2. No celular (mesma rede, **não** a de convidados): `http://192.168.0.25:5173`.
3. O celular só fala com a porta 5173; o Vite encaminha `/api` para a API, que continua em `127.0.0.1`. O
   PostgreSQL nunca é exposto.
4. Se o celular não abrir: o Windows pode bloquear a porta 5173. Permita o **Node.js** apenas em **Rede privada**
   quando o Firewall perguntar (ou crie uma regra de entrada TCP 5173 só para o perfil Privado). Não desative o
   firewall nem libere a 5432.
5. Lembre-se: é HTTP, sem criptografia; use só em rede doméstica confiável.

## 5. Verificação

```powershell
cd backend;  .\.venv\Scripts\python.exe -m pytest -q ; ruff check . ; ruff format --check . ; mypy
cd frontend; npm run typecheck; npm run lint; npm test; npm run build
```
