"""Repositório de usuários no PostgreSQL (implementa ``UsuarioRepository``)."""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from manutencao.application.erros import (
    CodigoErroAplicacao,
    NaoEncontradoError,
    RegraDeAplicacaoError,
)
from manutencao.application.portas.repositorios import CargoRepository
from manutencao.domain.cargo import Cargo
from manutencao.domain.enums import Disponibilidade, Papel
from manutencao.domain.matricula import gerar_matricula_unica
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
            matricula=modelo.matricula,
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

    def matricula_existe(self, matricula: str) -> bool:
        with self._banco.transacao() as sessao:
            achado = sessao.scalars(
                select(UsuarioModelo.id).where(UsuarioModelo.matricula == matricula)
            ).first()
            return achado is not None

    def obter_por_matricula(self, matricula: str) -> Usuario | None:
        with self._banco.transacao() as sessao:
            modelo = sessao.scalars(
                select(UsuarioModelo)
                .where(UsuarioModelo.matricula == matricula)
                .execution_options(populate_existing=True)
            ).first()
            if modelo is None:
                return None
            cargo = self._cargos.obter(modelo.cargo_id)
            if cargo is None:
                raise NaoEncontradoError("Cargo", modelo.cargo_id)
            return self._usuario(modelo, cargo)

    def adicionar(self, usuario: Usuario) -> None:
        """Grava o usuário. A restrição ``UNIQUE`` da matrícula é a garantia final contra corrida:
        a gravação roda num ponto de salvamento, de modo que uma colisão desfaz só ela (inclusive o
        registro da sequência) e vira ``matricula_em_uso``, sem contaminar a transação externa."""
        with self._banco.transacao() as sessao:
            self._exigir_cargo(usuario.cargo.id)
            gerada = usuario.matricula is None
            for _ in range(5 if gerada else 1):
                candidata = (
                    gerar_matricula_unica(self.matricula_existe)
                    if usuario.matricula is None
                    else usuario.matricula
                )
                try:
                    with sessao.begin_nested():
                        self._sequencia.registrar(sessao, usuario.id)
                        modelo = UsuarioModelo(id=usuario.id, matricula=candidata)
                        self._preencher(modelo, usuario)
                        sessao.add(modelo)
                        sessao.flush()
                except IntegrityError as erro:
                    if "matricula" not in str(erro.orig).lower():
                        raise
                    if gerada:
                        continue  # corrida rara: sorteia outra
                    raise RegraDeAplicacaoError(
                        CodigoErroAplicacao.MATRICULA_EM_USO, "Essa matrícula já está em uso."
                    ) from erro
                if gerada:
                    usuario.atribuir_matricula(candidata)
                return
            raise RegraDeAplicacaoError(
                CodigoErroAplicacao.MATRICULA_EM_USO, "Não foi possível gerar uma matrícula livre."
            )

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
