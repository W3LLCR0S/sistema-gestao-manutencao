# Mapeamento dos requisitos obrigatórios para a API (FastAPI) e a interface (React)

> **Atualização (Fase 05):** o frontend React está implementado em `frontend/` (ver [`FRONTEND.md`](FRONTEND.md)).
>
> **Atualização (Fase 04, 2026-11-17):** a **API e a autenticação (D-01, aprovada) estão implementadas** na branch
> `feat/api`; o contrato real é [`API.md`](API.md) (gerado também em `/docs`). Os endpoints reais seguem esta tabela
> com poucas diferenças (ex.: `PUT /usuarios/{id}/credencial`, `POST /auth/alterar-senha`, `GET /permissoes`,
> `GET /auth/sessao`, `GET /auth/permissoes/{p}`, `GET /painel`, `GET /saude`). **O frontend React ainda não existe**
> (próxima fase): as seções 3 e 4 abaixo permanecem como planejamento. A seção 4 foi **aprovada** com as
> alterações registradas em [`adr/0010`](adr/0010-autenticacao-e-sessao.md). Prazo acadêmico: 2026-11-20.

Princípios: a API é uma **borda fina** sobre os serviços que já existem (`ServicoDeUsuarios`,
`ServicoDeEquipamentos`, `ServicoDeOrdens`, `ServicoDeDisponibilidade`); **nenhuma regra de negócio
nova** na borda. A interface consome a API real, **sem dados simulados** como substituto da
integração. Execução **local** (PostgreSQL + FastAPI + React), sem hospedagem nem deploy.

## 1. Tradução de erros (já definida nos docstrings)

| Erro | HTTP |
|---|---|
| `PermissaoNegadaError` | 403 |
| `NaoEncontradoError` | 404 |
| `ConflitoDeEstadoError`, `IdentificadorJaEmitidoError`, `RegraDeAplicacaoError` | 409 |
| `ViolacaoDeRegraError` | 422 |
| não autenticado (D-01) | 401 |

Corpo: `{codigo, mensagem}` com o `CodigoErro`/`CodigoErroAplicacao` estável.

## 2. FastAPI

O ator de cada operação (`ator_id`) passa a vir da **sessão autenticada**, nunca do corpo da
requisição.

| Área | Endpoint (proposta) | Serviço | Permissão |
|---|---|---|---|
| Autenticação | `POST /auth/login`, `POST /auth/logout`, `GET /auth/me` | **novo** (D-01) | — |
| Usuários | `GET /usuarios`, `GET /usuarios/{id}` | `ServicoDeUsuarios.listar/consultar` | `gerir_usuarios` |
| | `POST /usuarios` | `cadastrar` | `gerir_usuarios` |
| | `PATCH /usuarios/{id}` | `atualizar_dados` | `gerir_usuarios` |
| | `PUT /usuarios/{id}/cargo`, `PUT /usuarios/{id}/papel` | `alterar_cargo`, `alterar_papel` | `gerir_usuarios` (papel: Gestor) |
| | `POST /usuarios/{id}/desativar`, `.../reativar` | `desativar`, `reativar` | `gerir_usuarios` |
| | `DELETE /usuarios/{id}` | `excluir` | `gerir_usuarios` |
| Cargos e permissões | `GET /cargos`, `PUT /cargos/{id}/permissoes` | `listar_cargos`, `definir_permissoes_do_cargo` | `gerir_usuarios` |
| Equipamentos | `GET /equipamentos?apenas_ativos=`, `GET /equipamentos/{id}` | `listar/consultar` | `ver_equipamentos` |
| | `POST /equipamentos`, `PUT /equipamentos/{id}`, `DELETE /equipamentos/{id}` | `cadastrar/atualizar/excluir` | `gerir_equipamentos` |
| | `POST /equipamentos/{id}/inativar`, `.../reativar` | `inativar`, `reativar` | `gerir_equipamentos` |
| Ordens de serviço | `GET /ordens?status=&criticidade=&equipamento_id=&tecnico_id=&encerrada=` | `listar(FiltroDeOrdens)` | `ver_os` |
| | `GET /ordens/{n}` | `consultar` | `ver_os` |
| | `POST /ordens` | `abrir` | `abrir_os` |
| Diagnóstico e atribuição | `POST /ordens/{n}/diagnostico` | `registrar_diagnostico` | `diagnosticar` (técnico da OS) |
| | `POST /ordens/{n}/atribuicao` (`tecnico_id`, `confirmar_ausente`) | `atribuir` | `atribuir_os` |
| Intervenções e conclusão | `POST /ordens/{n}/reparos` (horas, intervenção, peças) | `apontar_reparo` | `apontar_reparo` (técnico da OS) |
| | `POST /ordens/{n}/status` | `alterar_status` | `atualizar_status` (técnico da OS) |
| | `POST /ordens/{n}/conclusao-tecnica` | `concluir_tecnicamente` | `concluir_os` (técnico da OS) |
| | `POST /ordens/{n}/aprovacao`, `/reprovacao`, `/cancelamento` | `aprovar`, `reprovar`, `cancelar` | `aprovar_os` |
| Histórico | `GET /ordens/{n}/historico`, `POST /ordens/{n}/apontamentos` | `historico`, `adicionar_apontamento` | `ver_os`; `registrar_apontamento` + vínculo |
| Disponibilidade | `GET /disponibilidade` | `ServicoDeDisponibilidade.consultar` | `ver_disponibilidade` |
| | `PUT /me/disponibilidade`, `PUT /usuarios/{id}/disponibilidade` | `alterar_minha_disponibilidade`, `alterar_disponibilidade` | própria: livre; de outro: `gerir_usuarios` |
| Painel inicial | `GET /painel` | contagens por `FiltroDeOrdens` + `consultar` de disponibilidade | `ver_os` |

Pontos técnicos: configuração por variáveis de ambiente (já existe); CORS restrito à origem do
frontend local; escuta em `0.0.0.0` apenas por opção explícita para testes pelo celular na rede
local (o **PostgreSQL continua em `localhost`**, nunca exposto); datas em UTC na API
(D-11), conversão para `America/Sao_Paulo` na interface; OpenAPI gerado pelo FastAPI.

## 3. React

Mobile-first, layouts fluidos, **aplicação web responsiva** (nenhum app nativo).

| Tela | Consome | Observações |
|---|---|---|
| Login | `POST /auth/login`, `GET /auth/me` | trata 401; guarda a sessão conforme D-01 |
| Painel inicial | `GET /painel`, `GET /disponibilidade` | contagens por status, OS em aberto, técnicos |
| Usuários | `/usuarios`, `/cargos` | só Gestor; formulário de cadastro, papel, cargo, permissões, ativo |
| Equipamentos | `/equipamentos` | listar, cadastrar, editar, inativar/reativar, excluir |
| Listagem de OS | `GET /ordens` com filtros | tabela no desktop, **cartões no celular** |
| Detalhes da OS | `GET /ordens/{n}`, `/historico` | histórico, peças, horas, ações permitidas ao ator |
| Abertura de OS | `POST /ordens` | equipamento ativo, criticidade, falha |
| Acompanhamento | detalhes + atualização após cada ação | status e responsável visíveis |
| Ações do técnico | diagnóstico, reparo (peças), status, conclusão técnica | só na OS atribuída ao ator |
| Ações do gestor | atribuição (com confirmação de técnico ausente), aprovar, reprovar, cancelar | |

Requisitos de responsividade (definidos pelo responsável em 2026-11-17):

1. Mobile-first, layouts fluidos.
2. Navegação adaptativa: menu lateral no desktop; menu recolhível no celular.
3. Tabelas extensas viram cartões ou rolagem horizontal **controlada** no celular.
4. Formulários, botões, filtros e modais acessíveis por **toque**.
5. Sem rolagem horizontal da página nem elementos cortados.
6. **Todas** as operações essenciais disponíveis em tela pequena.
7. Larguras de teste: 320, 375, 390, 768, 1024, 1366 e 1920 px.
8. Validar fluxos reais de login, equipamentos, usuários e OS em celular e desktop.
9. Acesso pelo celular na mesma rede local, sem expor o banco.
10. Documentar como iniciar PostgreSQL, backend e frontend e como acessar pelo computador e pelo celular.

Critério de aceitação: funcionar com **mouse, teclado e toque**, não só "parecer" ajustado.

## 4. Decisão D-01 (autenticação): **aprovada e implementada** (ver ADR-0010); texto original da proposta

D-01 está **pendente** em `DECISOES_APROVADAS.md` (a recomendação ali é cookie de sessão
`HttpOnly` ou token de curta duração, senha em hash de biblioteca consolidada e gestor inicial
criado por comando, sem senha no código). Por não estar suficientemente especificada, **nada foi
implementado**. A menor proposta segura:

1. **Senha por usuário, em hash** (`argon2-cffi`/Argon2id; alternativa `bcrypt`): nova coluna
   `usuarios.senha_hash` por migração **0002**, anulável; a senha nunca é gravada, registrada nem
   devolvida.
2. **Sessão por cookie `HttpOnly; SameSite=Lax`** com token opaco aleatório, guardado **em hash**
   numa tabela `sessoes` (usuário, expira em, criada em), validade curta (8 h), `logout` apaga.
   Vantagens: sem JWT, revogação imediata, o JavaScript não lê o token. O usuário **inativo** é
   recusado no login e a cada requisição (`Usuario.exigir_ativo` já existe).
3. **Gestor inicial por comando**: `python -m manutencao.composicao.banco criar-gestor` pede a
   senha no terminal (ou `getpass`), nunca por argumento, variável de ambiente ou arquivo. O
   `semear` de demonstração passaria a **exigir** uma senha de demonstração informada no momento
   (não gravada no repositório).
4. **Sem recuperação de senha por e-mail** (fora do escopo): o Gestor redefine a senha de outro
   usuário (`PUT /usuarios/{id}/senha`), com a regra do último gestor já existente.
5. Limitação de tentativas simples por usuário/IP em memória (proteção básica contra força bruta).
6. CORS com credenciais restrito à origem do frontend local.

Pergunta para decisão: **cookie de sessão (recomendado) ou token `Bearer`?** Aprovando, a API
nasce com a autenticação; sem aprovação, a API não deve ser iniciada, pois `ator_id` não pode vir
do cliente.

## 5. Riscos para o prazo (2026-11-20)

- API + frontend + responsividade + documentação são o grosso do trabalho restante; a persistência
  e as regras já estão prontas e testadas.
- D-01 precisa de aprovação antes da API; tudo depende dela.
- Nenhum PostgreSQL de uso real existe neste computador ainda (ver `PERSISTENCIA.md`).
- A suíte de testes completa leva ~2 min (o PostgreSQL embutido sobe a cada sessão).
