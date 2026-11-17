"""Repositório de ordens de serviço em memória (implementa ``OrdemServicoRepository``)."""

import copy

from manutencao.application.erros import NaoEncontradoError
from manutencao.application.portas.repositorios import FiltroDeOrdens
from manutencao.domain.ordem_servico import OrdemServico
from manutencao.infrastructure.memoria.sequencia import SequenciaMonotonica


class OrdensEmMemoria:
    """Guarda e devolve cópias profundas do agregado (a OS, seu histórico e as referências).

    A entidade ``OrdemServico`` não expõe como restaurar o próprio estado, então a cópia é a do
    objeto inteiro (``copy.deepcopy``): a OS carrega cópias dos usuários e do equipamento como
    estavam quando foi salva. Essa é a política documentada na porta; o que vale é o identificador.
    """

    def __init__(self) -> None:
        self._itens: dict[int, OrdemServico] = {}
        self._sequencia = SequenciaMonotonica("Ordem de serviço")

    def proximo_numero(self) -> int:
        return self._sequencia.proximo()

    def adicionar(self, ordem: OrdemServico) -> None:
        self._sequencia.registrar(ordem.numero)
        self._itens[ordem.numero] = copy.deepcopy(ordem)

    def obter(self, numero: int) -> OrdemServico | None:
        achada = self._itens.get(numero)
        return None if achada is None else copy.deepcopy(achada)

    def _filtradas(self, filtro: FiltroDeOrdens | None) -> list[OrdemServico]:
        todas = (self._itens[numero] for numero in sorted(self._itens))
        return [o for o in todas if filtro is None or filtro.aceita(o)]

    def listar(self, filtro: FiltroDeOrdens | None = None) -> tuple[OrdemServico, ...]:
        return tuple(copy.deepcopy(o) for o in self._filtradas(filtro))

    def contar(self, filtro: FiltroDeOrdens | None = None) -> int:
        return len(self._filtradas(filtro))

    def salvar(self, ordem: OrdemServico) -> None:
        if ordem.numero not in self._itens:
            raise NaoEncontradoError("Ordem de serviço", ordem.numero)
        self._itens[ordem.numero] = copy.deepcopy(ordem)

    def usuario_tem_participacao(self, usuario_id: int) -> bool:
        for ordem in self._itens.values():
            tecnico = ordem.tecnico_atribuido
            if tecnico is not None and tecnico.id == usuario_id:
                return True
            if ordem.aberta_por.id == usuario_id:
                return True
            if any(
                s.responsavel is not None and s.responsavel.id == usuario_id for s in ordem.servicos
            ):
                return True
        return False
