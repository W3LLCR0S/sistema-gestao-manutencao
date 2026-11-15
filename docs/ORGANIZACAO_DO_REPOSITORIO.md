# Organização do repositório

Este documento descreve como o repositório está organizado **hoje** e define diretrizes para o crescimento do projeto.
As seções 1 a 5 descrevem o estado atual e verificável. A seção 6 descreve uma **arquitetura futura planejada**: nada
dela está implementado, e não deve ser lida como descrição do código existente.

## 1. Estrutura atual

```
.
├── main.py                  # ponto de entrada da CLI (usa ui.aplicacao.Aplicacao)
├── models/                  # classes do domínio e regras de negócio
├── persistencia/            # Repositorio: guarda objetos e salva/carrega o JSON
├── ui/                      # telas do terminal
├── app/                     # implementação paralela, aparentemente não utilizada
├── dados/                   # dados locais (somente .gitkeep é versionado)
├── docs/                    # documentação de desenvolvimento
├── README.md                # uso e visão geral da Entrega 1
├── DOCUMENTACAO.md          # decisões de projeto da Entrega 1
├── .gitignore
└── .gitattributes
```

## 2. Responsabilidade de cada diretório

| Caminho | Responsabilidade hoje |
|---------|-----------------------|
| `main.py` | Inicia `Aplicacao`. Não contém regra de negócio. |
| `models/` | Entidades (`Usuario`, `Cargo`, `OrdemServico`, `Servico`, `Equipamento`, `PecaMaterial`), enums, permissões e exceções de regra de negócio. |
| `persistencia/` | `Repositorio`: mantém os objetos em memória e grava/lê `dados/dados.json`. |
| `ui/` | Telas e entrada de dados do terminal, com menus conforme as permissões do cargo. |
| `app/` | Pacote com menu, módulos, persistência e constantes próprios, que duplica a finalidade de `ui/`, `models/` e `persistencia/`. Nenhum código fora dele o importa. Preservado sem alterações; ver `LIMITACOES_E_AUDITORIA.md`. |
| `dados/` | Local do arquivo de dados em tempo de execução. |
| `docs/` | Documentação de desenvolvimento (seção 3). |

## 3. Documentação

| Arquivo | Conteúdo |
|---------|----------|
| `README.md` | Como executar e visão geral da Entrega 1. |
| `DOCUMENTACAO.md` | Decisões de projeto da Entrega 1. |
| `docs/FLUXO_DE_DESENVOLVIMENTO.md` | Branches, commits, revisão, merge e tags. |
| `docs/LIMITACOES_E_AUDITORIA.md` | Limitações conhecidas da Entrega 1 e problemas da auditoria inicial. |
| `docs/ORGANIZACAO_DO_REPOSITORIO.md` | Este documento. |
| `docs/README.md` | Índice da documentação, incluindo auditoria, matriz de requisitos, ADRs, diagramas e plano de migração (Fase 01). |

Documentação de desenvolvimento fica em `docs/`. `README.md` e `DOCUMENTACAO.md` permanecem na raiz.

## 4. O que o Git inclui e ignora

**Versionado:** código-fonte (`main.py`, `models/`, `persistencia/`, `ui/`, `app/`), documentação (`README.md`,
`DOCUMENTACAO.md`, `docs/`), `dados/.gitkeep`, `.gitignore` e `.gitattributes`.

**Ignorado** (conforme o `.gitignore`):

- caches e artefatos de Python (`__pycache__/`, `*.pyc`, `build/`, `dist/`, caches de ferramentas, relatórios de cobertura);
- ambientes virtuais (`venv/`, `.venv/`, `env/`, `ENV/`);
- segredos e configuração local (`.env`, `.env.*`, `*.pem`, `*.key`);
- dados locais (`dados/*`, exceto `dados/.gitkeep`; também `*.db`, `*.sqlite`, `*.sqlite3`, `*.tmp`);
- logs, arquivos de IDE e do sistema operacional (`*.log`, `.vscode/`, `.idea/`, `.DS_Store`, `Thumbs.db`);
- materiais de trabalho privados do autor, mantidos fora do repositório.

## 5. Regras de higiene

### Arquivos de configuração

- Configuração sensível ou específica de cada máquina nunca é versionada. Use variáveis de ambiente ou `.env` local.
- Quando houver configuração necessária, versionar apenas um modelo sem valores reais (por exemplo `.env.example`) e
  documentar cada variável.
- Alterações no `.gitignore` entram em commit próprio (`chore:`).

### Proteção dos dados locais

- `dados/dados.json` pode conter dados reais e **não deve ser versionado**. A pasta existe no repositório só pelo `.gitkeep`.
- Antes de cada commit, confirmar com `git diff --cached --name-only` que nenhum arquivo de `dados/`, `.env` ou chave foi incluído.
- Não usar `git add -f` para contornar o `.gitignore`.
- Antes de qualquer migração ou alteração de formato dos dados, fazer cópia de segurança do arquivo local.
- Atenção: o `dados/dados.json` de uma máquina pode ter formato diferente do esperado por `main.py` (ver `LIMITACOES_E_AUDITORIA.md`).

### Convenções para novos arquivos

- Python: nomes de módulos e pastas em `snake_case`, minúsculos e sem acentos; classes em `PascalCase`.
- Documentação: Markdown em `docs/`, com nome em maiúsculas e sublinhados, como os existentes.
- Novo código vai na camada adequada à sua responsabilidade; não criar um terceiro conjunto paralelo de módulos.
- Não versionar artefatos gerados, binários desnecessários ou dados reais.
- Uma mudança por commit, com mensagem convencional (ver `FLUXO_DE_DESENVOLVIMENTO.md`).

## 6. Arquitetura futura (planejada, NÃO implementada)

> Esta seção é uma diretriz de direção. Nenhum dos itens abaixo existe no código atual. Os detalhes serão definidos e
> aprovados em etapas posteriores, e este documento será atualizado quando houver implementação.

**Organização por camadas.** A evolução prevista separa:

- **Domínio:** entidades e regras de negócio, sem dependência de interface nem de armazenamento. Hoje isso corresponde,
  em parte, a `models/`.
- **Aplicação:** casos de uso que orquestram o domínio.
- **Persistência:** acesso a dados atrás de uma interface (padrão Repository), de modo que a tecnologia de
  armazenamento possa mudar sem afetar o domínio. Hoje existe apenas `persistencia/repositorio.py`, acoplado ao JSON.
- **Interface:** entrada e saída. Hoje é o terminal em `ui/`.

**Frontend e backend.** A intenção é uma aplicação web em que o frontend e o backend fiquem em diretórios separados,
comunicando-se por uma API, com regras de negócio apenas no backend. A estrutura de pastas definitiva e o contrato
da API ainda **não foram definidos**. A direção técnica aprovada para documentação (stack, camadas, Repository,
injeção de dependências e testes) está registrada em [`adr/`](adr/README.md); continua **não implementada**.

**Qualidade.** Hoje não há testes automatizados. Testes serão introduzidos em etapa própria, em diretório dedicado.

## 7. Relação entre branches e fases

O trabalho é dividido em fases sequenciais. Cada fase usa uma branch exclusiva, criada a partir da `main` atualizada, e
só chega à `main` por merge `--no-ff` após revisão. Uma fase só começa depois que a anterior foi concluída e autorizada.

| Fase | Foco | Branch |
|------|------|--------|
| 00 | Publicação inicial e baseline | `setup/repositorio` |
| 01 | Auditoria técnica e arquitetura-alvo | `docs/auditoria` |
| 02 | Refatoração do domínio | `refactor/arquitetura` |
| 03 | Persistência | `feat/persistencia` |
| 04 | API e autenticação | `feat/api-autenticacao` |
| 05 | Frontend base | `feat/frontend-base` |
| 06 | Cadastros | `feat/gestao-cadastros` |
| 07 | Ordens de serviço | `feat/ordens-servico` |
| 08 | Dashboard e histórico | `feat/dashboard-historico` |
| 09 | Testes e segurança | `test/qualidade` |
| 10 | Publicação em produção | `deploy/producao` |
| 11 | Documentação final | `docs/entrega-final` |

Esta tabela indica a **intenção** de organização; o escopo de cada fase pode ser ajustado e só vale quando a fase for
iniciada. As branches são preservadas após o merge. A tag `entrega-1` marca o baseline da Entrega 1.
