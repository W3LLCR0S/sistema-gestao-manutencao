# ADR-0009 — Papéis, autorização e regras aprovadas da OS

- **Status:** Aprovada (D-02 a D-06); **implementada no novo backend na Operação E da Fase 02** (DLT-01 a DLT-06, DLT-08
  e DLT-09; ver a [seção 8 de `DECISOES_APROVADAS.md`](../DECISOES_APROVADAS.md#8-deltas-de-regras-de-negócio-operação-e-dlt-01-a-dlt-09)).
  A **regularização da Operação E** (REG-E-01 a REG-E-08, DLT-18 a DLT-23; seção 7 abaixo) foi aprovada em 2026-11-17.
  O baseline e o legado mantêm o comportamento descrito em [`AUDITORIA_ARQUITETURAL.md`](../AUDITORIA_ARQUITETURAL.md).
- **Data:** 2026-11-15
- **Relacionados:** ADR-0003; AUD-02, AUD-03, AUD-09, AUD-11, AUD-12, AUD-13, AUD-20, AUD-21;
  [`DECISOES_APROVADAS.md`](../DECISOES_APROVADAS.md) (detalhes e testes por decisão)

## Contexto

A auditoria encontrou regras que existiam só na interface (AUD-09), papéis definidos por permissão editável (AUD-20),
apontamento em OS encerrada (AUD-11), disponibilidade dependente de rotina da UI (AUD-13) e diagnóstico não obrigatório
antes de finalizar (AUD-21). Estas decisões fixam o que será implementado na Fase 02 e como será verificado.

## Decisão

### 1. Papel × permissão (D-02)

- **Papel** (Gestor, Técnico) é atributo explícito do usuário no domínio e **não é derivado de permissões**. O papel
  responde "quem é"; a permissão responde "o que pode executar".
- Pertencer à lista de técnicos, receber OS e ter carga e disponibilidade dependem do **papel**.
- Permissões continuam configuráveis (tipadas, ver ADR-0003); a negação gera erro de permissão (403).

### 2. Ausência e atribuição (D-03)

- Atribuir a Técnico Ausente é **recusado** (409) a menos que a operação traga a confirmação explícita.
- A confirmação é um **dado da operação** (por exemplo `confirmar_ausente=True`), validada no **caso de uso** de
  atribuição. Interfaces (web; a CLI legada não usa a nova regra) só coletam a confirmação do usuário; **não** são o local da regra.

### 3. Observações, diagnóstico, apontamentos e status (D-04)

- Quatro operações distintas, com permissões e tipos de histórico próprios (ver tabela em `DECISOES_APROVADAS.md`, seção
  D-04). Observação **nunca** altera o status.
- OS **Concluída** ou **Cancelada** não aceita novos registros de nenhum tipo, exceto o que o domínio definir como parte
  do encerramento.
- Regras de posse: operações técnicas só pelo **técnico responsável**; observação também por quem **abriu** a OS e
  pelo **gestor**; o autor da abertura não ganha capacidade técnica.
- Verificação no **servidor** (caso de uso), independentemente do frontend.

### 4. Disponibilidade (D-05)

- Valor **derivado** das OS do técnico: Em atendimento se há OS **Em Execução**; caso contrário, Disponível.
- **Ausente** é um estado manual **armazenado separadamente** e tem precedência sobre o derivado. O valor manual aceita
  só `Disponível` e `Ausente`; `Em atendimento` nunca é gravado à mão (REG-E-06, DLT-23).
- Calculada na leitura ou na mesma transação; **nunca** dependente de rotina da interface. Sem novo SLA nem novas regras.

### 5. Diagnóstico (D-06)

- A transição para **Reparo Finalizado** exige diagnóstico **e** intervenção registrados; o domínio recusa com mensagem
  clara. As demais transições do baseline são preservadas.

### 6. Validação de entradas e usuários inativos

- Campos obrigatórios vazios, números inválidos e duração menor ou igual a zero são rejeitados no domínio e na API.
- Usuários possuem `ativo`; inativos não autenticam nem operam; seu histórico é preservado. Quem tem OS ativas sob sua
  responsabilidade não é desativado nem deixa o papel Técnico (REG-E-04, DLT-21); nada é reatribuído nem cancelado
  automaticamente. A política completa de transferência de responsabilidades **não está decidida** (fase planejada).
- Os textos de observação e de descrição de peça também são obrigatórios (REG-E-05, DLT-22).

## Alternativas consideradas

| Alternativa | Avaliação |
|-------------|-----------|
| Manter "técnico = permissão" (baseline) | Frágil: a identidade muda ao editar uma permissão (AUD-20) |
| Confirmação de ausente apenas na interface | Contornável por chamada direta à API (AUD-09) |
| Permitir qualquer apontamento em OS encerrada | Histórico encerrado deixa de ser confiável (AUD-11) |
| Tratar observação como intervenção técnica | Daria capacidade técnica a quem só abriu a OS |
| Disponibilidade gravada por rotina periódica | Valor defasado e acoplado à UI (AUD-13) |

## Consequências

- Os testes de caracterização registram o **comportamento atual** antes de cada mudança, e cada mudança é aplicada em
  separado, com seu teste (ADR-0006, "Deltas de comportamento").
- Surge a necessidade de definir como o papel é armazenado e como se altera; ver Fase 06.
- Há **pontos ainda sem decisão** (separação de aprovar e cancelar, política completa de transferência de OS, D-15);
  eles estão listados em [`DECISOES_APROVADAS.md`](../DECISOES_APROVADAS.md), seção 6.

## 7. Regularização da Operação E (2026-11-17)

Oito decisões aprovadas depois da auditoria de leitura da Operação E (detalhes na
[seção 9 de `DECISOES_APROVADAS.md`](../DECISOES_APROVADAS.md#9-regularização-da-operação-e-reg-e-01-a-reg-e-08)):

| Decisão | Delta | Efeito sobre esta ADR |
|---------|-------|-----------------------|
| REG-E-01 | DLT-18 | O sistema nunca fica sem um gestor administrativamente apto (Gestor, ativo e com `gerir_usuarios`) |
| REG-E-02 | DLT-19 | Alterar o papel exige Gestor ativo **e** `gerir_usuarios` (ratificada); a exigência de papel não se estende a outras operações |
| REG-E-03 | DLT-20 | Ninguém se rebaixa de Gestor nem desativa a própria conta (ratificada) |
| REG-E-04 | DLT-21 | OS ativa impede desativar e deixar o papel Técnico; sem reatribuição nem cancelamento automáticos |
| REG-E-05 | DLT-22 | Observação e descrição de peça obrigatórias (ampliação da validação de entradas) |
| REG-E-06 | DLT-23 | Disponibilidade manual só `Disponível` e `Ausente`; política de autorização única para as duas vias |
| REG-E-07 | REG-E-07 | Rastreabilidade do CAR-37 ligada ao DLT-06 (variante só do legado) |
| REG-E-08 | REG-E-08 | Documentação dos campos validados corrigida |

Fora de escopo, e **pendente**: reatribuição automática, recuperação administrativa, autenticação (D-01) e a política completa
de transferência de responsabilidades.
