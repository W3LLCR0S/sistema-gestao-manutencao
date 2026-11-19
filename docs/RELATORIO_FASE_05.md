# Relatório da Fase 05 — Frontend React e validação ponta a ponta

Branch local `feat/frontend` (a partir de `feat/api`, `3d4e1d9`). Nada publicado: sem push, merge ou deploy.
Descrição técnica do frontend: [`FRONTEND.md`](FRONTEND.md). Execução: [`EXECUCAO_LOCAL.md`](EXECUCAO_LOCAL.md).

## O que foi entregue

Aplicação React 18 + TypeScript + Vite em `frontend/` (44 arquivos, +8744/−2 em relação à `feat/api`), consumindo
a API real; sem dados simulados nem sessão em `localStorage`. Commits da fase (todos locais):

| SHA | Mensagem |
|---|---|
| `fa15312` | feat(frontend): estrutura inicial, cliente HTTP e navegação |
| `70fedfb` | feat(frontend): autenticação e sessão |
| `b6ac917` | feat(frontend): painel e equipamentos |
| `b261dff` | feat(frontend): usuários, cargos e permissões |
| `e546db9` | feat(frontend): fluxo de ordens de serviço e rotas |
| `35dc324` | test(frontend): cliente HTTP, regras de ação e fluxos de tela |
| `b60dc34` | fix(frontend): manter o Host do navegador no proxy /api |
| `9e896a4` | docs: frontend, execução local e acesso pelo celular |
| (este) | docs: relatório da Fase 05 e validação ponta a ponta |

## Verificações executadas (2026-11-18)

**Estáticas e automatizadas**

- Backend (`backend/`, venv): `pytest` **3113 passed, 46 skipped** (228 s); `ruff check` e `ruff format --check`
  (184 arquivos) limpos; `mypy` strict sem erros (181 arquivos).
- Frontend: `npm run typecheck`, `npm run lint` limpos; `npm test` **27 passed** (3 arquivos); `npm run build` OK
  (JS 236 kB, 72 kB gzip).

**Ponta a ponta no PostgreSQL permanente** (API real em `127.0.0.1:8000`, banco `manutencao`, migração 0002)

- Login real dos três usuários fictícios do seed (`ana` Gestor; `bruno` e `carla` Técnicos); as senhas do seed
  foram redefinidas com o comando administrativo `banco definir-acesso --senha-stdin` (Argon2id, política de
  10+ caracteres mantida), por autorização expressa do usuário.
- Script HTTP com 48 verificações: **47 aprovadas, 1 divergente por expectativa errada do teste** (ver abaixo).
  Cobriu: senha errada (401), rota sem sessão (401), CSRF inválido (403), permissões de Técnico negadas
  (cadastrar equipamento, listar usuários, gerir cargos, atribuir, aprovar, cancelar), Técnico não responsável
  barrado, ciclo completo da OS (abrir → atribuir → Em Execução → diagnóstico → reparo com peça → observações do
  Técnico e do Gestor → Reparo Finalizado → conclusão técnica → aprovação → Concluída), OS encerrada imutável,
  histórico, técnico ausente recusado e atribuição com confirmação explícita (D-03), reatribuição, cancelamento com
  motivo obrigatório, reprovação, equipamento com OS não excluível, proteção do último gestor e da autoexclusão,
  cadastro/desativação de usuário e logout que invalida a sessão.
- A divergência: o teste esperava `sem_diagnostico` ao finalizar sem diagnóstico; a API respondeu
  `422 sem_intervencao`. É o comportamento documentado (DLT-06: a intervenção é verificada primeiro); a expectativa
  do script é que estava errada. Nenhuma falha de produto.
- Integração React → FastAPI → PostgreSQL: login, `/auth/me`, lista de OS, painel, `/usuarios` (Gestor 200, Técnico
  403) e logout, **pelo proxy do Vite** (`localhost:5173/api`, o mesmo caminho do navegador, com `Origin` da
  origem do frontend). 10 de 12 verificações passaram na primeira execução; as 2 restantes eram o formato
  esperado de `/auth/me` no script (as permissões vêm em `usuario.permissoes`, 9 para o Técnico); confirmado
  manualmente.

**Registros criados (identificados `E2E`; nenhum dado anterior alterado)**: equipamento 4 "E2E Prensa", OS 6
(Concluída), OS 7 e 8 (Canceladas), usuário 4 "E2E Usuario" (desativado). O estado de disponibilidade de Bruno foi
restaurado a Disponível. OS 1–5 e equipamentos 1–3 intactos.

## Pendências e limitações (sem afirmar o que não foi feito)

- **Verificação visual no navegador NÃO realizada**: a extensão do Chrome não estava conectada. Telas, larguras
  320/375/768/1024/1440 px, ausência de overflow horizontal, foco e contraste só foram cobertos pelos 27 testes
  automatizados e pelo código; precisam de conferência manual (inclusive no celular).
- Não houve login pela interface (digitar senha no formulário); o fluxo foi exercido por HTTP via proxy.
- Python 3.8, CLI legada e `dados/dados.json` seguem não verificados; sem concorrência otimista nas OS; HTTP sem TLS
  (uso em rede doméstica).
- Os 5 itens do E2E acima ficam no banco local como registros de teste; podem ser mantidos como evidência.
- Merge e push da Fase 05 dependem de `AUTORIZO MERGE FASE 05` (não dado).

## Segurança do procedimento

Senha de teste lida de arquivo temporário local e enviada por stdin sem pipeline do shell; não foi impressa nem
registrada em commit ou relatório; o arquivo foi excluído ao final. Um trecho do script que continha texto de
prompt apareceu na saída de uma checagem intermediária; recomenda-se tratar essa senha como comprometida.
