"""Porta ``Relogio``: a fonte de instantes da aplicação (D-11, ADR-0007).

O caso de uso lê o relógio **uma vez** e entrega o instante às operações do domínio como argumento
(``quando=``); o domínio nunca consulta o relógio nem conhece esta porta. A conversão para
``America/Sao_Paulo`` e a formatação são de apresentação (Fase 04) e não existem aqui.
"""

from datetime import datetime
from typing import Protocol, runtime_checkable


@runtime_checkable
class Relogio(Protocol):
    """Fornece o instante atual."""

    def agora(self) -> datetime:
        """O instante atual como ``datetime`` **com fuso, em UTC** (nunca ingênuo)."""
        ...
