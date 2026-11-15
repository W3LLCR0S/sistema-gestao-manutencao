# Limitações da Entrega 1 e problemas da auditoria inicial

Baseline: commit `e6f7354` (tag local `entrega-1`), aplicação CLI em Python, sem dependências externas.
Este documento registra o que foi observado no código; nada aqui foi corrigido na etapa de documentação.

## Limitações conhecidas da Entrega 1

1. **Login apenas por ID, sem senha.** `Aplicacao.login()` (`ui/aplicacao.py`) lista os usuários e aceita o ID digitado; qualquer pessoa com acesso ao terminal assume qualquer cargo, inclusive o de Gestor.
2. **Persistência em JSON sem suporte adequado a acesso simultâneo.** `Repositorio` (`persistencia/repositorio.py`) carrega o arquivo inteiro na memória e o regrava por completo a cada `salvar()`. A escrita usa arquivo temporário e `os.replace` (evita arquivo truncado), mas não há bloqueio, versionamento nem mesclagem: dois processos ativos ao mesmo tempo sobrescrevem as alterações um do outro (última gravação vence).
3. **Interface somente em terminal.** Não há interface web nem API.
4. **Sem testes automatizados.** O repositório não contém testes de unidade, integração ou ponta a ponta; as regras de negócio não têm verificação automática.
5. **Dados de exemplo fixos.** Na primeira execução sem `dados/dados.json`, o `Repositorio` cria três usuários e três equipamentos de exemplo.

## Problemas encontrados na auditoria

1. **`dados/dados.json` local incompatível com `main.py`.** Um arquivo `dados/dados.json` presente no ambiente local tem a estrutura gerada por `app/persistencia.py` (chaves `seq` e `servicos`, `cargo_id` nos usuários, permissões como `registrar_observacao`), diferente da estrutura que `persistencia/repositorio.py` grava (`cargos`, `usuarios`, `equipamentos`, `ordens`, com o campo de permissão `registrar_apontamento`). O arquivo está no `.gitignore` e não faz parte do repositório. Sem ele, `python main.py` inicia normalmente e cria um novo.
2. **Implementação paralela em `app/`.** O pacote `app/` (menu, módulos, persistência e constantes próprios) duplica a finalidade de `ui/`, `models/` e `persistencia/`. Nenhum código fora de `app/` o importa, e o ponto de entrada `main.py` usa `ui.aplicacao.Aplicacao`; `app/` parece não utilizado. Foi preservado sem alterações. Os dois conjuntos usam o mesmo caminho `dados/dados.json` com formatos diferentes, o que causa o problema anterior.
3. **Ausência de testes automatizados** (ver limitação 4).
4. **Login por ID sem senha** (ver limitação 1).
5. **Persistência JSON sem suporte adequado a acesso simultâneo** (ver limitação 2).

## Tratamento

Estes pontos serão tratados em etapas posteriores, cada uma em sua própria branch e com revisão. A etapa atual é apenas documental e não altera código funcional.
