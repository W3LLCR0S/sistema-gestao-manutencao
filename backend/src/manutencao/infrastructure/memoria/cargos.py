"""Repositório de cargos em memória (implementa ``CargoRepository``)."""

from dataclasses import dataclass

from manutencao.application.erros import NaoEncontradoError
from manutencao.domain.cargo import Cargo
from manutencao.domain.permissoes import Permissao, Permissoes
from manutencao.infrastructure.memoria.sequencia import SequenciaMonotonica


@dataclass(frozen=True)
class _RegistroCargo:
    """Valores do cargo; o ``Permissoes`` (mutável) é refeito a cada leitura."""

    id: int
    nome: str
    permissoes: tuple[Permissao, ...]


class CargosEmMemoria:
    """Guarda os valores do cargo e monta um ``Cargo`` novo a cada leitura."""

    def __init__(self) -> None:
        self._itens: dict[int, _RegistroCargo] = {}
        self._sequencia = SequenciaMonotonica("Cargo")

    @staticmethod
    def _registro(cargo: Cargo) -> _RegistroCargo:
        return _RegistroCargo(cargo.id, cargo.nome, cargo.permissoes.ativas())

    @staticmethod
    def _cargo(registro: _RegistroCargo) -> Cargo:
        return Cargo(registro.id, registro.nome, Permissoes(registro.permissoes))

    def proximo_id(self) -> int:
        return self._sequencia.proximo()

    def adicionar(self, cargo: Cargo) -> None:
        self._sequencia.registrar(cargo.id)
        self._itens[cargo.id] = self._registro(cargo)

    def obter(self, id: int) -> Cargo | None:
        achado = self._itens.get(id)
        return None if achado is None else self._cargo(achado)

    def listar(self) -> tuple[Cargo, ...]:
        return tuple(self._cargo(self._itens[id]) for id in sorted(self._itens))

    def salvar(self, cargo: Cargo) -> None:
        if cargo.id not in self._itens:
            raise NaoEncontradoError("Cargo", cargo.id)
        self._itens[cargo.id] = self._registro(cargo)
