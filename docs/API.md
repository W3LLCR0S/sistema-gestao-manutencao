# API HTTP (Fase 04)

API FastAPI sobre os serviços da aplicação, com PostgreSQL e autenticação por sessão (D-01,
[ADR-0010](adr/0010-autenticacao-e-sessao.md)). **As rotas não contêm regra de negócio**: cada uma resolve o ator
pela sessão e chama um caso de uso; permissões, transições e proteções (último gestor, OS ativas, técnico ausente...)
são do domínio e da aplicação. Prefixo: `/api/v1`.

## Executar (a partir de `backend/`)

Pré-requisitos: PostgreSQL configurado em `backend/.env` ([`PERSISTENCIA.md`](PERSISTENCIA.md),
[`INSTALACAO_POSTGRESQL_WINDOWS.md`](INSTALACAO_POSTGRESQL_WINDOWS.md)).

```powershell
cd backend
$env:PYTHONPATH = "src"
.\.venv\Scripts\python.exe -m manutencao.composicao.banco migrar                 # esquema (0001 a 0003)
.\.venv\Scripts\python.exe -m manutencao.composicao.banco criar-gestor --nome "Seu Nome"        # imprime a matrícula gerada
#   (pede a senha sem eco; ou: semear --com-acesso para a demonstração fictícia)
.\.venv\Scripts\python.exe -m manutencao.composicao.servidor                     # http://127.0.0.1:8000
```

- Documentação interativa (OpenAPI): <http://127.0.0.1:8000/docs> (também `/redoc` e `/openapi.json`).
- Saúde: `GET /api/v1/saude` → `{"status":"ok","banco":"ok"}`.
- `--porta 8001` troca a porta; `--rede` escuta em `0.0.0.0` (celular; ver [`ACESSO_PELO_CELULAR.md`](ACESSO_PELO_CELULAR.md)).
- O servidor se recusa a subir se o esquema não está na revisão mais recente.
- Outra forma: `uvicorn manutencao.composicao.servidor:criar --factory`.

### Configuração (variáveis de ambiente ou `backend/.env`)

| Variável | Padrão | Uso |
|---|---|---|
| `MANUTENCAO_DB_*` / `MANUTENCAO_DATABASE_URL` | — | conexão (ver `PERSISTENCIA.md`) |
| `MANUTENCAO_API_COOKIE_SECURE` | `false` | `true` quando servida por HTTPS (atributo `Secure`) |
| `MANUTENCAO_API_ORIGENS` | vazio | origens do frontend permitidas, por vírgula (CORS e `Origin`); **`*` é recusado** |
| `MANUTENCAO_API_DOCS` | `true` | expõe `/docs`, `/redoc`, `/openapi.json` |
| `MANUTENCAO_SESSAO_HORAS` | `8` | validade absoluta da sessão (1 a 72) |
| `MANUTENCAO_API_COOKIE_NOME` | `manutencao_sessao` | nome do cookie |

## Como o cliente fala com a API

1. `POST /api/v1/auth/login` com `{"matricula","senha"}` (matrícula `AA999999`; o nome de usuário antigo não é mais aceito) → cookie `HttpOnly` + `{usuario, csrf_token, expira_em}`.
2. Toda requisição leva o cookie (no navegador: `credentials: "include"` em chamadas entre origens, ou apenas mesma
   origem pelo proxy do frontend).
3. `POST/PUT/PATCH/DELETE` levam `X-CSRF-Token: <csrf_token>`. Após recarregar a página, `GET /auth/me` devolve o
   `csrf_token` de novo.
4. 401 = sessão ausente/expirada (o cliente volta ao login); 403 = sem permissão ou CSRF; 422 = entrada inválida.

## Erros

Corpo sempre `{"codigo": "...", "mensagem": "..."}` (422 de forma inclui `detalhes: [{campo, mensagem}]`, **sem** o
valor enviado). O `codigo` é estável.

| HTTP | Origem | Exemplos de `codigo` |
|---|---|---|
| 401 | não autenticado / credenciais | `nao_autenticado`, `credenciais_invalidas` |
| 403 | `PermissaoNegadaError`, CSRF, origem | `sem_permissao`, `nao_responsavel`, `sem_vinculo_com_a_os`, `tecnico_ausente`, `csrf_invalido`, `origem_nao_permitida` |
| 404 | `NaoEncontradoError` | `nao_encontrado`, `rota_nao_encontrada` |
| 409 | conflito de estado / regra de aplicação | `estado_invalido`, `os_encerrada`, `ja_nesse_status`, `usuario_com_os_ativas`, `usuario_com_historico`, `equipamento_com_os`, `ultimo_gestor`, `autoremocao_de_acesso_de_gestao`, `autoexclusao`, `login_em_uso` |
| 422 | `ViolacaoDeRegraError`, entrada inválida | `campo_obrigatorio`, `horas_negativas`, `horas_nao_positivas`, `quantidade_invalida`, `equipamento_inativo`, `status_nao_permitido`, `sem_intervencao`, `sem_diagnostico`, `nao_e_tecnico`, `disponibilidade_manual_invalida`, `entrada_invalida`, `senha_atual_incorreta` |
| 429 | limite de tentativas de login | `muitas_tentativas` (+ `Retry-After`) |
| 500 | erro inesperado | `erro_interno` (a causa vai só para o log) |

## Endpoints (44 operações)

Autenticação (`login`, `logout` e `saude` são públicos; os demais exigem sessão):

| Método e caminho | Descrição |
|---|---|
| `POST /auth/login` | abre a sessão |
| `POST /auth/logout` | encerra (idempotente; com sessão válida exige CSRF) |
| `GET /auth/me` | usuário autenticado, permissões efetivas e `csrf_token` |
| `GET /auth/sessao` | verificação de sessão |
| `GET /auth/permissoes/{permissao}` | se o usuário tem a permissão |
| `POST /auth/alterar-senha` | troca a própria senha (revoga as outras sessões) |

Usuários, cargos e disponibilidade (`gerir_usuarios`, salvo indicação):

| Método e caminho | Descrição |
|---|---|
| `GET /usuarios?ativo=&papel=&limite=&deslocamento=` | lista paginada |
| `POST /usuarios` | cadastra; a **matrícula é gerada pelo sistema** e devolvida em `matricula` (não pode ser enviada); opcionalmente já com `senha` (atômico) |
| `GET /usuarios/{id}` · `PATCH /usuarios/{id}` | detalhe · atualiza nome, e-mail, escala |
| `PUT /usuarios/{id}/cargo` · `PUT /usuarios/{id}/papel` | cargo · papel (só Gestor) |
| `POST /usuarios/{id}/desativar` · `/reativar` | ativação (desativar revoga as sessões) |
| `DELETE /usuarios/{id}` | exclui (sem histórico em OS) |
| `PUT /usuarios/{id}/credencial` | define/redefine a senha `{"senha"}`; a matrícula não muda (revoga as sessões do usuário) |
| `GET /cargos` · `PUT /cargos/{id}/permissoes` | cargos · define as permissões (tudo ou nada) |
| `GET /permissoes` | catálogo de permissões (qualquer autenticado) |
| `GET /disponibilidade?ordenar_por_carga=` | disponibilidade derivada e carga (`ver_disponibilidade`) |
| `PUT /me/disponibilidade` | a própria, `Disponível` ou `Ausente` |
| `PUT /usuarios/{id}/disponibilidade` | de outro (`gerir_usuarios`) |

Equipamentos (`ver_equipamentos` para ler, `gerir_equipamentos` para escrever):

`GET /equipamentos?apenas_ativos=&limite=&deslocamento=` · `POST /equipamentos` · `GET|PUT|DELETE /equipamentos/{id}`
· `POST /equipamentos/{id}/inativar` · `POST /equipamentos/{id}/reativar`.

Ordens de serviço (a OS atualizada é devolvida em cada ação):

| Método e caminho | Permissão / regra |
|---|---|
| `GET /ordens?status=&criticidade=&equipamento_id=&tecnico_id=&encerrada=&mais_antigas_primeiro=&limite=&deslocamento=` | `ver_os`; padrão: mais recentes primeiro |
| `POST /ordens` | `abrir_os`; o autor é o usuário da sessão |
| `GET /ordens/{n}` · `GET /ordens/{n}/historico` | `ver_os` |
| `POST /ordens/{n}/diagnostico` | `diagnosticar` + técnico da OS |
| `POST /ordens/{n}/reparos` | `apontar_reparo` + técnico da OS (horas, intervenção, peças) |
| `POST /ordens/{n}/status` | `atualizar_status` + técnico da OS |
| `POST /ordens/{n}/conclusao-tecnica` | `concluir_os` + técnico da OS → `{submetida_a_aprovacao, ordem}` |
| `POST /ordens/{n}/apontamentos` | `registrar_apontamento` + vínculo com a OS (observações) |
| `POST /ordens/{n}/atribuicao` | `atribuir_os`; `confirmar_ausente` para técnico ausente (D-03) → `{ordem, tecnico_anterior}` |
| `POST /ordens/{n}/aprovacao` · `/reprovacao` · `/cancelamento` | `aprovar_os` (`motivo` em reprovação e cancelamento) |

Painel: `GET /painel` (`ver_os`): totais, por status, por criticidade em aberto, minhas OS, 5 mais recentes e
disponibilidade dos técnicos (omitida sem `ver_disponibilidade`).

### Paginação

`limite` (1 a 200; padrão 100, 50 em OS) e `deslocamento` (≥ 0). Resposta: `{itens, total, limite, deslocamento}`;
`total` conta antes do corte.

### Datas

ISO 8601 com fuso, em UTC (D-11). A conversão para `America/Sao_Paulo` é da interface.

## Segurança: o que está e o que não está

- Hash Argon2id; só hashes no banco (senha e token). Respostas nunca trazem hash, token de sessão nem segredo.
- `Cache-Control: no-store` e `X-Content-Type-Options: nosniff` em toda resposta.
- CORS **só** para as origens configuradas e com credenciais; `*` é recusado na configuração.
- Verificação de `Origin` nas escritas (mesma origem ou configurada).
- **Limites:** em HTTP local o tráfego não é criptografado; o limitador de tentativas é por processo; não há
  controle de versão otimista nas OS (vale a última edição); não há paginação por cursor.

## Testes

`backend/tests/api` (320 testes; cada um roda **em memória e no PostgreSQL real**), `tests/aplicacao/test_autenticacao.py`
e `tests/integracao/test_api_postgres.py`. Os testes de contrato leem o OpenAPI e garantem que **toda** operação
(exceto `login`, `logout`, `saude`) exige autenticação, que toda escrita exige CSRF e que nenhum esquema aceita ator
nem expõe hash/token.
