"""Execução técnica: diagnóstico, reparos, horas, peças, status e conclusão (Entrega 1)."""

from collections.abc import Callable

import pytest

from tests.caracterizacao.adaptador_legado import AdaptadorLegado
from tests.caracterizacao.cenarios import (
    ANA,
    BRUNO,
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
from tests.caracterizacao.fachada import Fachada, Peca, PecaSnap, Recusa
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

TODOS_OS_STATUS = (
    STATUS_ABERTA,
    STATUS_ATRIBUIDA,
    STATUS_EM_EXECUCAO,
    STATUS_AGUARDANDO_PECA,
    STATUS_REPARO_FINALIZADO,
    STATUS_AGUARDANDO_APROVACAO,
    STATUS_CONCLUIDA,
    STATUS_CANCELADA,
)

CONSTRUTORES: dict[str, Callable[[Fachada], int]] = {
    STATUS_ABERTA: os_aberta,
    STATUS_ATRIBUIDA: os_atribuida,
    STATUS_EM_EXECUCAO: os_em_execucao,
    STATUS_AGUARDANDO_PECA: os_aguardando_peca,
    STATUS_REPARO_FINALIZADO: os_reparo_finalizado,
    STATUS_AGUARDANDO_APROVACAO: os_aguardando_aprovacao,
    STATUS_CONCLUIDA: os_concluida,
    STATUS_CANCELADA: lambda f: os_cancelada(f, atribuida=True),
}


# --------------------------------------------------------------------------------- diagnóstico


@pytest.mark.cenario("CAR-29")
def test_diagnostico_registra_parecer_causa_e_historico_sem_mudar_o_status(f: Fachada) -> None:
    numero = os_atribuida(f)
    aceitar(f.registrar_diagnostico(numero, BRUNO, "Rolamento gasto", "Falta de graxa"))

    os_ = os_snap(f, numero)
    assert (os_.diagnostico, os_.causa_raiz) == ("Rolamento gasto", "Falta de graxa")
    assert os_.status == STATUS_ATRIBUIDA
    ultimo = os_.historico[-1]
    assert (ultimo.tipo, ultimo.responsavel_id) == ("Diagnóstico", BRUNO)
    assert ultimo.descricao == "Rolamento gasto | Causa-raiz: Falta de graxa"


@pytest.mark.cenario("CAR-29")
def test_novo_diagnostico_substitui_o_atual_e_acrescenta_registro(f: Fachada) -> None:
    numero = os_atribuida(f)
    aceitar(f.registrar_diagnostico(numero, BRUNO, "Primeiro", "Causa 1"))
    aceitar(f.registrar_diagnostico(numero, BRUNO, "Segundo", "Causa 2"))
    os_ = os_snap(f, numero)
    assert (os_.diagnostico, os_.causa_raiz) == ("Segundo", "Causa 2")
    assert os_.tipos_do_historico.count("Diagnóstico") == 2


@pytest.mark.cenario("CAR-29")
@pytest.mark.parametrize("status", [STATUS_ATRIBUIDA, STATUS_EM_EXECUCAO, STATUS_AGUARDANDO_PECA])
def test_diagnostico_aceito_nos_estados_de_atendimento(f: Fachada, status: str) -> None:
    numero = CONSTRUTORES[status](f)
    aceitar(f.registrar_diagnostico(numero, BRUNO, "p", "c"))
    assert os_snap(f, numero).status == status


@pytest.mark.cenario("CAR-30")
@pytest.mark.parametrize(
    "status",
    [STATUS_REPARO_FINALIZADO, STATUS_AGUARDANDO_APROVACAO, STATUS_CONCLUIDA, STATUS_CANCELADA],
)
def test_diagnostico_recusado_fora_dos_estados_de_atendimento(f: Fachada, status: str) -> None:
    numero = CONSTRUTORES[status](f)
    antes = estado_global(f)
    resultado = recusada(f.registrar_diagnostico(numero, BRUNO, "p", "c"), Recusa.ESTADO_INVALIDO)
    assert resultado.mensagem == f"Operação não permitida com a OS em '{status}'."
    assert estado_global(f) == antes


@pytest.mark.cenario("CAR-30")
def test_diagnostico_exige_ser_o_tecnico_responsavel(f: Fachada) -> None:
    numero = os_atribuida(f, tecnico=BRUNO)
    antes = estado_global(f)
    resultado = recusada(f.registrar_diagnostico(numero, CARLA, "p", "c"), Recusa.NAO_RESPONSAVEL)
    assert resultado.mensagem == "Esta OS não está atribuída a você."
    assert estado_global(f) == antes


@pytest.mark.cenario("CAR-30")
def test_diagnostico_em_os_sem_tecnico_e_recusado_como_nao_responsavel(f: Fachada) -> None:
    numero = os_aberta(f)
    recusada(f.registrar_diagnostico(numero, BRUNO, "p", "c"), Recusa.NAO_RESPONSAVEL)


@pytest.mark.cenario("CAR-30")
def test_ordem_das_verificacoes_permissao_depois_responsavel_depois_estado(f: Fachada) -> None:
    concluida = os_concluida(f)  # estado inválido para diagnóstico
    # Carla não é a responsável: a recusa de responsável vence a de estado.
    recusada(f.registrar_diagnostico(concluida, CARLA, "p", "c"), Recusa.NAO_RESPONSAVEL)
    # Ana (gestora) não tem a permissão: a de permissão vence todas.
    recusada(f.registrar_diagnostico(concluida, ANA, "p", "c"), Recusa.SEM_PERMISSAO)


# ------------------------------------------------------------------------------------ reparos


@pytest.mark.cenario("CAR-31")
def test_primeiro_apontamento_move_atribuida_para_em_execucao(f: Fachada) -> None:
    numero = os_atribuida(f)
    aceitar(f.apontar_reparo(numero, BRUNO, 2.0, "Troca da correia", (Peca("Correia", 1),)))

    os_ = os_snap(f, numero)
    assert os_.status == STATUS_EM_EXECUCAO
    assert (os_.horas_trabalhadas, os_.intervencoes) == (2.0, ("Troca da correia",))
    assert os_.pecas == (PecaSnap("Correia", 1.0),)
    # primeiro a mudança de status, depois o registro do reparo
    assert [(s.tipo, s.descricao) for s in os_.historico[-2:]] == [
        ("Mudança de status", "Atribuída → Em Execução"),
        ("Reparo", "Troca da correia"),
    ]
    reparo = os_.historico[-1]
    assert (reparo.horas, reparo.pecas, reparo.responsavel_id) == (
        2.0,
        (PecaSnap("Correia", 1.0),),
        BRUNO,
    )


@pytest.mark.cenario("CAR-31")
def test_apontamentos_acumulam_horas_intervencoes_e_pecas(f: Fachada) -> None:
    numero = os_atribuida(f)
    aceitar(f.apontar_reparo(numero, BRUNO, 1.5, "Desmontagem", (Peca("Parafuso", 4),)))
    aceitar(
        f.apontar_reparo(numero, BRUNO, 0.25, "Montagem", (Peca("Selo", 1), Peca("Graxa", 0.5)))
    )
    os_ = os_snap(f, numero)
    assert os_.horas_trabalhadas == 1.75
    assert os_.intervencoes == ("Desmontagem", "Montagem")
    assert [(p.descricao, p.quantidade) for p in os_.pecas] == [
        ("Parafuso", 4.0),
        ("Selo", 1.0),
        ("Graxa", 0.5),
    ]
    # só o primeiro apontamento muda o status
    assert (
        os_.tipos_do_historico.count("Mudança de status") == 2
    )  # Aberta→Atribuída, Atribuída→Em Execução
    assert os_.tipos_do_historico.count("Reparo") == 2


@pytest.mark.cenario("CAR-31")
def test_apontamento_sem_pecas_e_valido(f: Fachada) -> None:
    numero = os_atribuida(f)
    aceitar(f.apontar_reparo(numero, BRUNO, 1.0, "Inspeção"))
    assert os_snap(f, numero).pecas == ()


@pytest.mark.cenario("CAR-31")
def test_apontamento_em_aguardando_peca_mantem_o_status(f: Fachada) -> None:
    numero = os_aguardando_peca(f)
    aceitar(f.apontar_reparo(numero, BRUNO, 1.0, "Pré-montagem"))
    assert os_snap(f, numero).status == STATUS_AGUARDANDO_PECA


@pytest.mark.cenario("CAR-32")
@pytest.mark.parametrize("quantidade", [0, -1, -0.5])
def test_peca_com_quantidade_nao_positiva_e_recusada_sem_alterar_a_os(
    f: Fachada, quantidade: float
) -> None:
    numero = os_atribuida(f)
    antes = estado_global(f)
    resultado = recusada(
        f.apontar_reparo(
            numero, BRUNO, 1.0, "i", (Peca("Válida", 1), Peca("Inválida", quantidade))
        ),
        Recusa.QUANTIDADE_INVALIDA,
    )
    assert resultado.mensagem == "A quantidade deve ser maior que zero."
    assert estado_global(f) == antes
    assert os_snap(f, numero).status == STATUS_ATRIBUIDA


@pytest.mark.cenario("CAR-32")
def test_horas_negativas_sao_recusadas_antes_de_mudar_o_status(f: Fachada) -> None:
    numero = os_atribuida(f)
    antes = estado_global(f)
    resultado = recusada(f.apontar_reparo(numero, BRUNO, -0.1, "i"), Recusa.HORAS_NEGATIVAS)
    assert resultado.mensagem == "Horas trabalhadas não podem ser negativas."
    assert estado_global(f) == antes


@pytest.mark.cenario("CAR-32")
@pytest.mark.parametrize("status", [STATUS_ATRIBUIDA, STATUS_EM_EXECUCAO, STATUS_AGUARDANDO_PECA])
def test_apontar_reparo_aceito_nos_estados_de_atendimento(f: Fachada, status: str) -> None:
    numero = CONSTRUTORES[status](f)
    horas = os_snap(f, numero).horas_trabalhadas
    aceitar(f.apontar_reparo(numero, BRUNO, 1.0, "i"))
    assert os_snap(f, numero).horas_trabalhadas == horas + 1.0


@pytest.mark.cenario("CAR-32")
@pytest.mark.parametrize(
    "status",
    [STATUS_REPARO_FINALIZADO, STATUS_AGUARDANDO_APROVACAO, STATUS_CONCLUIDA, STATUS_CANCELADA],
)
def test_apontar_reparo_recusado_fora_dos_estados_de_atendimento(f: Fachada, status: str) -> None:
    numero = CONSTRUTORES[status](f)
    antes = estado_global(f)
    recusada(f.apontar_reparo(numero, BRUNO, 1.0, "i"), Recusa.ESTADO_INVALIDO)
    assert estado_global(f) == antes


@pytest.mark.cenario("CAR-32")
def test_apontar_reparo_exige_ser_o_responsavel(f: Fachada) -> None:
    numero = os_atribuida(f, tecnico=BRUNO)
    antes = estado_global(f)
    recusada(f.apontar_reparo(numero, CARLA, 1.0, "i"), Recusa.NAO_RESPONSAVEL)
    assert estado_global(f) == antes


@pytest.mark.cenario("CAR-32")
def test_apontar_reparo_exige_a_permissao_apontar_reparo(f: Fachada) -> None:
    numero = os_atribuida(f)
    f.definir_permissoes_cargo(CARGO_TECNICO, ("ver_os", "abrir_os"))
    # Sem a permissão Bruno também deixa de ser "técnico" (AUD-20), mas a recusa é de permissão.
    resultado = recusada(f.apontar_reparo(numero, BRUNO, 1.0, "i"), Recusa.SEM_PERMISSAO)
    assert "Registrar horas, intervenções e peças" in resultado.mensagem


# ----------------------------------------------------------------------- transições do técnico


def _esperado(origem: str, destino: str) -> Recusa | None:
    """Tabela de transições do técnico, derivada de ``OrdemServico.alterar_status``."""
    if origem == STATUS_ABERTA:
        return Recusa.NAO_RESPONSAVEL  # sem técnico atribuído, nenhum técnico é o responsável
    if origem in (STATUS_AGUARDANDO_APROVACAO, STATUS_CONCLUIDA, STATUS_CANCELADA):
        return Recusa.ESTADO_INVALIDO
    if destino not in (STATUS_EM_EXECUCAO, STATUS_AGUARDANDO_PECA, STATUS_REPARO_FINALIZADO):
        return Recusa.STATUS_NAO_PERMITIDO
    if destino == origem:
        return Recusa.JA_NESSE_STATUS
    if destino == STATUS_REPARO_FINALIZADO and origem == STATUS_ATRIBUIDA:
        return Recusa.SEM_INTERVENCAO  # Atribuída ainda não tem intervenção registrada
    return None


@pytest.mark.cenario("CAR-33")
@pytest.mark.parametrize("destino", TODOS_OS_STATUS)
@pytest.mark.parametrize("origem", TODOS_OS_STATUS)
def test_tabela_completa_de_transicoes_do_tecnico(f: Fachada, origem: str, destino: str) -> None:
    numero = CONSTRUTORES[origem](f)
    assert os_snap(f, numero).status == origem
    # D-06 (DLT-06): finalizar exige diagnóstico. Registra-se um, onde a OS o aceita, para que a
    # tabela continue medindo só a transição; a ausência dele é testada à parte (DLT-06).
    f.registrar_diagnostico(numero, BRUNO, "Rolamento gasto", "Falta de graxa")
    antes = estado_global(f)
    esperado = _esperado(origem, destino)

    resultado = f.alterar_status(numero, BRUNO, destino)

    if esperado is None:
        assert resultado.aceito, resultado.mensagem
        os_ = os_snap(f, numero)
        assert os_.status == destino
        assert (os_.historico[-1].tipo, os_.historico[-1].descricao) == (
            "Mudança de status",
            f"{origem} → {destino}",
        )
    else:
        recusada(resultado, esperado)
        assert estado_global(f) == antes


@pytest.mark.cenario("CAR-33")
def test_mudanca_de_status_so_registra_a_mudanca_no_historico(f: Fachada) -> None:
    numero = os_em_execucao(f)
    antes = os_snap(f, numero)
    aceitar(f.alterar_status(numero, BRUNO, STATUS_AGUARDANDO_PECA))
    depois = os_snap(f, numero)
    assert len(depois.historico) == len(antes.historico) + 1
    assert (depois.horas_trabalhadas, depois.intervencoes, depois.pecas) == (
        antes.horas_trabalhadas,
        antes.intervencoes,
        antes.pecas,
    )


@pytest.mark.cenario("CAR-33")
def test_finalizar_reparo_exige_ao_menos_uma_intervencao(f: Fachada) -> None:
    numero = os_atribuida(f)
    aceitar(
        f.registrar_diagnostico(numero, BRUNO, "p", "c")
    )  # diagnóstico não substitui intervenção
    resultado = recusada(
        f.alterar_status(numero, BRUNO, STATUS_REPARO_FINALIZADO), Recusa.SEM_INTERVENCAO
    )
    assert resultado.mensagem == "Registre ao menos uma intervenção antes de finalizar o reparo."


@pytest.mark.cenario("CAR-33")
def test_tecnico_nao_define_status_de_gestao(f: Fachada) -> None:
    numero = os_em_execucao(f)
    for destino in (STATUS_AGUARDANDO_APROVACAO, STATUS_CONCLUIDA, STATUS_CANCELADA, STATUS_ABERTA):
        resultado = recusada(f.alterar_status(numero, BRUNO, destino), Recusa.STATUS_NAO_PERMITIDO)
        assert resultado.mensagem == f"O técnico não pode definir o status '{destino}'."


@pytest.mark.cenario("CAR-33")
def test_alterar_status_exige_ser_o_responsavel_e_ter_a_permissao(f: Fachada) -> None:
    numero = os_em_execucao(f, tecnico=BRUNO)
    recusada(f.alterar_status(numero, CARLA, STATUS_AGUARDANDO_PECA), Recusa.NAO_RESPONSAVEL)
    f.definir_permissoes_cargo(
        CARGO_TECNICO, tuple(p for p in PERMISSOES_PADRAO_TECNICO if p != "atualizar_status")
    )
    recusada(f.alterar_status(numero, BRUNO, STATUS_AGUARDANDO_PECA), Recusa.SEM_PERMISSAO)


@pytest.mark.cenario("CAR-34")
def test_finalizar_reparo_sem_diagnostico_e_aceito(f: Fachada) -> None:
    """D-06 (AUD-21): o legado só exige intervenção para finalizar o reparo."""
    numero = os_atribuida(f)
    aceitar(f.apontar_reparo(numero, BRUNO, 1.0, "troca"))
    aceitar(f.alterar_status(numero, BRUNO, STATUS_REPARO_FINALIZADO))
    os_ = os_snap(f, numero)
    assert (os_.status, os_.diagnostico) == (STATUS_REPARO_FINALIZADO, "")


# ---------------------------------------------------------------------------- conclusão técnica


@pytest.mark.cenario("CAR-35")
def test_conclusao_com_teste_aprovado_submete_a_os_para_aprovacao(f: Fachada) -> None:
    numero = os_reparo_finalizado(f)
    resultado = aceitar(f.concluir_tecnicamente(numero, BRUNO, "Operou 2 h sem falhas", True))
    assert resultado.valor is True

    os_ = os_snap(f, numero)
    assert os_.status == STATUS_AGUARDANDO_APROVACAO
    assert os_.teste_funcional == "Operou 2 h sem falhas"
    assert [(s.tipo, s.descricao, s.responsavel_id) for s in os_.historico[-2:]] == [
        ("Conclusão técnica", "Teste aprovado: Operou 2 h sem falhas", BRUNO),
        ("Mudança de status", "Reparo Finalizado → Aguardando Aprovação", BRUNO),
    ]
    assert os_.data_conclusao is None  # só a aprovação do gestor fixa a data


@pytest.mark.cenario("CAR-36")
def test_conclusao_com_teste_reprovado_mantem_a_os_em_reparo_finalizado(f: Fachada) -> None:
    numero = os_reparo_finalizado(f)
    antes = os_snap(f, numero)
    resultado = aceitar(f.concluir_tecnicamente(numero, BRUNO, "Vibração excessiva", False))
    assert resultado.valor is False  # operação aceita, mas o teste não passou

    os_ = os_snap(f, numero)
    assert os_.status == STATUS_REPARO_FINALIZADO
    assert os_.teste_funcional == ""  # o teste reprovado não é gravado como resultado final
    assert len(os_.historico) == len(antes.historico) + 1
    reprovado = os_.historico[-1]
    assert (reprovado.tipo, reprovado.descricao) == (
        "Teste funcional",
        "Reprovado: Vibração excessiva",
    )


@pytest.mark.cenario("CAR-36")
def test_apos_teste_reprovado_o_tecnico_pode_repetir_e_concluir(f: Fachada) -> None:
    numero = os_reparo_finalizado(f)
    aceitar(f.concluir_tecnicamente(numero, BRUNO, "Falhou", False))
    aceitar(f.concluir_tecnicamente(numero, BRUNO, "Falhou de novo", False))
    aceitar(f.concluir_tecnicamente(numero, BRUNO, "Passou", True))
    os_ = os_snap(f, numero)
    assert os_.status == STATUS_AGUARDANDO_APROVACAO
    assert os_.tipos_do_historico.count("Teste funcional") == 2


@pytest.mark.cenario("CAR-37")
def test_conclusao_sem_diagnostico_e_recusada(legado: AdaptadorLegado) -> None:
    """Só o legado chega a este estado: com a D-06 (DLT-06) a finalização exige diagnóstico, então
    uma OS em Reparo Finalizado sem diagnóstico é inalcançável nos serviços e no domínio. A
    verificação continua no domínio como invariante (``test_ordem_servico.py``)."""
    f = legado
    numero = os_atribuida(f)
    aceitar(f.apontar_reparo(numero, BRUNO, 1.0, "troca"))
    aceitar(f.alterar_status(numero, BRUNO, STATUS_REPARO_FINALIZADO))
    antes = estado_global(f)
    resultado = recusada(f.concluir_tecnicamente(numero, BRUNO, "ok", True), Recusa.SEM_DIAGNOSTICO)
    assert resultado.mensagem == "Registre o diagnóstico antes de concluir."
    assert estado_global(f) == antes


@pytest.mark.cenario("CAR-37")
@pytest.mark.parametrize(
    "status",
    [
        STATUS_ATRIBUIDA,
        STATUS_EM_EXECUCAO,
        STATUS_AGUARDANDO_PECA,
        STATUS_AGUARDANDO_APROVACAO,
        STATUS_CONCLUIDA,
        STATUS_CANCELADA,
    ],
)
def test_conclusao_so_vale_em_reparo_finalizado(f: Fachada, status: str) -> None:
    numero = CONSTRUTORES[status](f)
    antes = estado_global(f)
    recusada(f.concluir_tecnicamente(numero, BRUNO, "ok", True), Recusa.ESTADO_INVALIDO)
    assert estado_global(f) == antes


@pytest.mark.cenario("CAR-37")
def test_conclusao_exige_ser_o_responsavel_e_a_permissao(f: Fachada) -> None:
    numero = os_reparo_finalizado(f)
    recusada(f.concluir_tecnicamente(numero, CARLA, "ok", True), Recusa.NAO_RESPONSAVEL)
    f.definir_permissoes_cargo(
        CARGO_TECNICO, tuple(p for p in PERMISSOES_PADRAO_TECNICO if p != "concluir_os")
    )
    resultado = recusada(f.concluir_tecnicamente(numero, BRUNO, "ok", True), Recusa.SEM_PERMISSAO)
    assert "Conclusão técnica da OS" in resultado.mensagem
