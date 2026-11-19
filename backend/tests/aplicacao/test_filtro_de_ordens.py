"""``FiltroDeOrdens``: a definição única dos filtros de listagem (os do legado, combináveis)."""

import pytest

from manutencao.application.portas.repositorios import FiltroDeOrdens
from manutencao.domain.enums import Criticidade, StatusOS
from manutencao.domain.ordem_servico import OrdemServico
from tests.dominio.fabrica import Mundo


def test_filtro_vazio_aceita_toda_os() -> None:
    mundo = Mundo()
    for os_ in (mundo.aberta(), mundo.concluida(), mundo.cancelada()):
        assert FiltroDeOrdens().aceita(os_)


@pytest.mark.parametrize(
    ("status", "esperado"),
    [(StatusOS.ABERTA, True), (StatusOS.ATRIBUIDA, False), (StatusOS.CONCLUIDA, False)],
)
def test_filtro_por_status(status: StatusOS, esperado: bool) -> None:
    assert FiltroDeOrdens(status=status).aceita(Mundo().aberta()) is esperado


def test_filtro_por_criticidade() -> None:
    os_ = Mundo().aberta()  # criticidade Alta
    assert FiltroDeOrdens(criticidade=Criticidade.ALTA).aceita(os_)
    assert not FiltroDeOrdens(criticidade=Criticidade.BAIXA).aceita(os_)


def test_filtro_por_equipamento_compara_por_id() -> None:
    os_ = Mundo().aberta()
    assert FiltroDeOrdens(equipamento_id=1).aceita(os_)
    assert not FiltroDeOrdens(equipamento_id=2).aceita(os_)


def test_filtro_por_tecnico_so_casa_com_o_atribuido() -> None:
    mundo = Mundo()
    aberta = mundo.aberta()
    atribuida = mundo.atribuida()  # Bruno (id 2)
    assert not FiltroDeOrdens(tecnico_id=2).aceita(aberta)  # sem técnico não casa com ninguém
    assert FiltroDeOrdens(tecnico_id=2).aceita(atribuida)
    assert not FiltroDeOrdens(tecnico_id=3).aceita(atribuida)


@pytest.mark.parametrize(
    ("construir", "encerrada"),
    [
        ("aberta", False),
        ("em_execucao", False),
        ("aguardando_aprovacao", False),
        ("concluida", True),
        ("cancelada", True),
    ],
)
def test_filtro_de_encerradas_e_em_aberto(construir: str, encerrada: bool) -> None:
    os_: OrdemServico = getattr(Mundo(), construir)()
    assert FiltroDeOrdens(encerrada=True).aceita(os_) is encerrada
    assert FiltroDeOrdens(encerrada=False).aceita(os_) is (not encerrada)


def test_criterios_informados_se_combinam_com_e() -> None:
    os_ = Mundo().atribuida()  # Atribuída, Alta, torno (1), Bruno (2)
    assert FiltroDeOrdens(status=StatusOS.ATRIBUIDA, tecnico_id=2, equipamento_id=1).aceita(os_)
    assert not FiltroDeOrdens(status=StatusOS.ATRIBUIDA, tecnico_id=3).aceita(os_)
    assert not FiltroDeOrdens(status=StatusOS.ABERTA, tecnico_id=2).aceita(os_)
