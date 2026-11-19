"""Contrato da porta ``Relogio``: toda implementação devolve instantes com fuso, em UTC."""

from collections.abc import Callable
from datetime import UTC, datetime, timedelta, timezone

import pytest

from manutencao.application.portas.relogio import Relogio
from manutencao.infrastructure.relogio import RelogioDeSistema
from tests.apoio.relogio import INICIO, RelogioFixo

FABRICAS: dict[str, Callable[[], Relogio]] = {"sistema": RelogioDeSistema, "fixo": RelogioFixo}


@pytest.fixture(params=sorted(FABRICAS))
def relogio(request: pytest.FixtureRequest) -> Relogio:
    construido: Relogio = FABRICAS[request.param]()
    return construido


def test_satisfaz_a_porta(relogio: Relogio) -> None:
    assert isinstance(relogio, Relogio)


def test_agora_devolve_datetime_com_fuso_em_utc(relogio: Relogio) -> None:
    instante = relogio.agora()
    assert isinstance(instante, datetime)
    assert instante.tzinfo is not None
    assert instante.utcoffset() == timedelta(0)


def test_relogio_de_sistema_acompanha_a_hora_real() -> None:
    antes = datetime.now(UTC)
    instante = RelogioDeSistema().agora()
    depois = datetime.now(UTC)
    assert antes <= instante <= depois


def test_relogio_fixo_nao_anda_sozinho() -> None:
    relogio = RelogioFixo()
    assert relogio.agora() == relogio.agora() == INICIO


def test_relogio_fixo_avanca_e_define_so_por_ordem_do_teste() -> None:
    relogio = RelogioFixo()
    relogio.avancar(minutes=90)
    assert relogio.agora() == INICIO + timedelta(minutes=90)
    relogio.definir(datetime(2027, 1, 1, tzinfo=UTC))
    assert relogio.agora() == datetime(2027, 1, 1, tzinfo=UTC)


def test_relogio_fixo_normaliza_para_utc() -> None:
    relogio = RelogioFixo(datetime(2026, 3, 10, 6, 0, tzinfo=timezone(timedelta(hours=-3))))
    assert relogio.agora() == INICIO
    assert relogio.agora().utcoffset() == timedelta(0)


def test_relogio_fixo_recusa_instante_ingenuo() -> None:
    with pytest.raises(ValueError, match="fuso"):
        RelogioFixo(datetime(2026, 3, 10, 9, 0))
    relogio = RelogioFixo()
    with pytest.raises(ValueError, match="fuso"):
        relogio.definir(datetime(2026, 3, 10, 9, 0))
    assert relogio.agora() == INICIO
