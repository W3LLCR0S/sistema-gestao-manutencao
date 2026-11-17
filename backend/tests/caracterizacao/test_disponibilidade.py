"""Disponibilidade dos técnicos: os dez cenários da D-05 contra o legado.

No legado a disponibilidade é um valor **armazenado** que só muda por edição manual ou quando a
interface chama ``atualizar_disponibilidades()`` (``ui/aplicacao.py`` a chama após cada ação do
menu). Por isso cada cenário registra o valor **antes** e **depois** dessa rotina; a diferença é o
delta da D-05 (disponibilidade derivada das OS, sem rotina), registrado em ``deltas.py``.
"""

import pytest

from tests.caracterizacao.cenarios import (
    ANA,
    AUSENTE,
    BRUNO,
    CARLA,
    DISPONIVEL,
    EM_ATENDIMENTO,
    STATUS_AGUARDANDO_APROVACAO,
    STATUS_CONCLUIDA,
    STATUS_REPARO_FINALIZADO,
)
from tests.caracterizacao.fachada import Fachada
from tests.caracterizacao.fluxos import (
    aceitar,
    os_aberta,
    os_aguardando_aprovacao,
    os_aguardando_peca,
    os_atribuida,
    os_cancelada,
    os_concluida,
    os_em_execucao,
    os_snap,
)


def disp(f: Fachada, usuario: int) -> str:
    """Valor armazenado da disponibilidade (sem recalcular)."""
    snap = f.usuario(usuario)
    assert snap is not None
    return snap.disponibilidade


# ------------------------------------------------------------------- os dez cenários da D-05


@pytest.mark.cenario("CAR-41")
def test_d05_01_sem_os_ativas_e_nao_ausente_fica_disponivel(f: Fachada) -> None:
    assert disp(f, BRUNO) == DISPONIVEL
    f.atualizar_disponibilidades()
    assert disp(f, BRUNO) == DISPONIVEL


@pytest.mark.cenario("CAR-42")
def test_d05_02_os_atribuida_mantem_o_tecnico_disponivel(f: Fachada) -> None:
    os_atribuida(f)
    f.atualizar_disponibilidades()
    assert disp(f, BRUNO) == DISPONIVEL


@pytest.mark.cenario("CAR-43")
def test_d05_03_os_em_execucao_so_vira_em_atendimento_apos_a_rotina(f: Fachada) -> None:
    os_em_execucao(f)
    assert disp(f, BRUNO) == DISPONIVEL  # valor antigo: nada recalculou (AUD-13)
    f.atualizar_disponibilidades()
    assert disp(f, BRUNO) == EM_ATENDIMENTO


@pytest.mark.cenario("CAR-44")
def test_d05_04_aguardando_peca_sem_os_em_execucao_continua_disponivel(f: Fachada) -> None:
    os_aguardando_peca(f)
    f.atualizar_disponibilidades()
    assert disp(f, BRUNO) == DISPONIVEL


@pytest.mark.cenario("CAR-45")
def test_d05_05_em_execucao_e_aguardando_peca_juntas_contam_como_atendimento(f: Fachada) -> None:
    os_aguardando_peca(f)
    os_em_execucao(f)
    f.atualizar_disponibilidades()
    assert disp(f, BRUNO) == EM_ATENDIMENTO


@pytest.mark.cenario("CAR-46")
def test_d05_06_ausencia_manual_prevalece_sobre_os_em_execucao(f: Fachada) -> None:
    os_em_execucao(f)
    f.definir_disponibilidade(BRUNO, AUSENTE)
    f.atualizar_disponibilidades()
    assert disp(f, BRUNO) == AUSENTE


@pytest.mark.cenario("CAR-47")
def test_d05_07_remover_a_ausencia_so_recalcula_apos_a_rotina(f: Fachada) -> None:
    os_em_execucao(f)
    f.definir_disponibilidade(BRUNO, AUSENTE)
    f.atualizar_disponibilidades()
    f.definir_disponibilidade(BRUNO, DISPONIVEL)  # ausência removida
    assert disp(f, BRUNO) == DISPONIVEL  # a OS em execução ainda não foi considerada
    f.atualizar_disponibilidades()
    assert disp(f, BRUNO) == EM_ATENDIMENTO


@pytest.mark.cenario("CAR-48")
def test_d05_08_reparo_finalizado_so_libera_o_tecnico_apos_a_rotina(f: Fachada) -> None:
    numero = os_em_execucao(f)
    f.atualizar_disponibilidades()
    assert disp(f, BRUNO) == EM_ATENDIMENTO
    aceitar(f.alterar_status(numero, BRUNO, STATUS_REPARO_FINALIZADO))
    assert disp(f, BRUNO) == EM_ATENDIMENTO  # valor antigo
    f.atualizar_disponibilidades()
    assert disp(f, BRUNO) == DISPONIVEL


@pytest.mark.cenario("CAR-49")
def test_d05_09_reatribuicao_so_se_reflete_nos_dois_tecnicos_apos_a_rotina(f: Fachada) -> None:
    numero = os_em_execucao(f, tecnico=BRUNO)
    f.atualizar_disponibilidades()
    assert (disp(f, BRUNO), disp(f, CARLA)) == (EM_ATENDIMENTO, DISPONIVEL)
    aceitar(f.atribuir(numero, CARLA, ANA))
    assert (disp(f, BRUNO), disp(f, CARLA)) == (EM_ATENDIMENTO, DISPONIVEL)  # valores antigos
    f.atualizar_disponibilidades()
    assert (disp(f, BRUNO), disp(f, CARLA)) == (DISPONIVEL, EM_ATENDIMENTO)


@pytest.mark.cenario("CAR-50")
def test_d05_10_consulta_logo_apos_uma_transicao_devolve_valor_desatualizado(f: Fachada) -> None:
    """A OS volta a Em Execução por reprovação, mas a consulta imediata não reflete isso."""
    numero = os_aguardando_aprovacao(f)
    f.atualizar_disponibilidades()
    assert disp(f, BRUNO) == DISPONIVEL
    aceitar(f.reprovar(numero, ANA, "refazer"))
    assert os_snap(f, numero).status == "Em Execução"
    assert disp(f, BRUNO) == DISPONIVEL  # a consulta logo após a transição está desatualizada
    f.atualizar_disponibilidades()
    assert disp(f, BRUNO) == EM_ATENDIMENTO


# ------------------------------------------------------------------ manual, rotina e carga


@pytest.mark.cenario("CAR-51")
@pytest.mark.parametrize("valor", [DISPONIVEL, EM_ATENDIMENTO, AUSENTE])
def test_disponibilidade_manual_e_aceita_para_qualquer_usuario_sem_permissao(
    f: Fachada, valor: str
) -> None:
    """Preservar/AUD-09: não há permissão nem regra de domínio para alterar a disponibilidade."""
    f.definir_disponibilidade(CARLA, valor)
    assert disp(f, CARLA) == valor


@pytest.mark.cenario("CAR-51")
def test_rotina_sobrescreve_disponibilidade_manual_exceto_ausente(f: Fachada) -> None:
    f.definir_disponibilidade(BRUNO, EM_ATENDIMENTO)  # sem nenhuma OS em execução
    f.definir_disponibilidade(CARLA, AUSENTE)
    f.atualizar_disponibilidades()
    assert disp(f, BRUNO) == DISPONIVEL
    assert disp(f, CARLA) == AUSENTE


@pytest.mark.cenario("CAR-51")
def test_disponibilidade_sobrevive_a_gravacao_e_recarga(f: Fachada) -> None:
    f.definir_disponibilidade(CARLA, AUSENTE)
    os_em_execucao(f)
    f.atualizar_disponibilidades()
    f.salvar_e_recarregar()
    assert (disp(f, BRUNO), disp(f, CARLA)) == (EM_ATENDIMENTO, AUSENTE)


@pytest.mark.cenario("CAR-52")
def test_rotina_so_recalcula_tecnicos_e_nunca_altera_o_gestor(f: Fachada) -> None:
    f.definir_disponibilidade(ANA, EM_ATENDIMENTO)
    f.atualizar_disponibilidades()
    assert disp(f, ANA) == EM_ATENDIMENTO  # gestor não é técnico: fora do recálculo


@pytest.mark.cenario("CAR-53")
def test_carga_conta_apenas_os_ativas_atribuidas_ao_tecnico(f: Fachada) -> None:
    os_aberta(f)  # sem técnico: não conta
    os_atribuida(f, tecnico=BRUNO)
    os_em_execucao(f, tecnico=BRUNO)
    os_aguardando_aprovacao(f, tecnico=BRUNO)  # ainda ativa: conta
    assert {u.id: u.carga for u in f.usuarios()} == {ANA: 0, BRUNO: 3, CARLA: 0}


@pytest.mark.cenario("CAR-53")
def test_carga_ignora_os_concluidas_e_canceladas(f: Fachada) -> None:
    os_concluida(f, tecnico=BRUNO)
    os_cancelada(f, atribuida=True, tecnico=BRUNO)
    bruno = f.usuario(BRUNO)
    assert bruno is not None
    assert bruno.carga == 0
    assert os_snap(f, 1).status == STATUS_CONCLUIDA


@pytest.mark.cenario("CAR-53")
def test_carga_acompanha_a_reatribuicao_e_o_ciclo_da_os(f: Fachada) -> None:
    numero = os_aguardando_aprovacao(f, tecnico=BRUNO)
    assert os_snap(f, numero).status == STATUS_AGUARDANDO_APROVACAO
    assert {u.id: u.carga for u in f.usuarios()}[BRUNO] == 1
    aceitar(f.aprovar(numero, ANA))
    assert {u.id: u.carga for u in f.usuarios()}[BRUNO] == 0


@pytest.mark.cenario("CAR-54")
def test_tecnico_ausente_continua_listado_como_tecnico_e_com_carga(f: Fachada) -> None:
    numero = os_atribuida(f, tecnico=BRUNO)
    f.definir_disponibilidade(BRUNO, AUSENTE)
    f.atualizar_disponibilidades()
    assert f.tecnicos() == (BRUNO, CARLA)
    bruno = f.usuario(BRUNO)
    assert bruno is not None
    assert (bruno.disponibilidade, bruno.carga) == (AUSENTE, 1)
    assert os_snap(f, numero).tecnico_id == BRUNO  # a OS não é removida de quem está ausente
