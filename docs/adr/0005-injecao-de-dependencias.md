# ADR-0005 — Injeção de dependências

- **Status:** Aceita; **implementada na Fase 02** (injeção por construtor e raiz de composição). Os provedores `Depends` do FastAPI ficam para a Fase 04.
- **Data:** 2026-11-15
- **Relacionados:** ADR-0002, ADR-0004; AUD-16; E2-SOL-05, E2-PAD-01

## Contexto

`Aplicacao.__init__` cria `Repositorio()` diretamente (`ui/aplicacao.py:19`) e as telas o acessam por `self.app.repo`.
Não há como executar uma tela ou regra com outro armazenamento, nem com um dublê de teste. O construtor do
`Repositorio` ainda tem efeitos colaterais (lê ou cria o arquivo de dados). Na arquitetura-alvo, serviços de aplicação
precisam receber repositórios, relógio e serviço de hash sem conhecer as implementações concretas.

## Alternativas consideradas

| Alternativa | Avaliação |
|-------------|-----------|
| Importar e instanciar classes concretas nos serviços (situação atual) | Impede substituição e teste isolado; viola DIP |
| *Service Locator* / singletons globais | Esconde dependências e dificulta testes paralelos |
| Biblioteca de contêiner de DI | Dependência adicional sem ganho claro para o tamanho do sistema |
| **Injeção por construtor, com raiz de composição própria e provedores `Depends` do FastAPI que obtêm o serviço pronto** (escolhida) | Explícita, sem biblioteca extra, aproveita recurso nativo do *framework* e mantém a `api` sem importar `infrastructure` |

## Decisão

- **Injeção por construtor** nos serviços de aplicação: cada serviço declara, como parâmetros, as portas de que precisa
  (`Protocol`), e não importa implementações concretas.
- **Raiz de composição** em módulo próprio (`composicao`, ver [ADR-0002](0002-arquitetura-em-camadas.md)), a camada mais
  externa: cria repositórios SQLAlchemy, o relógio e o hash de senha, monta os serviços (com a sessão do banco em escopo
  de requisição) e os disponibiliza à aplicação FastAPI. É o **único** lugar que importa as implementações concretas.
- **A `api` não importa `infrastructure`.** Suas funções `Depends` apenas **obtêm o serviço pronto** do contêiner
  registrado pela raiz de composição. A API depende de `application`; a raiz de composição depende de todas as camadas.
- **Casos de uso dependem de abstrações** (`Protocol` definidos em `application`), nunca de classes concretas.
- **Isolamento do *framework***: `Depends` e demais tipos do FastAPI aparecem **somente** em `api` e `composicao`. Os
  serviços de aplicação e o domínio não os importam.
- **Testes** substituem dependências por implementações em memória (diretamente no construtor, ou com
  `dependency_overrides` nos testes de API).
- Por D-10 (aprovada), não há CLI sobre os novos serviços: a CLI legada permanece como está e não usa a injeção.
- O relógio é uma porta de `application` e seu instante é entregue ao domínio como argumento
  ([ADR-0007](0007-datas-fuso-horario-e-relogio.md)); o domínio não recebe dependências injetadas.
- Nenhum contêiner de DI de terceiros.

## Justificativa

- Torna DIP concreto e verificável: o serviço não sabe se fala com memória, JSON ou PostgreSQL.
- Evita acoplamento do domínio e da aplicação ao FastAPI.
- Simples de entender e de explicar no relatório.

## Consequências

- A raiz de composição concentra o conhecimento das implementações; deve permanecer pequena e sem regra de negócio.
- A configuração (URL do banco, segredos) entra por variáveis de ambiente lidas na composição; **nunca** no código.
- Se a quantidade de dependências crescer a ponto de a composição manual atrapalhar, reavaliar um contêiner por nova ADR.

## Revisão ao encerrar a Fase 02 (2026-11-17)

Implementado: serviços recebem portas pelo construtor (`application/servicos/*.py`); `composicao/container.py: montar` conhece só abstrações; `composicao/fabrica.py: criar_container_em_memoria` é o único módulo que importa implementações concretas (`test_so_a_fabrica_da_composicao_importa_a_infraestrutura`); sem localizador de serviços nem estado global (`test_nao_ha_localizador_de_servicos_nem_cache_de_instancia`). Os testes substituem implementações sem tocar o serviço (`aplicacao/test_injecao_de_dependencias.py`).
