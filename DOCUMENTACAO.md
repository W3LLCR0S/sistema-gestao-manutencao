# Documentação — Sistema de Gestão de Manutenção de Equipamentos

## 1. Visão geral

Aplicação em Python, orientada a objetos e com interface de linha de comando (CLI).
Ela controla o ciclo de manutenção de um equipamento: um usuário abre a OS, o gestor
atribui a um técnico, o técnico diagnostica, faz o reparo e testa, e o gestor aprova e
encerra. Tudo o que acontece em cada OS fica registrado no histórico dela.

**Execução:** `python main.py` (Python 3.8+ e nenhuma biblioteca externa).
Os dados ficam em `dados/dados.json`, criado na primeira execução com dados de exemplo:

| ID | Usuário | Cargo |
|---|---|---|
| 1 | Ana Souza | Gestor |
| 2 | Bruno Lima | Técnico |
| 3 | Carla Mendes | Técnico |

---

## 2. Arquitetura em três camadas

```
ui/            → telas: lê o teclado e mostra resultados
   │
models/        → classes do domínio e TODAS as regras de negócio
   │
persistencia/  → Repositorio: guarda os objetos e salva/carrega o JSON
```

**Por quê:** cada camada tem uma responsabilidade só.
- As **telas** não decidem nada. Elas só perguntam e mostram.
- As **classes** não sabem que existe terminal nem arquivo. Por isso a mesma
  `OrdemServico` funcionaria igual numa interface web ou desktop.
- A **persistência** fica isolada. Trocar o JSON por um banco de dados (SQLite,
  Oracle...) mexeria só no `Repositorio`.

---

## 3. Classes (seguindo a tree do exercício)

```
Usuario ──► Cargo ──► Permissoes
  id          nome       ver_equipamentos, ver_os, abrir_os, ...
  nome        permissoes diagnosticar, apontar_reparo, ...
  cargo                  gerir_usuarios, atribuir_os, aprovar_os ...

OrdemServico ──► Servico (1..N)          Equipamento
  numero           numero (sequencial)     id
  status           tipo, descrição         nome
  diagnostico      responsável, data       modelo
  horas_trabalhadas horas, peças
  intervencoes_realizadas
  pecas_utilizadas
  tecnico_atribuido
```

### Usuario → Cargo → Permissoes
Nem o usuário nem o cargo guardam as permissões soltas: o cargo aponta para um objeto
`Permissoes`, em que cada acesso é um atributo `True`/`False`.

**Por quê:**
- As permissões ficam **no cargo, não no usuário**. Mudar o que um cargo pode fazer
  vale para todos os usuários desse cargo de uma vez.
- **Os cargos são fixos: Gestor e Técnico**, os dois tipos de usuário exigidos pelo
  enunciado. O sistema não cria nem exclui cargos. Assim nunca fica um usuário sem cargo
  nem aparece um perfil que as telas não previram. Na tela "Permissões dos cargos", o
  gestor pode apenas **ajustar os acessos** de cada cargo (o "definir níveis de acesso"
  do enunciado).
- Ao cadastrar ou editar um usuário, o gestor escolhe um desses dois cargos.
- **Técnico não é definido pelo nome do cargo**: técnico é quem tem o acesso
  `apontar_reparo` (`usuario.e_tecnico`). A regra depende das permissões, não de
  comparar textos.

### OrdemServico e Servico
A `OrdemServico` tem os atributos da tree. O `Servico` representa **cada serviço/ação
feito dentro da OS**: abertura, atribuição, diagnóstico, reparo, mudança de status e
encerramento. A lista `os.servicos` é o **histórico sequencial** pedido no enunciado.

**Por quê:**
- A OS guarda o **estado atual** (total de horas, diagnóstico, status). Os serviços guardam
  **como se chegou nele**: quem fez o quê, quando e quanto tempo levou.
- Cada reparo apontado vira um `Servico` com suas horas e peças, e também soma nos totais
  da OS. Assim dá para ver o resumo e o detalhe.
- Os serviços são criados **só pelos métodos da própria OS**. Não tem como alterar a OS
  sem deixar registro no histórico.

### Equipamento
Só `id`, `nome` e `modelo`, mais o campo `ativo`.

**Por quê `ativo`:** o enunciado pede **inativar**. Um equipamento que já tem OS não pode ser
excluído, senão o histórico perderia a referência. Ele é inativado: continua aparecendo nas
consultas, mas não recebe novas OS.

### Classes de apoio
- `PecaMaterial` (descrição + quantidade): peça tem dois dados, não cabe num texto só.
- `Enums` (`StatusOS`, `Criticidade`, `Disponibilidade`, `TipoServico`): limitam os valores
  possíveis. Não tem como existir uma OS com status "Concluida" escrito errado.
- `RegraNegocioError`: exceção única para qualquer regra violada. A tela só mostra a mensagem.

---

## 4. Regras de negócio dentro das classes

Cada operação é um método da classe que valida tudo antes de alterar qualquer dado:

```python
def apontar_reparo(self, tecnico, horas, intervencao, pecas):
    tecnico.exigir("apontar_reparo")          # 1. tem permissão?
    self._exigir_tecnico_da_os(tecnico)       # 2. a OS é dele?
    self._exigir_status(ATRIBUIDA, EM_EXECUCAO, AGUARDANDO_PECA)  # 3. status permite?
    ...                                        # 4. só então altera e registra o Servico
```

**Por quê (encapsulamento):** a regra fica num lugar só. Qualquer tela que chamar
`apontar_reparo` passa pelas mesmas validações, e ninguém esquece de checar algo.

**Verificação dupla de permissão:** o menu só mostra as opções do cargo, e o método da
classe confere de novo com `exigir()`. O menu é a conveniência; o método é a garantia.

---

## 5. Fluxo de status da OS

```
Aberta → Atribuída → Em Execução ⇄ Aguardando Peça → Reparo Finalizado
       → Aguardando Aprovação → Concluída
                  (Cancelada: pelo gestor, em qualquer etapa antes do fim)
```

| Quem | Pode fazer |
|---|---|
| Gestor | atribuir (Aberta → Atribuída), aprovar (→ Concluída), reprovar (→ Em Execução), cancelar |
| Técnico | apontar reparo (Atribuída → Em Execução automático), mudar entre Em Execução / Aguardando Peça / Reparo Finalizado, concluir tecnicamente (→ Aguardando Aprovação) |

**Por quê o status "Aguardando Aprovação":** o enunciado separa a *conclusão técnica*
(técnico) da *aprovação e encerramento administrativo* (gestor). Esse status mostra que o
técnico terminou, mas o gestor ainda não validou.

Outras travas:
- não dá para marcar "Reparo Finalizado" sem nenhuma intervenção registrada;
- não dá para concluir sem diagnóstico;
- se o teste funcional falhar, a OS não avança.

---

## 6. Persistência

O `Repositorio` mantém listas de objetos em memória. Cada classe tem `to_dict()` para
gravar e `from_dict()` para recriar o objeto na leitura.

**Decisões:**
- **O JSON é só o formato do arquivo.** O programa trabalha sempre com objetos, e a
  conversão acontece apenas ao salvar e ao carregar.
- **Referências por ID:** no arquivo a OS guarda `tecnico_atribuido_id: 2`, não uma cópia do
  técnico. Na leitura o ID vira o objeto `Usuario` de novo. Assim os dados não se duplicam, e
  mudar o nome do técnico aparece em todas as OS.
- **Ordem de carga:** cargos → usuários → equipamentos → OS, porque cada item depende do
  anterior.
- **Gravação segura:** o sistema grava num arquivo temporário e depois o renomeia. Se o
  programa cair no meio, o `dados.json` antigo não se corrompe.
- **Salva após cada ação** do menu, para não perder dados se o terminal for fechado.
- **Não exclui o que tem histórico:** usuários e equipamentos que já aparecem
  em OS não podem ser excluídos. Isso evita referências quebradas.

---

## 7. Disponibilidade dos técnicos

Depois de cada ação, o sistema recalcula o status dos técnicos: quem tem OS **Em Execução**
fica "Em atendimento", os outros ficam "Disponível". Quem se marcou como **Ausente** só muda
manualmente.

**Por quê:** o status reflete o trabalho real sem depender de alguém lembrar de atualizar.
Na atribuição, os técnicos aparecem ordenados pela quantidade de OS ativas, para ajudar o
gestor a **balancear a carga**.

---

## 8. Limitações conhecidas

- **Sem senha (CLI legada):** o login é por ID, para facilitar a demonstração.
- **Um usuário por vez:** o arquivo JSON não trata acesso simultâneo. Para isso seria
  necessário um banco de dados.
- **Permissões por nome em texto** (`"aprovar_os"`): um erro de digitação no código não é
  detectado. Poderia virar um `Enum Acesso`.
