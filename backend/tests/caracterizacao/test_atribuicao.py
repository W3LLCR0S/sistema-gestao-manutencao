"""Atribuição e reatribuição de OS a técnicos (Entrega 1)."""

from collections.abc import Callable

import pytest

from tests.caracterizacao.cenarios import (
    ANA,
    AUSENTE,
    BRUNO,
    CARGO_GESTOR,
    CARGO_TECNICO,
    CARLA,
    PERMISSOES_PADRAO_TECNICO,
    STATUS_ABERTA,
    STATUS_AGUARDANDO_APROVACAO,
    STATUS_AGUARDANDO_PECA,
    STATUS_ATRIBUIDA,
    STATUS_CANCELADA,
    STATUS_CONCLUIDA,
    STATUS_EM_EXECUCAO,
    STATUS_REPARO_FINALIZADO,
)
from tests.caracterizacao.fachada import Fachada, Recusa
from tests.caracterizacao.fluxos import (
    aceitar,
    estado_global,
    os_aberta,
    os_aguardando_aprovacao,
    os_aguardando_peca,
    os_atribuida,
    os_cancelada,
    os_concluida,
    os_em_execucao,
    os_reparo_finalizado,
    os_snap,
    recusada,
)


@pytest.mark.cenario("CAR-10")
def test_atribuicao_inicial_leva_a_os_para_atribuida(f: Fachada) -> None:
    numero = os_aberta(f)
    resultado = aceitar(f.atribuir(numero, BRUNO, ANA))
    assert resultado.valor is None  # não havia técnico anterior

    os_ = os_snap(f, numero)
    assert (os_.status, os_.tecnico_id) == (STATUS_ATRIBUIDA, BRUNO)
    assert [(s.tipo, s.descricao, s.responsavel_id) for s in os_.historico[1:]] == [
        ("Atribuição", "Atribuída a Bruno Lima", ANA),
        ("Mudança de status", "Aberta → Atribuída", ANA),
    ]


@pytest.mark.cenario("CAR-11")
def test_reatribuicao_troca_o_tecnico_e_devolve_o_anterior(f: Fachada) -> None:
    numero = os_atribuida(f, tecnico=BRUNO)
    resultado = aceitar(f.atribuir(numero, CARLA, ANA))
    assert resultado.valor == BRUNO  # técnico anterior

    os_ = os_snap(f, numero)
    assert (os_.status, os_.tecnico_id) == (STATUS_ATRIBUIDA, CARLA)
    ultimo = os_.historico[-1]
    assert (ultimo.tipo, ultimo.descricao, ultimo.responsavel_id) == (
        "Reatribuição",
        "Bruno Lima → Carla Mendes",
        ANA,
    )
    # reatribuir não gera nova mudança de status
    assert os_.tipos_do_historico == ("Abertura", "Atribuição", "Mudança de status", "Reatribuição")


@pytest.mark.cenario("CAR-11")
def test_reatribuicao_em_execucao_preserva_status_e_apontamentos(f: Fachada) -> None:
    numero = os_em_execucao(f, tecnico=BRUNO)
    antes = os_snap(f, numero)
    aceitar(f.atribuir(numero, CARLA, ANA))
    depois = os_snap(f, numero)
    assert depois.status == STATUS_EM_EXECUCAO
    assert depois.tecnico_id == CARLA
    assert (depois.horas_trabalhadas, depois.intervencoes, depois.pecas) == (
        antes.horas_trabalhadas,
        antes.intervencoes,
        antes.pecas,
    )
    assert depois.historico[: len(antes.historico)] == antes.historico  # histórico só cresce


@pytest.mark.cenario("CAR-11")
def test_reatribuicao_atualiza_a_carga_dos_dois_tecnicos(f: Fachada) -> None:
    numero = os_atribuida(f, tecnico=BRUNO)
    carga = {u.id: u.carga for u in f.usuarios()}
    assert (carga[BRUNO], carga[CARLA]) == (1, 0)
    aceitar(f.atribuir(numero, CARLA, ANA))
    carga = {u.id: u.carga for u in f.usuarios()}
    assert (carga[BRUNO], carga[CARLA]) == (0, 1)


@pytest.mark.cenario("CAR-12")
def test_atribuir_ao_mesmo_tecnico_e_recusado_sem_alterar_a_os(f: Fachada) -> None:
    numero = os_atribuida(f, tecnico=BRUNO)
    antes = estado_global(f)
    recusada(f.atribuir(numero, BRUNO, ANA), Recusa.JA_ATRIBUIDA)
    assert estado_global(f) == antes


@pytest.mark.cenario("CAR-13")
def test_atribuir_a_quem_nao_e_tecnico_e_recusado(f: Fachada) -> None:
    numero = os_aberta(f)
    antes = estado_global(f)
    resultado = recusada(f.atribuir(numero, ANA, ANA), Recusa.NAO_E_TECNICO)
    assert resultado.mensagem == "Ana Souza não é técnico."
    assert estado_global(f) == antes


@pytest.mark.cenario("CAR-14")
def test_atribuir_sem_permissao_atribuir_os_e_recusado(f: Fachada) -> None:
    numero = os_aberta(f)
    antes = estado_global(f)
    resultado = recusada(f.atribuir(numero, CARLA, BRUNO), Recusa.SEM_PERMISSAO)
    assert "Atribuir/reatribuir OS a técnicos" in resultado.mensagem
    assert estado_global(f) == antes


@pytest.mark.cenario("CAR-14")
def test_permissao_atribuir_os_habilita_qualquer_cargo_que_a_receba(f: Fachada) -> None:
    """Quem decide é a permissão, não o cargo: um técnico com ``atribuir_os`` atribui."""
    numero = os_aberta(f)
    f.definir_permissoes_cargo(CARGO_TECNICO, (*PERMISSOES_PADRAO_TECNICO, "atribuir_os"))
    aceitar(f.atribuir(numero, CARLA, BRUNO))
    assert os_snap(f, numero).tecnico_id == CARLA
    assert os_snap(f, numero).historico[1].responsavel_id == BRUNO


@pytest.mark.cenario("CAR-14")
def test_gestor_sem_atribuir_os_nao_atribui(f: Fachada) -> None:
    numero = os_aberta(f)
    f.definir_permissoes_cargo(CARGO_GESTOR, ("ver_os",))
    recusada(f.atribuir(numero, BRUNO, ANA), Recusa.SEM_PERMISSAO)
    assert os_snap(f, numero).status == STATUS_ABERTA


@pytest.mark.cenario("CAR-15")
@pytest.mark.parametrize(
    ("construir", "status"),
    [
        (os_aberta, STATUS_ABERTA),
        (os_atribuida, STATUS_ATRIBUIDA),
        (os_em_execucao, STATUS_EM_EXECUCAO),
        (os_aguardando_peca, STATUS_AGUARDANDO_PECA),
        (os_reparo_finalizado, STATUS_REPARO_FINALIZADO),
    ],
)
def test_estados_que_permitem_atribuir_ou_reatribuir(
    f: Fachada, construir: Callable[[Fachada], int], status: str
) -> None:
    numero = construir(f)
    assert os_snap(f, numero).status == status
    # Carla nunca é a responsável nesses cenários; Bruno é (ou ninguém ainda).
    aceitar(f.atribuir(numero, CARLA, ANA))
    assert os_snap(f, numero).tecnico_id == CARLA


@pytest.mark.cenario("CAR-15")
def test_atribuir_os_aberta_muda_status_mas_reatribuir_reparo_finalizado_nao(f: Fachada) -> None:
    aberta = os_aberta(f)
    aceitar(f.atribuir(aberta, BRUNO, ANA))
    finalizada = os_reparo_finalizado(f)
    aceitar(f.atribuir(finalizada, CARLA, ANA))
    assert os_snap(f, aberta).status == STATUS_ATRIBUIDA
    assert os_snap(f, finalizada).status == STATUS_REPARO_FINALIZADO


@pytest.mark.cenario("CAR-16")
@pytest.mark.parametrize(
    ("construir", "status"),
    [
        (os_aguardando_aprovacao, STATUS_AGUARDANDO_APROVACAO),
        (os_concluida, STATUS_CONCLUIDA),
        (os_cancelada, STATUS_CANCELADA),
    ],
)
def test_estados_que_impedem_atribuir_ou_reatribuir(
    f: Fachada, construir: Callable[[Fachada], int], status: str
) -> None:
    numero = construir(f)
    assert os_snap(f, numero).status == status
    antes = estado_global(f)
    resultado = recusada(f.atribuir(numero, CARLA, ANA), Recusa.ESTADO_INVALIDO)
    assert resultado.mensagem == f"Não é possível atribuir uma OS em '{status}'."
    assert estado_global(f) == antes


@pytest.mark.cenario("CAR-17")
def test_atribuir_a_tecnico_ausente_e_aceito_pelo_dominio(f: Fachada) -> None:
    """D-03 (AUD-09): o legado só pede confirmação na tela; o domínio aceita sem erro."""
    aceitar(f.definir_disponibilidade(BRUNO, AUSENTE, solicitante=BRUNO))
    numero = os_aberta(f)
    resultado = aceitar(f.atribuir(numero, BRUNO, ANA))
    assert resultado.valor is None

    os_ = os_snap(f, numero)
    assert (os_.status, os_.tecnico_id) == (STATUS_ATRIBUIDA, BRUNO)
    # nada no histórico indica que o técnico estava ausente
    assert os_.historico[1].descricao == "Atribuída a Bruno Lima"
    # e a ausência não é alterada pela atribuição
    usuario = f.usuario(BRUNO)
    assert usuario is not None
    assert usuario.disponibilidade == AUSENTE


@pytest.mark.cenario("CAR-17")
def test_reatribuir_a_tecnico_ausente_tambem_e_aceito(f: Fachada) -> None:
    numero = os_atribuida(f, tecnico=BRUNO)
    aceitar(f.definir_disponibilidade(CARLA, AUSENTE, solicitante=CARLA))
    aceitar(f.atribuir(numero, CARLA, ANA))
    assert os_snap(f, numero).tecnico_id == CARLA


@pytest.mark.cenario("CAR-18")
def test_tecnico_deixa_de_ser_atribuivel_se_perder_a_permissao_apontar_reparo(f: Fachada) -> None:
    """AUD-20: ser técnico depende de uma permissão editável (o papel é a permissão)."""
    f.definir_permissoes_cargo(CARGO_TECNICO, ("ver_os", "abrir_os"))
    assert f.tecnicos() == ()
    numero = os_aberta(f, solicitante=ANA)
    recusada(f.atribuir(numero, BRUNO, ANA), Recusa.NAO_E_TECNICO)
