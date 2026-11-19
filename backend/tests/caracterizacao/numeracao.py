"""A numeração injetada nos adaptadores que não têm repositório (a política é a do repositório)."""

from manutencao.infrastructure.memoria.sequencia import SequenciaMonotonica


def nova_numeracao() -> SequenciaMonotonica:
    """Uma sequência nova de números de OS: crescente, sem reutilização (DLT-10)."""
    return SequenciaMonotonica("Ordem de serviço")
