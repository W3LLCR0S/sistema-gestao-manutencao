"""Histórico sequencial das OS: ordem, tipos, autores, conteúdo, datas e persistência."""

import re

import pytest

from tests.caracterizacao.cenarios import (
    ANA,
    BRUNO,
    CARLA,
    COMPRESSOR,
    STATUS_REPARO_FINALIZADO,
    TORNO,
)
from tests.caracterizacao.fachada import Fachada, Peca, RelogioFixo
from tests.caracterizacao.fluxos import (
    aceitar,
    os_aberta,
    os_aguardando_aprovacao,
    os_atribuida,
    os_concluida,
    os_snap,
)

FORMATO_DATA = re.compile(r"^\d{2}/\d{2}/\d{4} \d{2}:\d{2}$")


@pytest.mark.cenario("CAR-23")
def test_historico_e_numerado_de_1_a_n_sem_lacunas(f: Fachada) -> None:
    numero = os_concluida(f)
    assert [s.numero for s in os_snap(f, numero).historico] == list(range(1, 12))


@pytest.mark.cenario("CAR-23")
def test_cada_os_tem_a_sua_propria_numeracao_de_historico(f: Fachada) -> None:
    primeira = os_atribuida(f)
    segunda = os_aberta(f)
    assert [s.numero for s in os_snap(f, primeira).historico] == [1, 2, 3]
    assert [s.numero for s in os_snap(f, segunda).historico] == [1]


@pytest.mark.cenario("CAR-24")
def test_ordem_segue_a_ordem_das_operacoes_e_nao_a_data(f: Fachada, relogio: RelogioFixo) -> None:
    """A ordem do histórico é a de inclusão; a data (minuto) só informa o instante."""
    numero = os_aberta(f)
    aceitar(f.atribuir(numero, BRUNO, ANA))  # mesmo minuto da abertura
    relogio.avancar(minutes=30)
    aceitar(f.registrar_diagnostico(numero, BRUNO, "p", "c"))
    historico = os_snap(f, numero).historico
    assert [s.tipo for s in historico] == [
        "Abertura",
        "Atribuição",
        "Mudança de status",
        "Diagnóstico",
    ]
    assert [s.data for s in historico] == [
        "10/03/2026 09:00",
        "10/03/2026 09:00",
        "10/03/2026 09:00",
        "10/03/2026 09:30",
    ]


@pytest.mark.cenario("CAR-24")
def test_datas_do_historico_nunca_regridem_com_relogio_crescente(
    f: Fachada, relogio: RelogioFixo
) -> None:
    numero = os_aberta(f)
    for passo in range(5):
        relogio.avancar(minutes=7)
        aceitar(f.adicionar_observacao(numero, CARLA, f"nota {passo}"))
    datas = [s.data for s in os_snap(f, numero).historico]
    assert all(FORMATO_DATA.match(d) for d in datas)
    ordenadas = sorted(datas, key=lambda d: (d[6:10], d[3:5], d[0:2], d[11:]))
    assert datas == ordenadas


@pytest.mark.cenario("CAR-25")
def test_cada_tipo_de_registro_tem_autor_e_conteudo_proprios(f: Fachada) -> None:
    numero = os_atribuida(f)
    aceitar(f.registrar_diagnostico(numero, BRUNO, "Parecer", "Causa"))
    aceitar(f.apontar_reparo(numero, BRUNO, 2.5, "Troca", (Peca("Correia", 1), Peca("Graxa", 0.5))))
    aceitar(f.adicionar_observacao(numero, CARLA, "Cliente aguardando"))
    aceitar(f.alterar_status(numero, BRUNO, STATUS_REPARO_FINALIZADO))
    aceitar(f.concluir_tecnicamente(numero, BRUNO, "Teste A", False))

    por_tipo = {s.tipo: s for s in os_snap(f, numero).historico}
    assert por_tipo["Diagnóstico"].descricao == "Parecer | Causa-raiz: Causa"
    assert por_tipo["Diagnóstico"].responsavel_id == BRUNO
    reparo = por_tipo["Reparo"]
    assert (reparo.descricao, reparo.horas, reparo.responsavel_id) == ("Troca", 2.5, BRUNO)
    assert [(p.descricao, p.quantidade) for p in reparo.pecas] == [("Correia", 1.0), ("Graxa", 0.5)]
    assert (por_tipo["Apontamento"].descricao, por_tipo["Apontamento"].responsavel_id) == (
        "Cliente aguardando",
        CARLA,
    )
    assert por_tipo["Teste funcional"].descricao == "Reprovado: Teste A"
    assert por_tipo["Teste funcional"].responsavel_id == BRUNO


@pytest.mark.cenario("CAR-25")
def test_registros_que_nao_sao_de_reparo_nao_trazem_horas_nem_pecas(f: Fachada) -> None:
    numero = os_concluida(f)
    for s in os_snap(f, numero).historico:
        if s.tipo != "Reparo":
            assert (s.horas, s.pecas) == (0.0, ()), s.tipo


@pytest.mark.cenario("CAR-26")
def test_reprovacao_e_reatribuicao_acrescentam_registros_sem_apagar_os_anteriores(
    f: Fachada,
) -> None:
    numero = os_aguardando_aprovacao(f)
    antes = os_snap(f, numero).historico
    aceitar(f.reprovar(numero, ANA, "refazer"))
    aceitar(f.atribuir(numero, CARLA, ANA))
    depois = os_snap(f, numero).historico

    assert depois[: len(antes)] == antes
    assert [s.tipo for s in depois[len(antes) :]] == [
        "Reprovação",
        "Mudança de status",
        "Reatribuição",
    ]
    assert depois[-1].descricao == "Bruno Lima → Carla Mendes"
    assert [s.numero for s in depois] == list(range(1, len(depois) + 1))


@pytest.mark.cenario("CAR-27")
def test_data_de_abertura_e_de_cada_registro_vem_do_relogio(
    f: Fachada, relogio: RelogioFixo
) -> None:
    numero = os_aberta(f)
    relogio.avancar(days=2)
    aceitar(f.cancelar(numero, ANA, "x"))
    os_ = os_snap(f, numero)
    assert os_.data_abertura == "10/03/2026 09:00"
    assert os_.data_conclusao == "12/03/2026 09:00"
    assert [s.data for s in os_.historico] == [
        "10/03/2026 09:00",
        "12/03/2026 09:00",
        "12/03/2026 09:00",
    ]


@pytest.mark.cenario("CAR-27")
def test_data_de_conclusao_so_existe_ao_aprovar_ou_cancelar(f: Fachada) -> None:
    numero = os_aguardando_aprovacao(f)
    assert os_snap(f, numero).data_conclusao is None
    aceitar(f.reprovar(numero, ANA, "refazer"))
    assert os_snap(f, numero).data_conclusao is None


@pytest.mark.cenario("CAR-90")
def test_datas_sao_texto_dd_mm_aaaa_hh_mm_sem_fuso(f: Fachada) -> None:
    """AUD-07/D-11: o legado grava texto sem fuso e sem segundos (será substituído por UTC)."""
    numero = os_concluida(f)
    os_ = os_snap(f, numero)
    assert FORMATO_DATA.match(os_.data_abertura)
    assert os_.data_conclusao is not None
    assert FORMATO_DATA.match(os_.data_conclusao)
    assert all(isinstance(s.data, str) and FORMATO_DATA.match(s.data) for s in os_.historico)


@pytest.mark.cenario("CAR-28")
def test_historico_do_equipamento_agrega_as_os_vinculadas(f: Fachada) -> None:
    a = os_aberta(f, equipamento=TORNO)
    b = os_aberta(f, equipamento=COMPRESSOR)
    c = os_aberta(f, equipamento=TORNO)
    assert f.ordens_do_equipamento(TORNO) == (a, c)
    assert f.ordens_do_equipamento(COMPRESSOR) == (b,)


@pytest.mark.cenario("CAR-28")
def test_historico_completo_sobrevive_a_gravacao_e_recarga(
    f: Fachada, relogio: RelogioFixo
) -> None:
    numero = os_aguardando_aprovacao(f)
    relogio.avancar(hours=5)
    aceitar(f.reprovar(numero, ANA, "refazer"))
    outro = os_atribuida(f)
    antes = (f.todas_as_os(), f.usuarios(), f.equipamentos(), f.cargos())
    f.salvar_e_recarregar()
    assert (f.todas_as_os(), f.usuarios(), f.equipamentos(), f.cargos()) == antes
    assert os_snap(f, outro).tecnico_id == BRUNO
