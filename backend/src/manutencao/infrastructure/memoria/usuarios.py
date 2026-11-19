"""Repositório de usuários em memória (implementa ``UsuarioRepository``)."""

from dataclasses import dataclass

from manutencao.application.erros import (
    CodigoErroAplicacao,
    NaoEncontradoError,
    RegraDeAplicacaoError,
)
from manutencao.application.portas.repositorios import CargoRepository
from manutencao.domain.enums import Disponibilidade, Papel
from manutencao.domain.matricula import gerar_matricula_unica
from manutencao.domain.usuario import Usuario
from manutencao.infrastructure.memoria.sequencia import SequenciaMonotonica


@dataclass(frozen=True)
class _RegistroUsuario:
    """Valores do usuário; o cargo é guardado só pelo id e resolvido a cada leitura."""

    id: int
    nome: str
    cargo_id: int
    email: str
    escala: str
    disponibilidade: Disponibilidade
    papel: Papel
    ativo: bool
    matricula: str


class UsuariosEmMemoria:
    """Guarda valores e monta um ``Usuario`` novo, com o cargo atual, a cada leitura.

    Depende da **porta** ``CargoRepository`` (injetada), não de uma implementação: assim uma
    alteração das permissões de um cargo vale para todos os usuários dele na leitura seguinte.
    """

    def __init__(self, cargos: CargoRepository) -> None:
        self._cargos = cargos
        self._itens: dict[int, _RegistroUsuario] = {}
        self._sequencia = SequenciaMonotonica("Usuário")

    def _exigir_cargo(self, cargo_id: int) -> None:
        if self._cargos.obter(cargo_id) is None:
            raise NaoEncontradoError("Cargo", cargo_id)

    @staticmethod
    def _registro(usuario: Usuario) -> _RegistroUsuario:
        return _RegistroUsuario(
            usuario.id,
            usuario.nome,
            usuario.cargo.id,
            usuario.email,
            usuario.escala,
            usuario.disponibilidade,
            usuario.papel,
            usuario.ativo,
            usuario.matricula or "",
        )

    def _usuario(self, registro: _RegistroUsuario) -> Usuario:
        cargo = self._cargos.obter(registro.cargo_id)
        if cargo is None:  # cargos não são excluídos; só uma porta de cargos incoerente chega aqui
            raise NaoEncontradoError("Cargo", registro.cargo_id)
        return Usuario(
            registro.id,
            registro.nome,
            cargo,
            registro.email,
            registro.escala,
            registro.disponibilidade,
            papel=registro.papel,
            ativo=registro.ativo,
            matricula=registro.matricula,
        )

    def proximo_id(self) -> int:
        return self._sequencia.proximo()

    def matricula_existe(self, matricula: str) -> bool:
        return any(r.matricula == matricula for r in self._itens.values())

    def obter_por_matricula(self, matricula: str) -> Usuario | None:
        achado = next((r for r in self._itens.values() if r.matricula == matricula), None)
        return None if achado is None else self._usuario(achado)

    def adicionar(self, usuario: Usuario) -> None:
        self._exigir_cargo(usuario.cargo.id)
        if usuario.matricula is None:  # o repositório atribui uma matrícula livre ao objeto
            usuario.atribuir_matricula(gerar_matricula_unica(self.matricula_existe))
        elif self.matricula_existe(usuario.matricula):
            raise RegraDeAplicacaoError(
                CodigoErroAplicacao.MATRICULA_EM_USO, "Essa matrícula já está em uso."
            )
        self._sequencia.registrar(usuario.id)
        self._itens[usuario.id] = self._registro(usuario)

    def obter(self, id: int) -> Usuario | None:
        achado = self._itens.get(id)
        return None if achado is None else self._usuario(achado)

    def listar(self) -> tuple[Usuario, ...]:
        return tuple(self._usuario(self._itens[id]) for id in sorted(self._itens))

    def salvar(self, usuario: Usuario) -> None:
        if usuario.id not in self._itens:
            raise NaoEncontradoError("Usuário", usuario.id)
        self._exigir_cargo(usuario.cargo.id)
        self._itens[usuario.id] = self._registro(usuario)

    def remover(self, id: int) -> None:
        if id not in self._itens:
            raise NaoEncontradoError("Usuário", id)
        del self._itens[id]  # a sequência não recua: o id não será reutilizado
