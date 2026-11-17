"""Fixtures da caracterização: legado isolado em diretório temporário, relógio fixo, integridade."""

from collections.abc import Iterator
from pathlib import Path
from typing import NoReturn

import pytest

from tests.caracterizacao.adaptador_dominio import AdaptadorDominio
from tests.caracterizacao.adaptador_legado import AdaptadorLegado
from tests.caracterizacao.adaptador_servicos import AdaptadorServicos
from tests.caracterizacao.aplicabilidade import (
    NAO_REPRODUZIDOS_PELOS_SERVICOS,
    SUBSTITUIDOS_POR_DELTA,
    Inaplicavel,
    Responsabilidade,
    decidir,
    decidir_servicos,
)
from tests.caracterizacao.fachada import Fachada, RelogioFixo
from tests.caracterizacao.integridade import impressao_digital_do_legado, pycs_do_legado
from tests.caracterizacao.numeracao import nova_numeracao
from tests.caracterizacao.pares import Par
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
def legado(adaptador: AdaptadorLegado) -> AdaptadorLegado:
    """O legado, sem variantes: para o comportamento antigo que um delta aprovado substituiu."""
    return adaptador


def cenarios_do_teste(item: pytest.Item) -> tuple[str, ...]:
    """Os ``CAR-nn`` do marcador ``cenario`` de um teste (um por teste, por regra do registro)."""
    return tuple(str(marcador.args[0]) for marcador in item.iter_markers("cenario"))


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    """Cada teste de regra roda contra o legado e, quando se aplica, contra o domínio e os serviços.

    O adaptador do legado é sempre usado e continua com as mesmas expectativas. O do domínio só é
    acrescentado a testes que tenham exatamente um cenário e que o registro não tenha substituído
    por um delta implementado (``aplicabilidade.SUBSTITUIDOS_POR_DELTA``). O dos serviços, a testes
    de um cenário que os serviços não respondam de outro modo por decisão registrada
    (``aplicabilidade.NAO_REPRODUZIDOS_PELOS_SERVICOS``). Os testes de infraestrutura (sem
    cenário) são do legado e não ganham variante.
    """
    if "f" not in metafunc.fixturenames:
        return
    cenarios = cenarios_do_teste(metafunc.definition)
    variantes = ["legado"]
    if len(cenarios) == 1 and cenarios[0] not in SUBSTITUIDOS_POR_DELTA:
        variantes.append("dominio")
    if len(cenarios) == 1 and cenarios[0] not in NAO_REPRODUZIDOS_PELOS_SERVICOS:
        variantes.append("servicos")
    metafunc.parametrize("f", variantes, indirect=True)


def _pular_se_registrado(
    linha: Inaplicavel | None,
    cenarios: tuple[str, ...],
    responsabilidade: Responsabilidade,
    ausente_de: str,
    registro: str,
) -> NoReturn:
    """O único ``skip`` da caracterização: só pula o que o registro justifica; senão falha."""
    if linha is None:
        pytest.fail(
            f"{cenarios} exige a responsabilidade '{responsabilidade.value}', ausente "
            f"{ausente_de}, "
            f"mas o par não está em aplicabilidade.{registro}."
        )
    pytest.skip(linha.motivo)


@pytest.fixture
def f(request: pytest.FixtureRequest, relogio: RelogioFixo) -> Fachada:
    """A fachada comportamental: sobre o legado, o domínio puro ou os serviços (base de exemplo)."""
    if request.param == "legado":
        legado: Fachada = request.getfixturevalue("adaptador")
        return legado
    cenarios = cenarios_do_teste(request.node)

    if request.param == "servicos":

        def diante_da_ausencia_nos_servicos(responsabilidade: Responsabilidade) -> NoReturn:
            _pular_se_registrado(
                decidir_servicos(cenarios, responsabilidade),
                cenarios,
                responsabilidade,
                "dos serviços",
                "REGISTRO_SERVICOS",
            )

        return AdaptadorServicos(relogio, diante_da_ausencia_nos_servicos)

    def diante_da_ausencia(responsabilidade: Responsabilidade) -> NoReturn:
        _pular_se_registrado(
            decidir(cenarios, responsabilidade),
            cenarios,
            responsabilidade,
            "do domínio puro",
            "REGISTRO",
        )

    return AdaptadorDominio(relogio, diante_da_ausencia, numeracao=nova_numeracao())


@pytest.fixture
def par(caminho_base: Path, relogio: RelogioFixo) -> Iterator[Par]:
    """O legado e os serviços lado a lado, com o mesmo relógio fixo e bases independentes."""
    legado = AdaptadorLegado(caminho_base, relogio)
    try:
        yield Par(legado, AdaptadorServicos(relogio), relogio)
    finally:
        legado.fechar()
