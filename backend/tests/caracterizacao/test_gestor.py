"""Aprovação, reprovação e cancelamento de OS pelo Gestor (Entrega 1)."""

from collections.abc import Callable

import pytest

from tests.caracterizacao.cenarios import (
    ANA,
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
from tests.caracterizacao.fachada import Fachada, Peca, Recusa, RelogioFixo
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

# ------------------------------------------------------------------------------------- aprovar


@pytest.mark.cenario("CAR-19")
def test_aprovar_conclui_a_os_e_registra_a_data_de_conclusao(
    f: Fachada, relogio: RelogioFixo
) -> None:
    numero = os_aguardando_aprovacao(f)
    assert os_snap(f, numero).data_conclusao is None
    relogio.avancar(days=1, hours=3)
    aceitar(f.aprovar(numero, ANA))

    os_ = os_snap(f, numero)
    assert os_.status == STATUS_CONCLUIDA
    assert os_.data_conclusao == "11/03/2026 12:00"
    assert [(s.tipo, s.descricao, s.responsavel_id, s.data) for s in os_.historico[-2:]] == [
        ("Encerramento", "Reparo validado e OS encerrada.", ANA, "11/03/2026 12:00"),
        ("Mudança de status", "Aguardando Aprovação → Concluída", ANA, "11/03/2026 12:00"),
    ]


@pytest.mark.cenario("CAR-19")
@pytest.mark.parametrize(
    "construir",
    [
        os_aberta,
        os_atribuida,
        os_em_execucao,
        os_aguardando_peca,
        os_reparo_finalizado,
        os_concluida,
        os_cancelada,
    ],
)
def test_aprovar_so_vale_para_os_aguardando_aprovacao(
    f: Fachada, construir: Callable[[Fachada], int]
) -> None:
    numero = construir(f)
    antes = estado_global(f)
    recusada(f.aprovar(numero, ANA), Recusa.ESTADO_INVALIDO)
    assert estado_global(f) == antes


# ----------------------------------------------------------------------------------- reprovar


@pytest.mark.cenario("CAR-20")
def test_reprovar_devolve_a_os_ao_tecnico_em_execucao(f: Fachada) -> None:
    numero = os_aguardando_aprovacao(f)
    aceitar(f.reprovar(numero, ANA, "Vazamento persiste"))

    os_ = os_snap(f, numero)
    assert (os_.status, os_.tecnico_id) == (STATUS_EM_EXECUCAO, BRUNO)
    assert os_.data_conclusao is None
    assert [(s.tipo, s.descricao, s.responsavel_id) for s in os_.historico[-2:]] == [
        ("Reprovação", "Devolvida ao técnico: Vazamento persiste", ANA),
        ("Mudança de status", "Aguardando Aprovação → Em Execução", ANA),
    ]


@pytest.mark.cenario("CAR-20")
def test_reprovacao_preserva_o_que_o_tecnico_ja_registrou(f: Fachada) -> None:
    numero = os_aguardando_aprovacao(f)
    antes = os_snap(f, numero)
    aceitar(f.reprovar(numero, ANA, "refazer"))
    depois = os_snap(f, numero)
    assert depois.diagnostico == antes.diagnostico
    assert depois.causa_raiz == antes.causa_raiz
    assert depois.horas_trabalhadas == antes.horas_trabalhadas
    assert depois.pecas == antes.pecas
    assert depois.teste_funcional == antes.teste_funcional == "Funcionou sob carga"
    assert depois.historico[: len(antes.historico)] == antes.historico


@pytest.mark.cenario("CAR-20")
def test_apos_reprovar_o_ciclo_pode_ser_repetido_ate_concluir(f: Fachada) -> None:
    numero = os_aguardando_aprovacao(f)
    aceitar(f.reprovar(numero, ANA, "refazer"))
    aceitar(f.apontar_reparo(numero, BRUNO, 0.5, "Reaperto", (Peca("Parafuso", 4),)))
    aceitar(f.alterar_status(numero, BRUNO, STATUS_REPARO_FINALIZADO))
    aceitar(f.concluir_tecnicamente(numero, BRUNO, "Segundo teste", True))
    aceitar(f.aprovar(numero, ANA))

    os_ = os_snap(f, numero)
    assert os_.status == STATUS_CONCLUIDA
    assert os_.horas_trabalhadas == 2.0  # 1,5 h + 0,5 h
    assert os_.teste_funcional == "Segundo teste"
    assert "Reprovação" in os_.tipos_do_historico


@pytest.mark.cenario("CAR-20")
@pytest.mark.parametrize(
    "construir",
    [os_aberta, os_atribuida, os_em_execucao, os_reparo_finalizado, os_concluida, os_cancelada],
)
def test_reprovar_so_vale_para_os_aguardando_aprovacao(
    f: Fachada, construir: Callable[[Fachada], int]
) -> None:
    numero = construir(f)
    antes = estado_global(f)
    recusada(f.reprovar(numero, ANA, "motivo"), Recusa.ESTADO_INVALIDO)
    assert estado_global(f) == antes


# ----------------------------------------------------------------------------------- cancelar


@pytest.mark.cenario("CAR-21")
@pytest.mark.parametrize(
    ("construir", "status_anterior"),
    [
        (os_aberta, STATUS_ABERTA),
        (os_atribuida, STATUS_ATRIBUIDA),
        (os_em_execucao, STATUS_EM_EXECUCAO),
        (os_aguardando_peca, STATUS_AGUARDANDO_PECA),
        (os_reparo_finalizado, STATUS_REPARO_FINALIZADO),
        (os_aguardando_aprovacao, STATUS_AGUARDANDO_APROVACAO),
    ],
)
def test_cancelar_vale_para_qualquer_os_nao_encerrada(
    f: Fachada, relogio: RelogioFixo, construir: Callable[[Fachada], int], status_anterior: str
) -> None:
    numero = construir(f)
    assert os_snap(f, numero).status == status_anterior
    relogio.avancar(hours=1)
    aceitar(f.cancelar(numero, ANA, "Chamado indevido"))

    os_ = os_snap(f, numero)
    assert os_.status == STATUS_CANCELADA
    assert os_.motivo_cancelamento == "Chamado indevido"
    assert os_.data_conclusao is not None
    assert [(s.tipo, s.descricao, s.responsavel_id) for s in os_.historico[-2:]] == [
        ("Cancelamento", "Chamado indevido", ANA),
        ("Mudança de status", f"{status_anterior} → Cancelada", ANA),
    ]


@pytest.mark.cenario("CAR-21")
@pytest.mark.parametrize("construir", [os_concluida, os_cancelada])
def test_cancelar_os_encerrada_e_recusado(f: Fachada, construir: Callable[[Fachada], int]) -> None:
    numero = construir(f)
    antes = estado_global(f)
    resultado = recusada(f.cancelar(numero, ANA, "de novo"), Recusa.OS_ENCERRADA)
    assert resultado.mensagem == "A OS já está encerrada."
    assert estado_global(f) == antes


@pytest.mark.cenario("CAR-21")
def test_cancelamento_preserva_tecnico_e_dados_tecnicos(f: Fachada) -> None:
    numero = os_em_execucao(f)
    antes = os_snap(f, numero)
    aceitar(f.cancelar(numero, ANA, "Equipamento sucateado"))
    depois = os_snap(f, numero)
    assert depois.tecnico_id == BRUNO
    assert (depois.horas_trabalhadas, depois.intervencoes, depois.pecas) == (
        antes.horas_trabalhadas,
        antes.intervencoes,
        antes.pecas,
    )


# ------------------------------------------------------------ permissão única `aprovar_os`


@pytest.mark.cenario("CAR-22")
def test_aprovar_reprovar_e_cancelar_exigem_a_mesma_permissao_aprovar_os(f: Fachada) -> None:
    """Preservar: no baseline não há permissão própria para cancelar (decisão pendente)."""
    f.definir_permissoes_cargo(CARGO_GESTOR, ("ver_os", "atribuir_os"))  # Ana sem aprovar_os
    para_aprovar = os_aguardando_aprovacao(f)
    para_cancelar = os_aberta(f)
    antes = estado_global(f)
    resultados = [
        f.aprovar(para_aprovar, ANA),
        f.reprovar(para_aprovar, ANA, "m"),
        f.cancelar(para_cancelar, ANA, "m"),
    ]
    assert all(r.recusa is Recusa.SEM_PERMISSAO for r in resultados)
    assert all("Aprovar, cancelar e encerrar OS" in r.mensagem for r in resultados)
    assert estado_global(f) == antes


@pytest.mark.cenario("CAR-22")
def test_quem_recebe_aprovar_os_tambem_pode_cancelar(f: Fachada) -> None:
    """Conceder ``aprovar_os`` a um técnico lhe dá, de uma vez, aprovar, reprovar e cancelar."""
    f.definir_permissoes_cargo(CARGO_TECNICO, (*PERMISSOES_PADRAO_TECNICO, "aprovar_os"))
    aguardando = os_aguardando_aprovacao(f, tecnico=CARLA)
    outra = os_aberta(f)
    aceitar(f.reprovar(aguardando, BRUNO, "refazer"))
    aceitar(f.cancelar(outra, BRUNO, "indevida"))
    assert os_snap(f, aguardando).status == STATUS_EM_EXECUCAO
    assert os_snap(f, outra).status == STATUS_CANCELADA


@pytest.mark.cenario("CAR-22")
def test_tecnico_sem_aprovar_os_nao_aprova_nem_cancela(f: Fachada) -> None:
    aguardando = os_aguardando_aprovacao(f)
    recusada(f.aprovar(aguardando, BRUNO), Recusa.SEM_PERMISSAO)
    recusada(f.reprovar(aguardando, BRUNO, "m"), Recusa.SEM_PERMISSAO)
    recusada(f.cancelar(aguardando, BRUNO, "m"), Recusa.SEM_PERMISSAO)
    assert os_snap(f, aguardando).status == STATUS_AGUARDANDO_APROVACAO


@pytest.mark.cenario("CAR-22")
def test_gestor_nao_precisa_ser_o_responsavel_nem_quem_abriu_a_os(f: Fachada) -> None:
    """Autorização do gestor: só a permissão (sem vínculo com a OS)."""
    numero = os_aguardando_aprovacao(f)  # aberta por Carla, técnica Bruno
    aceitar(f.aprovar(numero, ANA))
    assert os_snap(f, numero).status == STATUS_CONCLUIDA
