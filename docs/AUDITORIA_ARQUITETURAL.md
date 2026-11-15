# Auditoria arquitetural do baseline (Entrega 1)

Auditoria técnica do código da Entrega 1 (commit `e6f7354`, tag `entrega-1`), feita na Fase 01 como base para a
evolução arquitetural. É um documento de diagnóstico: **nenhum código foi alterado**. Complementa
[`LIMITACOES_E_AUDITORIA.md`](LIMITACOES_E_AUDITORIA.md), que registra o resumo inicial, sem repetir seu conteúdo.

Os achados são da própria equipe. Não correspondem a apontamentos da avaliação da Entrega 1.

## 1. Método, evidências e limites

- **Leitura integral** de todos os arquivos `.py` versionados (`main.py`, `models/`, `persistencia/`, `ui/`, `app/`) e
  dos documentos `README.md` e `DOCUMENTACAO.md`.
- **Execução pontual** (2026-11-15, Python 3.11.9, Windows 11): um script ad hoc exercitou as classes de domínio e o
  `Repositorio` com arquivos de dados em **diretório temporário**, sem tocar em `dados/` nem em código. O script
  **não está versionado**; os trechos para reproduzir cada resultado estão no [Apêndice A](#apêndice-a--como-reproduzir-os-achados-executados).
  Ele será convertido em testes de caracterização na Fase 02.
- Cada achado traz uma marca de evidência:
  - **[Executado]**: o comportamento foi observado ao rodar o código.
  - **[Estático]**: conclusão por leitura do código, sem execução.
- **Não verificado nesta auditoria:** execução interativa da CLI (`python main.py`) e de cada tela; compatibilidade com
  Python 3.8 (o `README.md` declara 3.8+, mas só 3.11.9 foi usado); conteúdo do `dados/dados.json` local (dado
  privado, ignorado pelo Git).
- Referências `arquivo:linha` valem para o commit `e6f7354`.

Escala de severidade (relativa aos objetivos da Entrega 2): **Alta** = impede um requisito ou compromete segurança/integridade;
**Média** = impede a arquitetura-alvo ou gera risco relevante; **Baixa** = melhoria ou ambiguidade a decidir.

## 2. O que já está bem e deve ser preservado

| Ponto | Evidência |
|-------|-----------|
| O domínio não importa `ui/` nem `persistencia/` (dependência de `models/` aponta só para `models/`). | Imports de `models/*.py` **[Estático]** |
| Regras do ciclo da OS concentradas em métodos da entidade, com checagem de permissão, dono e status antes de alterar. | `models/ordem_servico.py:103-192` **[Estático]** |
| Histórico sequencial por OS, numerado 1..N, gerado só pelos métodos da OS; sobrevive à gravação e recarga. | `ordem_servico.py:69-73`; ciclo completo gerou 11 serviços numerados e a recarga manteve a numeração **[Executado]** |
| Exceção única de regra de negócio e mensagens claras em português. | `models/excecoes.py` **[Estático]** |
| Gravação em arquivo temporário seguida de `os.replace` (não deixa JSON truncado). | `persistencia/repositorio.py:52-56` **[Estático]** |
| Enums para status, criticidade, disponibilidade e tipo de serviço. | `models/enums.py` **[Estático]** |
| Equipamento com histórico é inativado, não excluído; usuário com histórico não é excluído. | `repositorio.py:131-145` **[Estático]** |

Esses comportamentos são o contrato funcional a ser protegido por testes de caracterização antes de qualquer refatoração.

## 3. Resumo dos achados

| ID | Achado | Severidade | Evidência |
|----|--------|------------|-----------|
| AUD-01 | Login por ID, sem credencial | Alta | Estático + busca |
| AUD-02 | Autorização aplicada de forma desigual (só OS tem `exigir` no domínio) | Alta | Executado |
| AUD-03 | Permissões por *string* sem validação | Média | Executado |
| AUD-04 | JSON regravado por inteiro, sem bloqueio nem versão (perda de atualização) | Alta | Executado |
| AUD-05 | Numeração por `max()+1` gera colisão e pode reaproveitar IDs | Alta | Executado / Estático |
| AUD-06 | `main.py` e `app/` gravam formatos incompatíveis no mesmo arquivo | Alta | Executado |
| AUD-07 | Serialização acoplada ao domínio, leitura frágil, datas como texto | Média | Estático |
| AUD-08 | Referências por identidade (`is`) e vínculos quebrados silenciosos | Média | Estático |
| AUD-09 | Regras de negócio presentes só na interface | Alta | Executado |
| AUD-10 | Regras de negócio dentro do `Repositorio` | Média | Estático |
| AUD-11 | Apontamento aceito em OS encerrada e por qualquer usuário com permissão | Média | Executado |
| AUD-12 | Validações de entrada só na UI; domínio aceita vazios e zero | Média | Executado |
| AUD-13 | Disponibilidade recalculada só pelo laço da UI | Média | Executado |
| AUD-14 | Exceção única não distingue permissão, validação, estado e inexistência | Média | Estático |
| AUD-15 | `OrdemServico` e `Repositorio` acumulam responsabilidades | Média | Estático |
| AUD-16 | UI depende do `Repositorio` concreto e controla a gravação | Média | Estático |
| AUD-17 | Ausência de testes automatizados, de manifesto de dependências e de CI | Alta | Executado (busca) |
| AUD-18 | Implementação paralela em `app/` sem ponto de entrada | Média | Executado (busca) + estático |
| AUD-19 | Documentação da Entrega 1 afirma mais do que o código sustenta | Baixa | Estático |
| AUD-20 | Ambiguidade: "técnico" definido por permissão editável | Baixa | Estático |
| AUD-21 | Reparo pode ser finalizado sem diagnóstico, que depois só é aceito voltando o status | Média | Executado |

## 4. Autenticação e autorização

### AUD-01 — Login por ID, sem credencial (Alta) [Estático + busca]
`Aplicacao.login()` lista os usuários e aceita o ID digitado (`ui/aplicacao.py:61-74`). `Usuario` não tem campo de
segredo (`models/usuario.py:12-19`; `to_dict` em `:38-40`). A busca por `senha|password|hash|bcrypt|token` em todos os
`.py` não encontrou ocorrências. Qualquer pessoa com acesso ao terminal assume qualquer cargo, inclusive Gestor.
**Impacto na Entrega 2:** inaceitável em aplicação web. **Tratamento:** Fase 04 (hash de senha, sessão com expiração,
autorização no servidor).

### AUD-02 — Autorização desigual entre operações (Alta) [Executado]
Só os métodos de `OrdemServico` verificam permissão no domínio (`usuario.exigir(...)`, `ordem_servico.py:91,99,104,...`).
As demais operações verificam permissão apenas na **entrada da tela** (`ui/tela_equipamentos.py:35`,
`ui/tela_usuarios.py:17,70`) ou só pelo **menu** (consultas `ver_*`, `ui/aplicacao.py:31-35`). `Equipamento.inativar()`,
`Repositorio.adicionar_equipamento()` e `Repositorio.remover_equipamento()` não recebem usuário algum
(`models/equipamento.py:16`, `repositorio.py:125,131`). Verificado: `remover_equipamento` removeu um equipamento sem
qualquer identidade ou permissão informada (Apêndice A, B4).
**Impacto:** ao trocar a CLI por uma API, cada rota teria de reimplementar a checagem; esquecer uma deixa a operação aberta.
**Tratamento:** casos de uso na camada de aplicação, com autorização central (Fases 02 e 04).

### AUD-03 — Permissões por *string* sem validação (Média) [Executado]
`Permissoes.tem()` usa `getattr(self, acesso, False)` (`models/permissoes.py:56-57`). Um nome errado devolve `False`
sem erro: `tem("aprovar_oss")` retorna `False` e `exigir("aprovar_oss")` nega com a mensagem "Sem permissão: aprovar_oss."
(Apêndice A, B3). Um erro de digitação no código vira negação silenciosa em vez de falha detectável. Cada permissão nova
exige alterar três lugares na mesma classe (`DESCRICOES`, `__init__` e atributos, `:8-53`), o que também afeta o OCP.
O próprio `DOCUMENTACAO.md` (§8) já reconhece o ponto. **Tratamento:** enumeração tipada de permissões (Fase 02).

### AUD-20 — "Técnico" definido por permissão editável (Baixa) [Estático]
`Usuario.e_tecnico` retorna `pode("apontar_reparo")` (`models/usuario.py:32-35`), e o Gestor pode editar as permissões
dos cargos (`ui/tela_usuarios.py:90-106`). Retirar essa permissão do cargo Técnico faz os técnicos desaparecerem de
`Repositorio.tecnicos()` (`repositorio.py:101-102`) e da atribuição, embora ainda tenham OS; conceder a permissão ao
cargo Gestor faz gestores aparecerem como técnicos. **Decisão pendente:** manter "técnico = permissão" ou vincular ao
cargo/papel (ver [`PLANO_DE_MIGRACAO.md`](PLANO_DE_MIGRACAO.md), decisões abertas).

## 5. Persistência, concorrência e integridade

### AUD-04 — Regravação integral sem bloqueio nem versão (Alta) [Executado]
`Repositorio.salvar()` serializa tudo e substitui o arquivo (`repositorio.py:45-56`); `carregar()` só roda no
construtor. Duas instâncias que carregaram a mesma versão e salvam depois não se enxergam. Verificado: A e B abriram uma
OS cada e salvaram em sequência; o arquivo final continha **apenas a OS de B** (Apêndice A, C). A gravação atômica
(`os.replace`) evita arquivo corrompido, mas não perda de atualização.
**Impacto:** com uma API atendendo requisições simultâneas, o problema ocorreria em uso normal.
**Tratamento:** transações e controle otimista de concorrência no banco (Fase 03; ver ADR-0004).

### AUD-05 — Numeração por `max()+1` (Alta) [Executado / Estático]
`Repositorio._proximo` calcula `max(valores, default=0) + 1` sobre a lista em memória (`repositorio.py:75-86`).
**[Executado]** Duas instâncias geraram o **mesmo número de OS (1)** (Apêndice A, C). **[Estático]** Ao excluir o item de
maior ID (usuário ou equipamento sem histórico, `repositorio.py:131-145`), o próximo cadastro reutiliza o ID excluído, o
que pode confundir registros externos que o referenciem. **Tratamento:** sequências do banco (Fase 03).

### AUD-06 — Formatos incompatíveis entre `main.py` e `app/` (Alta) [Executado]
Ambos usam `dados/dados.json` (`repositorio.py:16-17`; `app/persistencia.py:8-9`) com estruturas diferentes
(`app/` usa `seq`, `servicos`, `cargo_id`, permissões em lista, nomes como `registrar_observacao`; `main.py` usa
permissões em dicionário e `registrar_apontamento`). Verificado:
- `Repositorio` lendo um arquivo no formato de `app/` falha com `AttributeError: 'list' object has no attribute 'get'`;
- `app/` lendo um arquivo no formato do `Repositorio` falha com `KeyError: 'seq'` ao gerar o próximo ID, e seu teste de
  permissão (`permissao in cargo["permissoes"]`, `app/contexto.py:37-40`) devolve **verdadeiro para todas as
  permissões**, pois as chaves existem no dicionário mesmo com valor `False` (o técnico passou a "poder" `aprovar_os`).

Como `app/` não tem ponto de entrada (AUD-18), o segundo cenário hoje exige carregar o módulo manualmente; permanece como
evidência do risco de manter duas implementações sobre o mesmo arquivo.

### AUD-07 — Serialização acoplada, leitura frágil, datas como texto (Média) [Estático]
- `to_dict`/`from_dict` vivem nas entidades (`models/*.py`, ex.: `ordem_servico.py:195-237`), prendendo o domínio ao
  formato JSON.
- `from_dict` exige todas as chaves (`d["diagnostico"]`, `d["servicos"]`, ...): arquivo mais antigo ou parcial
  gera `KeyError`; não há versão de esquema nem migração.
- Datas são `str` no formato `dd/mm/aaaa hh:mm` (`ordem_servico.py:21-22`, `servico.py:27`): sem fuso, sem ordenação
  confiável por tipo e sem validação. Cálculos de atraso e dashboards exigirão tipo de data real.

### AUD-08 — Identidade por referência e vínculos silenciosos (Média) [Estático]
`esta_com` compara com `is` (`ordem_servico.py:65-66`); o mesmo vale em `repositorio.py:105,137` e na UI. Funciona porque
existe uma única instância de cada usuário em memória; numa API, cada requisição reconstrói objetos e a comparação
falharia. Na carga, `usuarios.get(...)` devolve `None` para responsável ou técnico inexistente sem avisar
(`ordem_servico.py:224,231`; `servico.py:54`), apagando silenciosamente o vínculo, enquanto o equipamento ausente
levanta `KeyError` (`:221`). Falta política de integridade referencial.

## 6. Regras de negócio e responsabilidades

### AUD-09 — Regras presentes só na interface (Alta) [Executado]
| Regra | Onde está | Domínio a impõe? |
|-------|-----------|------------------|
| Confirmar antes de atribuir a técnico **Ausente** | `ui/tela_gestor.py:27-29` | **Não**: `atribuir` aceitou técnico Ausente sem erro (Apêndice A, B2) |
| Impedir que o gestor remova o próprio acesso de gestão | `ui/tela_usuarios.py:58,104` | Não **[Estático]** |
| Qualquer usuário pode alterar a própria disponibilidade | item de menu sem permissão (`ui/aplicacao.py:36`, `ui/tela_ordens.py:76-79`) | Sem regra no domínio **[Estático]** |
| Gestor edita cargo e disponibilidade de usuários | atribuição direta a atributos (`ui/tela_usuarios.py:52-64`) | Sem método de domínio **[Estático]** |
| Inativar/reativar equipamento | `ui/tela_equipamentos.py:52` chama a entidade direto | Sem checagem de permissão (AUD-02) |

O `DOCUMENTACAO.md` afirma que "as telas não decidem nada" (§2); as linhas acima mostram exceções.
**Tratamento:** mover cada regra para um caso de uso testável (Fases 02 e 06).

### AUD-10 — Regras de negócio dentro do `Repositorio` (Média) [Estático]
`remover_equipamento`, `remover_usuario`, `_usuario_tem_historico`, `carga`, `tecnicos` e
`atualizar_disponibilidades` (`repositorio.py:101-145`) são regras, não persistência. Um repositório SQL teria de duplicá-las
ou o domínio passaria a depender de uma classe de infraestrutura (violação de SRP e DIP). O construtor ainda **semeia
dados e grava o arquivo** quando ele não existe (`:27-31`), efeito colateral inesperado em construtor.

### AUD-11 — Apontamento sem restrição de estado ou dono (Média) [Executado]
`OrdemServico.adicionar_apontamento` só exige a permissão `registrar_apontamento` (`ordem_servico.py:98-100`). Verificado:
um técnico que **não** é dono da OS incluiu um apontamento em OS **Concluída** (histórico passou de 11 para 12 registros,
status inalterado). Isso contradiz a ideia de histórico encerrado. **Decisão pendente:** permitir ou não apontamento em OS
encerrada e por quem (ver plano de migração).

### AUD-21 — Sequência diagnóstico × finalização inconsistente (Média) [Executado]
`alterar_status` só exige intervenção para finalizar o reparo (`ordem_servico.py:133-134`); `concluir_tecnicamente` exige
diagnóstico (`:142-143`); mas `registrar_diagnostico` só aceita OS em Atribuída, Em Execução ou Aguardando Peça
(`:106`). Verificado (Apêndice A, F): com a OS em "Reparo Finalizado" **sem diagnóstico**, a conclusão é recusada
("Registre o diagnóstico antes de concluir.") **e** o diagnóstico também é recusado ("Operação não permitida com a OS em
'Reparo Finalizado'."). O técnico só avança voltando o status para "Em Execução" (permitido), registrando o diagnóstico e
finalizando de novo. Não há bloqueio definitivo, mas o caminho é indireto e gera transições e registros de histórico
extras. **Decisão pendente:** exigir diagnóstico para finalizar, ou aceitar diagnóstico em "Reparo Finalizado".

### AUD-12 — Validações só na UI (Média) [Executado]
`ler_float(..., minimo)` (`ui/entrada.py:36-45`) e `ler(..., obrigatorio=True)` validam na tela. No domínio,
`apontar_reparo` só rejeita horas negativas (`ordem_servico.py:116`). Verificado: abertura de OS com falha vazia e
apontamento com 0 h e intervenção vazia foram aceitos pelo domínio (Apêndice A, B5). Uma API receberia esses dados sem a
barreira da CLI. **Tratamento:** validação no domínio (invariantes) e nos esquemas da API (Fases 02 e 04).

### AUD-13 — Disponibilidade derivada fora do domínio (Média) [Executado]
`Repositorio.atualizar_disponibilidades()` só é chamado pelo laço do menu (`ui/aplicacao.py:101`). Verificado: depois de
`apontar_reparo`, o técnico continuava "Disponível" até a chamada explícita, quando passou a "Em atendimento"; com a OS
em "Aguardando Peça", voltou a "Disponível" (Apêndice A, E). O comportamento segue o `DOCUMENTACAO.md` §7 (só "Em
Execução" conta), mas depende de lembrar de chamar o método. Em API, o valor deve ser derivado na leitura ou atualizado
na mesma transação. **Decisão pendente:** "Aguardando Peça" deve contar como "Em atendimento"?

### AUD-14 — Exceção única (Média) [Estático]
`RegraNegocioError` cobre falta de permissão, estado inválido, validação e regra de integridade (`models/excecoes.py`).
Uma API precisa distinguir 401/403/404/409/422. **Tratamento:** hierarquia de exceções de domínio mapeada na camada de
API (ADR-0003).

### AUD-15 — Responsabilidades acumuladas (Média) [Estático]
`OrdemServico` (237 linhas) reúne máquina de estados, autorização, geração de histórico, formatação de data e
serialização. `Repositorio` (145 linhas) reúne persistência, geração de IDs, consultas, regras de negócio, dados de
exemplo e disponibilidade. Detalhes por princípio em [`PRINCIPIOS_SOLID_E_PADROES.md`](PRINCIPIOS_SOLID_E_PADROES.md).

### AUD-16 — Acoplamento da UI ao `Repositorio` concreto (Média) [Estático]
`Aplicacao.__init__` cria `Repositorio()` diretamente (`ui/aplicacao.py:19`); as telas acessam `self.app.repo`
(`ui/tela_base.py:18-20`); a UI decide quando gravar (`aplicacao.py:102`, `tela_usuarios.py:39,88`,
`tela_equipamentos.py:60`), ou seja, a fronteira de transação está na interface. Não há como substituir o armazenamento
nem testar uma tela sem o arquivo real.

## 7. Qualidade

### AUD-17 — Sem testes, manifesto de dependências nem CI (Alta) [Executado (busca)]
`git ls-files` não contém nenhum arquivo com `test`, `pytest`, `requirements`, `pyproject` ou `setup.py` no nome
(0 ocorrências). Não há pipeline de integração contínua. As regras de negócio não tinham verificação automática antes
desta auditoria; o script ad hoc usado aqui não substitui testes versionados.

## 8. Análise da implementação paralela em `app/`

### AUD-18 — `app/` não é usada nem executável (Média) [Executado (busca) + estático]
- **Não é importada:** nenhuma linha fora de `app/` contém `import app` ou `from app...` (busca em todos os `.py`).
- **Sem ponto de entrada:** `menu_principal`, `login` (de `app/menu.py`) e `Contexto(...)` nunca são chamados; `app/` não
  tem `__main__`. Sozinha, não inicia.
- **Modelo diferente:** dados como dicionários, sem classes de domínio; regras e alterações de estado dentro dos módulos
  de tela (`app/modulos/tecnico.py:36-44`, `app/modulos/gestor.py:32-41`), sem checagem de permissão ou de dono nas
  ações (apenas no menu, `app/menu.py:55`).
- **Divergências de nomes de permissão:** `registrar_observacao` e `concluir_tecnico` (`app/constantes.py:8,12`) contra
  `registrar_apontamento` e `concluir_os` (`models/permissoes.py:13,17`).
- **Cargos mutáveis:** permite criar e excluir cargos (`app/modulos/usuarios.py:109-136`), contrariando a decisão de
  cargos fixos (Gestor e Técnico) documentada na Entrega 1.

**Funcionalidades potencialmente reaproveitáveis** (nenhuma foi migrada; todas dependem de decisão):

| Item em `app/` | Evidência | Avaliação |
|----------------|-----------|-----------|
| Campos extras de equipamento: fabricante, nº de série, setor, data de aquisição | `app/persistencia.py:29-34`, `app/modulos/equipamentos.py:48-69` | Útil para a ficha técnica do equipamento ("detalhes técnicos"); **decisão pendente** sobre incluir no modelo |
| Contadores monotônicos de ID (`seq`) | `app/persistencia.py:15`, `app/contexto.py:18-20` | Resolve reaproveitamento de IDs (AUD-05); na Fase 03 as sequências do banco cumprem esse papel |
| Histórico como coleção global com `equipamento_id` | `app/contexto.py:51-61` | Facilita consulta por equipamento; o mesmo é possível por consulta SQL no novo modelo |
| Bloqueio de exclusão de usuário com OS ativas | `app/modulos/usuarios.py:52-59` | Regra mais restritiva que a do baseline (que bloqueia por qualquer histórico); apenas como referência |

**Não reaproveitar:** persistência, interface, modelo de permissões por lista e criação de cargos. **Recomendação:**
manter `app/` intocada na Fase 01 e decidir sua remoção em fase posterior, com autorização específica.

## 9. Documentação existente

### AUD-19 — Afirmações além do código (Baixa) [Estático]
`DOCUMENTACAO.md` §2 diz que as telas "não decidem nada" e que trocar o JSON "mexeria só no `Repositorio`". Os achados
AUD-09, AUD-10 e AUD-16 mostram regras na UI e no `Repositorio` e a UI controlando a gravação. O `README.md` descreve a
estrutura sem mencionar `app/`. Esses textos documentam a Entrega 1 e **não foram alterados** (a tag `entrega-1` os
preserva); a documentação final (Fase 11) deve ser consistente com o código.

## Apêndice A — Como reproduzir os achados executados

Execute a partir da raiz do repositório, com dados em diretório temporário (não toca `dados/`):

```python
import sys, os, tempfile, json
sys.dont_write_bytecode = True
sys.path.insert(0, ".")
from models import (OrdemServico, StatusOS, Criticidade, Disponibilidade,
                    Permissoes, Equipamento)
from persistencia import Repositorio

tmp = tempfile.mkdtemp()
def arq(n): return os.path.join(tmp, n)
```

**B1 — apontamento em OS concluída (AUD-11)**
```python
r = Repositorio(arq("b1.json")); ana, bruno, carla = r.usuarios
o = OrdemServico.abrir(1, r.equipamentos[0], "x", Criticidade.ALTA, carla)
o.atribuir(bruno, ana); o.registrar_diagnostico(bruno, "d", "c")
o.apontar_reparo(bruno, 1, "i", []); o.alterar_status(bruno, StatusOS.REPARO_FINALIZADO)
o.concluir_tecnicamente(bruno, "t", True); o.aprovar(ana)
o.adicionar_apontamento(carla, "texto")        # sem exceção; status continua Concluída
```

**B2 — atribuição a técnico Ausente (AUD-09)**
```python
r = Repositorio(arq("b2.json")); ana, bruno, _ = r.usuarios
bruno.disponibilidade = Disponibilidade.AUSENTE
OrdemServico.abrir(1, r.equipamentos[0], "x", Criticidade.BAIXA, ana).atribuir(bruno, ana)   # sem exceção
```

**B3 — permissão com nome errado (AUD-03)**
```python
Permissoes.padrao_gestor().tem("aprovar_oss")  # False, sem erro
```

**B4 — remoção sem identidade (AUD-02)**
```python
r = Repositorio(arq("b4.json"))
e = Equipamento(r.proximo_id_equipamento(), "Teste", "T1"); r.adicionar_equipamento(e)
r.remover_equipamento(e)                        # sem usuário, sem permissão
```

**B5 — entradas vazias (AUD-12)**
```python
r = Repositorio(arq("b5.json")); ana, bruno, _ = r.usuarios
o = OrdemServico.abrir(1, r.equipamentos[0], "", Criticidade.BAIXA, ana)   # falha vazia
o.atribuir(bruno, ana); o.apontar_reparo(bruno, 0.0, "", [])               # 0 h e texto vazio
```

**C — perda de atualização e número duplicado (AUD-04, AUD-05)**
```python
Repositorio(arq("c.json"))
a, b = Repositorio(arq("c.json")), Repositorio(arq("c.json"))
oa = OrdemServico.abrir(a.proximo_numero_os(), a.equipamentos[0], "A", Criticidade.BAIXA, a.usuarios[0])
ob = OrdemServico.abrir(b.proximo_numero_os(), b.equipamentos[1], "B", Criticidade.ALTA, b.usuarios[0])
a.adicionar_os(oa); a.salvar(); b.adicionar_os(ob); b.salvar()
print(oa.numero, ob.numero, [(o.numero, o.falha) for o in Repositorio(arq("c.json")).ordens])
# 1 1 [(1, 'B')]
```

**D — formatos incompatíveis (AUD-06)** (reutiliza o arquivo `c.json` criado no item C)
```python
import app.persistencia as ap
from app.contexto import Contexto
json.dump(ap.dados_iniciais(), open(arq("d.json"), "w", encoding="utf-8"))
Repositorio(arq("d.json"))                     # AttributeError: 'list' object has no attribute 'get'
ap.ARQUIVO_DADOS, ap.PASTA_DADOS = arq("c.json"), tmp
ctx = Contexto(); ctx.prox_id("os")             # KeyError: 'seq'
ctx.pode("aprovar_os", ctx.db["usuarios"][1])   # True para o técnico (chaves do dict existem)
```

**F — finalizar sem diagnóstico (AUD-21)**
```python
r = Repositorio(arq("f.json")); ana, bruno, carla = r.usuarios
o = OrdemServico.abrir(1, r.equipamentos[0], "x", Criticidade.BAIXA, carla); o.atribuir(bruno, ana)
o.apontar_reparo(bruno, 1, "troca", []); o.alterar_status(bruno, StatusOS.REPARO_FINALIZADO)
o.concluir_tecnicamente(bruno, "t", True)      # RegraNegocioError: Registre o diagnóstico antes de concluir.
o.registrar_diagnostico(bruno, "p", "c")       # RegraNegocioError: Operação não permitida com a OS em 'Reparo Finalizado'.
o.alterar_status(bruno, StatusOS.EM_EXECUCAO)  # permitido; só então o diagnóstico é aceito
```

**E — disponibilidade (AUD-13)**
```python
r = Repositorio(arq("e.json")); ana, bruno, _ = r.usuarios
o = OrdemServico.abrir(1, r.equipamentos[0], "x", Criticidade.BAIXA, ana); r.adicionar_os(o)
o.atribuir(bruno, ana); o.apontar_reparo(bruno, 1, "i", [])
bruno.disponibilidade            # Disponível (ainda não recalculado)
r.atualizar_disponibilidades(); bruno.disponibilidade   # Em atendimento
o.alterar_status(bruno, StatusOS.AGUARDANDO_PECA); r.atualizar_disponibilidades(); bruno.disponibilidade   # Disponível
```
