"""Autorização nos serviços de aplicação: DLT-12 a DLT-17 (regularização da Operação D).

Cada teste prova duas coisas: o que é recusado (com o erro tipado) e que **nada mudou** (nenhum
repositório e nenhum identificador consumido). O legado permitia todas estas operações diretamente;
o comportamento antigo é caracterizado em ``tests/caracterizacao`` (ver ``deltas.py``).

* DLT-12 autoproteção do gestor        * DLT-15 disponibilidade de terceiros
* DLT-13 autorização de gestão         * DLT-16 precedência da autorização
* DLT-14 autorização de leitura        * DLT-17 ator inexistente
"""

from collections.abc import Callable
from typing import Any

import pytest

from manutencao.application.dto import PecaInformada
from manutencao.application.erros import (
    CodigoErroAplicacao,
    NaoEncontradoError,
    RegraDeAplicacaoError,
)
from manutencao.application.portas.repositorios import FiltroDeOrdens
from manutencao.domain.enums import Criticidade, Disponibilidade, StatusOS
from manutencao.domain.erros import CodigoErro, PermissaoNegadaError, ViolacaoDeRegraError
from manutencao.domain.ordem_servico import OrdemServico
from manutencao.domain.permissoes import Permissao
from tests.apoio.ambiente import (
    ANA,
    BRUNO,
    CARGO_GESTOR,
    CARGO_TECNICO,
    CARLA,
    COMPRESSOR,
    TORNO,
    Ambiente,
)
from tests.caracterizacao.cenarios import PERMISSOES_DO_SISTEMA

INEXISTENTE = 99


# --------------------------------------------------------------------------------- apoio


def _definir_permissoes(amb: Ambiente, cargo_id: int, *permissoes: Permissao) -> None:
    """Preparação de cenário: define as permissões de um cargo direto no repositório."""
    cargo = amb.cargos.obter(cargo_id)
    assert cargo is not None
    cargo.permissoes.definir(permissoes)
    amb.cargos.salvar(cargo)


def _estado(amb: Ambiente) -> tuple[Any, ...]:
    """Tudo o que uma recusa não pode alterar, inclusive o próximo id de cada sequência."""
    return (
        amb.usuarios.listar(),
        [(c.id, c.permissoes.ativas()) for c in amb.cargos.listar()],
        amb.equipamentos.listar(),
        amb.ordens.listar(),
        amb.usuarios.proximo_id(),
        amb.equipamentos.proximo_id(),
        amb.ordens.proximo_numero(),
    )


def _abrir_os(amb: Ambiente, *, por: int = CARLA, tecnico: int | None = None) -> int:
    """Uma OS no repositório (preparação), aberta por ``por`` e, se pedido, atribuída ao técnico."""
    torno = amb.equipamentos.obter(TORNO)
    abridor = amb.usuarios.obter(por)
    assert torno is not None
    assert abridor is not None
    ordem = OrdemServico.abrir(
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
        ordem.atribuir(alvo, gestor, quando=amb.relogio.agora())
    amb.ordens.adicionar(ordem)
    return ordem.numero


def _recusa_por_permissao(operacao: Callable[[], object], permissao: Permissao) -> None:
    with pytest.raises(PermissaoNegadaError) as erro:
        operacao()
    assert erro.value.codigo is CodigoErro.SEM_PERMISSAO
    assert permissao.descricao in erro.value.mensagem


# =========================================================================================
# DLT-12 — autoproteção do gestor
# =========================================================================================


def test_dlt12_gestor_nao_troca_o_proprio_cargo_por_um_sem_gestao(amb: Ambiente) -> None:
    antes = _estado(amb)
    with pytest.raises(RegraDeAplicacaoError) as erro:
        amb.servico_usuarios.alterar_cargo(ANA, ANA, CARGO_TECNICO)
    assert erro.value.codigo is CodigoErroAplicacao.AUTOREMOCAO_DE_ACESSO_DE_GESTAO
    assert _estado(amb) == antes
    ana = amb.usuarios.obter(ANA)
    assert ana is not None
    assert ana.pode(Permissao.GERIR_USUARIOS)


def test_dlt12_gestor_nao_remove_do_proprio_cargo_o_acesso_de_gestao(amb: Ambiente) -> None:
    antes = _estado(amb)
    sem_gestao = [p for p in Permissao if p is not Permissao.GERIR_USUARIOS]
    for selecao in (sem_gestao, [], [Permissao.VER_OS, Permissao.GERIR_EQUIPAMENTOS]):
        with pytest.raises(RegraDeAplicacaoError) as erro:
            amb.servico_usuarios.definir_permissoes_do_cargo(ANA, CARGO_GESTOR, selecao)
        assert erro.value.codigo is CodigoErroAplicacao.AUTOREMOCAO_DE_ACESSO_DE_GESTAO
        assert _estado(amb) == antes


def test_dlt12_reduzir_as_permissoes_do_proprio_cargo_so_e_recusado_se_perder_a_gestao(
    amb: Ambiente,
) -> None:
    """Reduzir é permitido enquanto o cargo mantém gerir_usuarios (a proteção é exata)."""
    mantendo = [Permissao.GERIR_USUARIOS, Permissao.VER_OS]
    cargo = amb.servico_usuarios.definir_permissoes_do_cargo(ANA, CARGO_GESTOR, mantendo)
    assert set(cargo.permissoes.ativas()) == set(mantendo)
    guardado = amb.cargos.obter(CARGO_GESTOR)
    assert guardado is not None
    assert set(guardado.permissoes.ativas()) == set(mantendo)


def test_dlt12_alteracoes_que_preservam_a_autorizacao_sao_permitidas(amb: Ambiente) -> None:
    # um segundo cargo com gestão: o gestor pode trocar para ele
    _definir_permissoes(amb, CARGO_TECNICO, Permissao.GERIR_USUARIOS, Permissao.VER_OS)
    amb.servico_usuarios.alterar_cargo(ANA, ANA, CARGO_TECNICO)
    ana = amb.usuarios.obter(ANA)
    assert ana is not None
    assert (ana.cargo.id, ana.pode(Permissao.GERIR_USUARIOS)) == (CARGO_TECNICO, True)
    # trocar para o mesmo cargo também preserva a autorização
    amb.servico_usuarios.alterar_cargo(ANA, ANA, CARGO_TECNICO)


def test_dlt12_a_protecao_e_so_do_proprio_gestor_outros_usuarios_podem_perder_o_acesso(
    amb: Ambiente,
) -> None:
    outra = amb.servico_usuarios.cadastrar(ANA, "Eva", CARGO_GESTOR)
    amb.servico_usuarios.alterar_cargo(ANA, outra.id, CARGO_TECNICO)  # Ana rebaixa a Eva
    rebaixada = amb.usuarios.obter(outra.id)
    assert rebaixada is not None
    assert not rebaixada.pode(Permissao.GERIR_USUARIOS)


def test_dlt12_a_protecao_nao_depende_de_interface_nem_do_id_do_cargo(amb: Ambiente) -> None:
    """Uma gestora com outro cargo de gestão não pode esvaziá-lo estando nele."""
    _definir_permissoes(amb, CARGO_TECNICO, Permissao.GERIR_USUARIOS)
    eva = amb.servico_usuarios.cadastrar(ANA, "Eva", CARGO_TECNICO)
    antes = _estado(amb)
    with pytest.raises(RegraDeAplicacaoError) as erro:
        amb.servico_usuarios.definir_permissoes_do_cargo(eva.id, CARGO_TECNICO, [Permissao.VER_OS])
    assert erro.value.codigo is CodigoErroAplicacao.AUTOREMOCAO_DE_ACESSO_DE_GESTAO
    assert _estado(amb) == antes
    # a Ana (de outro cargo) pode: não é o próprio cargo dela
    amb.servico_usuarios.definir_permissoes_do_cargo(ANA, CARGO_TECNICO, [Permissao.VER_OS])


# =========================================================================================
# DLT-13 — autorização de gestão
# =========================================================================================


def test_dlt13_gestao_de_equipamentos_exige_gerir_equipamentos(amb: Ambiente) -> None:
    antes = _estado(amb)
    s = amb.servico_equipamentos
    operacoes: tuple[Callable[[], object], ...] = (
        lambda: s.cadastrar(BRUNO, "Prensa", "P1"),
        lambda: s.atualizar(BRUNO, TORNO, "Torno 2", "T2"),
        lambda: s.inativar(BRUNO, TORNO),
        lambda: s.reativar(BRUNO, TORNO),
        lambda: s.excluir(BRUNO, COMPRESSOR),
    )
    for operacao in operacoes:
        _recusa_por_permissao(operacao, Permissao.GERIR_EQUIPAMENTOS)
        assert _estado(amb) == antes


def test_dlt13_gestao_de_usuarios_e_cargos_exige_gerir_usuarios(amb: Ambiente) -> None:
    antes = _estado(amb)
    s = amb.servico_usuarios
    operacoes: tuple[Callable[[], object], ...] = (
        lambda: s.cadastrar(BRUNO, "Diego", CARGO_TECNICO),
        lambda: s.atualizar_dados(BRUNO, CARLA, nome="Outro nome"),
        lambda: s.alterar_cargo(BRUNO, CARLA, CARGO_GESTOR),
        lambda: s.definir_permissoes_do_cargo(BRUNO, CARGO_TECNICO, [Permissao.VER_OS]),
        lambda: s.definir_disponibilidade(BRUNO, CARLA, Disponibilidade.AUSENTE),
    )
    for operacao in operacoes:
        _recusa_por_permissao(operacao, Permissao.GERIR_USUARIOS)
        assert _estado(amb) == antes


def test_dlt13_exclusao_de_usuario_exige_gerir_usuarios(amb: Ambiente) -> None:
    novo = amb.servico_usuarios.cadastrar(ANA, "Diego", CARGO_TECNICO)
    antes = _estado(amb)
    _recusa_por_permissao(
        lambda: amb.servico_usuarios.excluir(BRUNO, novo.id), Permissao.GERIR_USUARIOS
    )
    assert _estado(amb) == antes
    assert amb.usuarios.obter(novo.id) is not None


def test_dlt13_a_recusa_nao_consome_identificadores(amb: Ambiente) -> None:
    proximos = (amb.usuarios.proximo_id(), amb.equipamentos.proximo_id())
    with pytest.raises(PermissaoNegadaError):
        amb.servico_usuarios.cadastrar(BRUNO, "Diego", CARGO_TECNICO)
    with pytest.raises(PermissaoNegadaError):
        amb.servico_equipamentos.cadastrar(BRUNO, "Prensa", "P1")
    assert (amb.usuarios.proximo_id(), amb.equipamentos.proximo_id()) == proximos
    # o cadastro autorizado seguinte recebe exatamente o identificador que não foi gasto
    assert amb.servico_usuarios.cadastrar(ANA, "Diego", CARGO_TECNICO).id == proximos[0]
    assert amb.servico_equipamentos.cadastrar(ANA, "Prensa", "P1").id == proximos[1]


def test_dlt13_com_autorizacao_valida_a_gestao_e_permitida(amb: Ambiente) -> None:
    equipamento = amb.servico_equipamentos.cadastrar(ANA, "Prensa", "P1")
    amb.servico_equipamentos.atualizar(ANA, equipamento.id, "Prensa 2", "P2")
    amb.servico_equipamentos.inativar(ANA, equipamento.id)
    amb.servico_equipamentos.reativar(ANA, equipamento.id)
    amb.servico_equipamentos.excluir(ANA, equipamento.id)
    usuario = amb.servico_usuarios.cadastrar(ANA, "Diego", CARGO_TECNICO)
    amb.servico_usuarios.atualizar_dados(ANA, usuario.id, nome="Diego Silva")
    amb.servico_usuarios.alterar_cargo(ANA, usuario.id, CARGO_GESTOR)
    amb.servico_usuarios.excluir(ANA, usuario.id)
    assert amb.equipamentos.obter(equipamento.id) is None
    assert amb.usuarios.obter(usuario.id) is None


def test_dlt13_a_permissao_vem_do_cargo_atual_e_nao_de_um_nome_fixo(amb: Ambiente) -> None:
    """Quem ganha o cargo com a permissão passa a poder; quem a perde deixa de poder."""
    _definir_permissoes(amb, CARGO_TECNICO, Permissao.GERIR_EQUIPAMENTOS)
    amb.servico_equipamentos.cadastrar(BRUNO, "Prensa", "P1")  # técnico com a permissão concedida
    _definir_permissoes(amb, CARGO_TECNICO)
    _recusa_por_permissao(
        lambda: amb.servico_equipamentos.cadastrar(BRUNO, "Outra", "P2"),
        Permissao.GERIR_EQUIPAMENTOS,
    )


def test_dlt13_nenhuma_permissao_nova_foi_criada() -> None:
    assert tuple(p.value for p in Permissao) == PERMISSOES_DO_SISTEMA


# =========================================================================================
# DLT-14 — autorização de leitura
# =========================================================================================


def _consultas_de_equipamentos(amb: Ambiente) -> tuple[Callable[[], object], ...]:
    s = amb.servico_equipamentos
    return (lambda: s.consultar(BRUNO, TORNO), lambda: s.listar(BRUNO))


def _consultas_de_os(amb: Ambiente) -> tuple[Callable[[], object], ...]:
    numero = _abrir_os(amb)
    s = amb.servico_ordens
    return (
        lambda: s.consultar(BRUNO, numero),
        lambda: s.listar(BRUNO),
        lambda: s.listar(BRUNO, FiltroDeOrdens(equipamento_id=TORNO)),
        lambda: s.historico(BRUNO, numero),
    )


def _consultas_de_disponibilidade(amb: Ambiente) -> tuple[Callable[[], object], ...]:
    s = amb.servico_disponibilidade
    return (lambda: s.consultar(BRUNO), lambda: s.consultar(BRUNO, ordenar_por_carga=True))


def _consultas_de_usuarios_e_cargos(amb: Ambiente) -> tuple[Callable[[], object], ...]:
    s = amb.servico_usuarios
    return (
        lambda: s.consultar(BRUNO, ANA),
        lambda: s.listar(BRUNO),
        lambda: s.listar_cargos(BRUNO),
    )


LEITURAS = [
    pytest.param(_consultas_de_equipamentos, Permissao.VER_EQUIPAMENTOS, id="ver_equipamentos"),
    pytest.param(_consultas_de_os, Permissao.VER_OS, id="ver_os"),
    pytest.param(_consultas_de_disponibilidade, Permissao.VER_DISPONIBILIDADE, id="ver_disp"),
    pytest.param(_consultas_de_usuarios_e_cargos, Permissao.GERIR_USUARIOS, id="usuarios_e_cargos"),
]


@pytest.mark.parametrize(("consultas", "permissao"), LEITURAS)
def test_dlt14_consulta_sem_a_permissao_correspondente_e_recusada(
    amb: Ambiente,
    consultas: Callable[[Ambiente], tuple[Callable[[], object], ...]],
    permissao: Permissao,
) -> None:
    operacoes = consultas(amb)
    _definir_permissoes(amb, CARGO_TECNICO, *(p for p in Permissao if p is not permissao))
    antes = _estado(amb)
    for operacao in operacoes:
        _recusa_por_permissao(operacao, permissao)
    assert _estado(amb) == antes


@pytest.mark.parametrize(("consultas", "permissao"), LEITURAS)
def test_dlt14_com_a_permissao_correspondente_a_consulta_e_permitida(
    amb: Ambiente,
    consultas: Callable[[Ambiente], tuple[Callable[[], object], ...]],
    permissao: Permissao,
) -> None:
    operacoes = consultas(amb)
    _definir_permissoes(amb, CARGO_TECNICO, permissao)  # só ela, e nenhuma outra
    for operacao in operacoes:
        operacao()


def test_dlt14_uma_permissao_de_leitura_nao_amplia_as_demais(amb: Ambiente) -> None:
    _definir_permissoes(amb, CARGO_TECNICO, Permissao.VER_OS)
    amb.servico_ordens.listar(BRUNO)
    _recusa_por_permissao(
        lambda: amb.servico_equipamentos.listar(BRUNO), Permissao.VER_EQUIPAMENTOS
    )
    _recusa_por_permissao(
        lambda: amb.servico_disponibilidade.consultar(BRUNO), Permissao.VER_DISPONIBILIDADE
    )
    _recusa_por_permissao(lambda: amb.servico_usuarios.listar(BRUNO), Permissao.GERIR_USUARIOS)


def test_dlt14_atores_distintos_a_mesma_consulta_depende_de_quem_pede(amb: Ambiente) -> None:
    _definir_permissoes(amb, CARGO_TECNICO)  # o técnico perde tudo; o gestor mantém o seu
    assert amb.servico_equipamentos.listar(ANA)
    _recusa_por_permissao(
        lambda: amb.servico_equipamentos.listar(CARLA), Permissao.VER_EQUIPAMENTOS
    )
    _recusa_por_permissao(
        lambda: amb.servico_equipamentos.listar(BRUNO), Permissao.VER_EQUIPAMENTOS
    )


def test_dlt14_as_permissoes_padrao_do_legado_continuam_dando_as_mesmas_leituras(
    amb: Ambiente,
) -> None:
    """Sem regra de visibilidade nova: o técnico padrão lê OS, equipamentos e disponibilidade."""
    _abrir_os(amb)
    assert amb.servico_equipamentos.listar(BRUNO)
    assert amb.servico_ordens.listar(BRUNO)
    assert amb.servico_disponibilidade.consultar(BRUNO)
    _recusa_por_permissao(lambda: amb.servico_usuarios.listar(BRUNO), Permissao.GERIR_USUARIOS)


# =========================================================================================
# DLT-15 — disponibilidade manual de terceiros
# =========================================================================================


def test_dlt15_usuario_altera_a_propria_disponibilidade(amb: Ambiente) -> None:
    _definir_permissoes(amb, CARGO_TECNICO)  # nem precisa de permissão alguma
    amb.servico_disponibilidade.alterar_disponibilidade(BRUNO, BRUNO, Disponibilidade.AUSENTE)
    bruno = amb.usuarios.obter(BRUNO)
    assert bruno is not None
    assert bruno.disponibilidade is Disponibilidade.AUSENTE
    amb.servico_disponibilidade.alterar_minha_disponibilidade(BRUNO, Disponibilidade.DISPONIVEL)
    bruno = amb.usuarios.obter(BRUNO)
    assert bruno is not None
    assert bruno.disponibilidade is Disponibilidade.DISPONIVEL


def test_dlt15_gestor_altera_a_disponibilidade_de_outro(amb: Ambiente) -> None:
    resultado = amb.servico_disponibilidade.alterar_disponibilidade(
        ANA, CARLA, Disponibilidade.AUSENTE
    )
    assert resultado.id == CARLA
    carla = amb.usuarios.obter(CARLA)
    bruno = amb.usuarios.obter(BRUNO)
    ana = amb.usuarios.obter(ANA)
    assert carla is not None
    assert bruno is not None
    assert ana is not None
    assert carla.disponibilidade is Disponibilidade.AUSENTE
    assert (bruno.disponibilidade, ana.disponibilidade) == (
        Disponibilidade.DISPONIVEL,
        Disponibilidade.DISPONIVEL,
    )


def test_dlt15_sem_permissao_nao_altera_a_disponibilidade_de_terceiros(amb: Ambiente) -> None:
    antes = _estado(amb)
    _recusa_por_permissao(
        lambda: amb.servico_disponibilidade.alterar_disponibilidade(
            BRUNO, CARLA, Disponibilidade.AUSENTE
        ),
        Permissao.GERIR_USUARIOS,
    )
    assert _estado(amb) == antes


def test_dlt15_a_autorizacao_vem_antes_de_procurar_o_alvo(amb: Ambiente) -> None:
    antes = _estado(amb)
    _recusa_por_permissao(
        lambda: amb.servico_disponibilidade.alterar_disponibilidade(
            BRUNO, INEXISTENTE, Disponibilidade.AUSENTE
        ),
        Permissao.GERIR_USUARIOS,
    )
    assert _estado(amb) == antes
    with pytest.raises(NaoEncontradoError) as erro:  # o gestor autorizado vê o alvo inexistente
        amb.servico_disponibilidade.alterar_disponibilidade(
            ANA, INEXISTENTE, Disponibilidade.AUSENTE
        )
    assert erro.value.identificador == INEXISTENTE
    assert _estado(amb) == antes


def test_dlt15_o_alvo_nunca_e_o_ator_quem_pede_e_quem_e_alterado_sao_distintos(
    amb: Ambiente,
) -> None:
    """Bruno pede a alteração da Carla: a recusa não pode virar uma alteração do próprio Bruno."""
    with pytest.raises(PermissaoNegadaError):
        amb.servico_disponibilidade.alterar_disponibilidade(BRUNO, CARLA, Disponibilidade.AUSENTE)
    for id_ in (BRUNO, CARLA):
        usuario = amb.usuarios.obter(id_)
        assert usuario is not None
        assert usuario.disponibilidade is Disponibilidade.DISPONIVEL


def test_dlt15_nao_deriva_a_disponibilidade_so_decide_quem_pode_o_ajuste_manual(
    amb: Ambiente,
) -> None:
    """A D-05 não foi implementada: sem a rotina, uma OS em execução não muda o valor guardado."""
    numero = _abrir_os(amb, tecnico=BRUNO)
    amb.servico_ordens.apontar_reparo(BRUNO, numero, 1.0, "troca", [PecaInformada("Rolamento", 1)])
    ordem = amb.ordens.obter(numero)
    assert ordem is not None
    assert ordem.status is StatusOS.EM_EXECUCAO
    bruno = amb.usuarios.obter(BRUNO)
    assert bruno is not None
    assert bruno.disponibilidade is Disponibilidade.DISPONIVEL  # valor armazenado, não derivado


# =========================================================================================
# DLT-16 — a autorização é a primeira verificação funcional
# =========================================================================================


def test_dlt16_sem_permissao_e_autoexclusao_a_recusa_e_por_autorizacao(amb: Ambiente) -> None:
    antes = _estado(amb)
    # Bruno (sem gerir_usuarios) tenta excluir a si mesmo: haveria autoexclusão, mas a
    # autorização vem antes.
    _recusa_por_permissao(
        lambda: amb.servico_usuarios.excluir(BRUNO, BRUNO), Permissao.GERIR_USUARIOS
    )
    assert _estado(amb) == antes


def test_dlt16_sem_permissao_e_historico_a_recusa_e_por_autorizacao(amb: Ambiente) -> None:
    _abrir_os(amb, por=CARLA, tecnico=BRUNO)
    antes = _estado(amb)
    # Carla abriu a OS e Bruno é o técnico (ambos têm histórico), mas quem pede não tem permissão.
    for alvo in (CARLA, BRUNO, ANA):
        with pytest.raises(PermissaoNegadaError):
            amb.servico_usuarios.excluir(BRUNO, alvo)
        assert _estado(amb) == antes


def test_dlt16_sem_permissao_e_equipamento_com_os_a_recusa_e_por_autorizacao(
    amb: Ambiente,
) -> None:
    _abrir_os(amb)
    antes = _estado(amb)
    _recusa_por_permissao(
        lambda: amb.servico_equipamentos.excluir(BRUNO, TORNO), Permissao.GERIR_EQUIPAMENTOS
    )
    assert _estado(amb) == antes


def test_dlt16_sem_permissao_e_recurso_inexistente_a_recusa_e_por_autorizacao(
    amb: Ambiente,
) -> None:
    antes = _estado(amb)
    u, e = amb.servico_usuarios, amb.servico_equipamentos
    casos: tuple[tuple[Callable[[], object], Permissao], ...] = (
        (lambda: u.excluir(BRUNO, INEXISTENTE), Permissao.GERIR_USUARIOS),
        (lambda: u.atualizar_dados(BRUNO, INEXISTENTE, nome="x"), Permissao.GERIR_USUARIOS),
        (lambda: u.alterar_cargo(BRUNO, INEXISTENTE, CARGO_GESTOR), Permissao.GERIR_USUARIOS),
        (lambda: u.alterar_cargo(BRUNO, CARLA, INEXISTENTE), Permissao.GERIR_USUARIOS),
        (lambda: u.cadastrar(BRUNO, "x", INEXISTENTE), Permissao.GERIR_USUARIOS),
        (lambda: u.definir_permissoes_do_cargo(BRUNO, INEXISTENTE, []), Permissao.GERIR_USUARIOS),
        (lambda: u.consultar(BRUNO, INEXISTENTE), Permissao.GERIR_USUARIOS),
        (lambda: e.excluir(BRUNO, INEXISTENTE), Permissao.GERIR_EQUIPAMENTOS),
        (lambda: e.atualizar(BRUNO, INEXISTENTE, "x", "y"), Permissao.GERIR_EQUIPAMENTOS),
        (lambda: e.inativar(BRUNO, INEXISTENTE), Permissao.GERIR_EQUIPAMENTOS),
    )
    for operacao, permissao in casos:
        _recusa_por_permissao(operacao, permissao)
    assert _estado(amb) == antes


def test_dlt16_com_permissao_o_recurso_inexistente_e_o_erro_de_nao_encontrado(
    amb: Ambiente,
) -> None:
    """A precedência é exata: quem tem permissão recebe o erro funcional, e não o de autorização."""
    with pytest.raises(NaoEncontradoError):
        amb.servico_usuarios.excluir(ANA, INEXISTENTE)
    with pytest.raises(NaoEncontradoError):
        amb.servico_equipamentos.excluir(ANA, INEXISTENTE)


def test_dlt16_as_regras_do_dominio_preservam_a_ordem_com_permissao(amb: Ambiente) -> None:
    """Não altera a precedência já caracterizada: autoexclusão vem antes do histórico (CAR-64)."""
    _abrir_os(amb, por=CARLA, tecnico=BRUNO)  # a Ana atribuiu: tem histórico
    with pytest.raises(RegraDeAplicacaoError) as erro:
        amb.servico_usuarios.excluir(ANA, ANA)
    assert erro.value.codigo is CodigoErroAplicacao.AUTOEXCLUSAO
    with pytest.raises(RegraDeAplicacaoError) as erro:
        amb.servico_usuarios.excluir(ANA, CARLA)
    assert erro.value.codigo is CodigoErroAplicacao.USUARIO_COM_HISTORICO


OPERACOES_DE_OS: tuple[tuple[str, Permissao, Callable[[Ambiente, int, int], object]], ...] = (
    (
        "abrir",
        Permissao.ABRIR_OS,
        lambda a, ator, n: a.servico_ordens.abrir(ator, INEXISTENTE, "x", Criticidade.BAIXA),
    ),
    (
        "apontamento",
        Permissao.REGISTRAR_APONTAMENTO,
        lambda a, ator, n: a.servico_ordens.adicionar_apontamento(ator, n, "x"),
    ),
    (
        "diagnostico",
        Permissao.DIAGNOSTICAR,
        lambda a, ator, n: a.servico_ordens.registrar_diagnostico(ator, n, "p", "c"),
    ),
    (
        "reparo",
        Permissao.APONTAR_REPARO,
        lambda a, ator, n: a.servico_ordens.apontar_reparo(
            ator, n, 1.0, "x", [PecaInformada("p", -1)]
        ),
    ),
    (
        "status",
        Permissao.ATUALIZAR_STATUS,
        lambda a, ator, n: a.servico_ordens.alterar_status(ator, n, StatusOS.EM_EXECUCAO),
    ),
    (
        "concluir",
        Permissao.CONCLUIR_OS,
        lambda a, ator, n: a.servico_ordens.concluir_tecnicamente(ator, n, "t", True),
    ),
    (
        "atribuir",
        Permissao.ATRIBUIR_OS,
        lambda a, ator, n: a.servico_ordens.atribuir(ator, n, INEXISTENTE),
    ),
    ("aprovar", Permissao.APROVAR_OS, lambda a, ator, n: a.servico_ordens.aprovar(ator, n)),
    ("reprovar", Permissao.APROVAR_OS, lambda a, ator, n: a.servico_ordens.reprovar(ator, n, "m")),
    ("cancelar", Permissao.APROVAR_OS, lambda a, ator, n: a.servico_ordens.cancelar(ator, n, "m")),
)


@pytest.mark.parametrize(
    ("operacao", "permissao"),
    [pytest.param(nome, perm, id=nome) for nome, perm, _ in OPERACOES_DE_OS],
)
def test_dlt16_operacao_de_os_sem_permissao_e_recusada_antes_de_procurar_o_resto(
    amb: Ambiente, operacao: str, permissao: Permissao
) -> None:
    """OS inexistente, equipamento inexistente, técnico inexistente e peça inválida: nenhum deles
    prevalece sobre a falta de permissão."""
    _, _, executar = next(o for o in OPERACOES_DE_OS if o[0] == operacao)
    _definir_permissoes(amb, CARGO_TECNICO, *(p for p in Permissao if p is not permissao))
    _definir_permissoes(amb, CARGO_GESTOR, *(p for p in Permissao if p is not permissao))
    antes = _estado(amb)
    _recusa_por_permissao(lambda: executar(amb, BRUNO, INEXISTENTE), permissao)
    _recusa_por_permissao(lambda: executar(amb, ANA, INEXISTENTE), permissao)
    assert _estado(amb) == antes


@pytest.mark.parametrize(
    "operacao",
    [
        pytest.param(nome, id=nome)
        for nome, _, _ in OPERACOES_DE_OS
        if nome not in {"abrir", "reparo"}  # a peça inválida de "reparo" é de outro teste
    ],
)
def test_dlt16_com_permissao_a_os_inexistente_e_nao_encontrada(
    amb: Ambiente, operacao: str
) -> None:
    _, _, executar = next(o for o in OPERACOES_DE_OS if o[0] == operacao)
    ator = ANA if operacao in {"atribuir", "aprovar", "reprovar", "cancelar"} else BRUNO
    with pytest.raises(NaoEncontradoError) as erro:
        executar(amb, ator, INEXISTENTE)
    assert erro.value.entidade in {"Ordem de serviço", "Usuário"}


def test_dlt16_com_permissao_a_peca_invalida_continua_sendo_recusada_pelo_dominio(
    amb: Ambiente,
) -> None:
    """A ordem das regras de domínio não muda: com permissão, a peça é validada primeiro."""
    with pytest.raises(ViolacaoDeRegraError) as erro:
        amb.servico_ordens.apontar_reparo(BRUNO, INEXISTENTE, 1.0, "x", [PecaInformada("p", -1)])
    assert erro.value.codigo is CodigoErro.QUANTIDADE_INVALIDA


# =========================================================================================
# DLT-17 — ator inexistente
# =========================================================================================


def _todas_as_operacoes_com_ator(amb: Ambiente) -> list[tuple[str, Callable[[int], object]]]:
    numero = _abrir_os(amb)
    e, u, o, d = (
        amb.servico_equipamentos,
        amb.servico_usuarios,
        amb.servico_ordens,
        amb.servico_disponibilidade,
    )
    return [
        ("equip.consultar", lambda a: e.consultar(a, TORNO)),
        ("equip.listar", lambda a: e.listar(a)),
        ("equip.cadastrar", lambda a: e.cadastrar(a, "Prensa", "P1")),
        ("equip.atualizar", lambda a: e.atualizar(a, TORNO, "x", "y")),
        ("equip.inativar", lambda a: e.inativar(a, TORNO)),
        ("equip.reativar", lambda a: e.reativar(a, TORNO)),
        ("equip.excluir", lambda a: e.excluir(a, COMPRESSOR)),
        ("user.consultar", lambda a: u.consultar(a, BRUNO)),
        ("user.listar", lambda a: u.listar(a)),
        ("user.listar_cargos", lambda a: u.listar_cargos(a)),
        ("user.cadastrar", lambda a: u.cadastrar(a, "Diego", CARGO_TECNICO)),
        ("user.atualizar", lambda a: u.atualizar_dados(a, BRUNO, nome="x")),
        ("user.cargo", lambda a: u.alterar_cargo(a, BRUNO, CARGO_GESTOR)),
        ("user.disp", lambda a: u.definir_disponibilidade(a, BRUNO, Disponibilidade.AUSENTE)),
        ("user.excluir", lambda a: u.excluir(a, BRUNO)),
        ("user.permissoes", lambda a: u.definir_permissoes_do_cargo(a, CARGO_TECNICO, [])),
        ("os.consultar", lambda a: o.consultar(a, numero)),
        ("os.listar", lambda a: o.listar(a)),
        ("os.historico", lambda a: o.historico(a, numero)),
        ("os.abrir", lambda a: o.abrir(a, TORNO, "x", Criticidade.BAIXA)),
        ("os.apontamento", lambda a: o.adicionar_apontamento(a, numero, "x")),
        ("os.diagnostico", lambda a: o.registrar_diagnostico(a, numero, "p", "c")),
        ("os.reparo", lambda a: o.apontar_reparo(a, numero, 1.0, "x")),
        ("os.status", lambda a: o.alterar_status(a, numero, StatusOS.EM_EXECUCAO)),
        ("os.concluir", lambda a: o.concluir_tecnicamente(a, numero, "t", True)),
        ("os.atribuir", lambda a: o.atribuir(a, numero, BRUNO)),
        ("os.aprovar", lambda a: o.aprovar(a, numero)),
        ("os.reprovar", lambda a: o.reprovar(a, numero, "m")),
        ("os.cancelar", lambda a: o.cancelar(a, numero, "m")),
        ("disp.consultar", lambda a: d.consultar(a)),
        ("disp.alterar", lambda a: d.alterar_disponibilidade(a, BRUNO, Disponibilidade.AUSENTE)),
        ("disp.minha", lambda a: d.alterar_minha_disponibilidade(a, Disponibilidade.AUSENTE)),
    ]


def test_dlt17_ator_inexistente_e_recusado_em_toda_operacao_com_o_erro_tipado(
    amb: Ambiente,
) -> None:
    operacoes = _todas_as_operacoes_com_ator(amb)
    antes = _estado(amb)
    assert len(operacoes) == 32
    for nome, executar in operacoes:
        with pytest.raises(NaoEncontradoError) as erro:
            executar(INEXISTENTE)
        assert erro.value.codigo is CodigoErroAplicacao.NAO_ENCONTRADO, nome
        assert (erro.value.entidade, erro.value.identificador) == ("Usuário", INEXISTENTE), nome
        assert _estado(amb) == antes, nome


def test_dlt17_nao_cria_usuario_nem_consome_identificador(amb: Ambiente) -> None:
    operacoes = _todas_as_operacoes_com_ator(amb)
    usuarios = amb.usuarios.listar()
    proximo = amb.usuarios.proximo_id()
    for _, executar in operacoes:
        with pytest.raises(NaoEncontradoError):
            executar(INEXISTENTE)
    assert amb.usuarios.listar() == usuarios
    assert amb.usuarios.obter(INEXISTENTE) is None
    assert amb.usuarios.proximo_id() == proximo


def test_dlt17_o_ator_inexistente_nao_vira_administrador(amb: Ambiente) -> None:
    """Nenhuma operação que só um gestor faz é executada em nome de um ator desconhecido."""
    antes = _estado(amb)
    for ator in (INEXISTENTE, 0, -1, amb.usuarios.proximo_id()):
        with pytest.raises(NaoEncontradoError):
            amb.servico_usuarios.cadastrar(ator, "Intruso", CARGO_GESTOR)
        with pytest.raises(NaoEncontradoError):
            amb.servico_equipamentos.excluir(ator, COMPRESSOR)
    assert _estado(amb) == antes


def test_dlt17_a_inexistencia_do_ator_prevalece_sobre_qualquer_outro_impedimento(
    amb: Ambiente,
) -> None:
    """Sem ator não há autorização a avaliar: o erro é o do ator, não o do alvo nem o da regra."""
    with pytest.raises(NaoEncontradoError) as erro:
        amb.servico_usuarios.excluir(INEXISTENTE, INEXISTENTE + 1)
    assert erro.value.identificador == INEXISTENTE
    with pytest.raises(NaoEncontradoError) as erro:
        amb.servico_ordens.abrir(INEXISTENTE, INEXISTENTE + 1, "x", Criticidade.BAIXA)
    assert (erro.value.entidade, erro.value.identificador) == ("Usuário", INEXISTENTE)
