# ADR-0010 — Autenticação e sessão (D-01)

- **Status:** Aprovada pelo responsável em 2026-11-17; **implementada na Fase 04** (branch `feat/api`).
- **Data:** 2026-11-17
- **Relacionados:** AUD-01 (login só por identificador); ADR-0003 (autorização no servidor);
  [`DECISOES_APROVADAS.md`](../DECISOES_APROVADAS.md) (D-01); [`API.md`](../API.md);
  [`ACESSO_PELO_CELULAR.md`](../ACESSO_PELO_CELULAR.md)

## Contexto

O legado "autenticava" por identificador de usuário, sem senha, e o `ator_id` de cada caso de uso era
simplesmente um número. A API web não pode confiar em um identificador enviado pelo cliente: quem é o ator
precisa ser decidido pelo servidor. O sistema roda localmente (sem hospedagem pública) e será usado por
navegador (React) em computador e celular.

## Decisão (política aprovada)

| Aspecto | Decisão |
|---|---|
| Identificação | `login` (único, sem diferenciar maiúsculas) + senha |
| Senha | Hash **Argon2id** (`argon2-cffi`, parâmetros padrão da biblioteca), renovado no login se os parâmetros mudarem; 10 a 128 caracteres; não pode ser igual ao login |
| Sessão | **Do servidor**, persistida no PostgreSQL (`sessoes`); token aleatório de 256 bits; o servidor guarda **só o `sha256`** do token |
| Transporte | Cookie `HttpOnly`, `SameSite=Lax`, `Path=/`; `Secure` quando a API é servida por HTTPS (`MANUTENCAO_API_COOKIE_SECURE`) |
| Expiração | Absoluta, 8 h por padrão (`MANUTENCAO_SESSAO_HORAS`, 1 a 72); não se renova com o uso |
| Logout | Revoga a sessão no servidor (reapresentar o cookie antigo não funciona) |
| CSRF | *Synchronizer token*: cabeçalho `X-CSRF-Token` (valor de `csrf_token`) exigido em `POST/PUT/PATCH/DELETE`; **mais** verificação de `Origin` e `SameSite=Lax` |
| Autorização | Papéis e permissões existentes (D-02, ADR-0009), lidos **a cada requisição** (uma permissão alterada vale na seguinte) |
| Usuário inativo | Não entra; a cada requisição, usuário inativo ou excluído perde as sessões (e `desativar` as revoga explicitamente) |
| Ator | Sempre `autenticado.usuario.id`, da sessão. Entradas usam `extra="forbid"`: `ator_id` no corpo é 422 |
| Primeiro gestor | Procedimento **administrativo** por linha de comando (`criar-gestor`); senha pedida sem eco ou por `--senha-stdin`; nunca em argumento, variável de ambiente ou arquivo; nenhuma credencial no código |
| Recuperação | Sem e-mail. O Gestor redefine a credencial (`PUT /usuarios/{id}/credencial`) ou o administrador do servidor usa `definir-acesso` |
| Força bruta | 5 falhas por `ip\|login` em 15 min bloqueiam com 429 (`Retry-After`) |

**Não implementado, por decisão:** OAuth, login social, recuperação por e-mail, autenticação externa, JWT.

## Alternativas consideradas

- **JWT/token `Bearer`:** descartado. Exigiria guardar o token no JavaScript (exposto a XSS), não permite
  revogação imediata sem estado no servidor e traz complexidade sem ganho para uma aplicação de mesma origem.
- **Sessão em dicionário de memória:** descartado (vetado): não sobrevive a reinício nem a mais de um processo.
- **Hash com bcrypt/PBKDF2:** Argon2id é o recomendado atual (resistente a GPU); a biblioteca é consolidada.

## Consequências

- Cada requisição autenticada lê a sessão e o usuário no banco (uma ou duas consultas). Aceitável na escala do
  projeto; um cache exigiria cuidar da revogação imediata.
- O limitador de tentativas é **em memória do processo**: com vários processos, cada um conta o seu. Uma
  instância única (o caso local) é coberta.
- Em HTTP (desenvolvimento) o cookie **não** tem `Secure` e o tráfego não é criptografado: ver
  [`ACESSO_PELO_CELULAR.md`](../ACESSO_PELO_CELULAR.md). Não há equivalência entre HTTP na rede local e HTTPS.
- O `csrf_token` é guardado em texto na sessão (é inútil sem o cookie). O token de sessão **não** é.

## Verificação

`backend/tests/api/test_autenticacao.py` (login, senha incorreta, usuário inexistente, usuário inativo, sessão
expirada, logout, CSRF, origem, limite, troca de senha), `tests/aplicacao/test_autenticacao.py`,
`tests/api/test_contrato.py` (toda operação exige autenticação e CSRF; nenhum esquema aceita ator nem expõe hash)
e `tests/integracao/test_api_postgres.py` (sobrevive ao reinício; só hash no banco; comandos administrativos).
