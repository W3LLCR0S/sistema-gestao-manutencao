"""Instantes do domínio (D-11, ADR-0007; DLT-07).

O domínio **nunca consulta o relógio**: quem chama a operação fornece o instante (``quando``). Todo
instante precisa ter fuso (um ``datetime`` ingênuo é rejeitado, pois não identifica um momento) e é
normalizado para UTC antes de ser guardado. A conversão para ``America/Sao_Paulo`` e a formatação
são de apresentação e pertencem à Fase 04; nada disso existe aqui.
"""

from datetime import UTC, datetime

from manutencao.domain.erros import CodigoErro, ViolacaoDeRegraError


def garantir_utc(instante: object) -> datetime:
    """Devolve ``instante`` convertido para UTC; recusa o que não for ``datetime`` com fuso.

    A conversão preserva o momento (``2026-03-10 06:00-03:00`` vira ``2026-03-10 09:00+00:00``).
    É idempotente: um instante já em UTC volta igual.
    """
    if not isinstance(instante, datetime):
        raise ViolacaoDeRegraError(
            CodigoErro.INSTANTE_INVALIDO,
            f"O instante deve ser um datetime com fuso horário, não {type(instante).__name__}.",
        )
    if instante.tzinfo is None or instante.utcoffset() is None:
        raise ViolacaoDeRegraError(
            CodigoErro.INSTANTE_INVALIDO,
            "O instante deve ter fuso horário (datetime ingênuo não é aceito).",
        )
    return instante.astimezone(UTC)
