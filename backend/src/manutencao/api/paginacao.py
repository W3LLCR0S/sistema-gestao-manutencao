"""Paginação por limite e deslocamento (limites seguros: ``limite`` entre 1 e 200)."""

from collections.abc import Callable, Sequence
from typing import Annotated, TypeVar

from fastapi import Query

from manutencao.api.esquemas import Pagina

LIMITE_MAXIMO = 200

Limite = Annotated[int, Query(ge=1, le=LIMITE_MAXIMO, description="Itens por página")]
Deslocamento = Annotated[int, Query(ge=0, description="Itens a pular")]

T = TypeVar("T")
S = TypeVar("S")


def paginar(
    itens: Sequence[T], converter: Callable[[T], S], limite: int, deslocamento: int
) -> Pagina[S]:
    """Uma página de ``itens`` convertidos; ``total`` conta todos (antes do corte)."""
    pagina = itens[deslocamento : deslocamento + limite]
    return Pagina[S](
        itens=[converter(i) for i in pagina],
        total=len(itens),
        limite=limite,
        deslocamento=deslocamento,
    )
