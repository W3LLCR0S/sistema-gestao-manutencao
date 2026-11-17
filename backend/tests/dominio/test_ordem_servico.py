"""C4: a entidade OrdemServico reproduz as regras do legado (``models/ordem_servico.py``).

Cada teste escreve a expectativa **por extenso**, a partir do comportamento caracterizado na
Operação B (``tests/caracterizacao``): nada é derivado do código novo. As mudanças funcionais
aprovadas e ainda não aplicadas (D-02 a D-06, validações, usuário ativo, IDs) não são exercitadas
aqui; onde o legado tem um comportamento que elas mudarão, o teste diz isso.
"""

import inspect
from collections.abc import Callable
from dataclasses import FrozenInstanceError
from datetime import datetime

import pytest

from manutencao.domain.enums import Criticidade, StatusOS, TipoServico
from manutencao.domain.equipamento import Equipamento
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
from tests.dominio.fabrica import Mundo, instantaneo, sem_acesso

S = StatusOS
T = TipoServico
Chamada = Callable[[], object]

TODOS_OS_STATUS = tuple(StatusOS)
STATUS_NAO_FINAIS = tuple(s for s in TODOS_OS_STATUS if s not in (S.CONCLUIDA, S.CANCELADA))

# Escritos por extenso (não importados de ``transicoes``), como o legado os define.
TECNICO_DEFINE = frozenset({S.EM_EXECUCAO, S.AGUARDANDO_PECA, S.REPARO_FINALIZADO})
TECNICO_MUDA_A_PARTIR_DE = frozenset(
    {S.ATRIBUIDA, S.EM_EXECUCAO, S.AGUARDANDO_PECA, S.REPARO_FINALIZADO}
)
TECNICO_ATENDE = (S.ATRIBUIDA, S.EM_EXECUCAO, S.AGUARDANDO_PECA)


def recusa(
    os_: OrdemServico, erro: type[DominioError], codigo: CodigoErro, chamada: Chamada
) -> None:
    """A chamada é recusada com a classe e o código esperados, sem alterar nada na OS."""
    antes = instantaneo(os_)
    with pytest.raises(erro) as capturado:
        chamada()
    assert capturado.value.codigo is codigo
    assert instantaneo(os_) == antes


def origem(m: Mundo, status: StatusOS) -> OrdemServico:
    """Uma OS em ``status`` com o técnico Bruno como responsável sempre que possível."""
    if status is S.CANCELADA:
        return m.cancelada(atribuida=True)
    return m.em_status(status)


def tipos(os_: OrdemServico) -> list[TipoServico]:
    return [s.tipo for s in os_.servicos]


# =========================================================================== abertura


def test_abrir_cria_os_aberta_com_o_registro_de_abertura() -> None:
    m = Mundo()
    instante = m.quando()
    os_ = OrdemServico.abrir(7, m.torno, "Barulho", Criticidade.CRITICA, m.carla, quando=instante)
    assert (os_.numero, os_.status, os_.equipamento, os_.falha) == (7, S.ABERTA, m.torno, "Barulho")
    assert (os_.criticidade, os_.aberta_por, os_.data_abertura) == (
        Criticidade.CRITICA,
        m.carla,
        instante,
    )
    assert os_.tecnico_atribuido is None
    assert (os_.diagnostico, os_.causa_raiz, os_.teste_funcional) == ("", "", "")
    assert (os_.horas_trabalhadas, os_.intervencoes_realizadas, os_.pecas_utilizadas) == (
        0.0,
        (),
        (),
    )
    assert (os_.data_conclusao, os_.motivo_cancelamento, os_.encerrada) == (None, "", False)
    (abertura,) = os_.servicos
    assert (abertura.numero, abertura.tipo, abertura.responsavel) == (1, T.ABERTURA, m.carla)
    assert (abertura.descricao, abertura.data) == ("[Crítica] Barulho", instante)


@pytest.mark.parametrize("criticidade", list(Criticidade))
def test_abrir_aceita_todas_as_criticidades(criticidade: Criticidade) -> None:
    m = Mundo()
    os_ = OrdemServico.abrir(1, m.torno, "Falha", criticidade, m.bruno, quando=m.quando())
    assert os_.servicos[0].descricao == f"[{criticidade.value}] Falha"


@pytest.mark.parametrize("quem", ["gestor", "tecnico"])
def test_qualquer_perfil_com_abrir_os_abre(quem: str) -> None:
    m = Mundo()
    usuario = m.ana if quem == "gestor" else m.bruno
    os_ = OrdemServico.abrir(1, m.torno, "Falha", Criticidade.BAIXA, usuario, quando=m.quando())
    assert os_.aberta_por == usuario


def test_abrir_sem_permissao_e_recusado() -> None:
    m = Mundo()
    with pytest.raises(PermissaoNegadaError) as capturado:
        OrdemServico.abrir(1, m.torno, "Falha", Criticidade.BAIXA, sem_acesso(), quando=m.quando())
    assert capturado.value.codigo is CodigoErro.SEM_PERMISSAO
    assert capturado.value.mensagem == "Sem permissão: Abrir chamados (OS)."


def test_abrir_para_equipamento_inativo_e_recusado() -> None:
    m = Mundo()
    m.torno.inativar()
    with pytest.raises(ViolacaoDeRegraError) as capturado:
        OrdemServico.abrir(1, m.torno, "Falha", Criticidade.ALTA, m.carla, quando=m.quando())
    assert capturado.value.codigo is CodigoErro.EQUIPAMENTO_INATIVO
    assert capturado.value.mensagem == "Não é possível abrir OS para equipamento inativo."


def test_na_abertura_a_permissao_vem_antes_do_equipamento_inativo() -> None:
    m = Mundo()
    m.torno.inativar()
    with pytest.raises(PermissaoNegadaError):
        OrdemServico.abrir(1, m.torno, "Falha", Criticidade.ALTA, sem_acesso(), quando=m.quando())


def test_a_identidade_da_os_e_o_numero() -> None:
    m = Mundo()
    a, outra_a, b = m.aberta(1), m.aberta(1), m.aberta(2)
    assert a == outra_a
    assert hash(a) == hash(outra_a)
    assert a != b
    assert a != "1"


# =========================================================================== ciclo completo


def test_ciclo_completo_gera_onze_registros_na_ordem_esperada() -> None:
    m = Mundo()
    os_ = m.concluida()
    assert os_.status is S.CONCLUIDA
    assert [(s.numero, s.tipo, s.responsavel) for s in os_.servicos] == [
        (1, T.ABERTURA, m.carla),
        (2, T.ATRIBUICAO, m.ana),
        (3, T.MUDANCA_STATUS, m.ana),
        (4, T.DIAGNOSTICO, m.bruno),
        (5, T.MUDANCA_STATUS, m.bruno),
        (6, T.REPARO, m.bruno),
        (7, T.MUDANCA_STATUS, m.bruno),
        (8, T.CONCLUSAO_TECNICA, m.bruno),
        (9, T.MUDANCA_STATUS, m.bruno),
        (10, T.ENCERRAMENTO, m.ana),
        (11, T.MUDANCA_STATUS, m.ana),
    ]
    assert [s.descricao for s in os_.servicos] == [
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
    assert os_.tecnico_atribuido == m.bruno
    assert os_.data_conclusao is not None
    assert os_.encerrada


def test_status_percorre_as_etapas_do_fluxo_feliz() -> None:
    m = Mundo()
    os_ = m.aberta()
    percurso = [os_.status]
    os_.atribuir(m.bruno, m.ana, quando=m.quando())
    percurso.append(os_.status)
    os_.registrar_diagnostico(m.bruno, "p", "c", quando=m.quando())
    percurso.append(os_.status)  # o diagnóstico não muda o status
    os_.apontar_reparo(m.bruno, 1, "i", [], quando=m.quando())
    percurso.append(os_.status)
    os_.alterar_status(m.bruno, S.AGUARDANDO_PECA, quando=m.quando())
    percurso.append(os_.status)
    os_.alterar_status(m.bruno, S.EM_EXECUCAO, quando=m.quando())
    percurso.append(os_.status)
    os_.alterar_status(m.bruno, S.REPARO_FINALIZADO, quando=m.quando())
    percurso.append(os_.status)
    os_.concluir_tecnicamente(m.bruno, "ok", True, quando=m.quando())
    percurso.append(os_.status)
    os_.aprovar(m.ana, quando=m.quando())
    percurso.append(os_.status)
    assert percurso == [
        S.ABERTA,
        S.ATRIBUIDA,
        S.ATRIBUIDA,
        S.EM_EXECUCAO,
        S.AGUARDANDO_PECA,
        S.EM_EXECUCAO,
        S.REPARO_FINALIZADO,
        S.AGUARDANDO_APROVACAO,
        S.CONCLUIDA,
    ]


# =========================================================================== matriz 8x8


def esperado_do_tecnico(origem_: StatusOS, destino: StatusOS) -> CodigoErro | None:
    """Resultado de ``alterar_status`` do Bruno, na ordem de verificação do legado."""
    if origem_ is S.ABERTA:
        return CodigoErro.NAO_RESPONSAVEL  # nenhum técnico atribuído ainda
    if origem_ not in TECNICO_MUDA_A_PARTIR_DE:
        return CodigoErro.ESTADO_INVALIDO
    if destino not in TECNICO_DEFINE:
        return CodigoErro.STATUS_NAO_PERMITIDO
    if destino is origem_:
        return CodigoErro.JA_NESSE_STATUS
    if destino is S.REPARO_FINALIZADO and origem_ is S.ATRIBUIDA:
        return CodigoErro.SEM_INTERVENCAO  # em Atribuída ainda não há intervenção
    return None


@pytest.mark.parametrize("destino", TODOS_OS_STATUS)
@pytest.mark.parametrize("origem_", TODOS_OS_STATUS)
def test_matriz_8x8_do_tecnico(origem_: StatusOS, destino: StatusOS) -> None:
    m = Mundo()
    os_ = origem(m, origem_)
    esperado = esperado_do_tecnico(origem_, destino)

    def chamada() -> None:
        os_.alterar_status(m.bruno, destino, quando=m.quando())

    if esperado is None:
        chamada()
        assert os_.status is destino
        assert os_.servicos[-1].tipo is T.MUDANCA_STATUS
        assert os_.servicos[-1].descricao == f"{origem_.value} → {destino.value}"
    else:
        erro = (
            PermissaoNegadaError
            if esperado is CodigoErro.NAO_RESPONSAVEL
            else ViolacaoDeRegraError
            if esperado
            in (
                CodigoErro.STATUS_NAO_PERMITIDO,
                CodigoErro.SEM_INTERVENCAO,
            )
            else ConflitoDeEstadoError
        )
        recusa(os_, erro, esperado, chamada)


def test_todo_destino_alcancavel_por_alguma_operacao_esta_na_tabela() -> None:
    """Todas as operações em todos os estados: as mudanças de status são as do legado."""
    observadas: set[tuple[StatusOS, StatusOS]] = set()
    for origem_ in TODOS_OS_STATUS:
        m = Mundo()
        operacoes: list[Callable[[Mundo, OrdemServico], object]] = [
            lambda m, o: o.atribuir(m.carla, m.ana, quando=m.quando()),
            lambda m, o: o.apontar_reparo(m.bruno, 1, "i", [], quando=m.quando()),
            lambda m, o: o.concluir_tecnicamente(m.bruno, "t", True, quando=m.quando()),
            lambda m, o: o.aprovar(m.ana, quando=m.quando()),
            lambda m, o: o.reprovar(m.ana, "r", quando=m.quando()),
            lambda m, o: o.cancelar(m.ana, "c", quando=m.quando()),
            *(
                (lambda m, o, d=d: o.alterar_status(m.bruno, d, quando=m.quando()))
                for d in TODOS_OS_STATUS
            ),
        ]
        for operacao in operacoes:
            os_ = origem(m, origem_)
            try:
                operacao(m, os_)
            except DominioError:
                continue
            if os_.status is not origem_:
                observadas.add((origem_, os_.status))
    esperadas = {
        (S.ABERTA, S.ATRIBUIDA),
        (S.ATRIBUIDA, S.EM_EXECUCAO),
        (S.ATRIBUIDA, S.AGUARDANDO_PECA),
        (S.EM_EXECUCAO, S.AGUARDANDO_PECA),
        (S.EM_EXECUCAO, S.REPARO_FINALIZADO),
        (S.AGUARDANDO_PECA, S.EM_EXECUCAO),
        (S.AGUARDANDO_PECA, S.REPARO_FINALIZADO),
        (S.REPARO_FINALIZADO, S.EM_EXECUCAO),
        (S.REPARO_FINALIZADO, S.AGUARDANDO_PECA),
        (S.REPARO_FINALIZADO, S.AGUARDANDO_APROVACAO),
        (S.AGUARDANDO_APROVACAO, S.CONCLUIDA),
        (S.AGUARDANDO_APROVACAO, S.EM_EXECUCAO),
        *((o, S.CANCELADA) for o in STATUS_NAO_FINAIS),
    }
    assert observadas == esperadas


# =========================================================================== atribuição


def test_atribuicao_inicial_leva_a_atribuida_e_devolve_none() -> None:
    m = Mundo()
    os_ = m.aberta()
    anterior = os_.atribuir(m.bruno, m.ana, quando=m.quando())
    assert anterior is None
    assert (os_.status, os_.tecnico_atribuido) == (S.ATRIBUIDA, m.bruno)
    assert tipos(os_) == [T.ABERTURA, T.ATRIBUICAO, T.MUDANCA_STATUS]
    assert os_.servicos[1].descricao == "Atribuída a Bruno Lima"
    assert os_.servicos[1].responsavel == m.ana
    assert os_.esta_com(m.bruno)
    assert not os_.esta_com(m.carla)


def test_reatribuicao_troca_o_tecnico_e_preserva_o_trabalho_feito() -> None:
    m = Mundo()
    os_ = m.em_execucao()
    horas, intervencoes, pecas = (
        os_.horas_trabalhadas,
        os_.intervencoes_realizadas,
        os_.pecas_utilizadas,
    )
    quantidade = len(os_.servicos)
    anterior = os_.atribuir(m.carla, m.ana, quando=m.quando())
    assert anterior == m.bruno
    assert (os_.tecnico_atribuido, os_.status) == (m.carla, S.EM_EXECUCAO)
    assert len(os_.servicos) == quantidade + 1  # só um registro, sem mudança de status
    assert os_.servicos[-1].tipo is T.REATRIBUICAO
    assert os_.servicos[-1].descricao == "Bruno Lima → Carla Mendes"
    assert os_.servicos[-1].responsavel == m.ana
    assert (os_.horas_trabalhadas, os_.intervencoes_realizadas, os_.pecas_utilizadas) == (
        horas,
        intervencoes,
        pecas,
    )


def test_reatribuir_em_atribuida_nao_muda_o_status() -> None:
    m = Mundo()
    os_ = m.atribuida()
    os_.atribuir(m.carla, m.ana, quando=m.quando())
    assert os_.status is S.ATRIBUIDA
    assert tipos(os_)[-1] is T.REATRIBUICAO


def test_o_tecnico_anterior_perde_o_acesso_as_operacoes_tecnicas() -> None:
    m = Mundo()
    os_ = m.atribuida()
    os_.atribuir(m.carla, m.ana, quando=m.quando())
    recusa(
        os_,
        PermissaoNegadaError,
        CodigoErro.NAO_RESPONSAVEL,
        lambda: os_.registrar_diagnostico(m.bruno, "p", "c", quando=m.quando()),
    )
    os_.registrar_diagnostico(m.carla, "p", "c", quando=m.quando())


def test_atribuir_ao_mesmo_tecnico_e_recusado() -> None:
    m = Mundo()
    os_ = m.atribuida()
    recusa(
        os_,
        ConflitoDeEstadoError,
        CodigoErro.JA_ATRIBUIDA,
        lambda: os_.atribuir(m.bruno, m.ana, quando=m.quando()),
    )


def test_atribuir_a_quem_nao_e_tecnico_e_recusado() -> None:
    m = Mundo()
    os_ = m.aberta()
    with pytest.raises(ViolacaoDeRegraError) as capturado:
        os_.atribuir(m.ana, m.ana, quando=m.quando())
    assert capturado.value.codigo is CodigoErro.NAO_E_TECNICO
    assert capturado.value.mensagem == "Ana Souza não é técnico."
    assert os_.status is S.ABERTA
    assert os_.tecnico_atribuido is None


def test_atribuir_exige_a_permissao_atribuir_os() -> None:
    m = Mundo()
    os_ = m.aberta()
    recusa(
        os_,
        PermissaoNegadaError,
        CodigoErro.SEM_PERMISSAO,
        lambda: os_.atribuir(m.bruno, m.carla, quando=m.quando()),
    )


@pytest.mark.parametrize(
    "status",
    [S.ABERTA, S.ATRIBUIDA, S.EM_EXECUCAO, S.AGUARDANDO_PECA, S.REPARO_FINALIZADO],
)
def test_estados_que_permitem_atribuir_e_reatribuir(status: StatusOS) -> None:
    m = Mundo()
    os_ = origem(m, status)
    os_.atribuir(m.carla, m.ana, quando=m.quando())
    assert os_.tecnico_atribuido == m.carla


@pytest.mark.parametrize("status", [S.AGUARDANDO_APROVACAO, S.CONCLUIDA, S.CANCELADA])
def test_estados_que_impedem_atribuir(status: StatusOS) -> None:
    m = Mundo()
    os_ = origem(m, status)
    with pytest.raises(ConflitoDeEstadoError) as capturado:
        os_.atribuir(m.carla, m.ana, quando=m.quando())
    assert capturado.value.codigo is CodigoErro.ESTADO_INVALIDO
    assert capturado.value.mensagem == f"Não é possível atribuir uma OS em '{status.value}'."


# =========================================================================== diagnóstico


def test_diagnostico_registra_parecer_e_causa_sem_mudar_o_status() -> None:
    m = Mundo()
    os_ = m.atribuida()
    instante = m.quando()
    os_.registrar_diagnostico(m.bruno, "Rolamento gasto", "Falta de graxa", quando=instante)
    assert (os_.diagnostico, os_.causa_raiz, os_.status) == (
        "Rolamento gasto",
        "Falta de graxa",
        S.ATRIBUIDA,
    )
    registro = os_.servicos[-1]
    assert (registro.tipo, registro.responsavel, registro.data) == (
        T.DIAGNOSTICO,
        m.bruno,
        instante,
    )
    assert registro.descricao == "Rolamento gasto | Causa-raiz: Falta de graxa"


def test_um_novo_diagnostico_substitui_o_anterior_e_acumula_historico() -> None:
    m = Mundo()
    os_ = m.atribuida()
    os_.registrar_diagnostico(m.bruno, "A", "x", quando=m.quando())
    os_.registrar_diagnostico(m.bruno, "B", "y", quando=m.quando())
    assert (os_.diagnostico, os_.causa_raiz) == ("B", "y")
    assert tipos(os_).count(T.DIAGNOSTICO) == 2


@pytest.mark.parametrize("status", TECNICO_ATENDE)
def test_diagnostico_e_aceito_nos_estados_de_atendimento(status: StatusOS) -> None:
    m = Mundo()
    origem(m, status).registrar_diagnostico(m.bruno, "p", "c", quando=m.quando())


@pytest.mark.parametrize(
    "status", [S.REPARO_FINALIZADO, S.AGUARDANDO_APROVACAO, S.CONCLUIDA, S.CANCELADA]
)
def test_diagnostico_e_recusado_fora_do_atendimento(status: StatusOS) -> None:
    m = Mundo()
    os_ = origem(m, status)
    recusa(
        os_,
        ConflitoDeEstadoError,
        CodigoErro.ESTADO_INVALIDO,
        lambda: os_.registrar_diagnostico(m.bruno, "p", "c", quando=m.quando()),
    )


def test_diagnostico_exige_ser_o_tecnico_responsavel() -> None:
    m = Mundo()
    os_ = m.atribuida()
    recusa(
        os_,
        PermissaoNegadaError,
        CodigoErro.NAO_RESPONSAVEL,
        lambda: os_.registrar_diagnostico(m.carla, "p", "c", quando=m.quando()),
    )
    recusa(
        os_,
        PermissaoNegadaError,
        CodigoErro.SEM_PERMISSAO,
        lambda: os_.registrar_diagnostico(m.ana, "p", "c", quando=m.quando()),
    )


# =========================================================================== reparos e peças


def test_reparo_em_atribuida_inicia_a_execucao_e_registra_a_mudanca_antes_do_reparo() -> None:
    m = Mundo()
    os_ = m.atribuida()
    instante = m.quando()
    pecas = [PecaMaterial("Rolamento", 2), PecaMaterial("Graxa", 0.5)]
    os_.apontar_reparo(m.bruno, 1.5, "Troca", pecas, quando=instante)
    assert os_.status is S.EM_EXECUCAO
    assert tipos(os_)[-2:] == [T.MUDANCA_STATUS, T.REPARO]
    assert os_.servicos[-2].descricao == "Atribuída → Em Execução"
    reparo = os_.servicos[-1]
    assert (reparo.descricao, reparo.horas, reparo.responsavel) == ("Troca", 1.5, m.bruno)
    assert reparo.pecas == tuple(pecas)
    assert (os_.horas_trabalhadas, os_.intervencoes_realizadas) == (1.5, ("Troca",))
    assert os_.pecas_utilizadas == tuple(pecas)


def test_reparos_acumulam_horas_intervencoes_e_pecas() -> None:
    m = Mundo()
    os_ = m.em_execucao()  # já tem 1,5 h e uma peça
    os_.apontar_reparo(m.bruno, 2, "Ajuste", [PecaMaterial("Correia", 1)], quando=m.quando())
    assert os_.horas_trabalhadas == 3.5
    assert os_.intervencoes_realizadas == ("Troca do rolamento", "Ajuste")
    assert [p.descricao for p in os_.pecas_utilizadas] == ["Rolamento", "Correia"]
    assert os_.status is S.EM_EXECUCAO  # sem nova mudança de status
    assert tipos(os_).count(T.REPARO) == 2


def test_reparo_em_aguardando_peca_mantem_o_status() -> None:
    m = Mundo()
    os_ = m.aguardando_peca()
    os_.apontar_reparo(m.bruno, 1, "Ajuste", [], quando=m.quando())
    assert os_.status is S.AGUARDANDO_PECA
    assert tipos(os_)[-1] is T.REPARO


def test_reparo_sem_pecas_e_com_zero_hora_e_aceito_como_no_legado() -> None:
    # Comportamento do legado (CAR-80); a validação obrigatória é o DLT-08 (Operação E).
    m = Mundo()
    os_ = m.atribuida()
    os_.apontar_reparo(m.bruno, 0, "", [], quando=m.quando())
    assert (os_.horas_trabalhadas, os_.intervencoes_realizadas, os_.pecas_utilizadas) == (
        0.0,
        ("",),
        (),
    )


def test_a_os_nao_compartilha_a_lista_de_pecas_recebida() -> None:
    m = Mundo()
    os_ = m.atribuida()
    pecas = [PecaMaterial("Rolamento", 2)]
    os_.apontar_reparo(m.bruno, 1, "Troca", pecas, quando=m.quando())
    pecas.append(PecaMaterial("Intrusa", 1))
    assert [p.descricao for p in os_.pecas_utilizadas] == ["Rolamento"]
    assert [p.descricao for p in os_.servicos[-1].pecas] == ["Rolamento"]


def test_horas_negativas_sao_recusadas_sem_iniciar_a_execucao() -> None:
    m = Mundo()
    os_ = m.atribuida()
    with pytest.raises(ViolacaoDeRegraError) as capturado:
        os_.apontar_reparo(m.bruno, -0.5, "Troca", [], quando=m.quando())
    assert capturado.value.codigo is CodigoErro.HORAS_NEGATIVAS
    assert capturado.value.mensagem == "Horas trabalhadas não podem ser negativas."
    assert os_.status is S.ATRIBUIDA  # a mudança de status não ficou pela metade
    assert tipos(os_) == [T.ABERTURA, T.ATRIBUICAO, T.MUDANCA_STATUS]


def test_reparo_recusado_por_estado_responsavel_e_permissao() -> None:
    m = Mundo()
    finalizada = m.reparo_finalizado()
    recusa(
        finalizada,
        ConflitoDeEstadoError,
        CodigoErro.ESTADO_INVALIDO,
        lambda: finalizada.apontar_reparo(m.bruno, 1, "x", [], quando=m.quando()),
    )
    atribuida = m.atribuida()
    recusa(
        atribuida,
        PermissaoNegadaError,
        CodigoErro.NAO_RESPONSAVEL,
        lambda: atribuida.apontar_reparo(m.carla, 1, "x", [], quando=m.quando()),
    )
    recusa(
        atribuida,
        PermissaoNegadaError,
        CodigoErro.SEM_PERMISSAO,
        lambda: atribuida.apontar_reparo(m.ana, 1, "x", [], quando=m.quando()),
    )


# =========================================================================== status do técnico


def test_reparo_finalizado_exige_ao_menos_uma_intervencao() -> None:
    m = Mundo()
    os_ = m.atribuida()
    with pytest.raises(ViolacaoDeRegraError) as capturado:
        os_.alterar_status(m.bruno, S.REPARO_FINALIZADO, quando=m.quando())
    assert capturado.value.codigo is CodigoErro.SEM_INTERVENCAO
    assert (
        capturado.value.mensagem == "Registre ao menos uma intervenção antes de finalizar o reparo."
    )
    assert os_.status is S.ATRIBUIDA


def test_o_tecnico_nao_define_os_status_de_gestao() -> None:
    m = Mundo()
    os_ = m.em_execucao()
    for proibido in (S.ABERTA, S.ATRIBUIDA, S.AGUARDANDO_APROVACAO, S.CONCLUIDA, S.CANCELADA):
        recusa(
            os_,
            ViolacaoDeRegraError,
            CodigoErro.STATUS_NAO_PERMITIDO,
            lambda proibido=proibido: os_.alterar_status(m.bruno, proibido, quando=m.quando()),  # type: ignore[misc]
        )


def test_o_tecnico_reabre_o_reparo_finalizado() -> None:
    m = Mundo()
    os_ = m.reparo_finalizado()
    os_.alterar_status(m.bruno, S.EM_EXECUCAO, quando=m.quando())
    assert os_.status is S.EM_EXECUCAO
    assert os_.servicos[-1].descricao == "Reparo Finalizado → Em Execução"


def test_alterar_status_exige_a_permissao_atualizar_status() -> None:
    m = Mundo()
    os_ = m.em_execucao()
    recusa(
        os_,
        PermissaoNegadaError,
        CodigoErro.SEM_PERMISSAO,
        lambda: os_.alterar_status(m.ana, S.AGUARDANDO_PECA, quando=m.quando()),
    )


# =========================================================================== conclusão técnica


def test_conclusao_com_teste_aprovado_submete_a_os_para_aprovacao() -> None:
    m = Mundo()
    os_ = m.reparo_finalizado()
    assert os_.concluir_tecnicamente(m.bruno, "Sob carga", True, quando=m.quando()) is True
    assert (os_.status, os_.teste_funcional) == (S.AGUARDANDO_APROVACAO, "Sob carga")
    assert tipos(os_)[-2:] == [T.CONCLUSAO_TECNICA, T.MUDANCA_STATUS]
    assert os_.servicos[-2].descricao == "Teste aprovado: Sob carga"
    assert os_.servicos[-1].descricao == "Reparo Finalizado → Aguardando Aprovação"


def test_conclusao_com_teste_reprovado_so_registra_o_teste() -> None:
    m = Mundo()
    os_ = m.reparo_finalizado()
    quantidade = len(os_.servicos)
    assert os_.concluir_tecnicamente(m.bruno, "Vibrou", False, quando=m.quando()) is False
    assert os_.status is S.REPARO_FINALIZADO
    assert os_.teste_funcional == ""  # só o teste aprovado é guardado
    assert len(os_.servicos) == quantidade + 1
    assert os_.servicos[-1].tipo is T.TESTE_FUNCIONAL
    assert os_.servicos[-1].descricao == "Reprovado: Vibrou"


def test_conclusao_sem_diagnostico_e_recusada_mesmo_com_teste_reprovado() -> None:
    m = Mundo()
    for passou in (True, False):
        os_ = m.reparo_finalizado(com_diagnostico=False)
        with pytest.raises(ViolacaoDeRegraError) as capturado:
            os_.concluir_tecnicamente(m.bruno, "t", passou, quando=m.quando())
        assert capturado.value.codigo is CodigoErro.SEM_DIAGNOSTICO
        assert capturado.value.mensagem == "Registre o diagnóstico antes de concluir."
        assert os_.status is S.REPARO_FINALIZADO


@pytest.mark.parametrize("status", [s for s in TODOS_OS_STATUS if s is not S.REPARO_FINALIZADO])
def test_conclusao_exige_reparo_finalizado(status: StatusOS) -> None:
    m = Mundo()
    os_ = origem(m, status)
    # Em Aberta não há responsável: a recusa muda de causa, não de classe de erro.
    codigo = CodigoErro.NAO_RESPONSAVEL if status is S.ABERTA else CodigoErro.ESTADO_INVALIDO
    erro = PermissaoNegadaError if status is S.ABERTA else ConflitoDeEstadoError
    recusa(
        os_,
        erro,
        codigo,
        lambda: os_.concluir_tecnicamente(m.bruno, "t", True, quando=m.quando()),
    )


def test_conclusao_exige_responsavel_e_permissao() -> None:
    m = Mundo()
    os_ = m.reparo_finalizado()
    recusa(
        os_,
        PermissaoNegadaError,
        CodigoErro.NAO_RESPONSAVEL,
        lambda: os_.concluir_tecnicamente(m.carla, "t", True, quando=m.quando()),
    )
    recusa(
        os_,
        PermissaoNegadaError,
        CodigoErro.SEM_PERMISSAO,
        lambda: os_.concluir_tecnicamente(m.ana, "t", True, quando=m.quando()),
    )


# =========================================================================== aprovação


def test_aprovar_conclui_a_os_e_fixa_a_data_de_conclusao() -> None:
    m = Mundo()
    os_ = m.aguardando_aprovacao()
    instante = m.quando()
    os_.aprovar(m.ana, quando=instante)
    assert (os_.status, os_.data_conclusao, os_.encerrada) == (S.CONCLUIDA, instante, True)
    assert tipos(os_)[-2:] == [T.ENCERRAMENTO, T.MUDANCA_STATUS]
    assert os_.servicos[-2].descricao == "Reparo validado e OS encerrada."
    assert os_.servicos[-1].descricao == "Aguardando Aprovação → Concluída"
    assert all(s.responsavel == m.ana for s in os_.servicos[-2:])


@pytest.mark.parametrize("status", [s for s in TODOS_OS_STATUS if s is not S.AGUARDANDO_APROVACAO])
def test_aprovar_so_vale_aguardando_aprovacao(status: StatusOS) -> None:
    m = Mundo()
    os_ = origem(m, status)
    recusa(
        os_,
        ConflitoDeEstadoError,
        CodigoErro.ESTADO_INVALIDO,
        lambda: os_.aprovar(m.ana, quando=m.quando()),
    )


def test_aprovar_exige_aprovar_os_e_a_permissao_vem_antes_do_estado() -> None:
    m = Mundo()
    os_ = m.aguardando_aprovacao()
    recusa(
        os_,
        PermissaoNegadaError,
        CodigoErro.SEM_PERMISSAO,
        lambda: os_.aprovar(m.bruno, quando=m.quando()),
    )
    aberta = m.aberta()
    recusa(
        aberta,
        PermissaoNegadaError,
        CodigoErro.SEM_PERMISSAO,
        lambda: aberta.aprovar(m.bruno, quando=m.quando()),
    )


# =========================================================================== reprovação


def test_reprovar_devolve_a_os_ao_tecnico_em_execucao() -> None:
    m = Mundo()
    os_ = m.aguardando_aprovacao()
    os_.reprovar(m.ana, "Ainda vibra", quando=m.quando())
    assert (os_.status, os_.tecnico_atribuido, os_.data_conclusao) == (S.EM_EXECUCAO, m.bruno, None)
    assert tipos(os_)[-2:] == [T.REPROVACAO, T.MUDANCA_STATUS]
    assert os_.servicos[-2].descricao == "Devolvida ao técnico: Ainda vibra"
    assert os_.servicos[-1].descricao == "Aguardando Aprovação → Em Execução"
    assert not os_.encerrada


def test_apos_reprovar_o_ciclo_pode_ser_refeito_e_o_historico_so_cresce() -> None:
    m = Mundo()
    os_ = m.aguardando_aprovacao()
    antes = os_.servicos
    os_.reprovar(m.ana, "r", quando=m.quando())
    os_.alterar_status(m.bruno, S.REPARO_FINALIZADO, quando=m.quando())
    os_.concluir_tecnicamente(m.bruno, "ok", True, quando=m.quando())
    os_.aprovar(m.ana, quando=m.quando())
    assert os_.status is S.CONCLUIDA
    assert os_.servicos[: len(antes)] == antes


@pytest.mark.parametrize("status", [s for s in TODOS_OS_STATUS if s is not S.AGUARDANDO_APROVACAO])
def test_reprovar_so_vale_aguardando_aprovacao(status: StatusOS) -> None:
    m = Mundo()
    os_ = origem(m, status)
    recusa(
        os_,
        ConflitoDeEstadoError,
        CodigoErro.ESTADO_INVALIDO,
        lambda: os_.reprovar(m.ana, "r", quando=m.quando()),
    )


def test_reprovar_exige_aprovar_os() -> None:
    m = Mundo()
    os_ = m.aguardando_aprovacao()
    recusa(
        os_,
        PermissaoNegadaError,
        CodigoErro.SEM_PERMISSAO,
        lambda: os_.reprovar(m.bruno, "r", quando=m.quando()),
    )


# =========================================================================== cancelamento


@pytest.mark.parametrize("status", STATUS_NAO_FINAIS)
def test_cancelar_vale_para_qualquer_os_nao_encerrada(status: StatusOS) -> None:
    m = Mundo()
    os_ = origem(m, status)
    tecnico = os_.tecnico_atribuido
    instante = m.quando()
    os_.cancelar(m.ana, "Chamado indevido", quando=instante)
    assert (os_.status, os_.motivo_cancelamento, os_.data_conclusao) == (
        S.CANCELADA,
        "Chamado indevido",
        instante,
    )
    assert os_.tecnico_atribuido == tecnico
    assert tipos(os_)[-2:] == [T.CANCELAMENTO, T.MUDANCA_STATUS]
    assert os_.servicos[-2].descricao == "Chamado indevido"
    assert os_.servicos[-1].descricao == f"{status.value} → Cancelada"


@pytest.mark.parametrize("status", [S.CONCLUIDA, S.CANCELADA])
def test_cancelar_os_encerrada_e_recusado(status: StatusOS) -> None:
    m = Mundo()
    os_ = origem(m, status)
    with pytest.raises(ConflitoDeEstadoError) as capturado:
        os_.cancelar(m.ana, "x", quando=m.quando())
    assert capturado.value.codigo is CodigoErro.OS_ENCERRADA
    assert capturado.value.mensagem == "A OS já está encerrada."


def test_cancelar_exige_aprovar_os_e_a_permissao_vem_antes_do_estado() -> None:
    m = Mundo()
    aberta = m.aberta()
    recusa(
        aberta,
        PermissaoNegadaError,
        CodigoErro.SEM_PERMISSAO,
        lambda: aberta.cancelar(m.bruno, "x", quando=m.quando()),
    )
    concluida = m.concluida()
    recusa(
        concluida,
        PermissaoNegadaError,
        CodigoErro.SEM_PERMISSAO,
        lambda: concluida.cancelar(m.bruno, "x", quando=m.quando()),
    )


def test_aprovar_reprovar_e_cancelar_dependem_da_mesma_permissao() -> None:
    m = Mundo()
    m.gestor.permissoes.definir([])  # o cargo do gestor perde tudo
    chamadas: tuple[Chamada, ...] = (
        lambda: m.aguardando_aprovacao().aprovar(m.ana, quando=m.quando()),
        lambda: m.aguardando_aprovacao().reprovar(m.ana, "r", quando=m.quando()),
        lambda: m.aberta().cancelar(m.ana, "c", quando=m.quando()),
    )
    for chamada in chamadas:
        with pytest.raises(PermissaoNegadaError):
            chamada()


# =========================================================================== observações


def test_observacao_cria_apontamento_sem_mudar_o_status() -> None:
    m = Mundo()
    os_ = m.em_execucao()
    instante = m.quando()
    quantidade = len(os_.servicos)
    os_.adicionar_apontamento(m.carla, "Peça chegou", quando=instante)
    assert os_.status is S.EM_EXECUCAO
    assert len(os_.servicos) == quantidade + 1
    registro = os_.servicos[-1]
    assert (registro.tipo, registro.descricao, registro.responsavel, registro.data) == (
        T.APONTAMENTO,
        "Peça chegou",
        m.carla,
        instante,
    )


@pytest.mark.parametrize("quem", ["ana", "bruno", "carla"])
def test_qualquer_usuario_com_a_permissao_inclui_observacao(quem: str) -> None:
    # Comportamento do legado (CAR-39); a restrição por vínculo é o DLT-04 (Operação E).
    m = Mundo()
    os_ = m.atribuida()
    os_.adicionar_apontamento(getattr(m, quem), "nota", quando=m.quando())
    assert os_.servicos[-1].tipo is T.APONTAMENTO


def test_observacao_em_os_encerrada_e_aceita_como_no_legado() -> None:
    # Comportamento do legado (CAR-79); a recusa é o DLT-03 (Operação E).
    m = Mundo()
    for os_ in (m.concluida(), m.cancelada()):
        os_.adicionar_apontamento(m.bruno, "depois do fim", quando=m.quando())
        assert os_.servicos[-1].tipo is T.APONTAMENTO
        assert os_.encerrada


def test_observacao_exige_registrar_apontamento() -> None:
    m = Mundo()
    os_ = m.aberta()
    recusa(
        os_,
        PermissaoNegadaError,
        CodigoErro.SEM_PERMISSAO,
        lambda: os_.adicionar_apontamento(sem_acesso(), "x", quando=m.quando()),
    )


# =========================================================================== ordem das verificações


def _ordem(
    m: Mundo,
) -> list[tuple[str, OrdemServico, type[DominioError], CodigoErro, Chamada]]:
    """Cada caso viola duas regras de uma vez: vence a que o legado verifica primeiro."""
    atribuida = m.atribuida()
    concluida = m.concluida()
    aguardando = m.aguardando_aprovacao()
    finalizada = m.reparo_finalizado()
    q = m.quando
    sem = sem_acesso()
    return [
        (
            "diagnosticar: permissão antes de responsável",
            atribuida,
            PermissaoNegadaError,
            CodigoErro.SEM_PERMISSAO,
            lambda: atribuida.registrar_diagnostico(sem, "p", "c", quando=q()),
        ),
        (
            "diagnosticar: responsável antes de estado",
            m.aberta(),
            PermissaoNegadaError,
            CodigoErro.NAO_RESPONSAVEL,
            lambda: m.aberta().registrar_diagnostico(m.bruno, "p", "c", quando=q()),
        ),
        (
            "apontar_reparo: estado antes de horas negativas",
            finalizada,
            ConflitoDeEstadoError,
            CodigoErro.ESTADO_INVALIDO,
            lambda: finalizada.apontar_reparo(m.bruno, -1, "x", [], quando=q()),
        ),
        (
            "apontar_reparo: responsável antes de horas negativas",
            atribuida,
            PermissaoNegadaError,
            CodigoErro.NAO_RESPONSAVEL,
            lambda: atribuida.apontar_reparo(m.carla, -1, "x", [], quando=q()),
        ),
        (
            "alterar_status: estado antes de status não permitido",
            concluida,
            ConflitoDeEstadoError,
            CodigoErro.ESTADO_INVALIDO,
            lambda: concluida.alterar_status(m.bruno, S.ABERTA, quando=q()),
        ),
        (
            "alterar_status: status não permitido antes de já nesse status",
            atribuida,
            ViolacaoDeRegraError,
            CodigoErro.STATUS_NAO_PERMITIDO,
            lambda: atribuida.alterar_status(m.bruno, S.ATRIBUIDA, quando=q()),
        ),
        (
            "alterar_status: já nesse status antes de sem intervenção",
            finalizada,
            ConflitoDeEstadoError,
            CodigoErro.JA_NESSE_STATUS,
            lambda: finalizada.alterar_status(m.bruno, S.REPARO_FINALIZADO, quando=q()),
        ),
        (
            "concluir: responsável antes de estado",
            m.aberta(),
            PermissaoNegadaError,
            CodigoErro.NAO_RESPONSAVEL,
            lambda: m.aberta().concluir_tecnicamente(m.bruno, "t", True, quando=q()),
        ),
        (
            "concluir: estado antes de diagnóstico",
            atribuida,
            ConflitoDeEstadoError,
            CodigoErro.ESTADO_INVALIDO,
            lambda: atribuida.concluir_tecnicamente(m.bruno, "t", True, quando=q()),
        ),
        (
            "atribuir: permissão antes de estado",
            concluida,
            PermissaoNegadaError,
            CodigoErro.SEM_PERMISSAO,
            lambda: concluida.atribuir(m.carla, m.bruno, quando=q()),
        ),
        (
            "atribuir: estado antes de não ser técnico",
            concluida,
            ConflitoDeEstadoError,
            CodigoErro.ESTADO_INVALIDO,
            lambda: concluida.atribuir(m.ana, m.ana, quando=q()),
        ),
        (
            "atribuir: não ser técnico antes de já atribuída",
            atribuida,
            ViolacaoDeRegraError,
            CodigoErro.NAO_E_TECNICO,
            lambda: atribuida.atribuir(m.ana, m.ana, quando=q()),
        ),
        (
            "aprovar: permissão antes de estado",
            atribuida,
            PermissaoNegadaError,
            CodigoErro.SEM_PERMISSAO,
            lambda: atribuida.aprovar(m.bruno, quando=q()),
        ),
        (
            "reprovar: permissão antes de estado",
            aguardando,
            PermissaoNegadaError,
            CodigoErro.SEM_PERMISSAO,
            lambda: aguardando.reprovar(m.carla, "r", quando=q()),
        ),
        (
            "cancelar: permissão antes de OS encerrada",
            concluida,
            PermissaoNegadaError,
            CodigoErro.SEM_PERMISSAO,
            lambda: concluida.cancelar(m.bruno, "c", quando=q()),
        ),
    ]


def test_ordem_das_verificacoes_de_cada_operacao() -> None:
    m = Mundo()
    for descricao, os_, erro, codigo, chamada in _ordem(m):
        try:
            recusa(os_, erro, codigo, chamada)
        except AssertionError as falha:  # pragma: no cover - só para nomear o caso
            raise AssertionError(f"{descricao}: {falha}") from falha


def test_atribuir_verifica_se_e_tecnico_antes_de_ja_atribuida() -> None:
    """Só observável se o técnico perde ``apontar_reparo`` depois de atribuído (AUD-20)."""
    m = Mundo()
    os_ = m.atribuida()
    restantes = [p for p in m.tecnico.permissoes.ativas() if p is not Permissao.APONTAR_REPARO]
    m.tecnico.permissoes.definir(restantes)
    recusa(
        os_,
        ViolacaoDeRegraError,
        CodigoErro.NAO_E_TECNICO,
        lambda: os_.atribuir(m.bruno, m.ana, quando=m.quando()),
    )


# =========================================================================== recusas sem mutação


def _operacoes(m: Mundo) -> list[tuple[str, Callable[[OrdemServico], object]]]:
    q = m.quando
    pecas = [PecaMaterial("Peça", 1)]
    return [
        ("atribuir a Carla", lambda o: o.atribuir(m.carla, m.ana, quando=q())),
        ("atribuir a Bruno", lambda o: o.atribuir(m.bruno, m.ana, quando=q())),
        ("atribuir a Ana", lambda o: o.atribuir(m.ana, m.ana, quando=q())),
        ("atribuir sem permissão", lambda o: o.atribuir(m.carla, m.bruno, quando=q())),
        ("diagnosticar", lambda o: o.registrar_diagnostico(m.bruno, "p", "c", quando=q())),
        ("diagnosticar (outro)", lambda o: o.registrar_diagnostico(m.carla, "p", "c", quando=q())),
        ("reparo", lambda o: o.apontar_reparo(m.bruno, 1, "i", pecas, quando=q())),
        ("reparo (horas negativas)", lambda o: o.apontar_reparo(m.bruno, -1, "i", [], quando=q())),
        ("reparo (outro)", lambda o: o.apontar_reparo(m.carla, 1, "i", [], quando=q())),
        *(
            (f"status {d.value}", lambda o, d=d: o.alterar_status(m.bruno, d, quando=q()))
            for d in TODOS_OS_STATUS
        ),
        ("concluir (aprovado)", lambda o: o.concluir_tecnicamente(m.bruno, "t", True, quando=q())),
        (
            "concluir (reprovado)",
            lambda o: o.concluir_tecnicamente(m.bruno, "t", False, quando=q()),
        ),
        ("aprovar", lambda o: o.aprovar(m.ana, quando=q())),
        ("aprovar sem permissão", lambda o: o.aprovar(m.bruno, quando=q())),
        ("reprovar", lambda o: o.reprovar(m.ana, "r", quando=q())),
        ("cancelar", lambda o: o.cancelar(m.ana, "c", quando=q())),
        ("cancelar sem permissão", lambda o: o.cancelar(m.bruno, "c", quando=q())),
    ]


def test_toda_recusa_deixa_a_os_e_o_historico_intactos() -> None:
    """Varredura: cada operação, em cada estado; se foi recusada, nada mudou; se aceita, mudou."""
    recusadas = aceitas = 0
    nomes = [nome for nome, _ in _operacoes(Mundo())]
    for status in TODOS_OS_STATUS:
        for indice, nome in enumerate(nomes):
            m = Mundo()
            os_ = origem(m, status)
            antes = instantaneo(os_)
            operacao = _operacoes(m)[indice][1]
            try:
                operacao(os_)
            except DominioError:
                recusadas += 1
                assert instantaneo(os_) == antes, f"{nome} em {status.value} alterou a OS"
            else:
                aceitas += 1
                assert instantaneo(os_) != antes, f"{nome} em {status.value} foi aceita sem efeito"
    assert recusadas > 100  # a varredura realmente exercita as recusas
    assert aceitas > 20


# =========================================================================== histórico


def test_historico_e_numerado_de_1_a_n_por_os() -> None:
    m = Mundo()
    primeira = m.aguardando_aprovacao()
    segunda = OrdemServico.abrir(
        2, m.compressor, "Vazamento", Criticidade.MEDIA, m.ana, quando=m.quando()
    )
    for os_ in (primeira, segunda):
        assert [s.numero for s in os_.servicos] == list(range(1, len(os_.servicos) + 1))
    assert len(segunda.servicos) == 1  # o histórico da primeira não vaza para a segunda


def test_historico_segue_a_ordem_de_inclusao_com_datas_nao_decrescentes() -> None:
    m = Mundo()
    os_ = m.concluida()
    datas = [s.data for s in os_.servicos]
    assert datas == sorted(datas)
    assert datas[0] == os_.data_abertura
    assert datas[-1] == os_.data_conclusao


def test_registros_de_uma_mesma_operacao_compartilham_o_instante() -> None:
    m = Mundo()
    os_ = m.aberta()
    instante = m.quando()
    os_.atribuir(m.bruno, m.ana, quando=instante)
    assert [s.data for s in os_.servicos[-2:]] == [instante, instante]


def test_o_historico_exposto_e_um_instantaneo_imutavel() -> None:
    m = Mundo()
    os_ = m.aberta()
    antes = os_.servicos
    os_.atribuir(m.bruno, m.ana, quando=m.quando())
    assert len(antes) == 1  # a tupla anterior não muda quando o histórico cresce
    assert isinstance(antes, tuple)
    with pytest.raises(FrozenInstanceError):
        antes[0].descricao = "adulterado"  # type: ignore[misc]


def test_as_colecoes_expostas_sao_tuplas() -> None:
    os_ = Mundo().em_execucao()
    assert isinstance(os_.servicos, tuple)
    assert isinstance(os_.intervencoes_realizadas, tuple)
    assert isinstance(os_.pecas_utilizadas, tuple)


def test_reprovacao_e_reatribuicao_so_acrescentam_registros() -> None:
    m = Mundo()
    os_ = m.aguardando_aprovacao()
    antes = os_.servicos
    os_.reprovar(m.ana, "r", quando=m.quando())
    os_.atribuir(m.carla, m.ana, quando=m.quando())
    assert os_.servicos[: len(antes)] == antes
    assert len(os_.servicos) == len(antes) + 3


# =========================================================================== assinaturas

OPERACOES_QUE_REGISTRAM = (
    "abrir",
    "adicionar_apontamento",
    "registrar_diagnostico",
    "apontar_reparo",
    "alterar_status",
    "concluir_tecnicamente",
    "atribuir",
    "aprovar",
    "reprovar",
    "cancelar",
)


@pytest.mark.parametrize("nome", OPERACOES_QUE_REGISTRAM)
def test_toda_operacao_que_registra_recebe_o_instante_por_palavra_chave(nome: str) -> None:
    parametro = inspect.signature(getattr(OrdemServico, nome)).parameters["quando"]
    assert parametro.kind is inspect.Parameter.KEYWORD_ONLY
    assert parametro.default is inspect.Parameter.empty  # nenhum valor padrão: nunca o relógio
    assert parametro.annotation in (datetime, "datetime")


def test_o_historico_nao_depende_de_nenhum_relogio_do_sistema() -> None:
    # Duas execuções com os mesmos instantes produzem exatamente o mesmo histórico.
    primeira = Mundo().concluida()
    segunda = Mundo().concluida()
    assert primeira.servicos == segunda.servicos
    assert instantaneo(primeira) == instantaneo(segunda)


def test_equipamento_e_usuario_da_os_sao_os_objetos_informados() -> None:
    m = Mundo()
    os_ = m.aberta()
    assert os_.equipamento is m.torno
    assert os_.aberta_por is m.carla
    assert isinstance(os_.equipamento, Equipamento)
