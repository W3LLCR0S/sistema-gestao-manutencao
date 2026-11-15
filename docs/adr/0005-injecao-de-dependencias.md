# ADR-0005 — Injeção de dependências

- **Status:** Aceita para documentação (Fase 01).
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
| **Injeção por construtor, com composição na borda usando `Depends` do FastAPI** (escolhida) | Explícita, sem biblioteca extra, aproveita recurso nativo do *framework* |

## Decisão

- **Injeção por construtor** nos serviços de aplicação: cada serviço declara, como parâmetros, as portas de que precisa
  (`Protocol`), e não importa implementações concretas.
- **Raiz de composição** na camada `api`: funções `Depends` constroem repositórios SQLAlchemy, o relógio, o hash de senha
  e os serviços a cada requisição, com a sessão do banco como dependência de escopo de requisição.
- **Isolamento do *framework***: `Depends` e demais tipos do FastAPI aparecem **somente** em `api`. Os serviços não os
  importam.
- **Testes** substituem dependências por implementações em memória (diretamente no construtor, ou com
  `dependency_overrides` nos testes de API).
- **CLI de transição** (Fase 02) tem sua própria raiz de composição, montando os mesmos serviços.
- Nenhum contêiner de DI de terceiros.

## Justificativa

- Torna DIP concreto e verificável: o serviço não sabe se fala com memória, JSON ou PostgreSQL.
- Evita acoplamento do domínio e da aplicação ao FastAPI.
- Simples de entender e de explicar no relatório.

## Consequências

- A raiz de composição concentra o conhecimento das implementações; deve permanecer pequena e sem regra de negócio.
- A configuração (URL do banco, segredos) entra por variáveis de ambiente lidas na composição; **nunca** no código.
- Se a quantidade de dependências crescer a ponto de a composição manual atrapalhar, reavaliar um contêiner por nova ADR.
