# ADR-0003 — Separação de responsabilidades entre as camadas

- **Status:** Aceita para documentação (Fase 01). Detalhes de autenticação continuam em aberto.
- **Data:** 2026-11-15
- **Relacionados:** ADR-0002, ADR-0005; AUD-02, AUD-09, AUD-12, AUD-13, AUD-14; E2-SOL-01

## Contexto

No baseline, a mesma preocupação aparece em camadas diferentes: a permissão é conferida às vezes na tela, às vezes no
domínio, às vezes só no menu (AUD-02); validações estão só na UI (AUD-12); regras estão na UI e no repositório (AUD-09,
AUD-10); a disponibilidade depende de o laço da UI recalcular (AUD-13); e uma única exceção cobre todos os erros (AUD-14).
Numa API, isso significaria repetir ou esquecer regras em cada rota.

## Alternativas consideradas

| Alternativa | Avaliação |
|-------------|-----------|
| Manter regras nas rotas (controladores "gordos") | Duplica regras entre rotas e CLI; difícil de testar sem HTTP |
| Entidades "anêmicas" com toda a regra em serviços | Perde o encapsulamento que o baseline já tem e que funciona (`OrdemServico`) |
| Autorizar apenas na borda (API) | A regra deixa de proteger a CLI e outros adaptadores; falha se uma rota esquecer a verificação |
| **Invariantes na entidade, autorização e orquestração nos casos de uso, tradução na borda** (escolhida) | Cada preocupação em um único lugar testável |

## Decisão

| Preocupação | Onde fica | Observações |
|-------------|-----------|-------------|
| Formato e tipo da entrada (campos obrigatórios, tamanho, enum válido) | `api` (esquemas Pydantic) | Rejeita cedo; não substitui as invariantes de domínio |
| Invariantes e transições (máquina de estados da OS, histórico sequencial, horas > 0, quantidade > 0, equipamento inativo não recebe OS) | `domain` (entidades) | Métodos nomeados por intenção; sem `to_dict`/`from_dict` nas entidades |
| Autorização por papel e permissão, e posse da OS (técnico só opera a própria OS) | `application` (casos de uso, com política central) | Permissões tipadas (enumeração), não *strings* |
| Orquestração, transação e leitura/gravação via portas | `application` | O caso de uso define a fronteira da transação (ADR-0004) |
| Autenticação (quem é o usuário da requisição), sessão, CORS | `api` | Entrega o usuário autenticado ao caso de uso |
| Persistência e mapeamento entidade ↔ tabela | `infrastructure` | Repositórios não contêm regra de negócio |
| Disponibilidade do técnico | `domain`/`application` (derivada de OS ativas e do estado "Ausente" manual) | Calculada na leitura ou na mesma transação, nunca dependente da UI |
| Datas e horas | `domain` recebe um relógio (porta) | Tipo data/hora com fuso, não texto |
| Tradução de erros em respostas | `api` | Ver hierarquia abaixo |

**Hierarquia de erros de domínio** (substitui a exceção única, AUD-14), traduzida na borda:

| Erro | Quando | HTTP previsto |
|------|--------|---------------|
| Não autenticado | Credencial ausente ou inválida | 401 |
| Permissão negada | Papel sem a permissão, ou OS de outro técnico | 403 |
| Não encontrado | Entidade inexistente | 404 |
| Conflito de estado ou de concorrência | Transição inválida para o status atual; versão desatualizada | 409 |
| Violação de regra / validação de domínio | Horas inválidas, texto vazio, equipamento inativo | 422 |

A CLI de transição mostra a mensagem do mesmo erro, sem código HTTP.

## Justificativa

- Uma regra, um lugar: a mesma verificação vale para API, CLI e testes.
- Preserva o encapsulamento já existente nas entidades (ponto forte do baseline).
- Separa "quem pode" (aplicação) de "o que é válido" (domínio) e de "como chega" (API).

## Consequências

- Os testes de caracterização (ADR-0006) devem registrar o comportamento atual antes de mover cada regra.
- Os pontos em que o baseline diverge entre UI e domínio (AUD-09, AUD-11) exigem **decisões de regra**, listadas em
  [`PLANO_DE_MIGRACAO.md`](../PLANO_DE_MIGRACAO.md), e **não** são alterados por esta ADR.
- Autenticação (formato da sessão ou do token, política de senha inicial, recuperação de acesso) **ainda não está
  especificada**; será proposta na Fase 04 com aprovação específica. Esta ADR define só onde cada parte reside.
