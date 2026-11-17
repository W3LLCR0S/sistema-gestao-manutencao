# ADR-0008 — Estrutura do backend e convivência com o legado

- **Status:** Aprovada (D-14; convivência com o legado conforme D-10); **implementada na Fase 02**.
- **Data:** 2026-11-15
- **Relacionados:** ADR-0002, ADR-0006; AUD-06, AUD-18; [`DECISOES_APROVADAS.md`](../DECISOES_APROVADAS.md) (D-14, D-10)

## Contexto

O repositório tem `main.py`, `models/`, `ui/`, `persistencia/` (a CLI da Entrega 1) e `app/` (implementação paralela,
não importada, sem ponto de entrada, AUD-18). A nova implementação precisa ser construída e validada sem quebrar a CLI
e sem criar um terceiro conjunto de módulos misturado ao legado (R-09).

## Alternativas consideradas

| Alternativa | Avaliação |
|-------------|-----------|
| Refatorar `models/` e `persistencia/` no mesmo lugar | Mistura legado e novo; dificulta comparar comportamentos e reverter |
| Reutilizar o nome `app/` | Conflita com a implementação paralela existente |
| Novo repositório | Perde o histórico e a tag `entrega-1` como referência direta |
| **Novo pacote ao lado do legado, migração gradual** (escolhida) | Preserva a Entrega 1 e permite comparar comportamentos |

## Decisão

Criar o pacote `backend/src/manutencao/`. Estrutura-alvo (**implementada na Fase 02**; os nomes finais estão no código):

```
backend/
  src/
    manutencao/
      domain/           # entidades, regras, exceções (sem frameworks)
      application/      # casos de uso, autorização, portas (Protocol)
      infrastructure/   # repositórios, ORM, migrações, hash, relógio do sistema
      api/              # rotas FastAPI, esquemas, autenticação, tradução de erros
      composicao/       # raiz de composição (ver ADR-0002 e ADR-0005)
  tests/
    caracterizacao/ dominio/ aplicacao/ integracao/ contrato/ arquitetura/
frontend/
```

Convivência durante a migração:

1. O código legado **permanece no lugar e executável** enquanto a implementação nova é construída e validada.
2. O pacote novo **não importa** `models/`, `ui/`, `persistencia/` nem `app/`. A relação com o legado é comparar
   comportamentos por testes, não compartilhar código.
3. Comportamentos migram **gradualmente**: cada regra é primeiro caracterizada no legado (ADR-0006) e depois reproduzida
   no novo domínio.
4. A Entrega 1 fica preservada pela tag `entrega-1` (`e6f7354`), que não é alterada.
5. **Nada é excluído** enquanto não houver autorização específica.

### Destino futuro dos módulos legados

| Módulo | Papel hoje | Destino proposto | Condição para mudar |
|--------|------------|------------------|---------------------|
| `main.py` | Ponto de entrada da CLI | Preservado (D-10); remover ou manter como referência é decisão posterior | Autorização específica e atual |
| `models/` | Domínio da CLI | Permanece como **referência de comportamento** para a caracterização; substituído por `domain/` | Paridade comprovada pelos testes de caracterização e autorização específica |
| `persistencia/` | Repositório JSON da CLI | Preservado (D-10); não vira implementação final nem ganha adaptador novo (ADR-0004) | Autorização específica |
| `ui/` | Interface da CLI | Preservado (D-10); o novo frontend web é a interface principal | Autorização específica |
| `app/` | Implementação paralela não usada | **Preservada** (D-10); funcionalidades aproveitáveis são avaliadas caso a caso (OPC-06) | Autorização específica de remoção |
| `dados/` | Dados locais (ignorados pelo Git) | Nunca versionados; nunca lidos pelos testes | — |

A remoção de qualquer módulo exige: testes de caracterização aprovados e **autorização explícita
e atual** (a D-10 aprova a preservação, não a remoção). Nada disso ocorre na Fase 01.

## Justificativa

- Preserva o comportamento da Entrega 1 como referência e permite regressão visível.
- Evita conflito de nomes com `app/` e evita um terceiro conjunto paralelo.
- A estrutura `src/` separa o pacote de instalação dos testes e do restante do repositório.

## Consequências

- Durante um período haverá duas implementações no repositório; a documentação deve sempre indicar qual é o legado.
- Os testes de caracterização que usam o legado dependem de módulos que serão removidos depois; ver estratégia
  realista no ADR-0006 (testes por fachada estável e transição para o novo domínio).
- A regra "não criar um terceiro conjunto paralelo" passa a significar: todo código novo vai para `manutencao/`.

## Revisão ao encerrar a Fase 02 (2026-11-17)

O pacote `backend/src/manutencao/` existe, não importa o legado (`tests/arquitetura/test_isolamento_legado.py`) e o legado ficou **idêntico à tag `entrega-1`** (`git diff entrega-1 HEAD` vazio em `main.py models ui persistencia app dados README.md DOCUMENTACAO.md`). A relação com o legado é feita só pelos testes de caracterização. O pacote `app/` segue preservado e sem uso; sua remoção depende de autorização posterior (D-10). A estrutura-alvo descrita acima foi implementada, exceto `api/` (pacote vazio até a Fase 04).
