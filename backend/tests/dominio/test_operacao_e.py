"""Operação E no domínio: as regras de negócio aprovadas (D-02 a D-06, DLT-08 e DLT-09).

Cada teste escreve a expectativa por extenso e prova duas coisas: o que é recusado ou aceito e que
**uma recusa não altera nada** (nem a OS, nem o histórico). O comportamento antigo de cada regra é
caracterizado no legado (``tests/caracterizacao``, ver ``deltas.py``); a comparação lado a lado
está em ``tests/caracterizacao/test_operacao_e_servicos.py``.

* DLT-01 papéis explícitos (D-02)        * DLT-05 disponibilidade derivada (D-05)
* DLT-02 técnico ausente (D-03)          * DLT-06 diagnóstico obrigatório (D-06)
* DLT-03 observação em OS encerrada      * DLT-08 campos obrigatórios e horas positivas
* DLT-04 quem observa (D-04)             * DLT-09 usuário ativo ou inativo
"""

import math
from collections.abc import Callable

import pytest

from manutencao.domain.disponibilidade import derivar_disponibilidade
from manutencao.domain.enums import Criticidade, Disponibilidade, Papel, StatusOS, TipoServico
from manutencao.domain.erros import (
    CodigoErro,
    ConflitoDeEstadoError,
    DominioError,
    PermissaoNegadaError,
    ViolacaoDeRegraError,
)
from manutencao.domain.ordem_servico import OrdemServico
from manutencao.domain.peca_material import PecaMaterial
from manutencao.domain.permissoes import Permissao
from manutencao.domain.usuario import Usuario
from tests.dominio.fabrica import Mundo, instantaneo

Chamada = Callable[[], object]


def recusa(
    os_: OrdemServico, erro: type[DominioError], codigo: CodigoErro, chamada: Chamada
) -> DominioError:
    """A chamada é recusada com a classe e o código esperados, sem alterar nada na OS."""
    antes = instantaneo(os_)
    with pytest.raises(erro) as capturado:
        chamada()
    assert capturado.value.codigo is codigo
    assert instantaneo(os_) == antes
    return capturado.value


def _sem(permissao: Permissao, *, de: Mundo, cargo: str = "tecnico") -> None:
    alvo = de.tecnico if cargo == "tecnico" else de.gestor
    alvo.permissoes.definir([p for p in alvo.permissoes.ativas() if p is not permissao])


def _diego(m: Mundo) -> Usuario:
    """Um técnico que não tem relação nenhuma com as OS do cenário."""
    return Usuario(4, "Diego", m.tecnico, papel=Papel.TECNICO)


# =========================================================================================
# DLT-01 — papéis Gestor e Técnico (D-02)
# =========================================================================================


def test_dlt01_o_papel_e_obrigatorio_e_explicito() -> None:
    m = Mundo()
    with pytest.raises(TypeError):
        Usuario(4, "Sem papel", m.tecnico)  # type: ignore[call-arg]
    assert (m.ana.papel, m.bruno.papel) == (Papel.GESTOR, Papel.TECNICO)
    assert (m.ana.e_gestor, m.ana.e_tecnico) == (True, False)
    assert (m.bruno.e_gestor, m.bruno.e_tecnico) == (False, True)


def test_dlt01_o_papel_nao_depende_das_permissoes() -> None:
    m = Mundo()
    m.tecnico.permissoes.definir([])  # nenhuma permissão
    m.gestor.permissoes.definir(list(Permissao))  # todas, inclusive as técnicas
    assert (m.bruno.e_tecnico, m.carla.e_tecnico) == (True, True)
    assert (m.ana.e_tecnico, m.ana.e_gestor) == (False, True)


def test_dlt01_tecnico_sem_apontar_reparo_continua_atribuivel_e_e_negado_ao_apontar() -> None:
    m = Mundo()
    _sem(Permissao.APONTAR_REPARO, de=m)
    os_ = m.aberta()
    assert os_.atribuir(m.bruno, m.ana, quando=m.quando()) is None
    assert os_.tecnico_atribuido == m.bruno
    recusa(
        os_,
        PermissaoNegadaError,
        CodigoErro.SEM_PERMISSAO,
        lambda: os_.apontar_reparo(m.bruno, 1.0, "Troca", [], quando=m.quando()),
    )


def test_dlt01_gestor_com_permissoes_tecnicas_nao_recebe_atribuicao() -> None:
    m = Mundo()
    m.gestor.permissoes.definir([*m.gestor.permissoes.ativas(), Permissao.APONTAR_REPARO])
    assert m.ana.pode(Permissao.APONTAR_REPARO)
    os_ = m.aberta()
    erro = recusa(
        os_,
        ViolacaoDeRegraError,
        CodigoErro.NAO_E_TECNICO,
        lambda: os_.atribuir(m.ana, m.ana, quando=m.quando()),
    )
    assert erro.mensagem == "Ana Souza não é técnico."


# =========================================================================================
# DLT-02 — atribuição a técnico ausente (D-03)
# =========================================================================================


def _ausente(m: Mundo, quem: Usuario) -> None:
    quem.disponibilidade = Disponibilidade.AUSENTE


def test_dlt02_atribuir_a_tecnico_ausente_sem_confirmacao_e_recusado_sem_alterar_a_os() -> None:
    m = Mundo()
    _ausente(m, m.bruno)
    os_ = m.aberta()
    erro = recusa(
        os_,
        ConflitoDeEstadoError,
        CodigoErro.TECNICO_AUSENTE,
        lambda: os_.atribuir(m.bruno, m.ana, quando=m.quando()),
    )
    assert "ausente" in erro.mensagem
    assert (os_.status, os_.tecnico_atribuido, len(os_.servicos)) == (StatusOS.ABERTA, None, 1)


def test_dlt02_com_confirmacao_a_atribuicao_e_aceita_e_o_historico_registra_a_ausencia() -> None:
    m = Mundo()
    _ausente(m, m.bruno)
    os_ = m.aberta()
    os_.atribuir(m.bruno, m.ana, quando=m.quando(), confirmar_ausente=True)
    assert (os_.status, os_.tecnico_atribuido) == (StatusOS.ATRIBUIDA, m.bruno)
    atribuicao = os_.servicos[1]
    assert atribuicao.tipo is TipoServico.ATRIBUICAO
    assert atribuicao.descricao == (
        "Atribuída a Bruno Lima (técnico ausente; atribuição confirmada pelo gestor)"
    )
    assert m.bruno.disponibilidade is Disponibilidade.AUSENTE  # a ausência não é apagada


def test_dlt02_a_reatribuicao_a_tecnico_ausente_segue_a_mesma_regra() -> None:
    m = Mundo()
    os_ = m.atribuida(m.bruno)
    _ausente(m, m.carla)
    recusa(
        os_,
        ConflitoDeEstadoError,
        CodigoErro.TECNICO_AUSENTE,
        lambda: os_.atribuir(m.carla, m.ana, quando=m.quando()),
    )
    assert os_.tecnico_atribuido == m.bruno
    anterior = os_.atribuir(m.carla, m.ana, quando=m.quando(), confirmar_ausente=True)
    assert anterior == m.bruno
    assert os_.servicos[-1].tipo is TipoServico.REATRIBUICAO
    assert os_.servicos[-1].descricao == (
        "Bruno Lima → Carla Mendes (técnico ausente; atribuição confirmada pelo gestor)"
    )


def test_dlt02_a_confirmacao_nao_altera_a_atribuicao_a_tecnico_presente() -> None:
    m = Mundo()
    os_ = m.aberta()
    os_.atribuir(m.bruno, m.ana, quando=m.quando(), confirmar_ausente=True)
    assert os_.servicos[1].descricao == "Atribuída a Bruno Lima"


def test_dlt02_a_confirmacao_nao_substitui_a_permissao_de_atribuir() -> None:
    m = Mundo()
    _ausente(m, m.bruno)
    os_ = m.aberta()
    recusa(
        os_,
        PermissaoNegadaError,
        CodigoErro.SEM_PERMISSAO,
        lambda: os_.atribuir(m.bruno, m.carla, quando=m.quando(), confirmar_ausente=True),
    )


def test_dlt02_as_verificacoes_antigas_vem_antes_da_ausencia() -> None:
    m = Mundo()
    os_ = m.atribuida(m.bruno)
    _ausente(m, m.bruno)  # já é o responsável e está ausente: vale "já atribuída"
    recusa(
        os_,
        ConflitoDeEstadoError,
        CodigoErro.JA_ATRIBUIDA,
        lambda: os_.atribuir(m.bruno, m.ana, quando=m.quando()),
    )
    _ausente(m, m.ana)  # não é técnico e está ausente: vale "não é técnico"
    recusa(
        os_,
        ViolacaoDeRegraError,
        CodigoErro.NAO_E_TECNICO,
        lambda: os_.atribuir(m.ana, m.ana, quando=m.quando()),
    )


# =========================================================================================
# DLT-03 e DLT-04 — observações (D-04)
# =========================================================================================


def test_dlt03_observacao_em_os_concluida_ou_cancelada_e_recusada_para_todos() -> None:
    m = Mundo()
    for os_ in (m.concluida(), m.cancelada(atribuida=True)):
        for autor in (m.ana, m.bruno, m.carla):
            erro = recusa(
                os_,
                ConflitoDeEstadoError,
                CodigoErro.OS_ENCERRADA,
                lambda os_=os_, autor=autor: os_.adicionar_apontamento(  # type: ignore[misc]
                    autor, "depois do fim", quando=m.quando()
                ),
            )
            assert erro.mensagem == "A OS já está encerrada."


def test_dlt04_gestor_responsavel_e_autor_da_abertura_observam_em_os_ativa() -> None:
    m = Mundo()
    ativas = (
        m.aberta(),
        m.atribuida(),
        m.em_execucao(),
        m.aguardando_peca(),
        m.reparo_finalizado(),
        m.aguardando_aprovacao(),
    )
    for os_ in ativas:
        status = os_.status
        for autor in (m.ana, m.carla) + ((m.bruno,) if os_.tecnico_atribuido else ()):
            antes = len(os_.servicos)
            os_.adicionar_apontamento(autor, f"nota de {autor.nome}", quando=m.quando())
            registro = os_.servicos[-1]
            assert (registro.tipo, registro.responsavel) == (TipoServico.APONTAMENTO, autor)
            assert registro.descricao == f"nota de {autor.nome}"
            assert len(os_.servicos) == antes + 1
        assert os_.status is status  # a observação nunca altera o estado


def test_dlt04_tecnico_sem_vinculo_com_a_os_e_recusado_mesmo_em_os_encerrada() -> None:
    m = Mundo()
    diego = _diego(m)
    for os_ in (m.aberta(), m.atribuida(), m.em_execucao(), m.concluida()):
        erro = recusa(
            os_,
            PermissaoNegadaError,
            CodigoErro.SEM_VINCULO_COM_A_OS,
            lambda os_=os_: os_.adicionar_apontamento(diego, "passando", quando=m.quando()),  # type: ignore[misc]
        )
        assert "gestor, o técnico responsável ou quem abriu" in erro.mensagem


def test_dlt04_tecnico_que_nao_e_o_responsavel_e_recusado_mesmo_estando_atribuido_a_outro() -> None:
    m = Mundo()
    os_ = m.atribuida(m.bruno)  # aberta por Carla
    outro = _diego(m)
    recusa(
        os_,
        PermissaoNegadaError,
        CodigoErro.SEM_VINCULO_COM_A_OS,
        lambda: os_.adicionar_apontamento(outro, "x", quando=m.quando()),
    )
    os_.atribuir(m.carla, m.ana, quando=m.quando())  # reatribuída: Bruno deixa de ser responsável
    recusa(
        os_,
        PermissaoNegadaError,
        CodigoErro.SEM_VINCULO_COM_A_OS,
        lambda: os_.adicionar_apontamento(m.bruno, "x", quando=m.quando()),
    )


def test_dlt04_a_permissao_registrar_apontamento_continua_exigida() -> None:
    m = Mundo()
    os_ = m.atribuida()
    _sem(Permissao.REGISTRAR_APONTAMENTO, de=m, cargo="gestor")
    recusa(
        os_,
        PermissaoNegadaError,
        CodigoErro.SEM_PERMISSAO,
        lambda: os_.adicionar_apontamento(m.ana, "x", quando=m.quando()),
    )
    _sem(Permissao.REGISTRAR_APONTAMENTO, de=m)
    recusa(
        os_,
        PermissaoNegadaError,
        CodigoErro.SEM_PERMISSAO,
        lambda: os_.adicionar_apontamento(m.bruno, "x", quando=m.quando()),
    )


def test_dlt04_o_autor_da_abertura_nao_ganha_capacidade_tecnica() -> None:
    m = Mundo()
    os_ = m.em_execucao()  # aberta por Carla, de Bruno
    operacoes: tuple[Chamada, ...] = (
        lambda: os_.registrar_diagnostico(m.carla, "p", "c", quando=m.quando()),
        lambda: os_.apontar_reparo(m.carla, 1.0, "Troca", [], quando=m.quando()),
        lambda: os_.alterar_status(m.carla, StatusOS.AGUARDANDO_PECA, quando=m.quando()),
        lambda: os_.concluir_tecnicamente(m.carla, "ok", True, quando=m.quando()),
    )
    for operacao in operacoes:
        recusa(os_, PermissaoNegadaError, CodigoErro.NAO_RESPONSAVEL, operacao)


def test_dlt04_o_papel_gestor_e_o_que_autoriza_o_gestor_e_nao_o_cargo() -> None:
    """Quem observa por ser Gestor é o papel: um técnico com o cargo de gestor não o é."""
    m = Mundo()
    diego = Usuario(4, "Diego", m.gestor, papel=Papel.TECNICO)
    os_ = m.atribuida()
    recusa(
        os_,
        PermissaoNegadaError,
        CodigoErro.SEM_VINCULO_COM_A_OS,
        lambda: os_.adicionar_apontamento(diego, "x", quando=m.quando()),
    )


# =========================================================================================
# DLT-05 — disponibilidade derivada (D-05): a regra pura
# =========================================================================================


@pytest.mark.parametrize(
    ("manual", "em_execucao", "esperada"),
    [
        (Disponibilidade.DISPONIVEL, False, Disponibilidade.DISPONIVEL),
        (Disponibilidade.DISPONIVEL, True, Disponibilidade.EM_ATENDIMENTO),
        (Disponibilidade.EM_ATENDIMENTO, False, Disponibilidade.DISPONIVEL),
        (Disponibilidade.EM_ATENDIMENTO, True, Disponibilidade.EM_ATENDIMENTO),
        (Disponibilidade.AUSENTE, False, Disponibilidade.AUSENTE),
        (Disponibilidade.AUSENTE, True, Disponibilidade.AUSENTE),
    ],
)
def test_dlt05_a_ausencia_manual_prevalece_e_so_em_execucao_caracteriza_atendimento(
    manual: Disponibilidade, em_execucao: bool, esperada: Disponibilidade
) -> None:
    assert derivar_disponibilidade(manual, em_execucao) is esperada


# =========================================================================================
# DLT-06 — diagnóstico obrigatório antes de Reparo Finalizado (D-06)
# =========================================================================================


def _com_intervencao_sem_diagnostico(m: Mundo, status: StatusOS) -> OrdemServico:
    os_ = m.atribuida()
    os_.apontar_reparo(m.bruno, 1.5, "Troca do rolamento", [], quando=m.quando())
    if status is StatusOS.AGUARDANDO_PECA:
        os_.alterar_status(m.bruno, StatusOS.AGUARDANDO_PECA, quando=m.quando())
    assert (os_.status, os_.diagnostico) == (status, "")
    return os_


@pytest.mark.parametrize("origem", [StatusOS.EM_EXECUCAO, StatusOS.AGUARDANDO_PECA])
def test_dlt06_finalizar_sem_diagnostico_e_recusado_sem_alterar_status_nem_historico(
    origem: StatusOS,
) -> None:
    m = Mundo()
    os_ = _com_intervencao_sem_diagnostico(m, origem)
    erro = recusa(
        os_,
        ViolacaoDeRegraError,
        CodigoErro.SEM_DIAGNOSTICO,
        lambda: os_.alterar_status(m.bruno, StatusOS.REPARO_FINALIZADO, quando=m.quando()),
    )
    assert erro.mensagem == "Registre o diagnóstico técnico antes de finalizar o reparo."
    assert os_.status is origem


@pytest.mark.parametrize("origem", [StatusOS.EM_EXECUCAO, StatusOS.AGUARDANDO_PECA])
def test_dlt06_com_diagnostico_a_finalizacao_segue_exigindo_intervencao_e_funciona(
    origem: StatusOS,
) -> None:
    m = Mundo()
    os_ = _com_intervencao_sem_diagnostico(m, origem)
    os_.registrar_diagnostico(m.bruno, "Rolamento gasto", "Falta de graxa", quando=m.quando())
    os_.alterar_status(m.bruno, StatusOS.REPARO_FINALIZADO, quando=m.quando())
    assert os_.status is StatusOS.REPARO_FINALIZADO
    assert os_.servicos[-1].descricao == f"{origem.value} → Reparo Finalizado"


def test_dlt06_a_falta_de_intervencao_continua_sendo_verificada_primeiro() -> None:
    m = Mundo()
    os_ = m.atribuida()
    os_.registrar_diagnostico(m.bruno, "p", "c", quando=m.quando())
    recusa(
        os_,
        ViolacaoDeRegraError,
        CodigoErro.SEM_INTERVENCAO,
        lambda: os_.alterar_status(m.bruno, StatusOS.REPARO_FINALIZADO, quando=m.quando()),
    )
    # sem diagnóstico e sem intervenção, a recusa antiga (intervenção) prevalece
    sem_nada = m.atribuida()
    recusa(
        sem_nada,
        ViolacaoDeRegraError,
        CodigoErro.SEM_INTERVENCAO,
        lambda: sem_nada.alterar_status(m.bruno, StatusOS.REPARO_FINALIZADO, quando=m.quando()),
    )


def test_dlt06_o_diagnostico_nao_e_exigido_nas_demais_transicoes() -> None:
    m = Mundo()
    os_ = _com_intervencao_sem_diagnostico(m, StatusOS.EM_EXECUCAO)
    os_.alterar_status(m.bruno, StatusOS.AGUARDANDO_PECA, quando=m.quando())
    os_.alterar_status(m.bruno, StatusOS.EM_EXECUCAO, quando=m.quando())
    assert os_.status is StatusOS.EM_EXECUCAO
    outra = m.atribuida()
    outra.apontar_reparo(m.bruno, 1.0, "Ajuste", [], quando=m.quando())  # Atribuída -> Em Execução
    assert outra.status is StatusOS.EM_EXECUCAO


def test_dlt06_o_fluxo_completo_e_a_volta_do_reparo_finalizado_continuam_validos() -> None:
    m = Mundo()
    os_ = m.reparo_finalizado()
    os_.alterar_status(m.bruno, StatusOS.EM_EXECUCAO, quando=m.quando())  # reabre o reparo
    os_.alterar_status(m.bruno, StatusOS.AGUARDANDO_PECA, quando=m.quando())
    os_.alterar_status(m.bruno, StatusOS.REPARO_FINALIZADO, quando=m.quando())  # já tem diagnóstico
    assert os_.concluir_tecnicamente(m.bruno, "ok", True, quando=m.quando())
    os_.aprovar(m.ana, quando=m.quando())
    assert os_.status is StatusOS.CONCLUIDA
    assert m.concluida().status is StatusOS.CONCLUIDA


# =========================================================================================
# DLT-08 — campos obrigatórios e horas maiores que zero
# =========================================================================================


@pytest.mark.parametrize("falha", ["", " ", "   ", "\t\n"])
def test_dlt08_abrir_com_falha_vazia_ou_so_espacos_e_recusado(falha: str) -> None:
    m = Mundo()
    with pytest.raises(ViolacaoDeRegraError) as erro:
        OrdemServico.abrir(1, m.torno, falha, Criticidade.BAIXA, m.carla, quando=m.quando())
    assert erro.value.codigo is CodigoErro.CAMPO_OBRIGATORIO
    assert erro.value.mensagem == "Campo obrigatório: a descrição da falha."


def test_dlt08_o_texto_valido_e_guardado_exatamente_como_foi_informado() -> None:
    m = Mundo()
    os_ = OrdemServico.abrir(
        1, m.torno, "  Torno parado  ", Criticidade.BAIXA, m.carla, quando=m.quando()
    )
    assert os_.falha == "  Torno parado  "
    assert os_.servicos[0].descricao == "[Baixa]   Torno parado  "


@pytest.mark.parametrize(
    ("parecer", "causa"), [("", "c"), ("p", ""), ("   ", "c"), ("p", "  "), ("", "")]
)
def test_dlt08_diagnostico_com_campo_vazio_e_recusado_sem_alterar_a_os(
    parecer: str, causa: str
) -> None:
    m = Mundo()
    os_ = m.atribuida()
    recusa(
        os_,
        ViolacaoDeRegraError,
        CodigoErro.CAMPO_OBRIGATORIO,
        lambda: os_.registrar_diagnostico(m.bruno, parecer, causa, quando=m.quando()),
    )
    assert os_.diagnostico == ""


@pytest.mark.parametrize("horas", [0, 0.0, -0.0])
def test_dlt08_apontamento_com_zero_hora_e_recusado_e_a_os_continua_atribuida(
    horas: float,
) -> None:
    m = Mundo()
    os_ = m.atribuida()
    erro = recusa(
        os_,
        ViolacaoDeRegraError,
        CodigoErro.HORAS_NAO_POSITIVAS,
        lambda: os_.apontar_reparo(m.bruno, horas, "Ajuste", [], quando=m.quando()),
    )
    assert erro.mensagem == "As horas trabalhadas devem ser maiores que zero."
    assert os_.status is StatusOS.ATRIBUIDA  # a recusa não dispara Atribuída -> Em Execução


@pytest.mark.parametrize("horas", [math.nan, math.inf, -math.inf])
def test_dlt08_horas_nao_numericas_ou_infinitas_sao_recusadas(horas: float) -> None:
    m = Mundo()
    os_ = m.atribuida()
    esperado = CodigoErro.HORAS_NEGATIVAS if horas < 0 else CodigoErro.HORAS_NAO_POSITIVAS
    recusa(
        os_,
        ViolacaoDeRegraError,
        esperado,
        lambda: os_.apontar_reparo(m.bruno, horas, "Ajuste", [], quando=m.quando()),
    )


def test_dlt08_horas_negativas_continuam_com_a_recusa_e_a_mensagem_do_legado() -> None:
    m = Mundo()
    os_ = m.atribuida()
    erro = recusa(
        os_,
        ViolacaoDeRegraError,
        CodigoErro.HORAS_NEGATIVAS,
        lambda: os_.apontar_reparo(m.bruno, -1.0, "Ajuste", [], quando=m.quando()),
    )
    assert erro.mensagem == "Horas trabalhadas não podem ser negativas."


@pytest.mark.parametrize("intervencao", ["", "   "])
def test_dlt08_apontamento_com_intervencao_vazia_e_recusado(intervencao: str) -> None:
    m = Mundo()
    os_ = m.atribuida()
    recusa(
        os_,
        ViolacaoDeRegraError,
        CodigoErro.CAMPO_OBRIGATORIO,
        lambda: os_.apontar_reparo(m.bruno, 1.0, intervencao, [], quando=m.quando()),
    )
    assert (os_.horas_trabalhadas, os_.intervencoes_realizadas) == (0.0, ())


@pytest.mark.parametrize("quantidade", [0, -1, -0.5])
def test_dlt08_a_quantidade_de_peca_positiva_e_preservada(quantidade: float) -> None:
    with pytest.raises(ViolacaoDeRegraError) as erro:
        PecaMaterial("Rolamento", quantidade)
    assert erro.value.codigo is CodigoErro.QUANTIDADE_INVALIDA
    assert PecaMaterial("Rolamento", 0.25).quantidade == 0.25


def test_dlt08_motivos_de_reprovacao_e_de_cancelamento_vazios_sao_recusados() -> None:
    m = Mundo()
    aguardando = m.aguardando_aprovacao()
    recusa(
        aguardando,
        ViolacaoDeRegraError,
        CodigoErro.CAMPO_OBRIGATORIO,
        lambda: aguardando.reprovar(m.ana, "  ", quando=m.quando()),
    )
    ativa = m.atribuida()
    recusa(
        ativa,
        ViolacaoDeRegraError,
        CodigoErro.CAMPO_OBRIGATORIO,
        lambda: ativa.cancelar(m.ana, "", quando=m.quando()),
    )
    assert (ativa.status, ativa.motivo_cancelamento, ativa.data_conclusao) == (
        StatusOS.ATRIBUIDA,
        "",
        None,
    )


def test_dlt08_a_autorizacao_e_a_regra_de_estado_vem_antes_da_validacao() -> None:
    m = Mundo()
    os_ = m.atribuida()
    recusa(
        os_,
        PermissaoNegadaError,
        CodigoErro.NAO_RESPONSAVEL,
        lambda: os_.apontar_reparo(m.carla, 0, "", [], quando=m.quando()),
    )
    encerrada = m.concluida()
    recusa(
        encerrada,
        ConflitoDeEstadoError,
        CodigoErro.OS_ENCERRADA,
        lambda: encerrada.cancelar(m.ana, "", quando=m.quando()),
    )
    sem_acesso = Usuario(9, "Visitante", m.tecnico, papel=Papel.TECNICO)
    m.tecnico.permissoes.definir([])
    with pytest.raises(PermissaoNegadaError) as erro:  # a permissão vence a validação (abrir)
        OrdemServico.abrir(9, m.torno, "", Criticidade.BAIXA, sem_acesso, quando=m.quando())
    assert erro.value.codigo is CodigoErro.SEM_PERMISSAO


# =========================================================================================
# DLT-09 — usuário ativo ou inativo
# =========================================================================================


def test_dlt09_o_usuario_nasce_ativo_e_pode_ser_desativado_e_reativado() -> None:
    m = Mundo()
    assert m.bruno.ativo is True
    m.bruno.desativar()
    assert (m.bruno.ativo, m.bruno.e_tecnico, m.bruno.atribuivel) == (False, True, False)
    m.bruno.reativar()
    assert (m.bruno.ativo, m.bruno.atribuivel) == (True, True)


def test_dlt09_usuario_inativo_nao_opera_nenhuma_operacao_da_os() -> None:
    m = Mundo()
    atribuida = m.atribuida()  # de Bruno
    execucao = m.em_execucao()
    finalizada = m.reparo_finalizado()
    aprovacao = m.aguardando_aprovacao()
    m.bruno.desativar()
    m.ana.desativar()
    m.carla.desativar()
    operacoes: tuple[tuple[OrdemServico, Chamada], ...] = (
        (
            atribuida,
            lambda: OrdemServico.abrir(
                9, m.torno, "Falha", Criticidade.BAIXA, m.carla, quando=m.quando()
            ),
        ),
        (atribuida, lambda: atribuida.adicionar_apontamento(m.ana, "x", quando=m.quando())),
        (atribuida, lambda: atribuida.adicionar_apontamento(m.carla, "x", quando=m.quando())),
        (atribuida, lambda: atribuida.registrar_diagnostico(m.bruno, "p", "c", quando=m.quando())),
        (atribuida, lambda: atribuida.apontar_reparo(m.bruno, 1.0, "i", [], quando=m.quando())),
        (
            execucao,
            lambda: execucao.alterar_status(m.bruno, StatusOS.AGUARDANDO_PECA, quando=m.quando()),
        ),
        (
            finalizada,
            lambda: finalizada.concluir_tecnicamente(m.bruno, "t", True, quando=m.quando()),
        ),
        (atribuida, lambda: atribuida.atribuir(m.carla, m.ana, quando=m.quando())),
        (aprovacao, lambda: aprovacao.aprovar(m.ana, quando=m.quando())),
        (aprovacao, lambda: aprovacao.reprovar(m.ana, "x", quando=m.quando())),
        (atribuida, lambda: atribuida.cancelar(m.ana, "x", quando=m.quando())),
    )
    for os_, chamada in operacoes:
        recusa(os_, PermissaoNegadaError, CodigoErro.USUARIO_INATIVO, chamada)


def test_dlt09_usuario_inativo_nao_tem_permissao_efetiva() -> None:
    m = Mundo()
    assert m.bruno.pode(Permissao.VER_OS)
    m.bruno.desativar()
    assert not any(m.bruno.pode(p) for p in Permissao)
    with pytest.raises(PermissaoNegadaError) as erro:
        m.bruno.exigir(Permissao.VER_OS)
    assert erro.value.codigo is CodigoErro.USUARIO_INATIVO
    assert erro.value.mensagem == "Bruno Lima está inativo e não pode operar."


def test_dlt09_tecnico_inativo_nao_e_atribuivel() -> None:
    m = Mundo()
    os_ = m.aberta()
    m.bruno.desativar()
    erro = recusa(
        os_,
        ViolacaoDeRegraError,
        CodigoErro.USUARIO_INATIVO,
        lambda: os_.atribuir(m.bruno, m.ana, quando=m.quando(), confirmar_ausente=True),
    )
    assert erro.mensagem == "Bruno Lima está inativo e não pode receber OS."
    m.bruno.reativar()
    os_.atribuir(m.bruno, m.ana, quando=m.quando())
    assert os_.tecnico_atribuido == m.bruno


def test_dlt09_o_historico_preserva_a_referencia_a_quem_foi_desativado() -> None:
    m = Mundo()
    os_ = m.em_execucao()
    m.bruno.desativar()
    assert os_.tecnico_atribuido == m.bruno  # sem reatribuição automática
    assert os_.status is StatusOS.EM_EXECUCAO
    assert {s.responsavel for s in os_.servicos if s.responsavel} == {m.carla, m.ana, m.bruno}
    assert os_.servicos[-1].responsavel.nome == "Bruno Lima"  # type: ignore[union-attr]


def test_dlt09_a_desativacao_nao_destitui_o_papel_nem_muda_as_permissoes_do_cargo() -> None:
    m = Mundo()
    m.bruno.desativar()
    assert m.bruno.papel is Papel.TECNICO
    assert m.tecnico.permissoes.tem(Permissao.APONTAR_REPARO)
