"""Repositório de usuários no PostgreSQL (implementa ``UsuarioRepository``)."""

from sqlalchemy import select

from manutencao.application.erros import NaoEncontradoError
from manutencao.application.portas.repositorios import CargoRepository
from manutencao.domain.cargo import Cargo
from manutencao.domain.enums import Disponibilidade, Papel
from manutencao.domain.usuario import Usuario
from manutencao.infrastructure.postgres.banco import Banco
from manutencao.infrastructure.postgres.modelos import UsuarioModelo
from manutencao.infrastructure.postgres.sequencia import SequenciaNoBanco


class UsuariosNoBanco:
    """Usuários. O cargo é resolvido pela **porta** ``CargoRepository`` a cada leitura.

    Assim, alterar as permissões de um cargo vale para todos os usuários dele na leitura seguinte,
    exatamente como na implementação em memória.
    """

    def __init__(self, banco: Banco, cargos: CargoRepository) -> None:
        self._banco = banco
        self._cargos = cargos
        self._sequencia = SequenciaNoBanco("usuario", "Usuário")

    def _exigir_cargo(self, cargo_id: int) -> None:
        if self._cargos.obter(cargo_id) is None:
            raise NaoEncontradoError("Cargo", cargo_id)

    @staticmethod
    def _usuario(modelo: UsuarioModelo, cargo: Cargo) -> Usuario:
        return Usuario(
            modelo.id,
            modelo.nome,
            cargo,
            modelo.email,
            modelo.escala,
            Disponibilidade(modelo.disponibilidade),
            papel=Papel(modelo.papel),
            ativo=modelo.ativo,
        )

    @staticmethod
    def _preencher(modelo: UsuarioModelo, usuario: Usuario) -> None:
        modelo.nome = usuario.nome
        modelo.cargo_id = usuario.cargo.id
        modelo.email = usuario.email
        modelo.escala = usuario.escala
        modelo.disponibilidade = usuario.disponibilidade.value
        modelo.papel = usuario.papel.value
        modelo.ativo = usuario.ativo

    def proximo_id(self) -> int:
        with self._banco.transacao() as sessao:
            return self._sequencia.proximo(sessao)

    def adicionar(self, usuario: Usuario) -> None:
        with self._banco.transacao() as sessao:
            self._exigir_cargo(usuario.cargo.id)
            self._sequencia.registrar(sessao, usuario.id)
            modelo = UsuarioModelo(id=usuario.id)
            self._preencher(modelo, usuario)
            sessao.add(modelo)

    def obter(self, id: int) -> Usuario | None:
        with self._banco.transacao() as sessao:
            modelo = sessao.get(UsuarioModelo, id, populate_existing=True)
            if modelo is None:
                return None
            cargo = self._cargos.obter(modelo.cargo_id)
            if cargo is None:  # a chave estrangeira impede; só uma porta de cargos incoerente
                raise NaoEncontradoError("Cargo", modelo.cargo_id)
            return self._usuario(modelo, cargo)

    def listar(self) -> tuple[Usuario, ...]:
        with self._banco.transacao() as sessao:
            modelos = sessao.scalars(
                select(UsuarioModelo)
                .order_by(UsuarioModelo.id)
                .execution_options(populate_existing=True)
            ).all()
            cargos = {c.id: c for c in self._cargos.listar()}
            return tuple(self._usuario(m, cargos[m.cargo_id]) for m in modelos)

    def salvar(self, usuario: Usuario) -> None:
        with self._banco.transacao() as sessao:
            modelo = sessao.get(UsuarioModelo, usuario.id)
            if modelo is None:
                raise NaoEncontradoError("Usuário", usuario.id)
            self._exigir_cargo(usuario.cargo.id)
            self._preencher(modelo, usuario)

    def remover(self, id: int) -> None:
        with self._banco.transacao() as sessao:
            modelo = sessao.get(UsuarioModelo, id)
            if modelo is None:
                raise NaoEncontradoError("Usuário", id)
            sessao.delete(modelo)  # a sequência não recua: o id não será reutilizado
