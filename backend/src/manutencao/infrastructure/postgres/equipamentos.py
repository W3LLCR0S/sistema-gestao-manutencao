"""Repositório de equipamentos no PostgreSQL (implementa ``EquipamentoRepository``)."""

from sqlalchemy import select

from manutencao.application.erros import NaoEncontradoError
from manutencao.domain.equipamento import Equipamento
from manutencao.infrastructure.postgres.banco import Banco
from manutencao.infrastructure.postgres.modelos import EquipamentoModelo
from manutencao.infrastructure.postgres.sequencia import SequenciaNoBanco


def _equipamento(modelo: EquipamentoModelo) -> Equipamento:
    return Equipamento(modelo.id, modelo.nome, modelo.modelo, modelo.ativo)


class EquipamentosNoBanco:
    """Inventário de equipamentos. Cada chamada é uma transação (ou participa da externa)."""

    def __init__(self, banco: Banco) -> None:
        self._banco = banco
        self._sequencia = SequenciaNoBanco("equipamento", "Equipamento")

    def proximo_id(self) -> int:
        with self._banco.transacao() as sessao:
            return self._sequencia.proximo(sessao)

    def adicionar(self, equipamento: Equipamento) -> None:
        with self._banco.transacao() as sessao:
            self._sequencia.registrar(sessao, equipamento.id)
            sessao.add(
                EquipamentoModelo(
                    id=equipamento.id,
                    nome=equipamento.nome,
                    modelo=equipamento.modelo,
                    ativo=equipamento.ativo,
                )
            )

    def obter(self, id: int) -> Equipamento | None:
        with self._banco.transacao() as sessao:
            modelo = sessao.get(EquipamentoModelo, id, populate_existing=True)
            return None if modelo is None else _equipamento(modelo)

    def listar(self) -> tuple[Equipamento, ...]:
        with self._banco.transacao() as sessao:
            modelos = sessao.scalars(
                select(EquipamentoModelo)
                .order_by(EquipamentoModelo.id)
                .execution_options(populate_existing=True)
            ).all()
            return tuple(_equipamento(m) for m in modelos)

    def salvar(self, equipamento: Equipamento) -> None:
        with self._banco.transacao() as sessao:
            modelo = sessao.get(EquipamentoModelo, equipamento.id)
            if modelo is None:
                raise NaoEncontradoError("Equipamento", equipamento.id)
            modelo.nome = equipamento.nome
            modelo.modelo = equipamento.modelo
            modelo.ativo = equipamento.ativo

    def remover(self, id: int) -> None:
        with self._banco.transacao() as sessao:
            modelo = sessao.get(EquipamentoModelo, id)
            if modelo is None:
                raise NaoEncontradoError("Equipamento", id)
            sessao.delete(modelo)  # a sequência não recua: o id não será reutilizado
