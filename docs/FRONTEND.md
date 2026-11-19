# Frontend (Fase 05)

Aplicação web responsiva em **React 18 + TypeScript + Vite**, em `frontend/`. Consome a API FastAPI real
([`API.md`](API.md)); não há backend paralelo, dados simulados nem armazenamento local de sessão.

## Executar

Três processos, nesta ordem (veja também [`EXECUCAO_LOCAL.md`](EXECUCAO_LOCAL.md)):

```powershell
# 1) PostgreSQL: serviço "postgresql-x64-16" do Windows (já iniciado com o sistema)
# 2) API (a partir de backend/)
$env:PYTHONPATH = "src"
.\.venv\Scripts\python.exe -m manutencao.composicao.servidor      # http://127.0.0.1:8000
# 3) Frontend (a partir de frontend/)
npm install        # só na primeira vez
npm run dev        # http://localhost:5173 (escuta na rede para o celular)
```

Scripts: `npm run dev` · `npm run build` (tsc + vite) · `npm run lint` · `npm run typecheck` · `npm test`.

## Arquitetura

| Pasta (`frontend/src`) | Conteúdo |
|---|---|
| `api/` | `cliente.ts` (fetch, CSRF em memória, `ErroApi`, 401 → login), `servicos.ts` (uma função por endpoint), `tipos.ts` (espelho dos DTOs) |
| `auth/` | contexto de sessão, `RotaProtegida` (por login e por permissão) |
| `componentes/` | layout (menu lateral/móvel), modal acessível, formulários, selos de status, avisos |
| `paginas/` | Login, Painel, Equipamentos, Usuários, Cargos, Ordens, Detalhe da OS, Nova OS, Minha conta |
| `utilitarios/` | formatação (UTC → America/Sao_Paulo), `regras.ts` (quais botões mostrar), `useCarregar` |
| `estilos/global.css` | tokens, layout mobile-first, tabelas que viram cartões |
| `testes/` | Vitest + Testing Library |

Decisões:

- **Mesma origem por proxy.** O Vite encaminha `/api` para `127.0.0.1:8000` com `changeOrigin: false`. O cookie
  `HttpOnly; SameSite=Lax` e o CSRF funcionam sem CORS. Com `changeOrigin: true` a API recusa as escritas
  (`403 origem_nao_permitida`), pois compara `Origin` com `Host`.
- **Sessão:** só o cookie `HttpOnly`. O token CSRF fica **em memória** (recuperado por `GET /auth/me` ao recarregar);
  nada de senha ou token em `localStorage`/`sessionStorage` (há teste para isso).
- **O backend é a autoridade.** `utilitarios/regras.ts` apenas esconde botões inaplicáveis; qualquer ação indevida
  ainda recebe 403/409/422 da API e a mensagem é exibida.
- **401** em qualquer chamada devolve ao login com o aviso "sessão expirou"; 403/404/409/422 e falhas de rede
  aparecem no próprio diálogo ou como aviso.

## Telas

- **Login / Minha conta:** login por matrícula (`AA999999`, maiúsculas automáticas), logout, troca de senha, disponibilidade própria (técnico).
- **Painel:** totais, pendentes, em execução, minhas OS, OS por status e criticidade, técnicos e disponibilidade,
  atividade recente (dados de `GET /painel`).
- **Equipamentos:** busca, filtro, cadastro, edição, inativar/reativar, excluir, detalhes com histórico de OS.
- **Usuários:** busca/filtros, pesquisa por matrícula, cadastro (a matrícula é gerada e exibida na confirmação; senha opcional), edição, cargo, papel, disponibilidade, credencial,
  desativar/reativar, excluir. **Cargos:** permissões por cargo.
- **Ordens de serviço:** listagem com filtros (URL compartilhável), abertura, detalhe com diagnóstico, atribuição
  (com confirmação para técnico ausente, D-03), execução (status, reparos com horas/intervenção/peças),
  conclusão técnica, observações, aprovar/reprovar/cancelar e histórico.

## Responsividade e acessibilidade

Mobile-first; menu lateral fixo a partir de 1024 px e menu recolhível abaixo disso; tabelas viram **cartões**
abaixo de 768 px; áreas de toque de 44 px; modais viram "folha" inferior no celular; foco visível, link "pular
para o conteúdo", `label` em todos os campos, mensagens de erro com `role="alert"`, status nunca só por cor,
`prefers-reduced-motion` respeitado.

## Testes

`npm test`: cliente HTTP (CSRF, 401, 422, rede), regras de ação por papel/estado e fluxos de tela (login, rota
protegida, menu por permissão, logout, validação de formulário). Os testes de tela usam `fetch` simulado
**somente** na fronteira; o fluxo real (login → equipamento → OS → diagnóstico → atribuição → execução → peças →
conclusão → histórico) é validado contra a API e o PostgreSQL reais.

## Limitações conhecidas

- Sem testes automatizados em navegador real (Playwright/Cypress); a validação visual de 320–1920 px é manual.
- Sem paginação na interface (a API limita a 200 itens por consulta).
- Sem "esqueci a senha" (fora do escopo; o Gestor redefine a senha).
- HTTP na rede local não é criptografado ([`ACESSO_PELO_CELULAR.md`](ACESSO_PELO_CELULAR.md)).
- `npm audit` aponta ReDoS em `picomatch` (dependência de ferramentas de desenvolvimento; não entra no build).
