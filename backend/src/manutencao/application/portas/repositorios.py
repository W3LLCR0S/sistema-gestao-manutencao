"""Portas de repositório: um ``Protocol`` por agregado (ADR-0004), sem repositório genérico.

Os quatro contratos diferem de propósito: equipamentos e usuários podem ser excluídos, cargos são
fixos (só as permissões mudam) e a OS nunca é excluída, mas tem consultas próprias. Cada porta
expõe só o que seus clientes usam (ISP) e **nenhuma regra de negócio**.

Semântica comum, que toda implementação deve respeitar (a suíte de contrato a verifica):

* **Identidade e cópia.** ``obter`` e ``listar`` devolvem objetos **independentes** do armazenado:
  alterar o que se recebeu não altera o repositório. Uma alteração só passa a valer depois de
  ``salvar``. ``adicionar`` e ``salvar`` guardam uma cópia do que receberam. Entidades continuam
  sendo comparadas por identificador (``__eq__`` do domínio), nunca por identidade de objeto.
* **Ausência.** ``obter`` devolve ``None`` quando o identificador não existe. ``salvar`` e
  ``remover`` de um identificador inexistente levantam :class:`NaoEncontradoError`.
* **Identificadores monotônicos (DLT-10, AUD-05).** Cada repositório mantém uma sequência própria,
  independente das demais. ``proximo_*`` apenas **consulta** o identificador que o próximo
  ``adicionar`` receberia (não o consome; uma operação recusada antes de adicionar não gasta
  número, como no legado). ``adicionar`` exige um identificador **maior que todos os já emitidos**,
  inclusive os de objetos excluídos: caso contrário levanta :class:`IdentificadorJaEmitidoError`.
  Excluir nunca libera um identificador, e ``salvar`` nunca renumera.
* **Ordem.** ``listar`` devolve em ordem crescente de identificador (a ordem de cadastro).
* **Sem E/S.** Nada aqui conhece arquivo, banco ou rede; transações e concorrência são da
  implementação que as precisar (Fase 03).
"""

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from manutencao.domain.cargo import Cargo
from manutencao.domain.enums import Criticidade, StatusOS
from manutencao.domain.equipamento import Equipamento
from manutencao.domain.ordem_servico import OrdemServico
from manutencao.domain.usuario import Usuario


@dataclass(frozen=True)
class FiltroDeOrdens:
    """Critérios de listagem de OS; os informados se combinam (E). Vazio = todas.

    Cobre os filtros do legado (todas, em aberto, encerradas, por status, por equipamento, por
    técnico e por criticidade). ``tecnico_id`` casa com o técnico atribuído; ``encerrada`` casa com
    OS Concluída ou Cancelada (``False`` = em aberto).
    """

    status: StatusOS | None = None
    criticidade: Criticidade | None = None
    equipamento_id: int | None = None
    tecnico_id: int | None = None
    encerrada: bool | None = None

    def aceita(self, ordem: OrdemServico) -> bool:
        """Definição única do filtro; implementações em memória a usam, as de banco a traduzem."""
        tecnico = ordem.tecnico_atribuido
        return (
            (self.status is None or ordem.status == self.status)
            and (self.criticidade is None or ordem.criticidade == self.criticidade)
            and (self.equipamento_id is None or ordem.equipamento.id == self.equipamento_id)
            and (self.tecnico_id is None or (tecnico is not None and tecnico.id == self.tecnico_id))
            and (self.encerrada is None or ordem.encerrada == self.encerrada)
        )


@runtime_checkable
class EquipamentoRepository(Protocol):
    """Inventário de equipamentos."""

    def proximo_id(self) -> int:
        """O identificador que o próximo ``adicionar`` receberia (não o consome)."""
        ...

    def adicionar(self, equipamento: Equipamento) -> None:
        """Cadastra uma cópia. ``IdentificadorJaEmitidoError`` se o id já foi emitido."""
        ...

    def obter(self, id: int) -> Equipamento | None:
        """Uma cópia do equipamento, ou ``None`` se não existir."""
        ...

    def listar(self) -> tuple[Equipamento, ...]:
        """Cópias de todos os equipamentos, por id crescente."""
        ...

    def salvar(self, equipamento: Equipamento) -> None:
        """Atualiza o equipamento existente. ``NaoEncontradoError`` se não existir."""
        ...

    def remover(self, id: int) -> None:
        """Exclui. ``NaoEncontradoError`` se não existir. O id nunca é reutilizado."""
        ...


@runtime_checkable
class CargoRepository(Protocol):
    """Cargos e suas permissões. Os cargos são fixos: não há exclusão."""

    def proximo_id(self) -> int:
        """O identificador que o próximo ``adicionar`` receberia (não o consome)."""
        ...

    def adicionar(self, cargo: Cargo) -> None:
        """Cadastra uma cópia (carga inicial). ``IdentificadorJaEmitidoError`` se o id já saiu."""
        ...

    def obter(self, id: int) -> Cargo | None:
        """Uma cópia do cargo, ou ``None`` se não existir."""
        ...

    def listar(self) -> tuple[Cargo, ...]:
        """Cópias de todos os cargos, por id crescente."""
        ...

    def salvar(self, cargo: Cargo) -> None:
        """Atualiza nome e permissões. ``NaoEncontradoError`` se não existir."""
        ...


@runtime_checkable
class UsuarioRepository(Protocol):
    """Usuários. O cargo de cada um é resolvido pelo repositório de cargos a cada leitura."""

    def proximo_id(self) -> int:
        """O identificador que o próximo ``adicionar`` receberia (não o consome)."""
        ...

    def adicionar(self, usuario: Usuario) -> None:
        """Cadastra uma cópia. ``NaoEncontradoError`` se o cargo não existir e
        ``IdentificadorJaEmitidoError`` se o id já foi emitido.

        A matrícula é única: se o usuário a traz, ela é gravada (``RegraDeAplicacaoError``
        ``matricula_em_uso`` se pertencer a outro); se vem ``None``, o repositório gera uma livre
        e a atribui ao objeto recebido. Nenhuma operação posterior altera a matrícula."""
        ...

    def obter(self, id: int) -> Usuario | None:
        """Uma cópia do usuário (com o cargo e as permissões atuais), ou ``None``."""
        ...

    def obter_por_matricula(self, matricula: str) -> Usuario | None:
        """O usuário dono da matrícula (``AA999999``, comparação exata), ou ``None``."""
        ...

    def matricula_existe(self, matricula: str) -> bool:
        """Se algum usuário já tem a matrícula."""
        ...

    def listar(self) -> tuple[Usuario, ...]:
        """Cópias de todos os usuários, por id crescente."""
        ...

    def salvar(self, usuario: Usuario) -> None:
        """Atualiza o usuário existente. ``NaoEncontradoError`` se ele ou o cargo não existirem."""
        ...

    def remover(self, id: int) -> None:
        """Exclui. ``NaoEncontradoError`` se não existir. O id nunca é reutilizado."""
        ...


@runtime_checkable
class OrdemServicoRepository(Protocol):
    """Ordens de serviço (raiz do agregado: histórico e peças vão junto). Nunca são excluídas.

    A OS guarda **cópias** dos usuários e do equipamento a que se refere, como estavam quando ela
    foi salva; os dados atuais dessas entidades vêm dos repositórios delas. Só o identificador
    dessas referências é contrato.
    """

    def proximo_numero(self) -> int:
        """O número que o próximo ``adicionar`` receberia (não o consome)."""
        ...

    def adicionar(self, ordem: OrdemServico) -> None:
        """Cadastra uma cópia. ``IdentificadorJaEmitidoError`` se o número já foi emitido."""
        ...

    def obter(self, numero: int) -> OrdemServico | None:
        """Uma cópia da OS, ou ``None`` se não existir."""
        ...

    def listar(self, filtro: FiltroDeOrdens | None = None) -> tuple[OrdemServico, ...]:
        """Cópias das OS que satisfazem o filtro, por número crescente."""
        ...

    def contar(self, filtro: FiltroDeOrdens | None = None) -> int:
        """Quantas OS satisfazem o filtro."""
        ...

    def salvar(self, ordem: OrdemServico) -> None:
        """Atualiza a OS existente. ``NaoEncontradoError`` se não existir."""
        ...

    def usuario_tem_participacao(self, usuario_id: int) -> bool:
        """Se o usuário aparece em alguma OS: técnico atribuído, autor da abertura ou
        responsável por qualquer registro do histórico."""
        ...
