"""OCP: o controle é dirigido por dados; estender não exige editar a lógica de controle.

Evidência da Operação F (E2-SOL-02). Não muda regra nenhuma: mostra que a verificação de permissão
e a de transição não têm um ``if`` por permissão nem por status. Acrescentar uma permissão (um
membro de ``Permissao``) ou uma transição (uma entrada da tabela) basta para o controle existente
passar a tratá-la.
"""

import pytest

from manutencao.domain import transicoes
from manutencao.domain.cargo import Cargo
from manutencao.domain.enums import Papel, StatusOS
from manutencao.domain.erros import CodigoErro, PermissaoNegadaError
from manutencao.domain.permissoes import Permissao, Permissoes
from manutencao.domain.usuario import Usuario


@pytest.mark.parametrize("permissao", list(Permissao))
def test_o_controle_de_permissao_e_generico_para_cada_membro(permissao: Permissao) -> None:
    """Um cargo com **só** uma permissão passa nela e é recusado em todas as outras: a lógica de
    ``Usuario.exigir`` não conhece nenhuma permissão em particular."""
    usuario = Usuario(1, "Ana", Cargo(1, "Só uma", Permissoes((permissao,))), papel=Papel.GESTOR)
    usuario.exigir(permissao)
    for outra in Permissao:
        if outra is permissao:
            continue
        with pytest.raises(PermissaoNegadaError) as recusa:
            usuario.exigir(outra)
        assert recusa.value.codigo is CodigoErro.SEM_PERMISSAO


def test_toda_permissao_tem_descricao_para_a_mensagem_de_recusa() -> None:
    """Um membro novo sem descrição quebraria a recusa; o teste obriga a registrá-lo por inteiro."""
    for permissao in Permissao:
        assert permissao.descricao


def test_a_tabela_de_transicoes_cobre_todos_os_status() -> None:
    assert set(transicoes.TRANSICOES) == set(StatusOS)


def test_a_transicao_obedece_somente_a_tabela(monkeypatch: pytest.MonkeyPatch) -> None:
    """``transicao_permitida`` não tem regra própria: é a pertinência na tabela."""
    for origem in StatusOS:
        for destino in StatusOS:
            assert transicoes.transicao_permitida(origem, destino) == (
                destino in transicoes.TRANSICOES[origem]
            )
    assert not transicoes.transicao_permitida(StatusOS.ABERTA, StatusOS.EM_EXECUCAO)
    # Estender: uma entrada a mais na tabela, nenhuma linha de lógica alterada.
    estendida = transicoes.TRANSICOES[StatusOS.ABERTA] | {StatusOS.EM_EXECUCAO}
    monkeypatch.setitem(transicoes._TABELA, StatusOS.ABERTA, estendida)
    assert transicoes.transicao_permitida(StatusOS.ABERTA, StatusOS.EM_EXECUCAO)
