"""Fixtures da caracterização: legado isolado em diretório temporário, relógio fixo, integridade."""

from collections.abc import Iterator
from pathlib import Path
from typing import NoReturn

import pytest

from tests.caracterizacao.adaptador_dominio import AdaptadorDominio
from tests.caracterizacao.adaptador_legado import AdaptadorLegado
from tests.caracterizacao.aplicabilidade import (
    SUBSTITUIDOS_POR_DELTA,
    Responsabilidade,
    decidir,
)
from tests.caracterizacao.fachada import Fachada, RelogioFixo
from tests.caracterizacao.integridade import impressao_digital_do_legado, pycs_do_legado
from tests.caracterizacao.numeracao import nova_numeracao
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


def cenarios_do_teste(item: pytest.Item) -> tuple[str, ...]:
    """Os ``CAR-nn`` do marcador ``cenario`` de um teste (um por teste, por regra do registro)."""
    return tuple(str(marcador.args[0]) for marcador in item.iter_markers("cenario"))


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    """Cada teste de regra roda contra o legado e, quando se aplica, contra o domínio puro.

    O adaptador do legado é sempre usado e continua com as mesmas expectativas. O do domínio só é
    acrescentado a testes que tenham exatamente um cenário e que o registro não tenha substituído
    por um delta implementado (``aplicabilidade.SUBSTITUIDOS_POR_DELTA``). Os testes de
    infraestrutura (sem cenário) são do legado e não ganham a variante do domínio.
    """
    if "f" not in metafunc.fixturenames:
        return
    cenarios = cenarios_do_teste(metafunc.definition)
    variantes = ["legado"]
    if len(cenarios) == 1 and cenarios[0] not in SUBSTITUIDOS_POR_DELTA:
        variantes.append("dominio")
    metafunc.parametrize("f", variantes, indirect=True)


@pytest.fixture
def f(request: pytest.FixtureRequest, relogio: RelogioFixo) -> Fachada:
    """A fachada comportamental: sobre o legado (base inicial de exemplo) ou sobre o domínio."""
    if request.param == "legado":
        legado: Fachada = request.getfixturevalue("adaptador")
        return legado
    cenarios = cenarios_do_teste(request.node)

    def diante_da_ausencia(responsabilidade: Responsabilidade) -> NoReturn:
        """Pula só se o registro justifica; senão o teste falha (nada de skip por conveniência)."""
        linha = decidir(cenarios, responsabilidade)
        if linha is None:
            pytest.fail(
                f"{cenarios} exige a responsabilidade '{responsabilidade.value}', ausente do "
                "domínio puro, mas o par não está em aplicabilidade.REGISTRO."
            )
        pytest.skip(linha.motivo)

    return AdaptadorDominio(relogio, diante_da_ausencia, numeracao=nova_numeracao())
