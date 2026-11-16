"""Fixtures da caracterização: legado isolado em diretório temporário, relógio fixo, integridade."""

from collections.abc import Iterator
from pathlib import Path

import pytest

from tests.caracterizacao.adaptador_legado import AdaptadorLegado
from tests.caracterizacao.fachada import Fachada, RelogioFixo
from tests.caracterizacao.integridade import impressao_digital_do_legado, pycs_do_legado
from tests.guardas_ambiente import DIRETORIO_DADOS, caminho_em_dados


@pytest.fixture(scope="session", autouse=True)
def _legado_inalterado() -> Iterator[None]:
    """Falha a sessão se qualquer arquivo do legado mudar ou se surgir bytecode novo nele."""
    antes = impressao_digital_do_legado()
    pycs_antes = pycs_do_legado()
    yield
    assert impressao_digital_do_legado() == antes, "Arquivos do legado foram alterados."
    assert pycs_do_legado() == pycs_antes, "Os testes gravaram bytecode dentro do legado."


@pytest.fixture
def relogio() -> RelogioFixo:
    return RelogioFixo()


@pytest.fixture
def caminho_base(tmp_path: Path) -> Path:
    """Caminho (inexistente) do JSON isolado do teste. Nunca aponta para o ``dados/`` real."""
    caminho = tmp_path / "base_isolada.json"
    assert not caminho_em_dados(caminho)
    assert DIRETORIO_DADOS not in caminho.parents
    return caminho


@pytest.fixture
def adaptador(caminho_base: Path, relogio: RelogioFixo) -> Iterator[AdaptadorLegado]:
    """O adaptador concreto (para testes que precisam do arquivo JSON temporário)."""
    adaptador = AdaptadorLegado(caminho_base, relogio)
    try:
        yield adaptador
    finally:
        adaptador.fechar()


@pytest.fixture
def f(adaptador: AdaptadorLegado) -> Fachada:
    """A fachada comportamental sobre o legado, com a base inicial de exemplo."""
    return adaptador
