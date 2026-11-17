"""Repositório de equipamentos em memória (implementa ``EquipamentoRepository``)."""

import copy

from manutencao.application.erros import NaoEncontradoError
from manutencao.domain.equipamento import Equipamento
from manutencao.infrastructure.memoria.sequencia import SequenciaMonotonica


class EquipamentosEmMemoria:
    """Guarda cópias; devolve cópias. Estado só da instância: sem arquivo, sem global."""

    def __init__(self) -> None:
        self._itens: dict[int, Equipamento] = {}
        self._sequencia = SequenciaMonotonica("Equipamento")

    def proximo_id(self) -> int:
        return self._sequencia.proximo()

    def adicionar(self, equipamento: Equipamento) -> None:
        self._sequencia.registrar(equipamento.id)
        self._itens[equipamento.id] = copy.copy(equipamento)

    def obter(self, id: int) -> Equipamento | None:
        achado = self._itens.get(id)
        return None if achado is None else copy.copy(achado)

    def listar(self) -> tuple[Equipamento, ...]:
        return tuple(copy.copy(self._itens[id]) for id in sorted(self._itens))

    def salvar(self, equipamento: Equipamento) -> None:
        if equipamento.id not in self._itens:
            raise NaoEncontradoError("Equipamento", equipamento.id)
        self._itens[equipamento.id] = copy.copy(equipamento)

    def remover(self, id: int) -> None:
        if id not in self._itens:
            raise NaoEncontradoError("Equipamento", id)
        del self._itens[id]  # a sequência não recua: o id não será reutilizado
