"""Sequência de identificadores monotônica (DLT-10, AUD-05, ADR-0004).

A política de numeração é **do repositório**: nem o domínio nem a camada de aplicação a conhecem.
Cada repositório tem a sua sequência, independente das outras. Uma sequência só avança: o maior
identificador já emitido fica registrado mesmo que o objeto seja excluído, de modo que nenhum
identificador é reutilizado. Ao contrário do ``max(ids) + 1`` do legado, que devolvia o número de um
objeto excluído quando ele era o maior.
"""

from manutencao.application.erros import IdentificadorJaEmitidoError


class SequenciaMonotonica:
    """Identificadores crescentes, a partir de 1, sem reutilização e sem colisão."""

    def __init__(self, entidade: str) -> None:
        self._entidade = entidade
        self._ultimo = 0

    def proximo(self) -> int:
        """O identificador que o próximo ``registrar`` aceitaria por padrão (não consome)."""
        return self._ultimo + 1

    def registrar(self, identificador: int) -> None:
        """Consome ``identificador``, que precisa ser maior que todos os já emitidos.

        Aceita saltos (um identificador maior que o próximo, como numa importação futura), mas
        nunca um já emitido: nem o de um objeto existente (colisão) nem o de um excluído.
        """
        if identificador < 1:
            raise ValueError(f"O identificador de {self._entidade} deve ser positivo.")
        if identificador <= self._ultimo:
            raise IdentificadorJaEmitidoError(self._entidade, identificador)
        self._ultimo = identificador
