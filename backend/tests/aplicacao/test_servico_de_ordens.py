"""Ciclo de vida da OS pelos serviços: delegação ao domínio, ordem das verificações, sem mutação."""

from collections.abc import Callable
from datetime import timedelta

import pytest

from manutencao.application.dto import PecaInformada
from manutencao.application.erros import NaoEncontradoError
from manutencao.application.portas.repositorios import FiltroDeOrdens
from manutencao.domain.enums import Criticidade, StatusOS, TipoServico
from manutencao.domain.erros import (
    CodigoErro,
    ConflitoDeEstadoError,
    DominioError,
    PermissaoNegadaError,
    ViolacaoDeRegraError,
)
from manutencao.domain.ordem_servico import OrdemServico
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
from tests.apoio.relogio import INICIO
from tests.dominio.fabrica import instantaneo

PECAS = [PecaInformada("Rolamento", 2)]


# ----------------------------------------------------------- caminhos até cada estado (serviços)
def aberta(amb: Ambiente, solicitante: int = CARLA, equipamento: int = TORNO) -> int:
    return amb.servico_ordens.abrir(
        solicitante, equipamento, "Torno parado", Criticidade.ALTA
    ).numero


def atribuida(amb: Ambiente, tecnico: int = BRUNO) -> int:
    numero = aberta(amb)
    amb.servico_ordens.atribuir(ANA, numero, tecnico)
    return numero


def em_execucao(amb: Ambiente, tecnico: int = BRUNO) -> int:
    numero = atribuida(amb, tecnico)
    amb.servico_ordens.apontar_reparo(tecnico, numero, 1.5, "Troca do rolamento", PECAS)
    return numero


def reparo_finalizado(amb: Ambiente, tecnico: int = BRUNO, *, diagnostico: bool = True) -> int:
    numero = atribuida(amb, tecnico)
    if diagnostico:
        amb.servico_ordens.registrar_diagnostico(
            tecnico, numero, "Rolamento gasto", "Falta de graxa"
        )
    amb.servico_ordens.apontar_reparo(tecnico, numero, 1.5, "Troca do rolamento", PECAS)
    amb.servico_ordens.alterar_status(tecnico, numero, StatusOS.REPARO_FINALIZADO)
    return numero


def aguardando_aprovacao(amb: Ambiente) -> int:
    numero = reparo_finalizado(amb)
    assert amb.servico_ordens.concluir_tecnicamente(BRUNO, numero, "Funcionou", True)
    return numero


def guardada(amb: Ambiente, numero: int) -> OrdemServico:
    achada = amb.ordens.obter(numero)
    assert achada is not None
    return achada


# ------------------------------------------------------------------------------------ abertura


def test_abrir_cria_a_os_aberta_com_o_registro_de_abertura_e_persiste(amb: Ambiente) -> None:
    os_ = amb.servico_ordens.abrir(CARLA, TORNO, "Torno parado", Criticidade.ALTA)
    assert (os_.numero, os_.status, os_.aberta_por.id) == (1, StatusOS.ABERTA, CARLA)
    guardada_ = guardada(amb, 1)
    assert guardada_.equipamento.id == TORNO
    assert [(s.numero, s.tipo, s.descricao) for s in guardada_.servicos] == [
        (1, TipoServico.ABERTURA, "[Alta] Torno parado")
    ]
    assert guardada_.data_abertura == INICIO


def test_numeracao_e_sequencial_a_partir_de_1(amb: Ambiente) -> None:
    assert [aberta(amb) for _ in range(3)] == [1, 2, 3]


def test_abertura_recusada_nao_consome_numero_nem_cria_os(amb: Ambiente) -> None:
    assert aberta(amb) == 1
    amb.servico_equipamentos.inativar(ANA, COMPRESSOR)
    with pytest.raises(ViolacaoDeRegraError) as erro:
        amb.servico_ordens.abrir(CARLA, COMPRESSOR, "x", Criticidade.BAIXA)
    assert erro.value.codigo is CodigoErro.EQUIPAMENTO_INATIVO
    assert amb.ordens.contar() == 1
    assert aberta(amb) == 2


def test_abertura_sem_permissao_e_recusada(amb: Ambiente) -> None:
    amb.servico_usuarios.definir_permissoes_do_cargo(ANA, CARGO_TECNICO, [Permissao.VER_OS])
    with pytest.raises(PermissaoNegadaError):
        amb.servico_ordens.abrir(CARLA, TORNO, "x", Criticidade.BAIXA)
    assert amb.ordens.contar() == 0


def test_abrir_com_equipamento_ou_ator_inexistente_levanta_nao_encontrado(amb: Ambiente) -> None:
    with pytest.raises(NaoEncontradoError) as erro:
        amb.servico_ordens.abrir(CARLA, 99, "x", Criticidade.BAIXA)
    assert erro.value.entidade == "Equipamento"
    with pytest.raises(NaoEncontradoError) as erro:
        amb.servico_ordens.abrir(99, TORNO, "x", Criticidade.BAIXA)
    assert erro.value.entidade == "Usuário"
    assert amb.ordens.contar() == 0


def test_a_os_devolvida_e_copia_e_nao_o_objeto_guardado(amb: Ambiente) -> None:
    os_ = amb.servico_ordens.abrir(CARLA, TORNO, "x", Criticidade.BAIXA)
    os_.cancelar(amb.usuarios.obter(ANA), "alterada fora do serviço", quando=INICIO)  # type: ignore[arg-type]
    assert guardada(amb, 1).status is StatusOS.ABERTA


# -------------------------------------------------------------------------- ciclo completo


def test_ciclo_completo_ate_a_aprovacao_com_historico_sequencial(amb: Ambiente) -> None:
    numero = reparo_finalizado(amb)
    assert amb.servico_ordens.concluir_tecnicamente(BRUNO, numero, "Funcionou sob carga", True)
    amb.servico_ordens.aprovar(ANA, numero)

    os_ = guardada(amb, numero)
    assert os_.status is StatusOS.CONCLUIDA
    assert os_.data_conclusao == INICIO
    assert [s.numero for s in os_.servicos] == list(range(1, len(os_.servicos) + 1))
    assert [s.tipo for s in os_.servicos] == [
        TipoServico.ABERTURA,
        TipoServico.ATRIBUICAO,
        TipoServico.MUDANCA_STATUS,  # Aberta -> Atribuída
        TipoServico.DIAGNOSTICO,
        TipoServico.MUDANCA_STATUS,  # Atribuída -> Em Execução
        TipoServico.REPARO,
        TipoServico.MUDANCA_STATUS,  # Em Execução -> Reparo Finalizado
        TipoServico.CONCLUSAO_TECNICA,
        TipoServico.MUDANCA_STATUS,  # -> Aguardando Aprovação
        TipoServico.ENCERRAMENTO,
        TipoServico.MUDANCA_STATUS,  # -> Concluída
    ]
    assert os_.horas_trabalhadas == 1.5
    assert [(p.descricao, p.quantidade) for p in os_.pecas_utilizadas] == [("Rolamento", 2)]
    assert os_.diagnostico == "Rolamento gasto"


def test_reprovar_devolve_a_os_ao_tecnico(amb: Ambiente) -> None:
    numero = aguardando_aprovacao(amb)
    amb.servico_ordens.reprovar(ANA, numero, "Vazamento")
    assert guardada(amb, numero).status is StatusOS.EM_EXECUCAO


def test_cancelar_registra_motivo_e_data(amb: Ambiente) -> None:
    numero = atribuida(amb)
    amb.servico_ordens.cancelar(ANA, numero, "Chamado indevido")
    os_ = guardada(amb, numero)
    assert (os_.status, os_.motivo_cancelamento, os_.data_conclusao) == (
        StatusOS.CANCELADA,
        "Chamado indevido",
        INICIO,
    )


def test_reatribuir_devolve_o_tecnico_anterior_e_registra_reatribuicao(amb: Ambiente) -> None:
    numero = aberta(amb)
    assert amb.servico_ordens.atribuir(ANA, numero, BRUNO) is None
    anterior = amb.servico_ordens.atribuir(ANA, numero, CARLA)
    assert anterior is not None
    assert anterior.id == BRUNO
    os_ = guardada(amb, numero)
    assert os_.tecnico_atribuido is not None
    assert os_.tecnico_atribuido.id == CARLA
    assert os_.servicos[-1].tipo is TipoServico.REATRIBUICAO


def test_primeiro_apontamento_leva_a_os_para_em_execucao(amb: Ambiente) -> None:
    numero = atribuida(amb)
    amb.servico_ordens.apontar_reparo(BRUNO, numero, 2.0, "Limpeza")
    os_ = guardada(amb, numero)
    assert (os_.status, os_.horas_trabalhadas) == (StatusOS.EM_EXECUCAO, 2.0)


def test_teste_funcional_reprovado_devolve_false_e_registra_no_historico(amb: Ambiente) -> None:
    numero = reparo_finalizado(amb)
    assert amb.servico_ordens.concluir_tecnicamente(BRUNO, numero, "Falhou", False) is False
    os_ = guardada(amb, numero)
    assert os_.status is StatusOS.REPARO_FINALIZADO
    assert os_.servicos[-1].tipo is TipoServico.TESTE_FUNCIONAL
    assert os_.servicos[-1].descricao == "Reprovado: Falhou"


def test_adicionar_apontamento_registra_no_historico(amb: Ambiente) -> None:
    numero = aberta(amb)
    amb.servico_ordens.adicionar_apontamento(ANA, numero, "Acompanhando")
    ultimo = guardada(amb, numero).servicos[-1]
    assert (ultimo.tipo, ultimo.descricao, ultimo.responsavel.id) == (  # type: ignore[union-attr]
        TipoServico.APONTAMENTO,
        "Acompanhando",
        ANA,
    )


# ------------------------------------------------------------------------------- relógio


def test_cada_caso_de_uso_registra_o_instante_do_relogio_em_utc(amb: Ambiente) -> None:
    numero = aberta(amb)
    amb.relogio.avancar(minutes=30)
    amb.servico_ordens.atribuir(ANA, numero, BRUNO)
    amb.relogio.avancar(minutes=30)
    amb.servico_ordens.apontar_reparo(BRUNO, numero, 1.0, "x")
    os_ = guardada(amb, numero)
    datas = [s.data for s in os_.servicos]
    assert datas[0] == INICIO
    assert (
        datas[1] == datas[2] == INICIO + timedelta(minutes=30)
    )  # um único instante por caso de uso
    assert datas[3] == datas[4] == INICIO + timedelta(minutes=60)
    assert all(d.utcoffset() == timedelta(0) for d in datas)


# ------------------------------------------------------------------------ autorização e posse
RECUSAS_DE_PERMISSAO: dict[str, Callable[[Ambiente, int], object]] = {
    "diagnosticar": lambda a, n: a.servico_ordens.registrar_diagnostico(ANA, n, "p", "c"),
    "apontar": lambda a, n: a.servico_ordens.apontar_reparo(ANA, n, 1.0, "x"),
    "status": lambda a, n: a.servico_ordens.alterar_status(ANA, n, StatusOS.EM_EXECUCAO),
    "concluir": lambda a, n: a.servico_ordens.concluir_tecnicamente(ANA, n, "t", True),
    "atribuir": lambda a, n: a.servico_ordens.atribuir(BRUNO, n, CARLA),
    "aprovar": lambda a, n: a.servico_ordens.aprovar(BRUNO, n),
    "reprovar": lambda a, n: a.servico_ordens.reprovar(BRUNO, n, "m"),
    "cancelar": lambda a, n: a.servico_ordens.cancelar(BRUNO, n, "m"),
}


@pytest.mark.parametrize("operacao", sorted(RECUSAS_DE_PERMISSAO))
def test_gestor_nao_opera_o_lado_tecnico_e_tecnico_nao_opera_o_lado_gestor(
    amb: Ambiente, operacao: str
) -> None:
    numero = atribuida(amb)
    antes = instantaneo(guardada(amb, numero))
    with pytest.raises(PermissaoNegadaError) as erro:
        RECUSAS_DE_PERMISSAO[operacao](amb, numero)
    assert erro.value.codigo is CodigoErro.SEM_PERMISSAO
    assert instantaneo(guardada(amb, numero)) == antes


def test_so_o_tecnico_responsavel_opera_a_os(amb: Ambiente) -> None:
    numero = atribuida(amb, BRUNO)
    antes = instantaneo(guardada(amb, numero))
    operacoes: list[Callable[[], object]] = [
        lambda: amb.servico_ordens.registrar_diagnostico(CARLA, numero, "p", "c"),
        lambda: amb.servico_ordens.apontar_reparo(CARLA, numero, 1.0, "x"),
        lambda: amb.servico_ordens.alterar_status(CARLA, numero, StatusOS.EM_EXECUCAO),
        lambda: amb.servico_ordens.concluir_tecnicamente(CARLA, numero, "t", True),
    ]
    for operacao in operacoes:
        with pytest.raises(PermissaoNegadaError) as erro:
            operacao()
        assert erro.value.codigo is CodigoErro.NAO_RESPONSAVEL
    assert instantaneo(guardada(amb, numero)) == antes


def test_ordem_das_verificacoes_permissao_antes_de_responsavel_antes_de_estado(
    amb: Ambiente,
) -> None:
    """Preservada do legado: uma OS encerrada não troca a recusa por permissão ou posse."""
    numero = atribuida(amb)
    amb.servico_ordens.cancelar(ANA, numero, "x")
    with pytest.raises(PermissaoNegadaError) as sem_permissao:
        amb.servico_ordens.apontar_reparo(ANA, numero, 1.0, "x")
    assert sem_permissao.value.codigo is CodigoErro.SEM_PERMISSAO
    with pytest.raises(PermissaoNegadaError) as nao_responsavel:
        amb.servico_ordens.apontar_reparo(CARLA, numero, 1.0, "x")
    assert nao_responsavel.value.codigo is CodigoErro.NAO_RESPONSAVEL
    with pytest.raises(ConflitoDeEstadoError) as estado:
        amb.servico_ordens.apontar_reparo(BRUNO, numero, 1.0, "x")
    assert estado.value.codigo is CodigoErro.ESTADO_INVALIDO


def test_a_verificacao_de_tecnico_vem_antes_da_de_ja_atribuida(amb: Ambiente) -> None:
    numero = atribuida(amb, BRUNO)
    with pytest.raises(ViolacaoDeRegraError) as erro:
        amb.servico_ordens.atribuir(ANA, numero, ANA)  # a gestora não é técnica
    assert erro.value.codigo is CodigoErro.NAO_E_TECNICO
    with pytest.raises(ConflitoDeEstadoError) as erro_estado:
        amb.servico_ordens.atribuir(ANA, numero, BRUNO)
    assert erro_estado.value.codigo is CodigoErro.JA_ATRIBUIDA


def test_permissao_alterada_no_cargo_vale_na_chamada_seguinte(amb: Ambiente) -> None:
    numero = atribuida(amb)
    amb.servico_usuarios.definir_permissoes_do_cargo(
        ANA, CARGO_TECNICO, [Permissao.VER_OS, Permissao.DIAGNOSTICAR]
    )
    amb.servico_ordens.registrar_diagnostico(BRUNO, numero, "p", "c")  # ainda pode
    with pytest.raises(PermissaoNegadaError):
        amb.servico_ordens.apontar_reparo(BRUNO, numero, 1.0, "x")  # perdeu a permissão


# --------------------------------------------------------------------- recusas sem mutação
RECUSAS_DE_REGRA: dict[str, tuple[Callable[[Ambiente], int], Callable[[Ambiente, int], object]]] = {
    "horas negativas": (
        atribuida,
        lambda a, n: a.servico_ordens.apontar_reparo(BRUNO, n, -1.0, "x"),
    ),
    "status que o tecnico nao define": (
        atribuida,
        lambda a, n: a.servico_ordens.alterar_status(BRUNO, n, StatusOS.CONCLUIDA),
    ),
    "finalizar sem intervencao": (
        atribuida,
        lambda a, n: a.servico_ordens.alterar_status(BRUNO, n, StatusOS.REPARO_FINALIZADO),
    ),
    "concluir sem diagnostico": (
        lambda a: reparo_finalizado(a, diagnostico=False),
        lambda a, n: a.servico_ordens.concluir_tecnicamente(BRUNO, n, "t", True),
    ),
    "aprovar OS que nao aguarda": (
        em_execucao,
        lambda a, n: a.servico_ordens.aprovar(ANA, n),
    ),
    "atribuir OS aguardando aprovacao": (
        aguardando_aprovacao,
        lambda a, n: a.servico_ordens.atribuir(ANA, n, CARLA),
    ),
}


@pytest.mark.parametrize("caso", sorted(RECUSAS_DE_REGRA))
def test_recusa_de_regra_nao_altera_a_os_guardada(amb: Ambiente, caso: str) -> None:
    preparar, operacao = RECUSAS_DE_REGRA[caso]
    numero = preparar(amb)
    antes = instantaneo(guardada(amb, numero))
    with pytest.raises(DominioError):
        operacao(amb, numero)
    assert instantaneo(guardada(amb, numero)) == antes


def test_peca_com_quantidade_invalida_e_recusada_antes_de_tocar_a_os(amb: Ambiente) -> None:
    numero = atribuida(amb)
    antes = instantaneo(guardada(amb, numero))
    with pytest.raises(ViolacaoDeRegraError) as erro:
        amb.servico_ordens.apontar_reparo(BRUNO, numero, 1.0, "x", [PecaInformada("Parafuso", 0)])
    assert erro.value.codigo is CodigoErro.QUANTIDADE_INVALIDA
    assert instantaneo(guardada(amb, numero)) == antes


def test_os_encerrada_nao_muda_por_nenhuma_operacao_de_estado(amb: Ambiente) -> None:
    numero = atribuida(amb)
    amb.servico_ordens.cancelar(ANA, numero, "x")
    antes = instantaneo(guardada(amb, numero))
    with pytest.raises(ConflitoDeEstadoError):
        amb.servico_ordens.cancelar(ANA, numero, "de novo")
    with pytest.raises(ConflitoDeEstadoError):
        amb.servico_ordens.atribuir(ANA, numero, CARLA)
    assert instantaneo(guardada(amb, numero)) == antes


# -------------------------------------------------------------------------------- não encontrado


def test_operacoes_sobre_os_inexistente_levantam_nao_encontrado(amb: Ambiente) -> None:
    servico = amb.servico_ordens
    operacoes: list[Callable[[], object]] = [
        lambda: servico.consultar(ANA, 99),
        lambda: servico.historico(ANA, 99),
        lambda: servico.adicionar_apontamento(ANA, 99, "x"),
        lambda: servico.registrar_diagnostico(BRUNO, 99, "p", "c"),
        lambda: servico.apontar_reparo(BRUNO, 99, 1.0, "x"),
        lambda: servico.alterar_status(BRUNO, 99, StatusOS.EM_EXECUCAO),
        lambda: servico.concluir_tecnicamente(BRUNO, 99, "t", True),
        lambda: servico.atribuir(ANA, 99, BRUNO),
        lambda: servico.aprovar(ANA, 99),
        lambda: servico.reprovar(ANA, 99, "m"),
        lambda: servico.cancelar(ANA, 99, "m"),
    ]
    for operacao in operacoes:
        with pytest.raises(NaoEncontradoError) as erro:
            operacao()
        assert (erro.value.entidade, erro.value.identificador) == ("Ordem de serviço", 99)


def test_atribuir_a_tecnico_inexistente_levanta_nao_encontrado(amb: Ambiente) -> None:
    numero = aberta(amb)
    with pytest.raises(NaoEncontradoError) as erro:
        amb.servico_ordens.atribuir(ANA, numero, 99)
    assert erro.value.entidade == "Usuário"
    assert guardada(amb, numero).status is StatusOS.ABERTA


# ------------------------------------------------------------------------ consulta e histórico


def test_consultar_listar_e_historico_exigem_ver_os(amb: Ambiente) -> None:
    numero = aberta(amb)
    amb.servico_usuarios.definir_permissoes_do_cargo(ANA, CARGO_TECNICO, [Permissao.ABRIR_OS])
    for operacao in (
        lambda: amb.servico_ordens.consultar(BRUNO, numero),
        lambda: amb.servico_ordens.listar(BRUNO),
        lambda: amb.servico_ordens.historico(BRUNO, numero),
    ):
        with pytest.raises(PermissaoNegadaError):
            operacao()


def test_listar_filtra_como_o_legado(amb: Ambiente) -> None:
    def numeros(filtro: FiltroDeOrdens | None = None) -> list[int]:
        return [o.numero for o in amb.servico_ordens.listar(BRUNO, filtro)]

    primeira = aberta(amb)
    segunda = atribuida(amb)
    terceira = em_execucao(amb, CARLA)
    amb.servico_ordens.cancelar(ANA, primeira, "x")
    assert numeros() == [primeira, segunda, terceira]
    assert numeros(FiltroDeOrdens(encerrada=False)) == [segunda, terceira]
    assert numeros(FiltroDeOrdens(encerrada=True)) == [primeira]
    assert numeros(FiltroDeOrdens(status=StatusOS.EM_EXECUCAO)) == [terceira]
    assert numeros(FiltroDeOrdens(tecnico_id=BRUNO)) == [segunda]
    assert numeros(FiltroDeOrdens(equipamento_id=TORNO)) == [primeira, segunda, terceira]
    assert numeros(FiltroDeOrdens(criticidade=Criticidade.BAIXA)) == []


def test_historico_e_sequencial_e_imutavel_para_quem_consulta(amb: Ambiente) -> None:
    numero = atribuida(amb)
    historico = amb.servico_ordens.historico(BRUNO, numero)
    assert [s.numero for s in historico] == [1, 2, 3]
    assert isinstance(historico, tuple)
    assert len(amb.servico_ordens.historico(BRUNO, numero)) == 3
