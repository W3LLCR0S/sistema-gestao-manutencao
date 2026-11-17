"""Máquina de estados da OS: a tabela de transições permitidas.

A tabela é a **fonte única** das mudanças de status. Foi extraída de ``OrdemServico`` do legado
(``models/ordem_servico.py``), onde as transições estavam espalhadas pelos métodos, e confirmada
pela tabela completa 8x8 do técnico (CAR-33) e pelos cenários de atribuição, aprovação,
reprovação e cancelamento. Ela diz **quais** mudanças existem; as pré-condições de cada operação
(permissão, responsável, intervenção registrada, etc.) continuam em ``OrdemServico``.

Nada aqui corrige comportamento do legado: por exemplo, a finalização do reparo continua sem exigir
diagnóstico (D-06 é uma mudança da Operação E).
"""

from collections.abc import Mapping
from types import MappingProxyType

from manutencao.domain.enums import StatusOS

# Status que o técnico pode definir manualmente.
STATUS_TECNICO: tuple[StatusOS, ...] = (
    StatusOS.EM_EXECUCAO,
    StatusOS.AGUARDANDO_PECA,
    StatusOS.REPARO_FINALIZADO,
)

# Status em que a OS está encerrada: nenhuma mudança é possível.
STATUS_FINAIS: tuple[StatusOS, ...] = (StatusOS.CONCLUIDA, StatusOS.CANCELADA)

# Status em que o técnico responsável pode diagnosticar e apontar reparo.
STATUS_ATENDIMENTO: tuple[StatusOS, ...] = (
    StatusOS.ATRIBUIDA,
    StatusOS.EM_EXECUCAO,
    StatusOS.AGUARDANDO_PECA,
)

# Status de origem em que o técnico pode mudar o status manualmente.
STATUS_ORIGEM_TECNICO: tuple[StatusOS, ...] = (StatusOS.ATRIBUIDA, *STATUS_TECNICO)

_TABELA: dict[StatusOS, frozenset[StatusOS]] = {
    # atribuir (gestor); cancelar (gestor)
    StatusOS.ABERTA: frozenset({StatusOS.ATRIBUIDA, StatusOS.CANCELADA}),
    # apontar reparo ou alterar status (técnico); cancelar. Atribuída -> Reparo Finalizado só é
    # aceita pelo legado com intervenção registrada, o que o fluxo normal não produz em Atribuída.
    StatusOS.ATRIBUIDA: frozenset(
        {
            StatusOS.EM_EXECUCAO,
            StatusOS.AGUARDANDO_PECA,
            StatusOS.REPARO_FINALIZADO,
            StatusOS.CANCELADA,
        }
    ),
    StatusOS.EM_EXECUCAO: frozenset(
        {StatusOS.AGUARDANDO_PECA, StatusOS.REPARO_FINALIZADO, StatusOS.CANCELADA}
    ),
    StatusOS.AGUARDANDO_PECA: frozenset(
        {StatusOS.EM_EXECUCAO, StatusOS.REPARO_FINALIZADO, StatusOS.CANCELADA}
    ),
    # o técnico pode reabrir o reparo; a conclusão técnica submete à aprovação
    StatusOS.REPARO_FINALIZADO: frozenset(
        {
            StatusOS.EM_EXECUCAO,
            StatusOS.AGUARDANDO_PECA,
            StatusOS.AGUARDANDO_APROVACAO,
            StatusOS.CANCELADA,
        }
    ),
    # aprovar (-> Concluída), reprovar (-> Em Execução) ou cancelar
    StatusOS.AGUARDANDO_APROVACAO: frozenset(
        {StatusOS.CONCLUIDA, StatusOS.EM_EXECUCAO, StatusOS.CANCELADA}
    ),
    StatusOS.CONCLUIDA: frozenset(),
    StatusOS.CANCELADA: frozenset(),
}

TRANSICOES: Mapping[StatusOS, frozenset[StatusOS]] = MappingProxyType(_TABELA)


def transicao_permitida(origem: StatusOS, destino: StatusOS) -> bool:
    """Indica se existe a transição ``origem -> destino``."""
    return destino in TRANSICOES[origem]


def encerrada(status: StatusOS) -> bool:
    return status in STATUS_FINAIS
