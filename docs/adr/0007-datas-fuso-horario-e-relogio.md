# ADR-0007 — Datas, fuso horário e relógio

- **Status:** Aprovada (D-11). **Não implementada.** A conversão de dados legados continua futura.
- **Data:** 2026-11-15
- **Relacionados:** ADR-0002, ADR-0003, ADR-0005; AUD-07; [`DECISOES_APROVADAS.md`](../DECISOES_APROVADAS.md) (D-11)

## Contexto

No baseline as datas são texto `dd/mm/aaaa hh:mm`, sem fuso, geradas por `_agora()` dentro da entidade
(`models/ordem_servico.py:21-22`, `models/servico.py:27`; AUD-07). Isso impede ordenação confiável, comparação,
cálculo de intervalos e exibição correta em outro fuso. Além disso, quando o domínio chama o relógio por conta própria,
os testes dependem da hora real.

## Alternativas consideradas

| Alternativa | Avaliação |
|-------------|-----------|
| Manter texto `dd/mm/aaaa hh:mm` | Sem tipo, sem fuso, sem ordenação segura |
| `datetime` ingênuo em hora local | Ambíguo em mudança de horário e em servidores de fuso diferente |
| Armazenar em hora local de São Paulo | Amarra a persistência a um fuso e dificulta comparações |
| **`datetime` com fuso, armazenado em UTC, exibido em America/Sao_Paulo** (escolhida) | Instante inequívoco; a conversão fica na borda |
| Domínio chama um relógio injetado | Obriga o domínio a importar uma porta da aplicação (inverte a dependência) |
| **A aplicação obtém o instante e o entrega ao domínio** (escolhida) | Domínio determinístico e sem dependência de camada externa |

## Decisão

1. **Tipo:** instantes são `datetime` **com fuso** (a biblioteca padrão basta para o domínio). Datas ingênuas não são
   aceitas pelas novas implementações: as operações de domínio **rejeitam** `datetime` sem fuso.
2. **Armazenamento:** em **UTC** (`TIMESTAMP WITH TIME ZONE` no PostgreSQL, ver ADR-0004).
3. **Exibição:** converter para **America/Sao_Paulo** somente na borda (API, esquemas de resposta ou frontend). O domínio
   e a aplicação nunca formatam datas para exibição.
4. **Relógio:**
   - a porta `Relogio` (`Protocol` com `agora() -> datetime`) é definida na **camada de aplicação**;
   - o domínio **não importa** `Relogio` nem qualquer módulo de `application`;
   - cada caso de uso obtém `agora = relogio.agora()` **uma vez** e **passa o instante como argumento** às operações
     de domínio que precisam dele (por exemplo `ordem.aprovar(gestor, quando=agora)`);
   - a implementação real (UTC do sistema) fica em `infrastructure`; os testes usam um relógio fixo.
5. **Datas legadas:** a conversão de `dd/mm/aaaa hh:mm` (sem fuso) para UTC **não é feita nesta fase** e exige uma
   decisão adicional (fuso presumido das datas existentes, tratamento de horário ambíguo) **antes** de qualquer
   migração de dados (D-08). Dados reais só são tocados com autorização específica (OPC-07).

Esboço da direção das dependências (**proposta**, não implementada):

```
api  ──►  application (caso de uso + porta Relogio)  ──►  domain (recebe 'quando' como argumento)
                ▲
infrastructure (RelogioSistema implementa Relogio)
```

## Justificativa

- Mantém `domain` sem importar nada da aplicação (regra de dependência do ADR-0002).
- Torna o domínio puro e testável com datas fixas, sem simulação do relógio do sistema.
- Um único instante por caso de uso evita que duas entradas do mesmo histórico recebam horas diferentes.
- UTC no armazenamento evita ambiguidades de horário de verão e de servidor.

## Consequências

- As operações de domínio ganham o parâmetro de instante (assinatura diferente da do baseline); a caracterização cobre
  o comportamento, não a assinatura (ver ADR-0006).
- Serialização de datas na API deve usar formato com fuso (ISO 8601); o frontend converte para exibição.
- Será necessário definir, antes da importação, o fuso das datas legadas; hoje **não há decisão**.
- Ordenações e filtros por data no banco usam instantes UTC.
