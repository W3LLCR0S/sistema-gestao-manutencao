"""Casos de uso de usuários, cargos e permissões: regras do legado, autorização, sem mutação."""

import pytest

from manutencao.application.erros import (
    CodigoErroAplicacao,
    NaoEncontradoError,
    RegraDeAplicacaoError,
)
from manutencao.domain.enums import Criticidade, Disponibilidade
from manutencao.domain.erros import CodigoErro, PermissaoNegadaError, ViolacaoDeRegraError
from manutencao.domain.ordem_servico import OrdemServico
from manutencao.domain.permissoes import Permissao, Permissoes
from tests.apoio.ambiente import (
    ANA,
    BRUNO,
    CARGO_GESTOR,
    CARGO_TECNICO,
    CARLA,
    TORNO,
    Ambiente,
)


def _os_com_historico(
    amb: Ambiente, *, aberta_por: int = CARLA, tecnico: int | None = None
) -> None:
    """Uma OS no repositório, aberta por ``aberta_por`` e, se pedido, atribuída ao técnico."""
    torno = amb.equipamentos.obter(TORNO)
    abridor = amb.usuarios.obter(aberta_por)
    assert torno is not None
    assert abridor is not None
    os_ = OrdemServico.abrir(
        amb.ordens.proximo_numero(),
        torno,
        "Falha",
        Criticidade.BAIXA,
        abridor,
        quando=amb.relogio.agora(),
    )
    if tecnico is not None:
        gestor = amb.usuarios.obter(ANA)
        alvo = amb.usuarios.obter(tecnico)
        assert gestor is not None
        assert alvo is not None
        os_.atribuir(alvo, gestor, quando=amb.relogio.agora())
    amb.ordens.adicionar(os_)


# ----------------------------------------------------------------------------------- cadastro


def test_cadastrar_cria_usuario_disponivel_com_o_proximo_id(amb: Ambiente) -> None:
    novo = amb.servico_usuarios.cadastrar(ANA, "Diego", CARGO_TECNICO, "d@e.com", "Seg")
    assert (novo.id, novo.nome, novo.email, novo.escala) == (4, "Diego", "d@e.com", "Seg")
    assert novo.disponibilidade is Disponibilidade.DISPONIVEL
    guardado = amb.usuarios.obter(4)
    assert guardado is not None
    assert (guardado.cargo.id, guardado.e_tecnico) == (CARGO_TECNICO, True)


def test_novo_gestor_nao_e_tecnico(amb: Ambiente) -> None:
    novo = amb.servico_usuarios.cadastrar(ANA, "Eva", CARGO_GESTOR)
    assert novo.e_tecnico is False


def test_cadastrar_com_cargo_inexistente_recusa_sem_consumir_id(amb: Ambiente) -> None:
    with pytest.raises(NaoEncontradoError) as erro:
        amb.servico_usuarios.cadastrar(ANA, "Diego", 99)
    assert erro.value.entidade == "Cargo"
    assert len(amb.usuarios.listar()) == 3
    assert amb.usuarios.proximo_id() == 4


# ------------------------------------------------------------------------------ autorização


def test_tecnico_nao_gere_usuarios_nem_cargos_e_nada_muda(amb: Ambiente) -> None:
    servico = amb.servico_usuarios
    usuarios_antes = amb.usuarios.listar()
    cargos_antes = [(c.id, c.permissoes.ativas()) for c in amb.cargos.listar()]
    operacoes = (
        lambda: servico.cadastrar(BRUNO, "Diego", CARGO_TECNICO),
        lambda: servico.consultar(BRUNO, ANA),
        lambda: servico.listar(BRUNO),
        lambda: servico.listar_cargos(BRUNO),
        lambda: servico.atualizar_dados(BRUNO, CARLA, nome="x"),
        lambda: servico.alterar_cargo(BRUNO, CARLA, CARGO_GESTOR),
        lambda: servico.definir_disponibilidade(BRUNO, CARLA, Disponibilidade.AUSENTE),
        lambda: servico.excluir(BRUNO, CARLA),
        lambda: servico.definir_permissoes_do_cargo(BRUNO, CARGO_TECNICO, [Permissao.VER_OS]),
    )
    for operacao in operacoes:
        with pytest.raises(PermissaoNegadaError) as erro:
            operacao()
        assert erro.value.codigo is CodigoErro.SEM_PERMISSAO
    assert amb.usuarios.listar() == usuarios_antes
    assert [(c.id, c.permissoes.ativas()) for c in amb.cargos.listar()] == cargos_antes
    assert amb.usuarios.proximo_id() == 4


# ------------------------------------------------------------------------------------ consulta


def test_consultar_e_listar(amb: Ambiente) -> None:
    assert amb.servico_usuarios.consultar(ANA, BRUNO).nome == "Bruno Lima"
    assert [u.id for u in amb.servico_usuarios.listar(ANA)] == [1, 2, 3]
    assert [c.nome for c in amb.servico_usuarios.listar_cargos(ANA)] == ["Gestor", "Técnico"]
    with pytest.raises(NaoEncontradoError):
        amb.servico_usuarios.consultar(ANA, 99)


# ------------------------------------------------------------------------------------- editar


def test_atualizar_dados_altera_apenas_os_campos_informados(amb: Ambiente) -> None:
    amb.servico_usuarios.atualizar_dados(ANA, BRUNO, nome="Bruno L. Lima", escala="Seg-Qui 06h-14h")
    bruno = amb.usuarios.obter(BRUNO)
    assert bruno is not None
    assert (bruno.nome, bruno.escala, bruno.email, bruno.cargo.id) == (
        "Bruno L. Lima",
        "Seg-Qui 06h-14h",
        "bruno@empresa.com",
        CARGO_TECNICO,
    )


def test_atualizar_dados_de_inexistente_levanta_nao_encontrado(amb: Ambiente) -> None:
    with pytest.raises(NaoEncontradoError):
        amb.servico_usuarios.atualizar_dados(ANA, 99, nome="x")


def test_alterar_o_cargo_move_o_usuario_entre_tecnicos_e_gestores(amb: Ambiente) -> None:
    amb.servico_usuarios.alterar_cargo(ANA, CARLA, CARGO_GESTOR)
    carla = amb.usuarios.obter(CARLA)
    assert carla is not None
    assert (carla.cargo.id, carla.e_tecnico) == (CARGO_GESTOR, False)
    amb.servico_usuarios.alterar_cargo(ANA, CARLA, CARGO_TECNICO)
    carla = amb.usuarios.obter(CARLA)
    assert carla is not None
    assert carla.e_tecnico is True


def test_alterar_para_cargo_inexistente_levanta_nao_encontrado(amb: Ambiente) -> None:
    with pytest.raises(NaoEncontradoError):
        amb.servico_usuarios.alterar_cargo(ANA, CARLA, 99)
    carla = amb.usuarios.obter(CARLA)
    assert carla is not None
    assert carla.cargo.id == CARGO_TECNICO


def test_ninguem_remove_de_si_o_acesso_de_gestao_ao_trocar_de_cargo(amb: Ambiente) -> None:
    with pytest.raises(RegraDeAplicacaoError) as erro:
        amb.servico_usuarios.alterar_cargo(ANA, ANA, CARGO_TECNICO)
    assert erro.value.codigo is CodigoErroAplicacao.AUTOREMOCAO_DE_ACESSO_DE_GESTAO
    assert erro.value.mensagem == "Você não pode remover o próprio acesso de gestão."
    ana = amb.usuarios.obter(ANA)
    assert ana is not None
    assert ana.cargo.id == CARGO_GESTOR


def test_o_gestor_pode_trocar_o_proprio_cargo_por_outro_com_gestao(amb: Ambiente) -> None:
    amb.servico_usuarios.alterar_cargo(ANA, ANA, CARGO_GESTOR)
    ana = amb.usuarios.obter(ANA)
    assert ana is not None
    assert ana.cargo.id == CARGO_GESTOR


def test_gestor_ajusta_a_disponibilidade_de_outro_usuario(amb: Ambiente) -> None:
    amb.servico_usuarios.definir_disponibilidade(ANA, CARLA, Disponibilidade.AUSENTE)
    carla = amb.usuarios.obter(CARLA)
    assert carla is not None
    assert carla.disponibilidade is Disponibilidade.AUSENTE


# ------------------------------------------------------------------------------------ excluir


def test_excluir_usuario_sem_historico_o_remove_e_o_id_nao_volta(amb: Ambiente) -> None:
    novo = amb.servico_usuarios.cadastrar(ANA, "Diego", CARGO_TECNICO)
    amb.servico_usuarios.excluir(ANA, novo.id)
    assert amb.usuarios.obter(novo.id) is None
    assert amb.servico_usuarios.cadastrar(ANA, "Outro", CARGO_TECNICO).id == 5  # DLT-10


def test_autoexclusao_e_recusada(amb: Ambiente) -> None:
    with pytest.raises(RegraDeAplicacaoError) as erro:
        amb.servico_usuarios.excluir(ANA, ANA)
    assert erro.value.codigo is CodigoErroAplicacao.AUTOEXCLUSAO
    assert erro.value.mensagem == "Você não pode excluir o próprio usuário."
    assert amb.usuarios.obter(ANA) is not None


def _recusa_exclusao_de_bruno(amb: Ambiente) -> None:
    antes = amb.usuarios.listar()
    with pytest.raises(RegraDeAplicacaoError) as erro:
        amb.servico_usuarios.excluir(ANA, BRUNO)
    assert erro.value.codigo is CodigoErroAplicacao.USUARIO_COM_HISTORICO
    assert erro.value.mensagem == "Usuário possui histórico em OS; não pode ser excluído."
    assert amb.usuarios.listar() == antes


def test_autor_da_abertura_de_os_nao_e_excluido(amb: Ambiente) -> None:
    _os_com_historico(amb, aberta_por=BRUNO)
    _recusa_exclusao_de_bruno(amb)


def test_tecnico_atribuido_a_os_nao_e_excluido(amb: Ambiente) -> None:
    _os_com_historico(amb, tecnico=BRUNO)
    _recusa_exclusao_de_bruno(amb)


def test_quem_so_aparece_como_responsavel_de_um_registro_tambem_tem_historico(
    amb: Ambiente,
) -> None:
    amb.servico_usuarios.cadastrar(ANA, "Eva", CARGO_GESTOR)  # id 4
    _os_com_historico(amb, tecnico=BRUNO)  # o registro de atribuição é da Ana (gestora)
    outra_gestora = amb.servico_usuarios.consultar(ANA, 4)
    with pytest.raises(RegraDeAplicacaoError) as erro:
        amb.servico_usuarios.excluir(outra_gestora.id, ANA)  # Eva tenta excluir a Ana
    assert erro.value.codigo is CodigoErroAplicacao.USUARIO_COM_HISTORICO


def test_excluir_inexistente_levanta_nao_encontrado(amb: Ambiente) -> None:
    with pytest.raises(NaoEncontradoError):
        amb.servico_usuarios.excluir(ANA, 99)


# ------------------------------------------------------------------------------- permissões


def test_permissoes_do_cargo_valem_para_todos_os_usuarios_dele(amb: Ambiente) -> None:
    amb.servico_usuarios.definir_permissoes_do_cargo(
        ANA, CARGO_TECNICO, [Permissao.VER_OS, Permissao.ABRIR_OS]
    )
    for usuario_id in (BRUNO, CARLA):
        usuario = amb.usuarios.obter(usuario_id)
        assert usuario is not None
        assert usuario.pode(Permissao.ABRIR_OS)
        assert not usuario.pode(Permissao.APONTAR_REPARO)
        assert not usuario.e_tecnico  # AUD-20, preservado: técnico = apontar_reparo


def test_permissoes_do_cargo_sao_tudo_ou_nada(amb: Ambiente) -> None:
    amb.servico_usuarios.definir_permissoes_do_cargo(ANA, CARGO_TECNICO, [Permissao.VER_OS])
    cargo = amb.cargos.obter(CARGO_TECNICO)
    assert cargo is not None
    assert cargo.permissoes.ativas() == (Permissao.VER_OS,)
    amb.servico_usuarios.definir_permissoes_do_cargo(ANA, CARGO_TECNICO, [])
    cargo = amb.cargos.obter(CARGO_TECNICO)
    assert cargo is not None
    assert cargo.permissoes.ativas() == ()


def test_permissao_com_nome_invalido_e_erro_e_nada_muda(amb: Ambiente) -> None:
    """DLT-11: o legado ignorava nomes desconhecidos em silêncio."""
    antes = amb.cargos.obter(CARGO_TECNICO)
    assert antes is not None
    with pytest.raises(ViolacaoDeRegraError) as erro:
        amb.servico_usuarios.definir_permissoes_do_cargo(
            ANA,
            CARGO_TECNICO,
            [Permissao.VER_OS, "voar"],  # type: ignore[list-item]
        )
    assert erro.value.codigo is CodigoErro.PERMISSAO_INVALIDA
    depois = amb.cargos.obter(CARGO_TECNICO)
    assert depois is not None
    assert depois.permissoes.ativas() == antes.permissoes.ativas()


def test_gestor_nao_remove_do_proprio_cargo_o_acesso_de_gestao(amb: Ambiente) -> None:
    antes = amb.cargos.obter(CARGO_GESTOR)
    assert antes is not None
    with pytest.raises(RegraDeAplicacaoError) as erro:
        amb.servico_usuarios.definir_permissoes_do_cargo(
            ANA, CARGO_GESTOR, [Permissao.VER_OS, Permissao.ATRIBUIR_OS]
        )
    assert erro.value.codigo is CodigoErroAplicacao.AUTOREMOCAO_DE_ACESSO_DE_GESTAO
    assert erro.value.mensagem == "Você não pode remover do seu próprio cargo o acesso de gestão."
    depois = amb.cargos.obter(CARGO_GESTOR)
    assert depois is not None
    assert depois.permissoes.ativas() == antes.permissoes.ativas()


def test_gestor_pode_reduzir_o_proprio_cargo_se_mantem_a_gestao(amb: Ambiente) -> None:
    amb.servico_usuarios.definir_permissoes_do_cargo(
        ANA, CARGO_GESTOR, [Permissao.VER_OS, Permissao.GERIR_USUARIOS]
    )
    ana = amb.usuarios.obter(ANA)
    assert ana is not None
    assert ana.cargo.permissoes.ativas() == (Permissao.VER_OS, Permissao.GERIR_USUARIOS)


def test_cargo_inexistente_levanta_nao_encontrado(amb: Ambiente) -> None:
    with pytest.raises(NaoEncontradoError):
        amb.servico_usuarios.definir_permissoes_do_cargo(ANA, 99, [])


def test_perfis_padrao_da_base_batem_com_o_legado(amb: Ambiente) -> None:
    gestor = amb.cargos.obter(CARGO_GESTOR)
    tecnico = amb.cargos.obter(CARGO_TECNICO)
    assert gestor is not None
    assert tecnico is not None
    assert gestor.permissoes.ativas() == Permissoes.padrao_gestor().ativas()
    assert tecnico.permissoes.ativas() == Permissoes.padrao_tecnico().ativas()
