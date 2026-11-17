"""Relógio fixo para testes: implementa a porta ``Relogio`` sem consultar o relógio do sistema."""

from datetime import UTC, datetime, timedelta

INICIO = datetime(2026, 3, 10, 9, 0, tzinfo=UTC)


class RelogioFixo:
    """Devolve sempre o mesmo instante (com fuso, UTC) até o teste movê-lo."""

    def __init__(self, inicio: datetime = INICIO) -> None:
        self._agora = self._exigir_fuso(inicio)

    @staticmethod
    def _exigir_fuso(instante: datetime) -> datetime:
        if instante.tzinfo is None or instante.utcoffset() is None:
            raise ValueError("O relógio fixo exige um instante com fuso horário.")
        return instante.astimezone(UTC)

    def agora(self) -> datetime:
        return self._agora

    def definir(self, instante: datetime) -> None:
        self._agora = self._exigir_fuso(instante)

    def avancar(self, **intervalo: float) -> None:
        """Avança o relógio (``avancar(minutes=5)``); só o teste move o tempo."""
        self._agora += timedelta(**intervalo)
