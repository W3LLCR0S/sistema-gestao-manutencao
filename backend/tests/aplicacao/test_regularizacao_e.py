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

import inspect
from collections.abc import Callable
from typing import Any

import pytest

from manutencao.application.dto import PecaInformada
from manutencao.application.erros import (
    CodigoErroAplicacao,
    NaoEncontradoError,
    RegraDeAplicacaoError,
)
from manutencao.domain.cargo import Cargo
from manutencao.domain.enums import Disponibilidade, Papel, StatusOS, TipoServico
from manutencao.domain.erros import (
    CodigoErro,
    ConflitoDeEstadoError,
    PermissaoNegadaError,
    ViolacaoDeRegraError,
)
from manutencao.domain.permissoes import Permissao, Permissoes
from manutencao.domain.usuario import Usuario
from tests.apoio.ambiente import (
    ANA,
    BRUNO,
    CARGO_GESTOR,
    CARGO_TECNICO,
    CARLA,
    Ambiente,
    criar_ambiente,
)
from tests.apoio.caminhos import (
    aguardando_aprovacao,
    atribuida,
    em_execucao,
    guardada,
    reparo_finalizado,
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


def test_dlt18_exclusao_do_ultimo_gestor_respeita_a_precedencia_das_recusas(
    amb: Ambiente,
) -> None:
    """Autorização → existência → autoexclusão → histórico → último gestor; sem mutação."""
    # 1. autorização: quem não gere usuários recebe a recusa de permissão, não a do último gestor
    antes = _estado(amb)
    with pytest.raises(PermissaoNegadaError) as sem_permissao:
        amb.servico_usuarios.excluir(CARLA, ANA)
    assert sem_permissao.value.codigo is CodigoErro.SEM_PERMISSAO
    assert _estado(amb) == antes
    admin = _administrador_nao_gestor(amb)
    antes = _estado(amb)
    # 2. existência
    with pytest.raises(NaoEncontradoError):
        amb.servico_usuarios.excluir(admin, INEXISTENTE)
    assert _estado(amb) == antes
    # 3. autoexclusão (a própria Ana, último gestor, é recusada como autoexclusão)
    _recusado(amb, CodigoErroAplicacao.AUTOEXCLUSAO, lambda: amb.servico_usuarios.excluir(ANA, ANA))
    # 4. histórico antes do último gestor: Ana tem histórico (abriu e atribuiu uma OS)
    atribuida(amb)
    _recusado(
        amb,
        CodigoErroAplicacao.USUARIO_COM_HISTORICO,
        lambda: amb.servico_usuarios.excluir(admin, ANA),
    )
    assert [u.id for u in amb.usuarios.listar() if u.id == ANA] == [ANA]


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


# =========================================================================================
# REG-E-05 / DLT-22 — observação e descrição de peça obrigatórias
# =========================================================================================

VAZIOS = ["", " ", "   ", "\t", "\n", " \t\n "]


@pytest.mark.parametrize("texto", VAZIOS)
def test_dlt22_observacao_vazia_ou_so_com_espacos_e_recusada_sem_mutacao(
    amb: Ambiente, texto: str
) -> None:
    numero = em_execucao(amb, BRUNO)
    antes = _estado(amb)
    for autor in (ANA, BRUNO, CARLA):  # gestor, responsável e quem abriu
        with pytest.raises(ViolacaoDeRegraError) as capturado:
            amb.servico_ordens.adicionar_apontamento(autor, numero, texto)
        assert capturado.value.codigo is CodigoErro.CAMPO_OBRIGATORIO
        assert "observação" in str(capturado.value)
    assert _estado(amb) == antes  # nem o histórico nem os números mudaram


def test_dlt22_observacao_valida_e_aceita_e_guardada_como_informada(amb: Ambiente) -> None:
    numero = em_execucao(amb, BRUNO)
    antes = len(guardada(amb, numero).servicos)
    amb.servico_ordens.adicionar_apontamento(CARLA, numero, "  Ruído no eixo  ")
    registro = guardada(amb, numero).servicos[-1]
    assert (registro.tipo, registro.descricao) == (TipoServico.APONTAMENTO, "  Ruído no eixo  ")
    assert len(guardada(amb, numero).servicos) == antes + 1


def test_dlt22_precedencia_autorizacao_vinculo_estado_e_so_depois_o_conteudo(
    amb: Ambiente,
) -> None:
    ativa = em_execucao(amb, BRUNO)
    encerrada = aguardando_aprovacao(amb)
    amb.servico_ordens.aprovar(ANA, encerrada)
    ordens = amb.servico_ordens
    novo = amb.servico_usuarios.cadastrar(ANA, "Diego", CARGO_TECNICO, papel=Papel.TECNICO).id
    antes = _estado(amb)
    # 1. sem a permissão: recusa por autorização, mesmo com o texto vazio e a OS inexistente
    cargo = _cargo(amb, CARGO_TECNICO)
    cargo.permissoes.definir(
        [p for p in cargo.permissoes.ativas() if p is not Permissao.REGISTRAR_APONTAMENTO]
    )
    amb.cargos.salvar(cargo)
    with pytest.raises(PermissaoNegadaError) as a:
        ordens.adicionar_apontamento(CARLA, INEXISTENTE, "")
    assert a.value.codigo is CodigoErro.SEM_PERMISSAO
    cargo.permissoes.definir(Permissoes.padrao_tecnico().ativas())
    amb.cargos.salvar(cargo)
    # 2. sem vínculo com a OS: recusa por vínculo, com o texto vazio
    with pytest.raises(PermissaoNegadaError) as b:
        ordens.adicionar_apontamento(novo, ativa, "   ")
    assert b.value.codigo is CodigoErro.SEM_VINCULO_COM_A_OS
    # 3. OS encerrada: recusa por estado, com o texto vazio
    with pytest.raises(ConflitoDeEstadoError) as c:
        ordens.adicionar_apontamento(ANA, encerrada, "   ")
    assert c.value.codigo is CodigoErro.OS_ENCERRADA
    # 4. só então o conteúdo
    with pytest.raises(ViolacaoDeRegraError) as d:
        ordens.adicionar_apontamento(ANA, ativa, "   ")
    assert d.value.codigo is CodigoErro.CAMPO_OBRIGATORIO
    assert _estado(amb) == antes


@pytest.mark.parametrize("descricao", VAZIOS)
def test_dlt22_peca_com_descricao_vazia_e_recusada_e_a_os_nao_inicia_a_execucao(
    amb: Ambiente, descricao: str
) -> None:
    numero = atribuida(amb, BRUNO)
    antes = _estado(amb)
    with pytest.raises(ViolacaoDeRegraError) as capturado:
        amb.servico_ordens.apontar_reparo(
            BRUNO, numero, 1.0, "Troca", [PecaInformada(descricao, 1)]
        )
    assert capturado.value.codigo is CodigoErro.CAMPO_OBRIGATORIO
    assert "descrição da peça" in str(capturado.value)
    assert _estado(amb) == antes
    assert guardada(amb, numero).status is StatusOS.ATRIBUIDA  # não iniciou a execução
    assert guardada(amb, numero).pecas_utilizadas == ()


def test_dlt22_uma_peca_invalida_entre_varias_recusa_o_apontamento_inteiro(amb: Ambiente) -> None:
    numero = atribuida(amb, BRUNO)
    antes = _estado(amb)
    with pytest.raises(ViolacaoDeRegraError):
        amb.servico_ordens.apontar_reparo(
            BRUNO, numero, 1.0, "Troca", [PecaInformada("Rolamento", 1), PecaInformada("  ", 1)]
        )
    assert _estado(amb) == antes


def test_dlt22_peca_valida_e_aceita_com_o_texto_como_informado(amb: Ambiente) -> None:
    numero = atribuida(amb, BRUNO)
    amb.servico_ordens.apontar_reparo(
        BRUNO, numero, 1.0, "Troca", [PecaInformada(" Rolamento 6204 ", 2)]
    )
    peca = guardada(amb, numero).pecas_utilizadas[0]
    assert (peca.descricao, peca.quantidade) == (" Rolamento 6204 ", 2)


def test_dlt22_a_ordem_herdada_de_pecas_e_horas_e_preservada(amb: Ambiente) -> None:
    """As peças são validadas antes da OS e das horas (como no legado): a quantidade antes da
    descrição, e ambas antes das horas negativas ou da intervenção vazia."""
    numero = atribuida(amb, BRUNO)
    ordens = amb.servico_ordens
    with pytest.raises(ViolacaoDeRegraError) as quantidade:
        ordens.apontar_reparo(BRUNO, numero, -1.0, "", [PecaInformada("", 0)])
    assert quantidade.value.codigo is CodigoErro.QUANTIDADE_INVALIDA
    with pytest.raises(ViolacaoDeRegraError) as descricao:
        ordens.apontar_reparo(BRUNO, numero, -1.0, "", [PecaInformada(" ", 1)])
    assert descricao.value.codigo is CodigoErro.CAMPO_OBRIGATORIO
    with pytest.raises(NaoEncontradoError):  # a peça válida segue para a OS, que não existe
        ordens.apontar_reparo(BRUNO, INEXISTENTE, 1.0, "i", [PecaInformada("x", 1)])
    with pytest.raises(PermissaoNegadaError):  # a autorização (permissão) vem antes de tudo
        ordens.apontar_reparo(ANA, numero, 1.0, "i", [PecaInformada(" ", 1)])
    with pytest.raises(ViolacaoDeRegraError) as sem_posse:  # a peça é validada antes da posse
        ordens.apontar_reparo(CARLA, numero, 1.0, "i", [PecaInformada(" ", 1)])
    assert sem_posse.value.codigo is CodigoErro.CAMPO_OBRIGATORIO
    with pytest.raises(ViolacaoDeRegraError) as horas:
        ordens.apontar_reparo(BRUNO, numero, -1.0, "i", [PecaInformada("x", 1)])
    assert horas.value.codigo is CodigoErro.HORAS_NEGATIVAS


def test_dlt22_os_campos_nao_listados_continuam_opcionais(amb: Ambiente) -> None:
    """Modelo do equipamento, teste funcional, e-mail e escala seguem sem obrigatoriedade."""
    equipamento = amb.servico_equipamentos.cadastrar(ANA, "Prensa", "")
    assert equipamento.modelo == ""
    usuario = amb.servico_usuarios.cadastrar(
        ANA, "Diego", CARGO_TECNICO, "", "", papel=Papel.TECNICO
    )
    assert (usuario.email, usuario.escala) == ("", "")
    numero = reparo_finalizado(amb)
    assert amb.servico_ordens.concluir_tecnicamente(BRUNO, numero, "", True) is True
    assert guardada(amb, numero).teste_funcional == ""


# =========================================================================================
# REG-E-06 / DLT-23 — disponibilidade manual (só Disponível e Ausente) e política única
# =========================================================================================

Via = Callable[[Ambiente, int, int, Disponibilidade], object]


def _alterar_pela_gestao(amb: Ambiente, ator: int, alvo: int, valor: Disponibilidade) -> object:
    return amb.servico_usuarios.definir_disponibilidade(ator, alvo, valor)


def _alterar_pela_disponibilidade(
    amb: Ambiente, ator: int, alvo: int, valor: Disponibilidade
) -> object:
    return amb.servico_disponibilidade.alterar_disponibilidade(ator, alvo, valor)


VIAS = [
    pytest.param(_alterar_pela_gestao, id="ServicoDeUsuarios.definir_disponibilidade"),
    pytest.param(_alterar_pela_disponibilidade, id="ServicoDeDisponibilidade.alterar"),
]


@pytest.mark.parametrize("via", VIAS)
@pytest.mark.parametrize("valor", [Disponibilidade.DISPONIVEL, Disponibilidade.AUSENTE])
def test_dlt23_disponivel_e_ausente_sao_aceitos_como_valor_manual(
    amb: Ambiente, via: Via, valor: Disponibilidade
) -> None:
    via(amb, CARLA, CARLA, valor)
    assert _usuario(amb, CARLA).disponibilidade is valor


@pytest.mark.parametrize("via", VIAS)
def test_dlt23_em_atendimento_nao_pode_ser_gravado_manualmente(amb: Ambiente, via: Via) -> None:
    antes = _estado(amb)
    for ator, alvo in ((CARLA, CARLA), (ANA, CARLA), (ANA, ANA)):  # própria e de terceiro
        with pytest.raises(ViolacaoDeRegraError) as capturado:
            via(amb, ator, alvo, Disponibilidade.EM_ATENDIMENTO)
        assert capturado.value.codigo is CodigoErro.DISPONIBILIDADE_MANUAL_INVALIDA
        assert "derivado" in str(capturado.value)
    assert _estado(amb) == antes


def test_dlt23_em_atendimento_e_exclusivamente_derivado_das_os(amb: Ambiente) -> None:
    def efetiva(usuario: int) -> Disponibilidade:
        linhas = {linha.id: linha for linha in amb.servico_disponibilidade.consultar(ANA)}
        return linhas[usuario].disponibilidade

    assert efetiva(BRUNO) is Disponibilidade.DISPONIVEL
    em_execucao(amb, BRUNO)
    assert efetiva(BRUNO) is Disponibilidade.EM_ATENDIMENTO  # derivado
    assert _usuario(amb, BRUNO).disponibilidade is Disponibilidade.DISPONIVEL  # nada gravado
    amb.servico_disponibilidade.alterar_minha_disponibilidade(BRUNO, Disponibilidade.AUSENTE)
    assert efetiva(BRUNO) is Disponibilidade.AUSENTE  # a ausência manual prevalece
    amb.servico_disponibilidade.alterar_minha_disponibilidade(BRUNO, Disponibilidade.DISPONIVEL)
    assert efetiva(BRUNO) is Disponibilidade.EM_ATENDIMENTO


@pytest.mark.parametrize("via", VIAS)
def test_dlt23_o_usuario_altera_a_propria_disponibilidade_sem_permissao_de_gestao(
    amb: Ambiente, via: Via
) -> None:
    via(amb, BRUNO, BRUNO, Disponibilidade.AUSENTE)  # Bruno não tem gerir_usuarios
    assert _usuario(amb, BRUNO).disponibilidade is Disponibilidade.AUSENTE


@pytest.mark.parametrize("via", VIAS)
def test_dlt23_o_gestor_autorizado_altera_a_de_terceiros(amb: Ambiente, via: Via) -> None:
    via(amb, ANA, BRUNO, Disponibilidade.AUSENTE)
    assert _usuario(amb, BRUNO).disponibilidade is Disponibilidade.AUSENTE


@pytest.mark.parametrize("via", VIAS)
def test_dlt23_terceiro_sem_autorizacao_e_recusado_sem_mutacao(amb: Ambiente, via: Via) -> None:
    antes = _estado(amb)
    with pytest.raises(PermissaoNegadaError) as capturado:
        via(amb, BRUNO, CARLA, Disponibilidade.AUSENTE)
    assert capturado.value.codigo is CodigoErro.SEM_PERMISSAO
    with pytest.raises(PermissaoNegadaError):  # a autorização vence um alvo inexistente (DLT-16)
        via(amb, BRUNO, INEXISTENTE, Disponibilidade.AUSENTE)
    assert _estado(amb) == antes


@pytest.mark.parametrize("via", VIAS)
def test_dlt23_ator_inexistente_e_inativo_sao_recusados(amb: Ambiente, via: Via) -> None:
    with pytest.raises(NaoEncontradoError):
        via(amb, INEXISTENTE, CARLA, Disponibilidade.AUSENTE)
    amb.servico_usuarios.desativar(ANA, CARLA)
    with pytest.raises(PermissaoNegadaError) as capturado:
        via(amb, CARLA, CARLA, Disponibilidade.AUSENTE)
    assert capturado.value.codigo is CodigoErro.USUARIO_INATIVO


def _resultado(amb: Ambiente, via: Via, ator: int, alvo: int, valor: Disponibilidade) -> object:
    try:
        via(amb, ator, alvo, valor)
    except (PermissaoNegadaError, ViolacaoDeRegraError, NaoEncontradoError) as erro:
        return (type(erro).__name__, erro.codigo, str(erro))
    return "aceito"


@pytest.mark.parametrize("valor", list(Disponibilidade))
@pytest.mark.parametrize("alvo", [ANA, BRUNO, CARLA, INEXISTENTE])
@pytest.mark.parametrize("ator", [ANA, BRUNO, CARLA, INEXISTENTE])
def test_dlt23_as_duas_vias_decidem_igual_e_deixam_o_mesmo_estado(
    ator: int, alvo: int, valor: Disponibilidade
) -> None:
    """Uma única política: o mesmo resultado, o mesmo erro e o mesmo estado nas duas vias, para
    todas as combinações de ator, alvo e valor."""
    a, b = criar_ambiente(), criar_ambiente()
    resultado_a = _resultado(a, _alterar_pela_gestao, ator, alvo, valor)
    resultado_b = _resultado(b, _alterar_pela_disponibilidade, ator, alvo, valor)
    assert resultado_a == resultado_b
    assert _estado(a) == _estado(b)


def test_dlt23_as_duas_vias_delegam_a_mesma_politica_sem_duplicar_a_autorizacao() -> None:
    from manutencao.application.servicos import disponibilidade, usuarios

    for modulo in (usuarios, disponibilidade):
        assert "alterar_disponibilidade_manual" in inspect.getsource(modulo)
    assert "Permissao.GERIR_USUARIOS" not in inspect.getsource(disponibilidade)
