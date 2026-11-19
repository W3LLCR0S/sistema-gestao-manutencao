"""Casos de uso de equipamentos: permissões do legado, regras de exclusão, recusas sem mutação."""

import pytest

from manutencao.application.erros import (
    CodigoErroAplicacao,
    NaoEncontradoError,
    RegraDeAplicacaoError,
)
from manutencao.domain.enums import Criticidade
from manutencao.domain.erros import CodigoErro, PermissaoNegadaError
from manutencao.domain.ordem_servico import OrdemServico
from manutencao.domain.permissoes import Permissao, Permissoes
from tests.apoio.ambiente import (
    ANA,
    BRUNO,
    CARGO_TECNICO,
    CARLA,
    COMPRESSOR,
    EMPILHADEIRA,
    TORNO,
    Ambiente,
)


def _abrir_os_no(amb: Ambiente, equipamento_id: int) -> None:
    """Coloca uma OS no repositório (a abertura pelo serviço é testada em outro arquivo)."""
    equipamento = amb.equipamentos.obter(equipamento_id)
    carla = amb.usuarios.obter(CARLA)
    assert equipamento is not None
    assert carla is not None
    os_ = OrdemServico.abrir(
        amb.ordens.proximo_numero(),
        equipamento,
        "Falha",
        Criticidade.BAIXA,
        carla,
        quando=amb.relogio.agora(),
    )
    amb.ordens.adicionar(os_)


# ---------------------------------------------------------------------------------- cadastro


def test_cadastrar_usa_o_proximo_id_e_persiste(amb: Ambiente) -> None:
    novo = amb.servico_equipamentos.cadastrar(ANA, "Prensa", "P1")
    assert (novo.id, novo.nome, novo.modelo, novo.ativo) == (4, "Prensa", "P1", True)
    guardado = amb.equipamentos.obter(4)
    assert guardado is not None
    assert guardado.nome == "Prensa"


def test_consultar_e_listar_exigem_ver_equipamentos_e_funcionam_para_o_tecnico(
    amb: Ambiente,
) -> None:
    assert amb.servico_equipamentos.consultar(BRUNO, TORNO).nome == "Torno CNC"
    assert [e.id for e in amb.servico_equipamentos.listar(CARLA)] == [1, 2, 3]


def test_listar_apenas_ativos(amb: Ambiente) -> None:
    amb.servico_equipamentos.inativar(ANA, COMPRESSOR)
    todos = amb.servico_equipamentos.listar(ANA)
    ativos = amb.servico_equipamentos.listar(ANA, apenas_ativos=True)
    assert [e.id for e in todos] == [1, 2, 3]
    assert [e.id for e in ativos] == [1, 3]


def test_consultar_inexistente_levanta_nao_encontrado(amb: Ambiente) -> None:
    with pytest.raises(NaoEncontradoError) as erro:
        amb.servico_equipamentos.consultar(ANA, 99)
    assert (erro.value.entidade, erro.value.identificador) == ("Equipamento", 99)
    assert erro.value.codigo is CodigoErroAplicacao.NAO_ENCONTRADO


def test_ator_inexistente_levanta_nao_encontrado(amb: Ambiente) -> None:
    with pytest.raises(NaoEncontradoError) as erro:
        amb.servico_equipamentos.listar(99)
    assert erro.value.entidade == "Usuário"


# ------------------------------------------------------------------------------ autorização


@pytest.mark.parametrize("ator", [BRUNO, CARLA])
def test_tecnico_nao_gere_equipamentos_e_nada_muda(amb: Ambiente, ator: int) -> None:
    antes = amb.equipamentos.listar()
    servico = amb.servico_equipamentos
    for operacao in (
        lambda: servico.cadastrar(ator, "Prensa", "P1"),
        lambda: servico.atualizar(ator, TORNO, "x", "y"),
        lambda: servico.inativar(ator, TORNO),
        lambda: servico.reativar(ator, TORNO),
        lambda: servico.excluir(ator, EMPILHADEIRA),
    ):
        with pytest.raises(PermissaoNegadaError) as erro:
            operacao()
        assert erro.value.codigo is CodigoErro.SEM_PERMISSAO
    assert amb.equipamentos.listar() == antes
    assert amb.equipamentos.proximo_id() == 4


def test_a_permissao_vale_na_chamada_seguinte_a_sua_alteracao(amb: Ambiente) -> None:
    with pytest.raises(PermissaoNegadaError):
        amb.servico_equipamentos.cadastrar(BRUNO, "Prensa", "P1")
    permissoes = (*Permissoes.padrao_tecnico().ativas(), Permissao.GERIR_EQUIPAMENTOS)
    amb.servico_usuarios.definir_permissoes_do_cargo(ANA, CARGO_TECNICO, permissoes)
    assert amb.servico_equipamentos.cadastrar(BRUNO, "Prensa", "P1").id == 4


def test_leitura_exige_ver_equipamentos(amb: Ambiente) -> None:
    amb.servico_usuarios.definir_permissoes_do_cargo(ANA, CARGO_TECNICO, [Permissao.VER_OS])
    with pytest.raises(PermissaoNegadaError):
        amb.servico_equipamentos.listar(BRUNO)
    with pytest.raises(PermissaoNegadaError):
        amb.servico_equipamentos.consultar(BRUNO, TORNO)


# ------------------------------------------------------------------------------ atualizar


def test_atualizar_altera_nome_e_modelo_e_preserva_o_resto(amb: Ambiente) -> None:
    amb.servico_equipamentos.inativar(ANA, TORNO)
    editado = amb.servico_equipamentos.atualizar(ANA, TORNO, "Torno 2", "GL 300")
    assert (editado.id, editado.nome, editado.modelo, editado.ativo) == (
        1,
        "Torno 2",
        "GL 300",
        False,
    )
    guardado = amb.equipamentos.obter(TORNO)
    assert guardado is not None
    assert (guardado.nome, guardado.modelo, guardado.ativo) == ("Torno 2", "GL 300", False)


def test_atualizar_inexistente_levanta_nao_encontrado(amb: Ambiente) -> None:
    with pytest.raises(NaoEncontradoError):
        amb.servico_equipamentos.atualizar(ANA, 99, "x", "y")


# --------------------------------------------------------------------------- inativar/reativar


def test_inativar_e_reativar(amb: Ambiente) -> None:
    assert amb.servico_equipamentos.inativar(ANA, TORNO).ativo is False
    assert amb.servico_equipamentos.inativar(ANA, TORNO).ativo is False  # idempotente
    stored = amb.equipamentos.obter(TORNO)
    assert stored is not None
    assert stored.situacao == "Inativo"
    assert amb.servico_equipamentos.reativar(ANA, TORNO).ativo is True
    stored = amb.equipamentos.obter(TORNO)
    assert stored is not None
    assert stored.situacao == "Ativo"


# ------------------------------------------------------------------------------------ excluir


def test_excluir_equipamento_sem_os_o_remove_e_o_id_nao_volta(amb: Ambiente) -> None:
    amb.servico_equipamentos.excluir(ANA, EMPILHADEIRA)
    assert amb.equipamentos.obter(EMPILHADEIRA) is None
    assert amb.servico_equipamentos.cadastrar(ANA, "Prensa", "P1").id == 4  # DLT-10
    assert [e.id for e in amb.servico_equipamentos.listar(ANA)] == [1, 2, 4]


def test_excluir_equipamento_inativo_sem_os_e_permitido(amb: Ambiente) -> None:
    amb.servico_equipamentos.inativar(ANA, EMPILHADEIRA)
    amb.servico_equipamentos.excluir(ANA, EMPILHADEIRA)
    assert amb.equipamentos.obter(EMPILHADEIRA) is None


def test_excluir_equipamento_com_os_e_recusado_sem_mutacao(amb: Ambiente) -> None:
    _abrir_os_no(amb, TORNO)
    amb.servico_equipamentos.inativar(ANA, TORNO)  # inativar não libera a exclusão
    antes = amb.equipamentos.listar()
    with pytest.raises(RegraDeAplicacaoError) as erro:
        amb.servico_equipamentos.excluir(ANA, TORNO)
    assert erro.value.codigo is CodigoErroAplicacao.EQUIPAMENTO_COM_OS
    assert "use Inativar para preservar o histórico" in erro.value.mensagem
    assert amb.equipamentos.listar() == antes
    assert amb.ordens.contar() == 1


def test_excluir_inexistente_levanta_nao_encontrado(amb: Ambiente) -> None:
    with pytest.raises(NaoEncontradoError):
        amb.servico_equipamentos.excluir(ANA, 99)
