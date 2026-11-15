# Fluxo de desenvolvimento

Convenções de Git adotadas neste repositório. Valem para todo o trabalho posterior à Entrega 1.

## Branches

- `main`: histórico estável e auditável. Só recebe alterações por merge de uma branch de trabalho, depois de revisão.
- Uma branch por etapa de trabalho, criada a partir da `main` atualizada, com prefixo que indica a natureza:
  `setup/`, `docs/`, `refactor/`, `feat/`, `fix/`, `test/`, `deploy/`.
  Exemplo: `setup/repositorio`.
- Branches não são apagadas após o merge, para preservar o histórico.
- Nunca se faz commit direto na `main`.

## Commits

Mensagens no padrão *Conventional Commits*: `<tipo>: <descrição no imperativo, em minúsculas>`.

| Tipo | Uso |
|------|-----|
| `feat` | nova funcionalidade |
| `fix` | correção de defeito |
| `refactor` | mudança interna sem alterar comportamento |
| `test` | criação ou ajuste de testes |
| `docs` | documentação |
| `chore` | configuração, manutenção, importação |

Diretrizes:
- commits pequenos e focados em uma única mudança;
- não misturar documentação, refatoração e mudança funcional no mesmo commit;
- nunca incluir segredos, `.env`, bancos locais, dados reais ou artefatos gerados.

## Revisões

Antes de cada commit:
1. `git status --short` e `git branch --show-current` para confirmar o que será versionado e em qual branch;
2. `git diff` (ou `git diff --cached`) lido por inteiro;
3. conferir `git diff --cached --name-only` em busca de arquivos sensíveis ou locais (`dados/*.json`, `.env`, chaves, logs);
4. executar os testes da etapa, quando existirem, e registrar o resultado real.

## Merge

- Merge sempre **não-fast-forward** (`git merge --no-ff`), para que cada etapa fique visível como um conjunto no histórico.
- O merge só ocorre após revisão e aprovação explícita; o push da `main` é feito depois do merge e verificado contra `origin/main`.
- Proibidos sem aprovação específica: `push --force`, `reset --hard`, `clean -fd`, rebase destrutivo e exclusão de branches.

## Tags

- `entrega-1` marca o baseline fiel da Entrega 1 (commit `e6f7354`, "chore: import initial CLI maintenance system").
- Tags são anotadas e só são publicadas com decisão explícita.
