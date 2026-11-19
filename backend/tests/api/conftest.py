"""Fixtures da API: cada teste roda sobre repositórios em memória **e** sobre o PostgreSQL real."""

from collections.abc import Iterator

import pytest

from manutencao.composicao.aplicacao import criar_aplicacao_em_memoria, criar_aplicacao_postgres
from tests.apoio.api import HASHER_RAPIDO, Mundo, montar_mundo
from tests.apoio.relogio import RelogioFixo


@pytest.fixture(params=["memoria", "postgres"])
def mundo(request: pytest.FixtureRequest) -> Iterator[Mundo]:
    relogio = RelogioFixo()
    if request.param == "memoria":
        aplicacao = criar_aplicacao_em_memoria(relogio=relogio, hasher=HASHER_RAPIDO)
    else:
        banco = request.getfixturevalue("banco_limpo")
        aplicacao = criar_aplicacao_postgres(banco, relogio=relogio, hasher=HASHER_RAPIDO)
    mundo = montar_mundo(request.param, aplicacao, relogio)
    try:
        yield mundo
    finally:
        mundo.fechar()
