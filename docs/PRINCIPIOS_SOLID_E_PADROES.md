# SOLID e padrões de projeto: situação atual e plano

Este documento diferencia, para cada princípio e padrão, **o que existe hoje** (baseline `e6f7354`, verificável no
código) do que está **planejado** (não implementado). Nada na coluna "planejado" deve ser lido como já demonstrado.
O relatório final (Fase 11) só poderá afirmar que um princípio foi aplicado com arquivo, linha e teste reais.

Referências: achados `AUD-nn` em [`AUDITORIA_ARQUITETURAL.md`](AUDITORIA_ARQUITETURAL.md); requisitos `E2-SOL-nn` e
`E2-PAD-01` em [`MATRIZ_RASTREABILIDADE.md`](MATRIZ_RASTREABILIDADE.md); decisões em [`adr/`](adr/README.md).

## 1. Princípios SOLID

Resumo:

| Princípio | Requisito | Situação hoje | Fase de aplicação |
|-----------|-----------|---------------|-------------------|
| SRP | E2-SOL-01 | Parcial | 02 |
| OCP | E2-SOL-02 | Não atendido | 02 |
| LSP | E2-SOL-03 | **Não demonstrado** (sem exemplos concretos) | 02, 03 |
| ISP | E2-SOL-04 | Não atendido | 02 |
| DIP | E2-SOL-05 | Parcial | 02, 04 |

### 1.1 SRP — Responsabilidade Única

**Implementação atual:** o domínio está separado de interface e persistência em pacotes distintos, e as regras da OS
ficam nos métodos da entidade (ponto positivo). Porém:
- `OrdemServico` (`models/ordem_servico.py`, 237 linhas) acumula máquina de estados, autorização
  (`usuario.exigir`), geração do histórico, formatação de data (`_agora`, `:21-22`) e serialização (`to_dict`/`from_dict`,
  `:195-237`) (AUD-15, AUD-07).
- `Repositorio` (`persistencia/repositorio.py`) acumula persistência, geração de IDs, consultas, regras
  (`remover_*`, `carga`, `atualizar_disponibilidades`) e dados de exemplo (AUD-10).
- As telas de `ui/` alteram entidades diretamente e decidem quando gravar (AUD-09, AUD-16).

**Solução planejada:**

| Responsabilidade | Destino |
|------------------|---------|
| Estados, transições e invariantes da OS; histórico sequencial | Entidade `OrdemServico` em `domain` |
| Autorização e orquestração do caso de uso | Serviços de `application` |
| Conversão entidade ↔ JSON/tabela | Mapeadores em `infrastructure` |
| Hora atual | Porta `Relogio` em `application`; o caso de uso obtém o instante e o **entrega ao domínio** como argumento (ADR-0007) |
| Persistência e consulta | Repositórios em `infrastructure`, sem regra de negócio |
| Entrada/saída | `api` (e CLI de transição), sem regra de negócio |

**Como será demonstrado ou testado:** (a) teste de arquitetura: `domain` não importa `json`, FastAPI, SQLAlchemy nem
define `to_dict`/`from_dict`; (b) testes de unidade da entidade sem repositório e testes de serviço com repositório em
memória; (c) relatório lista cada classe com sua única responsabilidade, com arquivo e linha reais.

### 1.2 OCP — Aberto/Fechado

**Implementação atual:** adicionar uma permissão exige editar três pontos da mesma classe: `DESCRICOES`, a assinatura de
`__init__` e a atribuição de atributos (`models/permissoes.py:8-53`) (AUD-03). Adicionar um status ou transição exige
alterar vários métodos de `OrdemServico` (`_exigir_status` espalhado em `:106,115,125,141,174,...`), e a lista de permissões
do menu é montada à mão (`ui/aplicacao.py:29-48`). Não há ponto de extensão.

**Solução planejada:** tornar a variação **dado** quando houver variação real, e não abstração especulativa:
- permissões como **enumeração** (`Permissao`) e papéis como mapeamento papel → conjunto de permissões;
- **tabela de transições** da OS (status atual, ação → status destino e quem pode), consultada pelos métodos da entidade;
- itens de menu/rotas derivados da permissão exigida, não de lista manual.

**Como será demonstrado ou testado:** teste que acrescenta uma permissão e uma transição **sem modificar o código
existente de verificação** (apenas dados/registro novo), e teste parametrizado que percorre toda a tabela de transições
(válidas e inválidas). Fica registrado que OCP só é alegado onde essa demonstração existir; não será forçado em classes
estáveis.

### 1.3 LSP — Substituição de Liskov

**Implementação atual:** o domínio não tem hierarquias de classes que se especializem (as únicas heranças são
`Enum`, `Exception` em `RegraNegocioError` e `TelaBase`/telas). **Não há exemplo concreto de LSP no baseline e ele não deve ser alegado como demonstrado.**

**Solução planejada:** o ponto natural de substituição são as **portas de repositório** (ADR-0004), que terão ao menos
duas implementações: em memória e SQLAlchemy (e, só se necessário, um JSON de transição). Para que uma possa substituir a
outra, o comportamento observável deve ser o mesmo: tipo de retorno, ausência (resultado vazio ou erro de não encontrado,
um só critério), ordenação das listas, tratamento de duplicidade e erro de conflito de versão.

**Como será demonstrado ou testado (nada disso existe hoje):** **suíte de contrato** parametrizada, executada
contra todas as implementações da mesma porta, e verificação de tipos com **`mypy`** (introduzido na Fase 02, D-13)
confirmando que cada implementação satisfaz o `Protocol`. LSP só será declarado demonstrado quando a suíte passar para
as duas implementações **e** o `mypy` aprovar ambas.

### 1.4 ISP — Segregação de Interfaces

**Implementação atual:** existe uma única classe ampla, `Repositorio`, usada por todas as telas, que dependem do conjunto
inteiro mesmo usando poucas operações (por exemplo `TelaOrdens` usa buscas de OS, equipamento, técnicos e carga).
Não há interfaces.

**Solução planejada:** portas pequenas por agregado e por finalidade (`OrdemServicoRepository`, `UsuarioRepository`,
`EquipamentoRepository`; eventuais portas de leitura para o *dashboard*; porta de relógio; porta de hash de senha). Cada
serviço declara apenas as portas de que usa.

**Como será demonstrado ou testado (nada disso existe hoje):** as assinaturas dos construtores dos serviços listam só as
portas necessárias; os testes usam dublês que implementam apenas essas operações e o **`mypy`** (Fase 02) rejeita o uso de
método fora da porta declarada; revisão de que nenhuma porta carrega métodos que seus clientes não chamam.

### 1.5 DIP — Inversão de Dependências

**Implementação atual:** parcial. Ponto positivo: o domínio não importa `ui/` nem `persistencia/`. Ponto negativo:
`Aplicacao` instancia `Repositorio()` (`ui/aplicacao.py:19`), as telas dependem do concreto (`ui/tela_base.py:18-20`) e o
`Repositorio` conhece detalhes do JSON e carrega regras (AUD-10, AUD-16).

**Solução planejada:** casos de uso dependem de **portas** (`Protocol`) definidas em `application`; implementações ficam
em `infrastructure`; a **raiz de composição** (`composicao`, a camada mais externa) cria as implementações concretas e as
liga às abstrações por injeção (ADR-0005), de modo que a `api` não importa `infrastructure`. `domain` e `application` não
importam FastAPI, SQLAlchemy nem `infrastructure`, e o `domain` não importa `application` (o relógio é porta de
`application` e seu instante chega ao domínio como argumento, ADR-0007).

**Como será demonstrado ou testado (nada disso existe hoje):** teste de arquitetura de importações (inclusive
`domain` não importar `application` e `api` não importar `infrastructure`); verificação de tipos com **`mypy`** (Fase
02); os mesmos serviços executados com repositórios em memória (unidade) e SQLAlchemy (integração) sem alteração; evidência
de que trocar a implementação não altera `domain` nem `application` (diff vazio nessas camadas na troca de repositório).
DIP só será declarado demonstrado quando esses testes existirem e passarem.

## 2. Padrões de projeto

O enunciado exige **pelo menos um** padrão reconhecido e a justificativa do problema que ele resolve. Adotam-se poucos
padrões, cada um ligado a um problema concreto já evidenciado na auditoria.

### 2.1 Padrões adotados

| Padrão | Situação hoje | Fase | Problema que resolve |
|--------|---------------|------|----------------------|
| **Repository** | Não implementado. O `Repositorio` atual não tem contrato nem implementação alternativa e carrega regras; **não conta como padrão demonstrado** | 02 (porta e versão em memória), 03 (SQLAlchemy) | AUD-10, AUD-16, AUD-04 a AUD-06: persistência acoplada ao JSON, regras no repositório, impossibilidade de trocar o armazenamento ou testar isoladamente |
| **Dependency Injection** | Não implementado (`Aplicacao` cria `Repositorio()` direto) | 02 (construtores e raiz de composição), 04 (provedores `Depends` na API) | AUD-16: dependências concretas dentro das classes, sem substituição nem teste isolado |
| **Service Layer** | Não implementado; regras de orquestração estão nas telas | 02 | AUD-02, AUD-09: autorização e orquestração repetidas ou ausentes em cada adaptador (CLI, API) |

**Repository**
- *Alternativas:* *Active Record* com modelos do ORM como entidades; sessão do ORM exposta aos serviços; repositório
  genérico único; arquivo JSON com bloqueio (detalhes no ADR-0004).
- *Escolha:* repositório por agregado, com porta em `application` e adaptadores em `infrastructure`. Preserva o domínio
  livre de ORM e dá um ponto único para controle de versão e transação.
- *Evidência futura:* porta + ao menos duas implementações + suíte de contrato aprovada em ambas.

**Dependency Injection**
- *Alternativas:* instanciar classes concretas; *Service Locator*/singleton global; contêiner de DI de terceiros
  (detalhes no ADR-0005).
- *Escolha:* injeção por construtor, com raiz de composição própria e provedores `Depends` do FastAPI que obtêm o
  serviço pronto. Sem biblioteca extra.
- *Evidência futura:* construtores dos serviços recebendo portas; testes de unidade e de API trocando dependências.

**Service Layer**
- *Alternativas:* regras nas rotas/telas; entidades anêmicas com toda regra em serviços (rejeitada, pois o baseline já
  encapsula bem as invariantes na entidade).
- *Escolha:* serviços de aplicação finos, que carregam agregados, verificam permissão, chamam a entidade e confirmam a
  transação. Invariantes permanecem no domínio.
- *Evidência futura:* um serviço por conjunto coeso de casos de uso (OS, equipamentos, usuários); CLI e API usando os mesmos serviços.

### 2.2 Padrões considerados e **não** adotados agora

Para evitar abstração artificial, estes padrões foram avaliados e adiados ou descartados:

| Padrão | Decisão | Motivo |
|--------|---------|--------|
| **State** (um objeto por status da OS) | Adiado | São 8 status e transições simples; uma **tabela de transições** (ver OCP) resolve com menos código. Reavaliar apenas se o comportamento por estado crescer |
| **Strategy** (política de atribuição, disponibilidade, permissão) | Adiado | Hoje há um único critério (ordenar por carga, `ui/tela_gestor.py:16`) e a regra de disponibilidade foi mantida (D-05, sem novas regras de ocupação). Só se justifica se surgirem critérios alternativos reais |
| **Observer / eventos de domínio** (gerar histórico) | Descartado | O histórico faz parte do agregado `OrdemServico` e é gerado na própria transição, de forma síncrona e atômica |
| **Factory Method** | Já existe, não será contado | `OrdemServico.abrir` (`models/ordem_servico.py:88-96`) é um método de fábrica que garante o estado inicial e o primeiro registro de histórico; será mantido sem ser apresentado como padrão novo |
| **Unit of Work** | Parte do ADR-0004 (proposta) | Tende a ser a sessão do SQLAlchemy usada como unidade de trabalho; não será implementado como camada própria sem necessidade |
| **MVC/MVVM** | Não adotado | O frontend é uma SPA separada; a organização é por camadas (ADR-0002), não por MVC |

## 3. Plano de evidências

| Item | Evidência que será exigida antes de afirmar "aplicado" |
|------|--------------------------------------------------------|
| SRP | Teste de arquitetura sem serialização/ORM no domínio; classes com responsabilidade única descritas com arquivo e linha |
| OCP | Teste que estende permissões/transições sem editar a lógica existente |
| LSP | Suíte de contrato aprovada em todas as implementações de cada porta **e** `mypy` aprovando a conformidade ao `Protocol` (ferramentas a partir da Fase 02) |
| ISP | Construtores com portas mínimas; dublês de teste enxutos; `mypy` sem acesso a método fora da porta |
| DIP | Teste de importações; `mypy`; troca de implementação sem diff em `domain`/`application`; composição só na raiz de composição |
| Repository | Porta + duas implementações + suíte de contrato |
| Dependency Injection | Serviços construídos com dublês em testes; composição na borda |
| Service Layer | CLI e API chamando os mesmos serviços |

Enquanto essas evidências não existirem, a documentação deve usar os termos "planejado" ou "proposto" e não
"implementado" ou "demonstrado". **Hoje nenhum dos três princípios LSP, ISP e DIP está demonstrado**: as ferramentas de
verificação estática (`pytest`, `ruff`, `mypy`) só serão introduzidas na Fase 02 (D-13) e nenhuma foi instalada.
