# ADR-0004 — Repository e persistência

- **Status:** Aceita para documentação (Fase 01). Itens marcados como *proposta* serão confirmados nas Fases 02 e 03.
- **Data:** 2026-11-15
- **Relacionados:** ADR-0001, ADR-0002; AUD-04 a AUD-08, AUD-10, AUD-16; E2-PAD-01, E2-PER-01, E2-SOL-03, E2-SOL-04

## Contexto

O `Repositorio` atual (`persistencia/repositorio.py`) guarda todos os objetos em listas e regrava o JSON inteiro. Mistura
persistência, geração de IDs, consultas, regras de negócio e dados de exemplo (AUD-10); não tem contrato, então não há
como substituí-lo nem testá-lo isoladamente (AUD-16); e não suporta escrita concorrente (AUD-04, AUD-05). Também não
trata a incompatibilidade com a implementação paralela em `app/` (AUD-06).

## Alternativas consideradas

| Alternativa | Avaliação |
|-------------|-----------|
| *Active Record* (modelos SQLAlchemy usados como entidades de domínio) | Simples, mas prende o domínio ao ORM e inverte a dependência desejada |
| Expor a `Session` do SQLAlchemy diretamente aos serviços | Espalha consultas pelos casos de uso e dificulta a troca ou o uso de dublês nos testes |
| Repositório genérico único (`get/add/list` para tudo) | Esconde consultas específicas do negócio e viola a segregação de interfaces |
| Manter JSON com bloqueio de arquivo | Corrige parte de AUD-04, mas não dá transações, integridade referencial nem escala para API |
| **Repository por agregado, com portas em `application` e adaptadores em `infrastructure`** (escolhida) | Isola a persistência sem esconder consultas relevantes |

## Decisão

1. **Um repositório por agregado**, definido como `Protocol` na camada `application`:
   - `OrdemServicoRepository` (raiz do agregado: `OrdemServico`, que contém seus `Servico` e `PecaMaterial`);
   - `UsuarioRepository` (usuários e cargos/permissões);
   - `EquipamentoRepository`.
   Cada porta expõe apenas as operações de que seus clientes precisam (por exemplo: buscar por número, listar com
   filtros, listar OS ativas de um técnico), sem regra de negócio.
2. **Implementações** (adaptadores em `infrastructure`):
   - **em memória**, para testes de unidade e de aplicação;
   - **sem JSON de transição**: por D-10 (aprovada), a CLI legada permanece intacta e executável com seu próprio
     repositório, e **nenhum** adaptador JSON é criado para os novos serviços;
   - **SQLAlchemy 2 / PostgreSQL**, na Fase 03.
3. **Fronteira de transação** no caso de uso: o serviço de aplicação abre a unidade de trabalho e confirma ao final
   (*proposta*: usar a sessão do SQLAlchemy como unidade de trabalho, exposta por uma porta simples). A UI deixa de
   chamar `salvar()`.
4. **Mapeamento**: modelos de persistência separados das entidades de domínio, com mapeadores explícitos
   (*proposta*, para manter o domínio livre de ORM; alternativa de mapeamento imperativo a avaliar na Fase 03).
   Datas persistidas como instantes em UTC com fuso (D-11, [ADR-0007](0007-datas-fuso-horario-e-relogio.md)).
5. **Concorrência**: controle otimista por coluna de versão na `OrdemServico`; escrita sobre versão desatualizada falha com
   erro de conflito (HTTP 409), sem sobrescrever (*proposta*, a confirmar na Fase 03).
6. **Identificadores**: sequências do banco; na eventual importação, os IDs existentes são preservados (ver decisões
   abertas). Entidades passam a ser comparadas **por ID**, não por identidade de objeto (AUD-08).
7. **Integridade referencial** por chaves estrangeiras; exclusão de equipamento ou usuário com histórico continua
   proibida (inativar), regra mantida no domínio/aplicação, com restrição de banco como segunda barreira.
8. **Contrato testável**: uma suíte de testes de contrato é executada contra **todas** as implementações da mesma porta
   (base para demonstrar LSP, ver `PRINCIPIOS_SOLID_E_PADROES.md`).

## Justificativa

- Resolve a causa de AUD-10 e AUD-16 e viabiliza E2-PER-01 de modo verificável.
- A versão otimista e as transações atacam diretamente AUD-04 e AUD-05, o que o JSON não consegue.
- Portas pequenas por agregado atendem ISP e tornam os testes de aplicação rápidos (sem banco).

## Consequências

- Mais código de mapeamento e uma suíte de contrato a manter.
- A migração de **dados reais** do JSON **não** faz parte desta decisão: exige plano idempotente, *backup*, simulação
  (*dry-run*) e **autorização específica** (OPC-07).
- Consultas de leitura para o *dashboard* podem justificar uma porta de leitura separada (Fase 08), sem alterar os
  repositórios de escrita.
- O repositório JSON atual não é reaproveitado como implementação final; o `Repositorio` e `app/` são preservados até
  decisão posterior ([ADR-0008](0008-estrutura-do-backend-e-convivencia-com-o-legado.md)).
- Usuários passam a ter o campo `ativo` (desativação sem exclusão, `DECISOES_APROVADAS.md`, seção 5.2); as chaves
  estrangeiras para usuários desativados são mantidas para preservar o histórico.
