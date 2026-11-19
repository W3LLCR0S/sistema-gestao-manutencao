"""Relógio de sistema: implementa a porta ``Relogio`` com a hora real em UTC."""

from datetime import UTC, datetime


class RelogioDeSistema:
    """O instante atual do sistema operacional, com fuso UTC (D-11)."""

    def agora(self) -> datetime:
        return datetime.now(UTC)
