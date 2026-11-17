"""Regularização da Operação E nos serviços de aplicação (REG-E-01 a REG-E-06).

Correspondência entre as decisões de regularização e os registros definitivos (deltas):

* REG-E-01 último gestor ........................ DLT-18
* REG-E-02 alteração de papel (ratificação) ..... DLT-19
* REG-E-03 autoproteção estendida (ratificação) . DLT-20
* REG-E-04 ordens de serviço ativas ............. DLT-21
* REG-E-05 campos obrigatórios (ampliação) ...... DLT-22
* REG-E-06 disponibilidade manual e derivada .... DLT-23

Cada recusa é provada **sem mutação**: nem usuários, nem cargos, nem OS (com o histórico), nem as
sequências de identificadores mudam (``_estado``). O erro é tipado e de conflito
(``RegraDeAplicacaoError``, traduzido em 409 pela borda).
"""

from collections.abc import Callable
from typing import Any

import pytest

from manutencao.application.erros import (
    CodigoErroAplicacao,
    NaoEncontradoError,
    RegraDeAplicacaoError,
)
from manutencao.domain.cargo import Cargo
from manutencao.domain.enums import Papel, StatusOS
from manutencao.domain.erros import CodigoErro, PermissaoNegadaError
from manutencao.domain.permissoes import Permissao, Permissoes
from manutencao.domain.usuario import Usuario
from tests.apoio.ambiente import ANA, BRUNO, CARGO_GESTOR, CARGO_TECNICO, CARLA, Ambiente
from tests.apoio.caminhos import (
    aguardando_aprovacao,
    atribuida,
    em_execucao,
    guardada,
)
from tests.dominio.fabrica import instantaneo

INEXISTENTE = 99
Operacao = Callable[[], object]


# --------------------------------------------------------------------------------- apoio


def _estado(amb: Ambiente) -> tuple[Any, ...]:
    """Tudo o que uma recusa não pode alterar, inclusive o próximo id de cada sequência."""
    return (
        tuple(
            (u.id, u.nome, u.cargo.id, u.email, u.escala, u.disponibilidade, u.papel, u.ativo)
            for u in amb.usuarios.listar()
        ),
        [(c.id, c.nome, c.permissoes.ativas()) for c in amb.cargos.listar()],
        [(e.id, e.nome, e.modelo, e.ativo) for e in amb.equipamentos.listar()],
        [instantaneo(o) for o in amb.ordens.listar()],
        amb.usuarios.proximo_id(),
        amb.cargos.proximo_id(),
        amb.equipamentos.proximo_id(),
        amb.ordens.proximo_numero(),
    )


def _recusado(
    amb: Ambiente, codigo: CodigoErroAplicacao, operacao: Operacao
) -> RegraDeAplicacaoError:
    antes = _estado(amb)
    with pytest.raises(RegraDeAplicacaoError) as capturado:
        operacao()
    assert capturado.value.codigo is codigo
    assert _estado(amb) == antes, "uma recusa não pode deixar mutação"
    return capturado.value


def _usuario(amb: Ambiente, usuario_id: int) -> Usuario:
    achado = amb.usuarios.obter(usuario_id)
    assert achado is not None
    return achado


def _cargo(amb: Ambiente, cargo_id: int) -> Cargo:
    achado = amb.cargos.obter(cargo_id)
    assert achado is not None
    return achado


def _novo_cargo(amb: Ambiente, nome: str, *permissoes: Permissao) -> int:
    cargo = Cargo(amb.cargos.proximo_id(), nome, Permissoes(permissoes))
    amb.cargos.adicionar(cargo)
    return cargo.id


def _administrador_nao_gestor(amb: Ambiente) -> int:
    """Bruno (Técnico) passa a poder gerir usuários: um ator que **não** é o gestor, para provar
    as proteções em que o próprio gestor não poderia agir sobre si."""
    cargo = _cargo(amb, CARGO_TECNICO)
    cargo.permissoes.definir((*cargo.permissoes.ativas(), Permissao.GERIR_USUARIOS))
    amb.cargos.salvar(cargo)
    return BRUNO


def _segundo_gestor(amb: Ambiente, nome: str = "Eva") -> int:
    return amb.servico_usuarios.cadastrar(ANA, nome, CARGO_GESTOR, papel=Papel.GESTOR).id


def _gestores_aptos(amb: Ambiente) -> list[int]:
    return [u.id for u in amb.usuarios.listar() if u.e_gestor_administrativo]


# =========================================================================================
# REG-E-01 / DLT-18 — proteção do último gestor administrativamente apto
# =========================================================================================


def test_dlt18_o_gestor_apto_e_papel_gestor_ativo_e_com_gerir_usuarios(amb: Ambiente) -> None:
    assert _gestores_aptos(amb) == [ANA]
    sem_permissao = _novo_cargo(amb, "Supervisão", Permissao.VER_OS)
    eva = amb.servico_usuarios.cadastrar(ANA, "Eva", sem_permissao, papel=Papel.GESTOR).id
    assert _gestores_aptos(amb) == [ANA]  # papel Gestor sem gerir_usuarios não é apto
    assert not _usuario(amb, BRUNO).e_gestor_administrativo  # técnico não é gestor
    amb.servico_usuarios.alterar_cargo(ANA, eva, CARGO_GESTOR)
    assert _gestores_aptos(amb) == [ANA, eva]
    amb.servico_usuarios.desativar(ANA, eva)
    assert _gestores_aptos(amb) == [ANA]  # inativo não é apto


def test_dlt18_um_unico_gestor_apto_nao_pode_ser_desativado(amb: Ambiente) -> None:
    admin = _administrador_nao_gestor(amb)
    erro = _recusado(
        amb, CodigoErroAplicacao.ULTIMO_GESTOR, lambda: amb.servico_usuarios.desativar(admin, ANA)
    )
    assert "sem gestor" in str(erro)
    assert _gestores_aptos(amb) == [ANA]


def test_dlt18_com_dois_gestores_aptos_um_deles_pode_ser_desativado(amb: Ambiente) -> None:
    admin = _administrador_nao_gestor(amb)
    eva = _segundo_gestor(amb)
    amb.servico_usuarios.desativar(admin, ANA)
    assert _gestores_aptos(amb) == [eva]
    # e agora Eva é a última
    _recusado(
        amb, CodigoErroAplicacao.ULTIMO_GESTOR, lambda: amb.servico_usuarios.desativar(admin, eva)
    )


def test_dlt18_o_gestor_sem_gerir_usuarios_nao_conta_como_outro_gestor(amb: Ambiente) -> None:
    admin = _administrador_nao_gestor(amb)
    sem_permissao = _novo_cargo(amb, "Supervisão", Permissao.VER_OS)
    amb.servico_usuarios.cadastrar(ANA, "Eva", sem_permissao, papel=Papel.GESTOR)
    _recusado(
        amb, CodigoErroAplicacao.ULTIMO_GESTOR, lambda: amb.servico_usuarios.desativar(admin, ANA)
    )


def test_dlt18_o_gestor_inativo_nao_conta_como_outro_gestor(amb: Ambiente) -> None:
    admin = _administrador_nao_gestor(amb)
    eva = _segundo_gestor(amb)
    amb.servico_usuarios.desativar(ANA, eva)
    _recusado(
        amb, CodigoErroAplicacao.ULTIMO_GESTOR, lambda: amb.servico_usuarios.desativar(admin, ANA)
    )


def test_dlt18_o_tecnico_com_gerir_usuarios_nao_conta_como_gestor(amb: Ambiente) -> None:
    admin = _administrador_nao_gestor(amb)
    assert _usuario(amb, admin).pode(Permissao.GERIR_USUARIOS)
    assert _gestores_aptos(amb) == [ANA]
    _recusado(
        amb, CodigoErroAplicacao.ULTIMO_GESTOR, lambda: amb.servico_usuarios.desativar(admin, ANA)
    )


def test_dlt18_alterar_o_cargo_do_ultimo_gestor_para_um_sem_gestao_e_recusado(
    amb: Ambiente,
) -> None:
    admin = _administrador_nao_gestor(amb)
    sem_gestao = _novo_cargo(amb, "Operacional", Permissao.VER_OS)
    _recusado(
        amb,
        CodigoErroAplicacao.ULTIMO_GESTOR,
        lambda: amb.servico_usuarios.alterar_cargo(admin, ANA, sem_gestao),
    )
    # com outro gestor apto a troca é aceita
    _segundo_gestor(amb)
    amb.servico_usuarios.alterar_cargo(admin, ANA, sem_gestao)
    assert _usuario(amb, ANA).cargo.id == sem_gestao


def test_dlt18_alterar_o_cargo_para_um_que_preserva_a_gestao_e_aceito(amb: Ambiente) -> None:
    admin = _administrador_nao_gestor(amb)
    outro = _novo_cargo(amb, "Chefia", Permissao.GERIR_USUARIOS, Permissao.VER_OS)
    amb.servico_usuarios.alterar_cargo(admin, ANA, outro)
    assert _gestores_aptos(amb) == [ANA]


def test_dlt18_retirar_gerir_usuarios_de_um_cargo_compartilhado_considera_todos_os_usuarios(
    amb: Ambiente,
) -> None:
    admin = _administrador_nao_gestor(amb)
    _segundo_gestor(amb)  # Ana e Eva compartilham o cargo Gestor
    sem_gestao = tuple(
        p
        for p in _cargo(amb, CARGO_GESTOR).permissoes.ativas()
        if p is not Permissao.GERIR_USUARIOS
    )
    _recusado(
        amb,
        CodigoErroAplicacao.ULTIMO_GESTOR,
        lambda: amb.servico_usuarios.definir_permissoes_do_cargo(admin, CARGO_GESTOR, sem_gestao),
    )
    assert len(_gestores_aptos(amb)) == 2  # nenhum dos dois perdeu a condição


def test_dlt18_o_cargo_compartilhado_pode_perder_a_gestao_se_outro_gestor_permanece(
    amb: Ambiente,
) -> None:
    admin = _administrador_nao_gestor(amb)
    chefia = _novo_cargo(amb, "Chefia", Permissao.GERIR_USUARIOS)
    fabio = amb.servico_usuarios.cadastrar(ANA, "Fábio", chefia, papel=Papel.GESTOR).id
    _segundo_gestor(amb)
    sem_gestao = tuple(
        p
        for p in _cargo(amb, CARGO_GESTOR).permissoes.ativas()
        if p is not Permissao.GERIR_USUARIOS
    )
    amb.servico_usuarios.definir_permissoes_do_cargo(admin, CARGO_GESTOR, sem_gestao)
    assert _gestores_aptos(amb) == [fabio]


def test_dlt18_alterar_permissoes_do_cargo_preservando_a_gestao_e_aceito(amb: Ambiente) -> None:
    admin = _administrador_nao_gestor(amb)
    amb.servico_usuarios.definir_permissoes_do_cargo(
        admin, CARGO_GESTOR, (Permissao.GERIR_USUARIOS, Permissao.VER_OS)
    )
    assert _gestores_aptos(amb) == [ANA]


def test_dlt18_o_gestor_apto_tambem_nao_e_excluido_quando_e_o_ultimo(amb: Ambiente) -> None:
    admin = _administrador_nao_gestor(amb)
    _recusado(
        amb, CodigoErroAplicacao.ULTIMO_GESTOR, lambda: amb.servico_usuarios.excluir(admin, ANA)
    )
    eva = _segundo_gestor(amb)
    amb.servico_usuarios.excluir(admin, eva)  # sem histórico e com Ana apta: aceito
    assert _gestores_aptos(amb) == [ANA]


def test_dlt18_mudar_o_papel_de_outro_gestor_preserva_quem_age(amb: Ambiente) -> None:
    eva = _segundo_gestor(amb)
    amb.servico_usuarios.alterar_papel(ANA, eva, Papel.TECNICO)
    assert _gestores_aptos(amb) == [ANA]  # quem altera o papel é, por construção, um gestor apto


def test_dlt18_sem_nenhum_gestor_apto_antes_a_regra_nao_impede_o_que_nao_o_elimina(
    amb: Ambiente,
) -> None:
    """A regra recusa a operação que **elimina** o último gestor apto; se ninguém era apto antes,
    nada foi eliminado e as demais operações seguem as outras regras."""
    admin = _administrador_nao_gestor(amb)
    sem_gestao = _novo_cargo(amb, "Operacional", Permissao.VER_OS)
    ana = _usuario(amb, ANA)
    ana.cargo = _cargo(amb, sem_gestao)
    amb.usuarios.salvar(ana)  # estado herdado de uma base sem gestor apto
    assert _gestores_aptos(amb) == []
    amb.servico_usuarios.desativar(admin, CARLA)
    assert not _usuario(amb, CARLA).ativo


def test_dlt18_a_recusa_nao_cria_usuario_nem_concede_permissao(amb: Ambiente) -> None:
    admin = _administrador_nao_gestor(amb)
    usuarios_antes = [u.id for u in amb.usuarios.listar()]
    permissoes_antes = _cargo(amb, CARGO_GESTOR).permissoes.ativas()
    _recusado(
        amb, CodigoErroAplicacao.ULTIMO_GESTOR, lambda: amb.servico_usuarios.desativar(admin, ANA)
    )
    assert [u.id for u in amb.usuarios.listar()] == usuarios_antes  # nenhum usuário criado
    assert _cargo(amb, CARGO_GESTOR).permissoes.ativas() == permissoes_antes  # nada concedido


def test_dlt18_a_autorizacao_e_a_primeira_verificacao(amb: Ambiente) -> None:
    # Carla não tem gerir_usuarios: a recusa é por autorização, não "último gestor".
    with pytest.raises(PermissaoNegadaError) as capturado:
        amb.servico_usuarios.desativar(CARLA, ANA)
    assert capturado.value.codigo is CodigoErro.SEM_PERMISSAO
    with pytest.raises(NaoEncontradoError):
        amb.servico_usuarios.desativar(INEXISTENTE, ANA)


# =========================================================================================
# REG-E-02 / DLT-19 — alteração de papel (ratificação)
# =========================================================================================


def test_dlt19_alterar_o_papel_exige_gestor_ativo_com_gerir_usuarios(amb: Ambiente) -> None:
    eva = _segundo_gestor(amb)
    # só a permissão: Bruno (Técnico com gerir_usuarios) não basta
    admin = _administrador_nao_gestor(amb)
    with pytest.raises(PermissaoNegadaError) as so_permissao:
        amb.servico_usuarios.alterar_papel(admin, CARLA, Papel.GESTOR)
    assert so_permissao.value.codigo is CodigoErro.SEM_PERMISSAO
    # só o papel: Gestor sem gerir_usuarios não basta
    sem_permissao = _novo_cargo(amb, "Supervisão", Permissao.VER_OS)
    supervisor = amb.servico_usuarios.cadastrar(ANA, "Sara", sem_permissao, papel=Papel.GESTOR).id
    with pytest.raises(PermissaoNegadaError) as so_papel:
        amb.servico_usuarios.alterar_papel(supervisor, CARLA, Papel.GESTOR)
    assert so_papel.value.codigo is CodigoErro.SEM_PERMISSAO
    # gestor inativo não basta
    amb.servico_usuarios.desativar(ANA, eva)
    with pytest.raises(PermissaoNegadaError) as inativo:
        amb.servico_usuarios.alterar_papel(eva, CARLA, Papel.GESTOR)
    assert inativo.value.codigo is CodigoErro.USUARIO_INATIVO
    assert _usuario(amb, CARLA).papel is Papel.TECNICO
    # as duas condições juntas bastam
    amb.servico_usuarios.alterar_papel(ANA, CARLA, Papel.GESTOR)
    assert _usuario(amb, CARLA).papel is Papel.GESTOR


def test_dlt19_a_exigencia_de_papel_gestor_nao_se_estende_as_outras_operacoes_de_gestao(
    amb: Ambiente,
) -> None:
    """Só a alteração de papel exige o papel Gestor; as demais dependem apenas da permissão."""
    admin = _administrador_nao_gestor(amb)
    usuarios = amb.servico_usuarios
    novo = usuarios.cadastrar(admin, "Diego", CARGO_TECNICO, papel=Papel.TECNICO).id
    usuarios.atualizar_dados(admin, novo, nome="Diego Silva")
    usuarios.alterar_cargo(admin, novo, CARGO_TECNICO)
    usuarios.desativar(admin, novo)
    usuarios.reativar(admin, novo)
    usuarios.definir_permissoes_do_cargo(
        admin, CARGO_TECNICO, (*_cargo(amb, CARGO_TECNICO).permissoes.ativas(),)
    )
    usuarios.excluir(admin, novo)
    assert usuarios.listar(admin)


def test_dlt19_a_precedencia_de_autorizacao_e_mantida(amb: Ambiente) -> None:
    with pytest.raises(NaoEncontradoError):
        amb.servico_usuarios.alterar_papel(INEXISTENTE, CARLA, Papel.GESTOR)
    with pytest.raises(PermissaoNegadaError):  # sem permissão vence um alvo inexistente
        amb.servico_usuarios.alterar_papel(BRUNO, INEXISTENTE, Papel.GESTOR)
    with pytest.raises(NaoEncontradoError):
        amb.servico_usuarios.alterar_papel(ANA, INEXISTENTE, Papel.GESTOR)


# =========================================================================================
# REG-E-03 / DLT-20 — autoproteção estendida (ratificação)
# =========================================================================================


def test_dlt20_um_gestor_nao_retira_de_si_mesmo_o_papel_gestor(amb: Ambiente) -> None:
    erro = _recusado(
        amb,
        CodigoErroAplicacao.AUTOREMOCAO_DE_ACESSO_DE_GESTAO,
        lambda: amb.servico_usuarios.alterar_papel(ANA, ANA, Papel.TECNICO),
    )
    assert "gestor" in str(erro)
    amb.servico_usuarios.alterar_papel(ANA, ANA, Papel.GESTOR)  # manter o papel é permitido


def test_dlt20_ninguem_desativa_a_propria_conta(amb: Ambiente) -> None:
    eva = _segundo_gestor(amb)  # mesmo com outro gestor apto, a própria conta não se desativa
    erro = _recusado(
        amb,
        CodigoErroAplicacao.AUTOREMOCAO_DE_ACESSO_DE_GESTAO,
        lambda: amb.servico_usuarios.desativar(eva, eva),
    )
    assert "próprio" in str(erro)


def test_dlt20_a_autoprotecao_vem_antes_do_ultimo_gestor(amb: Ambiente) -> None:
    """Ana é a única apta e tenta a si mesma: o erro é o da autoproteção (preservado, DLT-12)."""
    _recusado(
        amb,
        CodigoErroAplicacao.AUTOREMOCAO_DE_ACESSO_DE_GESTAO,
        lambda: amb.servico_usuarios.desativar(ANA, ANA),
    )


def test_dlt20_nao_ha_outras_restricoes_de_autoprotecao(amb: Ambiente) -> None:
    """Só as proteções aprovadas: o gestor ainda edita os próprios dados, a própria
    disponibilidade e troca para um cargo que preserva a gestão."""
    amb.servico_usuarios.atualizar_dados(ANA, ANA, nome="Ana S.", email="a@x.com", escala="Seg")
    amb.servico_disponibilidade.alterar_minha_disponibilidade(
        ANA, _usuario(amb, ANA).disponibilidade
    )
    amb.servico_usuarios.alterar_cargo(ANA, ANA, CARGO_GESTOR)
    amb.servico_usuarios.reativar(ANA, ANA)
    assert _usuario(amb, ANA).nome == "Ana S."


# =========================================================================================
# REG-E-04 / DLT-21 — OS ativas impedem desativar e deixar o papel Técnico
# =========================================================================================


def _aguardando_peca(amb: Ambiente) -> int:
    numero = em_execucao(amb, BRUNO)
    amb.servico_ordens.alterar_status(BRUNO, numero, StatusOS.AGUARDANDO_PECA)
    return numero


def _concluida(amb: Ambiente) -> int:
    numero = aguardando_aprovacao(amb)
    amb.servico_ordens.aprovar(ANA, numero)
    return numero


def _cancelada(amb: Ambiente) -> int:
    numero = atribuida(amb, BRUNO)
    amb.servico_ordens.cancelar(ANA, numero, "Chamado indevido")
    return numero


ATIVAS = [
    pytest.param(lambda amb: atribuida(amb, BRUNO), StatusOS.ATRIBUIDA, id="atribuida"),
    pytest.param(lambda amb: em_execucao(amb, BRUNO), StatusOS.EM_EXECUCAO, id="em_execucao"),
    pytest.param(_aguardando_peca, StatusOS.AGUARDANDO_PECA, id="aguardando_peca"),
    pytest.param(aguardando_aprovacao, StatusOS.AGUARDANDO_APROVACAO, id="aguardando_aprovacao"),
]
ENCERRADAS = [
    pytest.param(_concluida, StatusOS.CONCLUIDA, id="concluida"),
    pytest.param(_cancelada, StatusOS.CANCELADA, id="cancelada"),
]


@pytest.mark.parametrize(("construir", "status"), ATIVAS)
def test_dlt21_usuario_com_os_ativa_nao_e_desativado(
    amb: Ambiente, construir: Callable[[Ambiente], int], status: StatusOS
) -> None:
    numero = construir(amb)
    assert guardada(amb, numero).status is status
    historico = guardada(amb, numero).servicos
    erro = _recusado(
        amb,
        CodigoErroAplicacao.USUARIO_COM_OS_ATIVAS,
        lambda: amb.servico_usuarios.desativar(ANA, BRUNO),
    )
    assert "ordens de serviço ativas" in str(erro)
    assert _usuario(amb, BRUNO).ativo
    os_ = guardada(amb, numero)
    assert (os_.status, os_.servicos) == (status, historico)  # OS e histórico preservados
    assert os_.tecnico_atribuido == _usuario(amb, BRUNO)  # nenhuma reatribuição


@pytest.mark.parametrize(("construir", "status"), ATIVAS)
def test_dlt21_tecnico_com_os_ativa_nao_muda_de_papel(
    amb: Ambiente, construir: Callable[[Ambiente], int], status: StatusOS
) -> None:
    numero = construir(amb)
    historico = guardada(amb, numero).servicos
    _recusado(
        amb,
        CodigoErroAplicacao.USUARIO_COM_OS_ATIVAS,
        lambda: amb.servico_usuarios.alterar_papel(ANA, BRUNO, Papel.GESTOR),
    )
    assert _usuario(amb, BRUNO).papel is Papel.TECNICO
    assert (guardada(amb, numero).status, guardada(amb, numero).servicos) == (status, historico)


@pytest.mark.parametrize(("construir", "status"), ENCERRADAS)
def test_dlt21_com_a_os_encerrada_a_desativacao_e_a_mudanca_de_papel_sao_aceitas(
    amb: Ambiente, construir: Callable[[Ambiente], int], status: StatusOS
) -> None:
    numero = construir(amb)
    historico = guardada(amb, numero).servicos
    amb.servico_usuarios.alterar_papel(ANA, BRUNO, Papel.GESTOR)
    amb.servico_usuarios.alterar_papel(ANA, BRUNO, Papel.TECNICO)
    amb.servico_usuarios.desativar(ANA, BRUNO)
    assert not _usuario(amb, BRUNO).ativo
    os_ = guardada(amb, numero)
    assert (os_.status, os_.servicos) == (status, historico)  # o histórico não é tocado
    assert os_.tecnico_atribuido == _usuario(amb, BRUNO)


def test_dlt21_usuario_sem_os_e_desativado_e_muda_de_papel(amb: Ambiente) -> None:
    amb.servico_usuarios.alterar_papel(ANA, CARLA, Papel.GESTOR)
    amb.servico_usuarios.desativar(ANA, BRUNO)
    assert not _usuario(amb, BRUNO).ativo


def test_dlt21_so_conta_a_os_sob_responsabilidade_do_usuario(amb: Ambiente) -> None:
    """OS de outro técnico, ou aberta pelo usuário sem ser dele, não impede nada."""
    atribuida(amb, BRUNO)  # aberta por Carla, atribuída a Bruno
    amb.servico_usuarios.desativar(ANA, CARLA)
    assert not _usuario(amb, CARLA).ativo


def test_dlt21_a_mudanca_de_cargo_que_preserva_o_papel_tecnico_nao_e_impedida(
    amb: Ambiente,
) -> None:
    atribuida(amb, BRUNO)
    outro = _novo_cargo(amb, "Técnico sênior", *_cargo(amb, CARGO_TECNICO).permissoes.ativas())
    amb.servico_usuarios.alterar_cargo(ANA, BRUNO, outro)
    usuario = _usuario(amb, BRUNO)
    assert (usuario.cargo.id, usuario.papel, usuario.atribuivel) == (outro, Papel.TECNICO, True)


def test_dlt21_o_gestor_resolve_as_os_a_mao_e_entao_desativa(amb: Ambiente) -> None:
    """Nada é reatribuído sozinho: o gestor transfere a OS e só então a desativação passa."""
    numero = em_execucao(amb, BRUNO)
    _recusado(
        amb,
        CodigoErroAplicacao.USUARIO_COM_OS_ATIVAS,
        lambda: amb.servico_usuarios.desativar(ANA, BRUNO),
    )
    amb.servico_ordens.atribuir(ANA, numero, CARLA)
    amb.servico_usuarios.desativar(ANA, BRUNO)
    assert guardada(amb, numero).tecnico_atribuido == _usuario(amb, CARLA)


def test_dlt21_desativar_quem_ja_esta_inativo_continua_idempotente(amb: Ambiente) -> None:
    atribuida(amb, BRUNO)
    bruno = _usuario(amb, BRUNO)
    bruno.desativar()
    amb.usuarios.salvar(bruno)  # estado herdado: inativo com OS (não alcançável pelo serviço)
    antes = _estado(amb)
    amb.servico_usuarios.desativar(ANA, BRUNO)
    assert _estado(amb) == antes


def test_dlt21_a_autorizacao_vem_antes_da_regra_das_os(amb: Ambiente) -> None:
    atribuida(amb, BRUNO)
    with pytest.raises(PermissaoNegadaError) as capturado:
        amb.servico_usuarios.desativar(CARLA, BRUNO)
    assert capturado.value.codigo is CodigoErro.SEM_PERMISSAO
    with pytest.raises(PermissaoNegadaError):
        amb.servico_usuarios.alterar_papel(CARLA, BRUNO, Papel.GESTOR)


def test_dlt21_nao_cancela_nem_reatribui_automaticamente(amb: Ambiente) -> None:
    primeira = atribuida(amb, BRUNO)
    segunda = em_execucao(amb, BRUNO)
    antes = [instantaneo(guardada(amb, n)) for n in (primeira, segunda)]
    operacoes: tuple[Operacao, ...] = (
        lambda: amb.servico_usuarios.desativar(ANA, BRUNO),
        lambda: amb.servico_usuarios.alterar_papel(ANA, BRUNO, Papel.GESTOR),
    )
    for operacao in operacoes:
        with pytest.raises(RegraDeAplicacaoError):
            operacao()
    assert [instantaneo(guardada(amb, n)) for n in (primeira, segunda)] == antes
