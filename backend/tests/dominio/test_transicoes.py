"""C2: tabela de transições da OS (máquina de estados)."""

import pytest

from manutencao.domain.enums import StatusOS
from manutencao.domain.transicoes import (
    STATUS_ATENDIMENTO,
    STATUS_FINAIS,
    STATUS_ORIGEM_TECNICO,
    STATUS_TECNICO,
    TRANSICOES,
    encerrada,
    transicao_permitida,
)

TODOS = tuple(StatusOS)
NAO_FINAIS = tuple(s for s in TODOS if s not in STATUS_FINAIS)

# A tabela, escrita por extenso a partir do legado (models/ordem_servico.py): quem faz cada mudança.
ESPERADAS = {
    (StatusOS.ABERTA, StatusOS.ATRIBUIDA),  # atribuir
    (StatusOS.ATRIBUIDA, StatusOS.EM_EXECUCAO),  # apontar reparo / alterar status
    (StatusOS.ATRIBUIDA, StatusOS.AGUARDANDO_PECA),  # alterar status
    (StatusOS.ATRIBUIDA, StatusOS.REPARO_FINALIZADO),  # alterar status (exige intervenção)
    (StatusOS.EM_EXECUCAO, StatusOS.AGUARDANDO_PECA),
    (StatusOS.EM_EXECUCAO, StatusOS.REPARO_FINALIZADO),
    (StatusOS.AGUARDANDO_PECA, StatusOS.EM_EXECUCAO),
    (StatusOS.AGUARDANDO_PECA, StatusOS.REPARO_FINALIZADO),
    (StatusOS.REPARO_FINALIZADO, StatusOS.EM_EXECUCAO),  # o técnico reabre o reparo
    (StatusOS.REPARO_FINALIZADO, StatusOS.AGUARDANDO_PECA),
    (StatusOS.REPARO_FINALIZADO, StatusOS.AGUARDANDO_APROVACAO),  # conclusão técnica
    (StatusOS.AGUARDANDO_APROVACAO, StatusOS.CONCLUIDA),  # aprovar
    (StatusOS.AGUARDANDO_APROVACAO, StatusOS.EM_EXECUCAO),  # reprovar
    *((origem, StatusOS.CANCELADA) for origem in NAO_FINAIS),  # cancelar
}


def test_a_tabela_cobre_todos_os_status_como_origem() -> None:
    assert set(TRANSICOES) == set(TODOS)


@pytest.mark.parametrize("destino", TODOS)
@pytest.mark.parametrize("origem", TODOS)
def test_matriz_8x8_das_transicoes_permitidas(origem: StatusOS, destino: StatusOS) -> None:
    assert transicao_permitida(origem, destino) is ((origem, destino) in ESPERADAS)


def test_status_finais_nao_tem_saida() -> None:
    for status in STATUS_FINAIS:
        assert TRANSICOES[status] == frozenset()
        assert encerrada(status)


def test_so_os_status_finais_sao_encerrados() -> None:
    assert [s for s in TODOS if encerrada(s)] == list(STATUS_FINAIS)


def test_toda_os_nao_encerrada_pode_ser_cancelada() -> None:
    assert all(transicao_permitida(s, StatusOS.CANCELADA) for s in NAO_FINAIS)


def test_nenhum_status_volta_para_aberta_nem_vai_para_si_mesmo() -> None:
    for origem, destinos in TRANSICOES.items():
        assert StatusOS.ABERTA not in destinos
        assert origem not in destinos


def test_a_tabela_e_somente_leitura() -> None:
    with pytest.raises(TypeError):
        TRANSICOES[StatusOS.ABERTA] = frozenset()  # type: ignore[index]
    assert isinstance(TRANSICOES[StatusOS.ABERTA], frozenset)


def test_conjuntos_de_status_do_tecnico_sao_os_do_legado() -> None:
    assert STATUS_TECNICO == (
        StatusOS.EM_EXECUCAO,
        StatusOS.AGUARDANDO_PECA,
        StatusOS.REPARO_FINALIZADO,
    )
    assert STATUS_FINAIS == (StatusOS.CONCLUIDA, StatusOS.CANCELADA)
    assert STATUS_ATENDIMENTO == (
        StatusOS.ATRIBUIDA,
        StatusOS.EM_EXECUCAO,
        StatusOS.AGUARDANDO_PECA,
    )
    assert (StatusOS.ATRIBUIDA, *STATUS_TECNICO) == STATUS_ORIGEM_TECNICO


def test_destinos_que_o_tecnico_define_estao_na_tabela_a_partir_de_origens_do_tecnico() -> None:
    for origem in STATUS_ORIGEM_TECNICO:
        for destino in STATUS_TECNICO:
            if destino != origem:
                assert transicao_permitida(origem, destino), (origem, destino)
