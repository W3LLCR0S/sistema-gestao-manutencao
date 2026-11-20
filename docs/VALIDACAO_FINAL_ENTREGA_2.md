# Validação final — Entrega 2

Data: 2026-11-20. Código validado: `8427977` (tag `entrega-2`) mais as alterações de documentação e a correção do
`README.md` descritas em `EVIDENCIAS_GIT_ENTREGA_2.md`. Nenhum teste foi desativado nem alterado; **nenhuma correção de
código foi necessária**.

## 1. Ambiente

| Item | Valor |
|---|---|
| Sistema | Windows 11 Pro (10.0.26300), Git Bash e PowerShell |
| Python | 3.11.9 (venv `backend/.venv`) |
| Node.js / npm | 24.14.1 / 11.11.0 |
| PostgreSQL permanente | serviço `postgresql-x64-16` (PostgreSQL 16), `127.0.0.1:5432`, banco `manutencao` (**não modificado**: só consultado com `banco estado` e `banco usuarios`) |
| PostgreSQL de validação | instância **embutida e isolada** (`pgserver` 0.1.4), porta local aleatória, bancos `manutencao_validacao` e `manutencao_vazio` |
| Navegador | extensão Claude in Chrome **não conectada**: a verificação visual não foi feita |

## 2. Resultados

| Verificação | Resultado | Evidência |
|---|---|---|
| Instalação do backend | APROVADO | venv já existente com `requirements-dev.txt`; `pytest`, `ruff`, `mypy` executam |
| Instalação do frontend | APROVADO | `node_modules` já presente; scripts executam |
| PostgreSQL | APROVADO | serviço ativo; `banco estado` conecta ao banco permanente (revisão 0003) e à instância isolada |
| Migrações | APROVADO | `banco migrar` em banco vazio aplicou 0001→0003 (`Esquema na revisão 0003`) |
| Banco vazio e primeiro usuário | APROVADO | `criar-gestor` em `manutencao_vazio` criou o gestor e imprimiu a matrícula; `usuarios` o listou |
| Testes Python | APROVADO | `pytest -q`: **3218 passed, 46 skipped, 0 failed** em 436,97 s (3264 coletados). Os 46 *skipped* são cenários de caracterização do legado marcados como dependentes de outra camada (`tests/caracterizacao/conftest.py`), não testes desativados nesta auditoria |
| Lint Python | APROVADO | `ruff check .`: All checks passed; `ruff format --check .`: 190 arquivos já formatados |
| Tipagem Python | APROVADO | `mypy` (strict): no issues found in 186 source files |
| Testes React | APROVADO | `npm test`: 4 arquivos, **35 testes aprovados** |
| Typecheck React | APROVADO | `npm run typecheck` sem erros |
| Lint React | APROVADO | `npm run lint` sem erros |
| Build React | APROVADO | `npm run build`: JS 237,62 kB (72,47 kB gzip) |
| Inicialização da API | APROVADO | `GET /api/v1/saude` → `{"status":"ok","banco":"ok"}`; `/docs` HTTP 200; OpenAPI com 44 operações |
| Inicialização do frontend | APROVADO | `http://localhost:5173/` HTTP 200; `/api/v1/saude` pelo proxy do Vite também responde `ok` |
| Integração completa | APROVADO | requisições HTTP pelo proxy do frontend (mesma origem e cookie do navegador) até o PostgreSQL |
| Teste funcional | APROVADO COM RESSALVA | script HTTP integrado, **28/28** verificações; ver seção 3. **Sem navegador**: telas e responsividade não foram vistas |
| Pacote ZIP | APROVADO | ver seção 4 |
| Cobertura de código | NÃO EXECUTADO | não está configurada no projeto |
| Auditoria de acessibilidade WCAG | NÃO EXECUTADO | fora do alcance desta validação |

## 3. Teste funcional integrado

Executado contra a API real e um PostgreSQL real (instância isolada, dados de demonstração fictícios + registros
`E2E`), pelo endereço do frontend (`http://localhost:5173/api/v1`) com cookie de sessão, `X-CSRF-Token` e `Origin`.
O ator é sempre o usuário da sessão.

Verificado (28): login com senha errada (401); rota protegida sem sessão (401); login do gestor; painel; cadastro e
listagem de equipamento; cadastro de técnico com matrícula gerada e listagem de usuários; abertura de OS; login do
técnico recém-criado; técnico **não** cadastra equipamento, não lista usuários, não atribui e não aprova (403);
atribuição pelo gestor; técnico altera para Em Execução, registra diagnóstico, aponta reparo com horas e peça, finaliza
o reparo e faz a conclusão técnica; aprovação pelo gestor (Concluída); OS encerrada não pode ser cancelada (409);
histórico; filtro por status; cancelamento com motivo; equipamento com OS não é excluído (409); CSRF inválido (403);
logout invalida a sessão (401).

Na primeira execução o script falhou em 5 verificações por **erro do próprio script** (nomes de campo errados:
`parecer` e `teste` em vez de `diagnostico` e `teste_funcional`; e um logout enviado com CSRF inválido). A API se
comportou conforme o contrato (422 e 403). Corrigido o script, a segunda execução aprovou 28/28. Ficou, portanto, um
resíduo de dados `E2E` extra no banco isolado.

**Não coberto:** interface visual no navegador (renderização, cliques, larguras 320–1440 px), técnico ausente com
confirmação (D-03), reprovação, reatribuição, troca de senha e gestão de cargos pela UI. Esses fluxos têm testes
automatizados de API/domínio na suíte do backend.

## 4. Pacote de entrega

`C:\Users\Usuario\Downloads\projeto_luca\sistema_manutencao_entrega_2_final.zip` (fora do repositório).

- Conteúdo: `git ls-files --cached --others --exclude-standard` (arquivos versionados e novos não ignorados), sob a
  pasta `sistema_manutencao/`. Sem `.git/` (o remoto e as evidências estão em `EVIDENCIAS_GIT_ENTREGA_2.md`).
- Ausentes: `.venv/`, `node_modules/`, `dist/`, caches, `__pycache__`, `*.log`, `dados/*`, `backend/.env`.
  Presente: `backend/.env.example` (sem segredo).
- Verificações: `zipfile.testzip()` sem erro; extração completa; nenhum arquivo indesejado; busca por texto da senha do
  `.env` real, da senha de demonstração, chaves privadas e tokens conhecidos: **nenhuma ocorrência** (os valores não são
  exibidos aqui).
- O ZIP inclui `models/permissoes.py` com a compatibilidade de listas no formato antigo, já commitada (ver evidências Git).

- Revalidação pré-publicação (20/11/2026): backend `pytest` 3218 aprovados, 46 ignorados, 0 falhas (5m33s); ruff check, ruff format --check e mypy strict limpos; frontend typecheck, lint, 35 testes e build de produção aprovados.

## 5. Falhas e limitações

- Sem verificação visual no navegador (extensão desconectada). A interface foi confirmada apenas por HTTP 200 e pelos
  35 testes de componentes/fluxo.
- Sem cobertura de código medida e sem teste automatizado em navegador real.
- O PostgreSQL permanente escuta em `0.0.0.0:5432` conforme `netstat`; o guia do projeto recomenda `127.0.0.1` e não
  abrir a porta no firewall. Não foi alterado (configuração do sistema).
- Correção do `README.md`: o comando `cd ..\frontend` estava corrompido por um caractere de controle (`\f`).

## 6. Comandos usados

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check . ; .\.venv\Scripts\python.exe -m ruff format --check . ; .\.venv\Scripts\python.exe -m mypy
cd ..\frontend
npm run typecheck ; npm run lint ; npm test ; npm run build
# banco isolado (MANUTENCAO_DATABASE_URL apontando para a instância pgserver)
$env:PYTHONPATH="src"
.\.venv\Scripts\python.exe -m manutencao.composicao.banco migrar
.\.venv\Scripts\python.exe -m manutencao.composicao.banco criar-gestor --nome "..." --senha-stdin
.\.venv\Scripts\python.exe -m manutencao.composicao.banco semear --com-acesso --senha-stdin
.\.venv\Scripts\python.exe -m manutencao.composicao.servidor --porta 8000
npm run dev
```
