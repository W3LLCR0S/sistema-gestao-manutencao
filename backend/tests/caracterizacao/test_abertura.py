"""Abertura de OS, numeração, equipamento inativo e ciclo de vida completo (Entrega 1)."""

from collections.abc import Callable

import pytest

from tests.caracterizacao.cenarios import (
    ALTA,
    ANA,
    BAIXA,
    BRUNO,
    CARGO_TECNICO,
    CARLA,
    COMPRESSOR,
    CRITICA,
    MEDIA,
    STATUS_ABERTA,
    STATUS_AGUARDANDO_APROVACAO,
    STATUS_AGUARDANDO_PECA,
    STATUS_ATRIBUIDA,
    STATUS_CANCELADA,
    STATUS_CONCLUIDA,
    STATUS_EM_EXECUCAO,
    STATUS_REPARO_FINALIZADO,
    TORNO,
)
from tests.caracterizacao.fachada import Fachada, Peca, Recusa
from tests.caracterizacao.fluxos import (
    aceitar,
    estado_global,
    os_aberta,
    os_aguardando_aprovacao,
    os_atribuida,
    os_cancelada,
    os_concluida,
    os_em_execucao,
    os_reparo_finalizado,
    os_snap,
    recusada,
)

DATA_INICIAL = "10/03/2026 09:00"


@pytest.mark.cenario("CAR-01")
def test_abertura_cria_os_aberta_com_historico_de_abertura(f: Fachada) -> None:
    resultado = aceitar(f.abrir_os(CARLA, TORNO, "Torno parado", ALTA))
    assert resultado.valor == 1

    os_ = os_snap(f, 1)
    assert os_.status == STATUS_ABERTA
    assert (os_.equipamento_id, os_.falha, os_.criticidade) == (TORNO, "Torno parado", ALTA)
    assert os_.aberta_por_id == CARLA
    assert os_.tecnico_id is None
    assert (os_.diagnostico, os_.causa_raiz, os_.horas_trabalhadas) == ("", "", 0.0)
    assert os_.intervencoes == ()
    assert os_.pecas == ()
    assert os_.data_abertura == DATA_INICIAL
    assert os_.data_conclusao is None
    assert (os_.teste_funcional, os_.motivo_cancelamento) == ("", "")
    assert len(os_.historico) == 1
    abertura = os_.historico[0]
    assert (abertura.numero, abertura.tipo) == (1, "Abertura")
    assert abertura.descricao == "[Alta] Torno parado"
    assert (abertura.responsavel_id, abertura.data) == (CARLA, DATA_INICIAL)
    assert (abertura.horas, abertura.pecas) == (0.0, ())


@pytest.mark.cenario("CAR-02")
@pytest.mark.parametrize("solicitante", [ANA, BRUNO, CARLA])
def test_qualquer_perfil_com_permissao_padrao_abre_os(f: Fachada, solicitante: int) -> None:
    resultado = aceitar(f.abrir_os(solicitante, COMPRESSOR, "Vazamento", MEDIA))
    assert os_snap(f, int(resultado.valor)).aberta_por_id == solicitante


@pytest.mark.cenario("CAR-03")
@pytest.mark.parametrize("criticidade", [BAIXA, MEDIA, ALTA, CRITICA])
def test_abertura_registra_a_criticidade_informada(f: Fachada, criticidade: str) -> None:
    numero = int(aceitar(f.abrir_os(CARLA, TORNO, "Falha", criticidade)).valor)
    os_ = os_snap(f, numero)
    assert os_.criticidade == criticidade
    assert os_.historico[0].descricao == f"[{criticidade}] Falha"


@pytest.mark.cenario("CAR-04")
def test_numeracao_e_sequencial_a_partir_de_1(f: Fachada) -> None:
    numeros = [os_aberta(f) for _ in range(3)]
    assert numeros == [1, 2, 3]
    assert [o.numero for o in f.todas_as_os()] == [1, 2, 3]


@pytest.mark.cenario("CAR-04")
def test_abertura_recusada_nao_consome_numero(f: Fachada) -> None:
    assert os_aberta(f) == 1
    f.inativar_equipamento(COMPRESSOR)
    recusada(f.abrir_os(CARLA, COMPRESSOR, "x", BAIXA), Recusa.EQUIPAMENTO_INATIVO)
    assert os_aberta(f) == 2


@pytest.mark.cenario("CAR-05")
def test_equipamento_inativo_recusa_abertura_sem_criar_os(f: Fachada) -> None:
    f.inativar_equipamento(TORNO)
    antes = estado_global(f)
    resultado = recusada(f.abrir_os(CARLA, TORNO, "Torno parado", ALTA), Recusa.EQUIPAMENTO_INATIVO)
    assert "equipamento inativo" in resultado.mensagem
    assert f.todas_as_os() == ()
    assert estado_global(f) == antes


@pytest.mark.cenario("CAR-05")
def test_equipamento_reativado_volta_a_aceitar_abertura(f: Fachada) -> None:
    f.inativar_equipamento(TORNO)
    f.reativar_equipamento(TORNO)
    assert aceitar(f.abrir_os(CARLA, TORNO, "Torno parado", ALTA)).valor == 1


@pytest.mark.cenario("CAR-06")
def test_abertura_sem_permissao_e_recusada_sem_criar_os(f: Fachada) -> None:
    f.definir_permissoes_cargo(CARGO_TECNICO, ("ver_os",))
    resultado = recusada(f.abrir_os(CARLA, TORNO, "x", BAIXA), Recusa.SEM_PERMISSAO)
    assert "Abrir chamados (OS)" in resultado.mensagem
    assert f.todas_as_os() == ()


@pytest.mark.cenario("CAR-06")
def test_permissao_e_verificada_antes_do_equipamento_inativo(f: Fachada) -> None:
    f.definir_permissoes_cargo(CARGO_TECNICO, ())
    f.inativar_equipamento(TORNO)
    recusada(f.abrir_os(CARLA, TORNO, "x", BAIXA), Recusa.SEM_PERMISSAO)


@pytest.mark.cenario("CAR-07")
def test_ciclo_completo_gera_onze_registros_na_ordem_esperada(f: Fachada) -> None:
    numero = os_concluida(f)
    os_ = os_snap(f, numero)
    assert os_.status == STATUS_CONCLUIDA
    assert [(s.numero, s.tipo, s.responsavel_id) for s in os_.historico] == [
        (1, "Abertura", CARLA),
        (2, "Atribuição", ANA),
        (3, "Mudança de status", ANA),
        (4, "Diagnóstico", BRUNO),
        (5, "Mudança de status", BRUNO),
        (6, "Reparo", BRUNO),
        (7, "Mudança de status", BRUNO),
        (8, "Conclusão técnica", BRUNO),
        (9, "Mudança de status", BRUNO),
        (10, "Encerramento", ANA),
        (11, "Mudança de status", ANA),
    ]
    assert [s.descricao for s in os_.historico] == [
        "[Alta] Torno parado",
        "Atribuída a Bruno Lima",
        "Aberta → Atribuída",
        "Rolamento gasto | Causa-raiz: Falta de graxa",
        "Atribuída → Em Execução",
        "Troca do rolamento",
        "Em Execução → Reparo Finalizado",
        "Teste aprovado: Funcionou sob carga",
        "Reparo Finalizado → Aguardando Aprovação",
        "Reparo validado e OS encerrada.",
        "Aguardando Aprovação → Concluída",
    ]
    assert os_.tecnico_id == BRUNO
    assert os_.data_conclusao is not None


@pytest.mark.cenario("CAR-08")
def test_status_percorre_as_etapas_do_fluxo_feliz(f: Fachada) -> None:
    numero = os_aberta(f)
    assert os_snap(f, numero).status == STATUS_ABERTA
    aceitar(f.atribuir(numero, BRUNO, ANA))
    assert os_snap(f, numero).status == STATUS_ATRIBUIDA
    aceitar(f.registrar_diagnostico(numero, BRUNO, "p", "c"))
    assert os_snap(f, numero).status == STATUS_ATRIBUIDA  # diagnóstico não muda o status
    aceitar(f.apontar_reparo(numero, BRUNO, 1, "i"))
    assert os_snap(f, numero).status == STATUS_EM_EXECUCAO
    aceitar(f.alterar_status(numero, BRUNO, STATUS_AGUARDANDO_PECA))
    assert os_snap(f, numero).status == STATUS_AGUARDANDO_PECA
    aceitar(f.alterar_status(numero, BRUNO, STATUS_REPARO_FINALIZADO))
    assert os_snap(f, numero).status == STATUS_REPARO_FINALIZADO
    aceitar(f.concluir_tecnicamente(numero, BRUNO, "ok", True))
    assert os_snap(f, numero).status == STATUS_AGUARDANDO_APROVACAO
    aceitar(f.aprovar(numero, ANA))
    assert os_snap(f, numero).status == STATUS_CONCLUIDA


@pytest.mark.cenario("CAR-09")
@pytest.mark.parametrize(
    ("construir", "status"),
    [
        (os_aberta, STATUS_ABERTA),
        (os_atribuida, STATUS_ATRIBUIDA),
        (os_em_execucao, STATUS_EM_EXECUCAO),
        (os_reparo_finalizado, STATUS_REPARO_FINALIZADO),
        (os_aguardando_aprovacao, STATUS_AGUARDANDO_APROVACAO),
        (os_concluida, STATUS_CONCLUIDA),
        (os_cancelada, STATUS_CANCELADA),
    ],
)
def test_recusa_por_falta_de_permissao_nunca_altera_estado_nem_historico(
    f: Fachada, construir: Callable[[Fachada], int], status: str
) -> None:
    """Tenta, sem nenhuma permissão, cada operação sobre a OS em cada estado."""
    numero = construir(f)
    assert os_snap(f, numero).status == status
    f.definir_permissoes_cargo(CARGO_TECNICO, ())  # Bruno e Carla sem nenhuma permissão
    antes = estado_global(f)
    tentativas = [
        f.registrar_diagnostico(numero, BRUNO, "p", "c"),
        f.apontar_reparo(numero, BRUNO, 1, "i", (Peca("x", 1),)),
        f.alterar_status(numero, BRUNO, STATUS_EM_EXECUCAO),
        f.concluir_tecnicamente(numero, BRUNO, "t", True),
        f.adicionar_observacao(numero, BRUNO, "obs"),
        f.atribuir(numero, CARLA, BRUNO),
        f.aprovar(numero, BRUNO),
        f.reprovar(numero, BRUNO, "m"),
        f.cancelar(numero, BRUNO, "m"),
    ]
    assert all(t.recusado and t.recusa is Recusa.SEM_PERMISSAO for t in tentativas)
    assert estado_global(f) == antes
