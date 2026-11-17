"""Disponibilidade, carga e projeções de leitura: o comportamento ATUAL do legado (sem a D-05)."""

import pytest

from manutencao.application.dto import DisponibilidadeDoTecnico
from manutencao.application.erros import NaoEncontradoError
from manutencao.domain.enums import Disponibilidade, StatusOS
from manutencao.domain.erros import PermissaoNegadaError
from manutencao.domain.permissoes import Permissao
from tests.apoio.ambiente import (
    ANA,
    BRUNO,
    CARGO_TECNICO,
    CARLA,
    COMPRESSOR,
    TORNO,
    Ambiente,
)
from tests.apoio.caminhos import (
    aberta,
    aguardando_aprovacao,
    atribuida,
    em_execucao,
)


def _disp(amb: Ambiente, usuario_id: int) -> Disponibilidade:
    usuario = amb.usuarios.obter(usuario_id)
    assert usuario is not None
    return usuario.disponibilidade


# ------------------------------------------------------------------------------------- carga


def test_carga_conta_so_as_os_ativas_do_tecnico(amb: Ambiente) -> None:
    assert amb.projecoes.carga_do_tecnico(BRUNO) == 0
    atribuida(amb, BRUNO)
    em_execucao(amb, BRUNO)
    atribuida(amb, CARLA)
    assert amb.projecoes.carga_do_tecnico(BRUNO) == 2
    assert amb.projecoes.carga_do_tecnico(CARLA) == 1
    assert amb.projecoes.carga_do_tecnico(ANA) == 0


def test_os_encerrada_sai_da_carga_mas_continua_atribuida(amb: Ambiente) -> None:
    numero = aguardando_aprovacao(amb)
    assert amb.projecoes.carga_do_tecnico(BRUNO) == 1  # aguardando aprovação ainda é ativa
    amb.servico_ordens.aprovar(ANA, numero)
    assert amb.projecoes.carga_do_tecnico(BRUNO) == 0
    assert [o.numero for o in amb.projecoes.ordens_do_tecnico(BRUNO)] == [numero]


def test_os_cancelada_nao_conta_na_carga(amb: Ambiente) -> None:
    numero = atribuida(amb, BRUNO)
    amb.servico_ordens.cancelar(ANA, numero, "x")
    assert amb.projecoes.carga_do_tecnico(BRUNO) == 0


def test_reatribuir_move_a_carga_de_um_tecnico_para_o_outro(amb: Ambiente) -> None:
    numero = atribuida(amb, BRUNO)
    amb.servico_ordens.atribuir(ANA, numero, CARLA)
    assert (amb.projecoes.carga_do_tecnico(BRUNO), amb.projecoes.carga_do_tecnico(CARLA)) == (0, 1)


# --------------------------------------------------------------------------------- projeções


def test_tecnicos_sao_quem_tem_apontar_reparo_como_no_legado(amb: Ambiente) -> None:
    assert [t.id for t in amb.projecoes.tecnicos()] == [BRUNO, CARLA]
    amb.servico_usuarios.definir_permissoes_do_cargo(ANA, CARGO_TECNICO, [Permissao.VER_OS])
    assert amb.projecoes.tecnicos() == ()  # AUD-20, preservado (D-02 é da Operação E)


def test_ordens_por_equipamento_incluem_todos_os_estados(amb: Ambiente) -> None:
    primeira = aberta(amb, equipamento=TORNO)
    segunda = atribuida(amb)
    amb.servico_ordens.cancelar(ANA, segunda, "x")
    outra = aberta(amb, equipamento=COMPRESSOR)
    assert [o.numero for o in amb.projecoes.ordens_do_equipamento(TORNO)] == [primeira, segunda]
    assert [o.numero for o in amb.projecoes.ordens_do_equipamento(COMPRESSOR)] == [outra]
    assert amb.projecoes.ordens_do_equipamento(3) == ()


def test_ordens_por_tecnico_ignoram_os_sem_tecnico(amb: Ambiente) -> None:
    aberta(amb)
    numero = atribuida(amb, CARLA)
    assert amb.projecoes.ordens_do_tecnico(BRUNO) == ()
    assert [o.numero for o in amb.projecoes.ordens_do_tecnico(CARLA)] == [numero]


# --------------------------------------------------------------------------------- consulta


def test_consultar_lista_escala_disponibilidade_armazenada_e_carga(amb: Ambiente) -> None:
    atribuida(amb, BRUNO)
    linhas = amb.servico_disponibilidade.consultar(ANA)
    assert linhas == (
        DisponibilidadeDoTecnico(
            BRUNO, "Bruno Lima", "Seg-Sex 07h-16h", Disponibilidade.DISPONIVEL, 1
        ),
        DisponibilidadeDoTecnico(
            CARLA, "Carla Mendes", "Seg-Sex 13h-22h", Disponibilidade.DISPONIVEL, 0
        ),
    )


def test_consulta_ordenada_por_carga_balanceia_com_desempate_estavel(amb: Ambiente) -> None:
    atribuida(amb, BRUNO)
    atribuida(amb, BRUNO)
    linhas = amb.servico_disponibilidade.consultar(ANA, ordenar_por_carga=True)
    assert [(linha.id, linha.carga) for linha in linhas] == [(CARLA, 0), (BRUNO, 2)]
    assert [linha.id for linha in amb.servico_disponibilidade.consultar(ANA)] == [BRUNO, CARLA]


def test_consultar_exige_ver_disponibilidade(amb: Ambiente) -> None:
    amb.servico_usuarios.definir_permissoes_do_cargo(ANA, CARGO_TECNICO, [Permissao.VER_OS])
    with pytest.raises(PermissaoNegadaError):
        amb.servico_disponibilidade.consultar(BRUNO)
    assert len(amb.servico_disponibilidade.consultar(ANA)) == 0  # sem técnicos: lista vazia


def test_consulta_antes_da_rotina_mostra_o_valor_antigo(amb: Ambiente) -> None:
    """AUD-13 (D-05 nº 10): a OS entra em execução e a disponibilidade só muda pela rotina."""
    em_execucao(amb, BRUNO)
    antes = amb.servico_disponibilidade.consultar(ANA)
    assert antes[0].disponibilidade is Disponibilidade.DISPONIVEL
    amb.servico_disponibilidade.atualizar_disponibilidades()
    depois = amb.servico_disponibilidade.consultar(ANA)
    assert depois[0].disponibilidade is Disponibilidade.EM_ATENDIMENTO


# ---------------------------------------------------------------------------- ajuste manual


def test_cada_usuario_ajusta_a_propria_disponibilidade_sem_permissao(amb: Ambiente) -> None:
    amb.servico_usuarios.definir_permissoes_do_cargo(ANA, CARGO_TECNICO, [])
    amb.servico_disponibilidade.alterar_minha_disponibilidade(CARLA, Disponibilidade.AUSENTE)
    assert _disp(amb, CARLA) is Disponibilidade.AUSENTE
    assert _disp(amb, BRUNO) is Disponibilidade.DISPONIVEL  # só a própria


def test_ajuste_manual_de_usuario_inexistente_levanta_nao_encontrado(amb: Ambiente) -> None:
    with pytest.raises(NaoEncontradoError):
        amb.servico_disponibilidade.alterar_minha_disponibilidade(99, Disponibilidade.AUSENTE)


# ---------------------------------------------------------------------------------- rotina


def test_rotina_em_execucao_vira_em_atendimento_e_sem_execucao_volta_a_disponivel(
    amb: Ambiente,
) -> None:
    numero = em_execucao(amb, BRUNO)
    amb.servico_disponibilidade.atualizar_disponibilidades()
    assert _disp(amb, BRUNO) is Disponibilidade.EM_ATENDIMENTO
    assert _disp(amb, CARLA) is Disponibilidade.DISPONIVEL
    amb.servico_ordens.alterar_status(BRUNO, numero, StatusOS.AGUARDANDO_PECA)
    amb.servico_disponibilidade.atualizar_disponibilidades()
    assert _disp(amb, BRUNO) is Disponibilidade.DISPONIVEL  # só "Em Execução" conta


def test_rotina_so_considera_os_em_execucao(amb: Ambiente) -> None:
    atribuida(amb, BRUNO)  # Atribuída não é "em campo"
    amb.servico_disponibilidade.atualizar_disponibilidades()
    assert _disp(amb, BRUNO) is Disponibilidade.DISPONIVEL


def test_rotina_nao_altera_quem_esta_ausente_mesmo_com_os_em_execucao(amb: Ambiente) -> None:
    em_execucao(amb, BRUNO)
    amb.servico_disponibilidade.alterar_minha_disponibilidade(BRUNO, Disponibilidade.AUSENTE)
    amb.servico_disponibilidade.atualizar_disponibilidades()
    assert _disp(amb, BRUNO) is Disponibilidade.AUSENTE
    assert amb.projecoes.carga_do_tecnico(BRUNO) == 1  # continua técnico, com carga
    assert [t.id for t in amb.projecoes.tecnicos()] == [BRUNO, CARLA]


def test_rotina_so_recalcula_tecnicos(amb: Ambiente) -> None:
    amb.servico_disponibilidade.alterar_minha_disponibilidade(ANA, Disponibilidade.EM_ATENDIMENTO)
    amb.servico_disponibilidade.atualizar_disponibilidades()
    assert _disp(amb, ANA) is Disponibilidade.EM_ATENDIMENTO  # a gestora não é técnica


def test_rotina_sobrescreve_o_ajuste_manual_de_um_tecnico_nao_ausente(amb: Ambiente) -> None:
    amb.servico_disponibilidade.alterar_minha_disponibilidade(CARLA, Disponibilidade.EM_ATENDIMENTO)
    amb.servico_disponibilidade.atualizar_disponibilidades()
    assert _disp(amb, CARLA) is Disponibilidade.DISPONIVEL


def test_rotina_e_idempotente(amb: Ambiente) -> None:
    em_execucao(amb, BRUNO)
    amb.servico_disponibilidade.atualizar_disponibilidades()
    primeira = [(u.id, u.disponibilidade) for u in amb.usuarios.listar()]
    amb.servico_disponibilidade.atualizar_disponibilidades()
    assert [(u.id, u.disponibilidade) for u in amb.usuarios.listar()] == primeira


def test_nenhum_caso_de_uso_atualiza_a_disponibilidade_sozinho(amb: Ambiente) -> None:
    """A D-05 (derivação) é da Operação E: aqui só a rotina explícita recalcula."""
    em_execucao(amb, BRUNO)
    assert _disp(amb, BRUNO) is Disponibilidade.DISPONIVEL
    amb.servico_ordens.cancelar(ANA, 1, "x")
    assert _disp(amb, BRUNO) is Disponibilidade.DISPONIVEL
