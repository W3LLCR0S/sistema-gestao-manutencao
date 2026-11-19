"""Repositório de cargos no PostgreSQL (implementa ``CargoRepository``)."""

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from manutencao.application.erros import NaoEncontradoError
from manutencao.domain.cargo import Cargo
from manutencao.domain.permissoes import Permissao, Permissoes
from manutencao.infrastructure.postgres.banco import Banco
from manutencao.infrastructure.postgres.modelos import CargoModelo, CargoPermissaoModelo
from manutencao.infrastructure.postgres.sequencia import SequenciaNoBanco


def _cargo(modelo: CargoModelo) -> Cargo:
    permissoes = Permissoes(Permissao(p.permissao) for p in modelo.permissoes)
    return Cargo(modelo.id, modelo.nome, permissoes)


class CargosNoBanco:
    """Cargos e permissões. Cada chamada é uma transação (ou participa da externa)."""

    def __init__(self, banco: Banco) -> None:
        self._banco = banco
        self._sequencia = SequenciaNoBanco("cargo", "Cargo")

    @staticmethod
    def _gravar_permissoes(sessao: Session, cargo: Cargo) -> None:
        sessao.execute(
            delete(CargoPermissaoModelo).where(CargoPermissaoModelo.cargo_id == cargo.id)
        )
        sessao.add_all(
            CargoPermissaoModelo(cargo_id=cargo.id, permissao=p.value)
            for p in cargo.permissoes.ativas()
        )

    def proximo_id(self) -> int:
        with self._banco.transacao() as sessao:
            return self._sequencia.proximo(sessao)

    def adicionar(self, cargo: Cargo) -> None:
        with self._banco.transacao() as sessao:
            self._sequencia.registrar(sessao, cargo.id)
            sessao.add(CargoModelo(id=cargo.id, nome=cargo.nome))
            sessao.flush()
            self._gravar_permissoes(sessao, cargo)

    def obter(self, id: int) -> Cargo | None:
        with self._banco.transacao() as sessao:
            modelo = sessao.get(CargoModelo, id, populate_existing=True)
            return None if modelo is None else _cargo(modelo)

    def listar(self) -> tuple[Cargo, ...]:
        with self._banco.transacao() as sessao:
            modelos = sessao.scalars(
                select(CargoModelo)
                .order_by(CargoModelo.id)
                .execution_options(populate_existing=True)
            ).all()
            return tuple(_cargo(m) for m in modelos)

    def salvar(self, cargo: Cargo) -> None:
        with self._banco.transacao() as sessao:
            modelo = sessao.get(CargoModelo, cargo.id)
            if modelo is None:
                raise NaoEncontradoError("Cargo", cargo.id)
            modelo.nome = cargo.nome
            sessao.flush()
            self._gravar_permissoes(sessao, cargo)
            sessao.expire(modelo)
