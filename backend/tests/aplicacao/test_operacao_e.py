"""Operação E nos serviços de aplicação: as regras de negócio aprovadas (D-02 a D-06, DLT-08/09).

Cada teste prova o que é aceito ou recusado (com o erro tipado) e que **a recusa não altera nada**:
nem os repositórios, nem o histórico das OS, nem os identificadores (``_estado``). A autorização
continua sendo a primeira verificação (DLT-16) e um ator inexistente é recusado (DLT-17): as regras
novas se somam às dos DLT-12 a DLT-17 e nunca as enfraquecem. O comportamento antigo está
caracterizado no legado; a comparação lado a lado, em
``tests/caracterizacao/test_operacao_e_servicos.py``.

* DLT-01 papéis (D-02)                 * DLT-05 disponibilidade derivada (D-05)
* DLT-02 técnico ausente (D-03)        * DLT-06 diagnóstico obrigatório (D-06)
* DLT-03/04 observações (D-04)         * DLT-08 campos obrigatórios e horas positivas
* DLT-09 usuário ativo ou inativo
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
from manutencao.domain.enums import Criticidade, Disponibilidade, Papel, StatusOS, TipoServico
from manutencao.domain.erros import (
    CodigoErro,
    ConflitoDeEstadoError,
    PermissaoNegadaError,
    ViolacaoDeRegraError,
)
from manutencao.domain.permissoes import Permissao
from tests.apoio.ambiente import (
    ANA,
    BRUNO,
    CARGO_GESTOR,
    CARGO_TECNICO,
    CARLA,
    TORNO,
    Ambiente,
)
from tests.apoio.caminhos import (
    aberta,
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
    """Tudo o que uma recusa não pode alterar, inclusive o próximo id de cada sequência.

    Os usuários são comparados campo a campo (a igualdade da entidade é só pelo identificador).
    """
    return (
        tuple(
            (u.id, u.nome, u.cargo.id, u.email, u.escala, u.disponibilidade, u.papel, u.ativo)
            for u in amb.usuarios.listar()
        ),
        [(c.id, c.permissoes.ativas()) for c in amb.cargos.listar()],
        [(e.id, e.nome, e.modelo, e.ativo) for e in amb.equipamentos.listar()],
        [instantaneo(o) for o in amb.ordens.listar()],
        amb.usuarios.proximo_id(),
        amb.equipamentos.proximo_id(),
        amb.ordens.proximo_numero(),
    )


def _recusado(amb: Ambiente, erro: type[Exception], codigo: Any, operacao: Operacao) -> Exception:
    antes = _estado(amb)
    with pytest.raises(erro) as capturado:
        operacao()
    assert getattr(capturado.value, "codigo", None) is codigo
    assert _estado(amb) == antes
    return capturado.value


def _definir_permissoes(amb: Ambiente, cargo_id: int, *permissoes: Permissao) -> None:
    cargo = amb.cargos.obter(cargo_id)
    assert cargo is not None
    cargo.permissoes.definir(permissoes)
    amb.cargos.salvar(cargo)


def _sem(amb: Ambiente, cargo_id: int, permissao: Permissao) -> None:
    cargo = amb.cargos.obter(cargo_id)
    assert cargo is not None
    _definir_permissoes(
        amb, cargo_id, *(p for p in cargo.permissoes.ativas() if p is not permissao)
    )


def _usuario(amb: Ambiente, usuario_id: int) -> Any:
    achado = amb.usuarios.obter(usuario_id)
    assert achado is not None
    return achado


def _efetiva(amb: Ambiente, usuario_id: int) -> Disponibilidade:
    """O que a consulta de disponibilidade mostra para o técnico."""
    linhas = {linha.id: linha for linha in amb.servico_disponibilidade.consultar(ANA)}
    return linhas[usuario_id].disponibilidade


def _novo_tecnico(amb: Ambiente, nome: str = "Diego") -> int:
    return amb.servico_usuarios.cadastrar(ANA, nome, CARGO_TECNICO, papel=Papel.TECNICO).id


# =========================================================================================
# DLT-01 — papéis Gestor e Técnico (D-02)
# =========================================================================================


def test_dlt01_a_lista_de_tecnicos_depende_do_papel_e_nao_das_permissoes(amb: Ambiente) -> None:
    assert [t.id for t in amb.projecoes.tecnicos()] == [BRUNO, CARLA]
    _definir_permissoes(amb, CARGO_TECNICO)  # nenhuma permissão
    _definir_permissoes(amb, CARGO_GESTOR, *Permissao)  # todas, inclusive as técnicas
    assert [t.id for t in amb.projecoes.tecnicos()] == [BRUNO, CARLA]
    assert [linha.id for linha in amb.servico_disponibilidade.consultar(ANA)] == [BRUNO, CARLA]


def test_dlt01_tecnico_sem_apontar_reparo_e_atribuivel_e_e_negado_ao_apontar(
    amb: Ambiente,
) -> None:
    _sem(amb, CARGO_TECNICO, Permissao.APONTAR_REPARO)
    numero = aberta(amb)
    assert amb.servico_ordens.atribuir(ANA, numero, BRUNO) is None
    assert guardada(amb, numero).tecnico_atribuido == _usuario(amb, BRUNO)
    _recusado(
        amb,
        PermissaoNegadaError,
        CodigoErro.SEM_PERMISSAO,
        lambda: amb.servico_ordens.apontar_reparo(BRUNO, numero, 1.0, "Troca"),
    )


def test_dlt01_gestor_com_permissoes_tecnicas_nao_aparece_nem_recebe_atribuicao(
    amb: Ambiente,
) -> None:
    _definir_permissoes(amb, CARGO_GESTOR, *Permissao)
    assert ANA not in [t.id for t in amb.projecoes.tecnicos()]
    numero = aberta(amb)
    _recusado(
        amb,
        ViolacaoDeRegraError,
        CodigoErro.NAO_E_TECNICO,
        lambda: amb.servico_ordens.atribuir(ANA, numero, ANA),
    )


def test_dlt01_o_cadastro_guarda_o_papel_informado(amb: Ambiente) -> None:
    tecnico = amb.servico_usuarios.cadastrar(ANA, "Diego", CARGO_TECNICO, papel=Papel.TECNICO)
    gestor = amb.servico_usuarios.cadastrar(ANA, "Eva", CARGO_GESTOR, papel=Papel.GESTOR)
    assert (_usuario(amb, tecnico.id).papel, _usuario(amb, gestor.id).papel) == (
        Papel.TECNICO,
        Papel.GESTOR,
    )
    assert tecnico.id in [t.id for t in amb.projecoes.tecnicos()]
    assert gestor.id not in [t.id for t in amb.projecoes.tecnicos()]
    with pytest.raises(TypeError):  # o papel é obrigatório: nada é deduzido do cargo
        amb.servico_usuarios.cadastrar(ANA, "Sem papel", CARGO_TECNICO)  # type: ignore[call-arg]


def test_dlt01_o_gestor_altera_o_papel_por_uma_operacao_explicita(amb: Ambiente) -> None:
    alterado = amb.servico_usuarios.alterar_papel(ANA, CARLA, Papel.GESTOR)
    assert alterado.papel is Papel.GESTOR
    assert _usuario(amb, CARLA).papel is Papel.GESTOR  # guardado
    assert [t.id for t in amb.projecoes.tecnicos()] == [BRUNO]
    amb.servico_usuarios.alterar_papel(ANA, CARLA, Papel.TECNICO)
    assert [t.id for t in amb.projecoes.tecnicos()] == [BRUNO, CARLA]


def test_dlt01_alterar_papel_e_restrito_ao_gestor_mesmo_com_a_permissao_de_gerir_usuarios(
    amb: Ambiente,
) -> None:
    # um técnico comum, sem a permissão
    _recusado(
        amb,
        PermissaoNegadaError,
        CodigoErro.SEM_PERMISSAO,
        lambda: amb.servico_usuarios.alterar_papel(BRUNO, CARLA, Papel.GESTOR),
    )
    # um técnico que recebeu a permissão de gerir usuários: a operação é do papel Gestor
    _definir_permissoes(amb, CARGO_TECNICO, *Permissao)
    erro = _recusado(
        amb,
        PermissaoNegadaError,
        CodigoErro.SEM_PERMISSAO,
        lambda: amb.servico_usuarios.alterar_papel(BRUNO, CARLA, Papel.GESTOR),
    )
    assert "Apenas o gestor" in str(erro)


def test_dlt01_um_gestor_sem_a_permissao_de_gerir_usuarios_tambem_e_recusado(
    amb: Ambiente,
) -> None:
    _sem(amb, CARGO_GESTOR, Permissao.GERIR_USUARIOS)
    _recusado(
        amb,
        PermissaoNegadaError,
        CodigoErro.SEM_PERMISSAO,
        lambda: amb.servico_usuarios.alterar_papel(ANA, CARLA, Papel.GESTOR),
    )


def test_dlt01_ninguem_deixa_de_ser_gestor_por_conta_propria(amb: Ambiente) -> None:
    erro = _recusado(
        amb,
        RegraDeAplicacaoError,
        CodigoErroAplicacao.AUTOREMOCAO_DE_ACESSO_DE_GESTAO,
        lambda: amb.servico_usuarios.alterar_papel(ANA, ANA, Papel.TECNICO),
    )
    assert "deixar de ser gestor" in str(erro)
    amb.servico_usuarios.alterar_papel(ANA, ANA, Papel.GESTOR)  # manter o papel é permitido


def test_dlt01_mudar_o_papel_nao_reatribui_as_os(amb: Ambiente) -> None:
    # Com OS ativa a mudança é recusada (REG-E-04); com a OS já encerrada ela é aceita e a OS
    # continua como estava, sem reatribuição automática.
    numero = aguardando_aprovacao(amb)
    amb.servico_ordens.aprovar(ANA, numero)
    historico = guardada(amb, numero).servicos
    amb.servico_usuarios.alterar_papel(ANA, BRUNO, Papel.GESTOR)
    os_ = guardada(amb, numero)
    assert os_.tecnico_atribuido == _usuario(amb, BRUNO)  # sem reatribuição automática
    assert (os_.status, os_.servicos) == (StatusOS.CONCLUIDA, historico)


def test_dlt01_alterar_papel_segue_a_precedencia_da_autorizacao(amb: Ambiente) -> None:
    with pytest.raises(NaoEncontradoError) as erro:  # ator inexistente (DLT-17)
        amb.servico_usuarios.alterar_papel(INEXISTENTE, CARLA, Papel.GESTOR)
    assert erro.value.entidade == "Usuário"
    # sem autorização, a existência do alvo não é revelada (DLT-16)
    _recusado(
        amb,
        PermissaoNegadaError,
        CodigoErro.SEM_PERMISSAO,
        lambda: amb.servico_usuarios.alterar_papel(BRUNO, INEXISTENTE, Papel.GESTOR),
    )
    with pytest.raises(NaoEncontradoError):  # autorizado, o alvo inexistente é "não encontrado"
        amb.servico_usuarios.alterar_papel(ANA, INEXISTENTE, Papel.GESTOR)


# =========================================================================================
# DLT-02 — atribuição a técnico ausente (D-03)
# =========================================================================================


def _ausentar(amb: Ambiente, usuario_id: int) -> None:
    amb.servico_disponibilidade.alterar_minha_disponibilidade(usuario_id, Disponibilidade.AUSENTE)


def test_dlt02_atribuir_a_tecnico_ausente_sem_confirmacao_e_recusado_sem_mutacao(
    amb: Ambiente,
) -> None:
    _ausentar(amb, BRUNO)
    numero = aberta(amb)
    erro = _recusado(
        amb,
        ConflitoDeEstadoError,
        CodigoErro.TECNICO_AUSENTE,
        lambda: amb.servico_ordens.atribuir(ANA, numero, BRUNO),
    )
    assert "ausente" in str(erro)
    os_ = guardada(amb, numero)
    assert (os_.status, os_.tecnico_atribuido, len(os_.servicos)) == (StatusOS.ABERTA, None, 1)


def test_dlt02_com_confirmacao_explicita_a_atribuicao_e_aceita_e_registrada(
    amb: Ambiente,
) -> None:
    _ausentar(amb, BRUNO)
    numero = aberta(amb)
    anterior = amb.servico_ordens.atribuir(ANA, numero, BRUNO, confirmar_ausente=True)
    assert anterior is None
    os_ = guardada(amb, numero)
    assert (os_.status, os_.tecnico_atribuido) == (StatusOS.ATRIBUIDA, _usuario(amb, BRUNO))
    assert os_.servicos[1].tipo is TipoServico.ATRIBUICAO
    assert "técnico ausente" in os_.servicos[1].descricao
    assert os_.servicos[1].responsavel == _usuario(amb, ANA)
    assert _usuario(amb, BRUNO).disponibilidade is Disponibilidade.AUSENTE  # segue ausente


def test_dlt02_a_reatribuicao_a_tecnico_ausente_segue_a_mesma_regra(amb: Ambiente) -> None:
    numero = atribuida(amb, BRUNO)
    _ausentar(amb, CARLA)
    _recusado(
        amb,
        ConflitoDeEstadoError,
        CodigoErro.TECNICO_AUSENTE,
        lambda: amb.servico_ordens.atribuir(ANA, numero, CARLA),
    )
    anterior = amb.servico_ordens.atribuir(ANA, numero, CARLA, confirmar_ausente=True)
    assert anterior is not None
    assert anterior.id == BRUNO
    ultimo = guardada(amb, numero).servicos[-1]
    assert (ultimo.tipo, "técnico ausente" in ultimo.descricao) == (TipoServico.REATRIBUICAO, True)


def test_dlt02_a_confirmacao_nao_e_aceita_de_quem_nao_pode_atribuir(amb: Ambiente) -> None:
    _ausentar(amb, CARLA)
    numero = aberta(amb)
    _recusado(
        amb,
        PermissaoNegadaError,
        CodigoErro.SEM_PERMISSAO,
        lambda: amb.servico_ordens.atribuir(BRUNO, numero, CARLA, confirmar_ausente=True),
    )
    assert guardada(amb, numero).tecnico_atribuido is None


def test_dlt02_removida_a_ausencia_a_atribuicao_dispensa_a_confirmacao(amb: Ambiente) -> None:
    _ausentar(amb, BRUNO)
    numero = aberta(amb)
    amb.servico_disponibilidade.alterar_minha_disponibilidade(BRUNO, Disponibilidade.DISPONIVEL)
    amb.servico_ordens.atribuir(ANA, numero, BRUNO)
    assert guardada(amb, numero).servicos[1].descricao == "Atribuída a Bruno Lima"


def test_dlt02_so_a_ausencia_manual_exige_confirmacao_nao_o_estar_em_atendimento(
    amb: Ambiente,
) -> None:
    em_execucao(amb, BRUNO)  # Em atendimento (derivado), mas não ausente
    outra = aberta(amb)
    amb.servico_ordens.atribuir(ANA, outra, BRUNO)
    assert guardada(amb, outra).tecnico_atribuido == _usuario(amb, BRUNO)


# =========================================================================================
# DLT-03 e DLT-04 — observações (D-04)
# =========================================================================================


def test_dlt03_observacao_em_os_concluida_ou_cancelada_e_recusada_pelo_servico(
    amb: Ambiente,
) -> None:
    concluida = aguardando_aprovacao(amb)
    amb.servico_ordens.aprovar(ANA, concluida)
    cancelada = atribuida(amb)
    amb.servico_ordens.cancelar(ANA, cancelada, "Chamado indevido")
    for numero in (concluida, cancelada):
        for autor in (ANA, BRUNO, CARLA):
            _recusado(
                amb,
                ConflitoDeEstadoError,
                CodigoErro.OS_ENCERRADA,
                lambda numero=numero, autor=autor: amb.servico_ordens.adicionar_apontamento(  # type: ignore[misc]
                    autor, numero, "depois do fim"
                ),
            )


def test_dlt04_gestor_responsavel_e_autor_da_abertura_observam_e_o_status_nao_muda(
    amb: Ambiente,
) -> None:
    numero = em_execucao(amb, BRUNO)  # aberta por Carla, de Bruno; Ana é gestora
    for autor in (ANA, BRUNO, CARLA):
        antes = guardada(amb, numero)
        amb.servico_ordens.adicionar_apontamento(autor, numero, f"nota {autor}")
        depois = guardada(amb, numero)
        assert depois.status is antes.status is StatusOS.EM_EXECUCAO
        registro = depois.servicos[-1]
        assert (registro.tipo, registro.descricao) == (TipoServico.APONTAMENTO, f"nota {autor}")
        assert registro.responsavel == _usuario(amb, autor)
        assert registro.data == amb.relogio.agora()
        assert len(depois.servicos) == len(antes.servicos) + 1


def test_dlt04_quem_nao_tem_vinculo_com_a_os_e_recusado_sem_mutacao(amb: Ambiente) -> None:
    numero = em_execucao(amb, BRUNO)
    diego = _novo_tecnico(amb)
    _recusado(
        amb,
        PermissaoNegadaError,
        CodigoErro.SEM_VINCULO_COM_A_OS,
        lambda: amb.servico_ordens.adicionar_apontamento(diego, numero, "passando"),
    )
    amb.servico_ordens.atribuir(ANA, numero, CARLA)  # Bruno deixa de ser o responsável
    _recusado(
        amb,
        PermissaoNegadaError,
        CodigoErro.SEM_VINCULO_COM_A_OS,
        lambda: amb.servico_ordens.adicionar_apontamento(BRUNO, numero, "x"),
    )


def test_dlt04_o_autor_da_abertura_nao_executa_operacoes_tecnicas(amb: Ambiente) -> None:
    numero = em_execucao(amb, BRUNO)  # Carla abriu; Bruno é o responsável
    servico = amb.servico_ordens
    operacoes: tuple[Operacao, ...] = (
        lambda: servico.registrar_diagnostico(CARLA, numero, "p", "c"),
        lambda: servico.apontar_reparo(CARLA, numero, 1.0, "Troca"),
        lambda: servico.alterar_status(CARLA, numero, StatusOS.AGUARDANDO_PECA),
        lambda: servico.concluir_tecnicamente(CARLA, numero, "ok", True),
    )
    for operacao in operacoes:
        _recusado(amb, PermissaoNegadaError, CodigoErro.NAO_RESPONSAVEL, operacao)
    servico.adicionar_apontamento(CARLA, numero, "mas pode observar")  # a observação é permitida


def test_dlt04_a_observacao_continua_exigindo_a_permissao_e_a_ordem_da_autorizacao(
    amb: Ambiente,
) -> None:
    numero = atribuida(amb, BRUNO)
    _sem(amb, CARGO_TECNICO, Permissao.REGISTRAR_APONTAMENTO)
    _recusado(
        amb,
        PermissaoNegadaError,
        CodigoErro.SEM_PERMISSAO,
        lambda: amb.servico_ordens.adicionar_apontamento(BRUNO, numero, "x"),
    )
    with pytest.raises(NaoEncontradoError):  # ator inexistente (DLT-17)
        amb.servico_ordens.adicionar_apontamento(INEXISTENTE, numero, "x")
    _recusado(
        amb,
        PermissaoNegadaError,
        CodigoErro.SEM_PERMISSAO,
        lambda: amb.servico_ordens.adicionar_apontamento(BRUNO, INEXISTENTE, "x"),
    )


# =========================================================================================
# DLT-05 — disponibilidade derivada das OS (D-05): os dez cenários da decisão
# =========================================================================================


def test_dlt05_01_sem_os_ativas_e_nao_ausente_o_tecnico_esta_disponivel(amb: Ambiente) -> None:
    assert (_efetiva(amb, BRUNO), _efetiva(amb, CARLA)) == (
        Disponibilidade.DISPONIVEL,
        Disponibilidade.DISPONIVEL,
    )


def test_dlt05_02_uma_os_atribuida_nao_caracteriza_atendimento(amb: Ambiente) -> None:
    atribuida(amb, BRUNO)
    assert _efetiva(amb, BRUNO) is Disponibilidade.DISPONIVEL


def test_dlt05_03_uma_os_em_execucao_caracteriza_atendimento_sem_rotina(amb: Ambiente) -> None:
    em_execucao(amb, BRUNO)
    assert _efetiva(amb, BRUNO) is Disponibilidade.EM_ATENDIMENTO
    assert _efetiva(amb, CARLA) is Disponibilidade.DISPONIVEL


def test_dlt05_04_uma_os_aguardando_peca_sozinha_nao_caracteriza_atendimento(
    amb: Ambiente,
) -> None:
    numero = em_execucao(amb, BRUNO)
    amb.servico_ordens.alterar_status(BRUNO, numero, StatusOS.AGUARDANDO_PECA)
    assert _efetiva(amb, BRUNO) is Disponibilidade.DISPONIVEL


def test_dlt05_05_em_execucao_e_aguardando_peca_juntas_caracterizam_atendimento(
    amb: Ambiente,
) -> None:
    primeira = em_execucao(amb, BRUNO)
    em_execucao(amb, BRUNO)
    amb.servico_ordens.alterar_status(BRUNO, primeira, StatusOS.AGUARDANDO_PECA)
    assert _efetiva(amb, BRUNO) is Disponibilidade.EM_ATENDIMENTO


def test_dlt05_06_a_ausencia_manual_prevalece_sobre_o_estado_derivado(amb: Ambiente) -> None:
    em_execucao(amb, BRUNO)
    _ausentar(amb, BRUNO)
    assert _efetiva(amb, BRUNO) is Disponibilidade.AUSENTE
    assert amb.projecoes.carga_do_tecnico(BRUNO) == 1  # continua técnico, com carga
    assert BRUNO in [t.id for t in amb.projecoes.tecnicos()]


def test_dlt05_07_removida_a_ausencia_o_valor_e_recalculado_sem_acao_extra(
    amb: Ambiente,
) -> None:
    em_execucao(amb, BRUNO)
    _ausentar(amb, BRUNO)
    amb.servico_disponibilidade.alterar_minha_disponibilidade(BRUNO, Disponibilidade.DISPONIVEL)
    assert _efetiva(amb, BRUNO) is Disponibilidade.EM_ATENDIMENTO


def test_dlt05_08_ao_finalizar_o_reparo_o_tecnico_fica_disponivel_sem_rotina(
    amb: Ambiente,
) -> None:
    numero = atribuida(amb, BRUNO)
    amb.servico_ordens.registrar_diagnostico(BRUNO, numero, "p", "c")
    amb.servico_ordens.apontar_reparo(BRUNO, numero, 1.0, "Troca")
    assert _efetiva(amb, BRUNO) is Disponibilidade.EM_ATENDIMENTO
    amb.servico_ordens.alterar_status(BRUNO, numero, StatusOS.REPARO_FINALIZADO)
    assert _efetiva(amb, BRUNO) is Disponibilidade.DISPONIVEL


def test_dlt05_09_a_reatribuicao_reflete_nos_dois_tecnicos_imediatamente(amb: Ambiente) -> None:
    numero = em_execucao(amb, BRUNO)
    assert (_efetiva(amb, BRUNO), _efetiva(amb, CARLA)) == (
        Disponibilidade.EM_ATENDIMENTO,
        Disponibilidade.DISPONIVEL,
    )
    amb.servico_ordens.atribuir(ANA, numero, CARLA)
    assert (_efetiva(amb, BRUNO), _efetiva(amb, CARLA)) == (
        Disponibilidade.DISPONIVEL,
        Disponibilidade.EM_ATENDIMENTO,
    )


def test_dlt05_10_a_consulta_logo_apos_a_transicao_ja_traz_o_valor_correto(
    amb: Ambiente,
) -> None:
    numero = atribuida(amb, BRUNO)
    antes = amb.servico_disponibilidade.consultar(ANA)
    amb.servico_ordens.apontar_reparo(BRUNO, numero, 1.0, "Troca")
    depois = amb.servico_disponibilidade.consultar(ANA)
    assert (antes[0].disponibilidade, depois[0].disponibilidade) == (
        Disponibilidade.DISPONIVEL,
        Disponibilidade.EM_ATENDIMENTO,
    )
    assert depois[0].carga == 1


def test_dlt05_a_derivacao_nao_grava_nada_nem_depende_de_rotina(amb: Ambiente) -> None:
    em_execucao(amb, BRUNO)
    antes = _estado(amb)
    amb.servico_disponibilidade.consultar(ANA)
    assert _estado(amb) == antes
    assert _usuario(amb, BRUNO).disponibilidade is Disponibilidade.DISPONIVEL  # valor manual
    assert not hasattr(amb.servico_disponibilidade, "atualizar_disponibilidades")


def test_dlt05_a_autorizacao_para_alterar_a_ausencia_de_terceiros_e_a_do_dlt15(
    amb: Ambiente,
) -> None:
    em_execucao(amb, BRUNO)
    amb.servico_disponibilidade.alterar_disponibilidade(ANA, BRUNO, Disponibilidade.AUSENTE)
    assert _efetiva(amb, BRUNO) is Disponibilidade.AUSENTE  # o gestor ausenta um técnico
    _recusado(
        amb,
        PermissaoNegadaError,
        CodigoErro.SEM_PERMISSAO,
        lambda: amb.servico_disponibilidade.alterar_disponibilidade(
            CARLA, BRUNO, Disponibilidade.DISPONIVEL
        ),
    )
    assert _efetiva(amb, BRUNO) is Disponibilidade.AUSENTE


# =========================================================================================
# DLT-06 — diagnóstico obrigatório antes de Reparo Finalizado (D-06)
# =========================================================================================


def test_dlt06_finalizar_sem_diagnostico_e_recusado_pelo_servico_sem_mutacao(
    amb: Ambiente,
) -> None:
    numero = em_execucao(amb, BRUNO)  # tem intervenção, mas nenhum diagnóstico
    erro = _recusado(
        amb,
        ViolacaoDeRegraError,
        CodigoErro.SEM_DIAGNOSTICO,
        lambda: amb.servico_ordens.alterar_status(BRUNO, numero, StatusOS.REPARO_FINALIZADO),
    )
    assert "diagnóstico" in str(erro)
    os_ = guardada(amb, numero)
    assert (os_.status, os_.diagnostico) == (StatusOS.EM_EXECUCAO, "")
    assert os_.servicos[-1].tipo is TipoServico.REPARO  # nenhuma mudança de status no histórico


def test_dlt06_com_diagnostico_a_finalizacao_e_o_fluxo_completo_funcionam(amb: Ambiente) -> None:
    numero = reparo_finalizado(amb)
    assert amb.servico_ordens.concluir_tecnicamente(BRUNO, numero, "Funcionou", True)
    amb.servico_ordens.aprovar(ANA, numero)
    assert guardada(amb, numero).status is StatusOS.CONCLUIDA


def test_dlt06_o_diagnostico_registrado_depois_destrava_a_finalizacao(amb: Ambiente) -> None:
    numero = em_execucao(amb, BRUNO)
    _recusado(
        amb,
        ViolacaoDeRegraError,
        CodigoErro.SEM_DIAGNOSTICO,
        lambda: amb.servico_ordens.alterar_status(BRUNO, numero, StatusOS.REPARO_FINALIZADO),
    )
    amb.servico_ordens.registrar_diagnostico(BRUNO, numero, "Rolamento gasto", "Falta de graxa")
    amb.servico_ordens.alterar_status(BRUNO, numero, StatusOS.REPARO_FINALIZADO)
    assert guardada(amb, numero).status is StatusOS.REPARO_FINALIZADO
    # e o caminho indireto do legado (voltar o status só para diagnosticar) deixa de ser preciso
    tipos = [s.tipo for s in guardada(amb, numero).servicos]
    assert tipos.count(TipoServico.MUDANCA_STATUS) == 3  # atribuição, execução, finalização


# =========================================================================================
# DLT-08 — campos obrigatórios e horas maiores que zero
# =========================================================================================


@pytest.mark.parametrize("falha", ["", "   "])
def test_dlt08_abrir_com_falha_vazia_nao_cria_a_os_nem_consome_o_numero(
    amb: Ambiente, falha: str
) -> None:
    _recusado(
        amb,
        ViolacaoDeRegraError,
        CodigoErro.CAMPO_OBRIGATORIO,
        lambda: amb.servico_ordens.abrir(CARLA, TORNO, falha, Criticidade.BAIXA),
    )
    assert amb.ordens.contar() == 0
    assert aberta(amb) == 1  # o primeiro número ainda está livre


@pytest.mark.parametrize("nome", ["", "  "])
def test_dlt08_cadastrar_usuario_ou_equipamento_sem_nome_nao_consome_identificador(
    amb: Ambiente, nome: str
) -> None:
    _recusado(
        amb,
        ViolacaoDeRegraError,
        CodigoErro.CAMPO_OBRIGATORIO,
        lambda: amb.servico_usuarios.cadastrar(ANA, nome, CARGO_TECNICO, papel=Papel.TECNICO),
    )
    _recusado(
        amb,
        ViolacaoDeRegraError,
        CodigoErro.CAMPO_OBRIGATORIO,
        lambda: amb.servico_equipamentos.cadastrar(ANA, nome, "M1"),
    )
    assert (amb.usuarios.proximo_id(), amb.equipamentos.proximo_id()) == (4, 4)


def test_dlt08_editar_o_nome_para_vazio_e_recusado_e_o_nome_antigo_fica(amb: Ambiente) -> None:
    _recusado(
        amb,
        ViolacaoDeRegraError,
        CodigoErro.CAMPO_OBRIGATORIO,
        lambda: amb.servico_usuarios.atualizar_dados(ANA, BRUNO, nome=" "),
    )
    _recusado(
        amb,
        ViolacaoDeRegraError,
        CodigoErro.CAMPO_OBRIGATORIO,
        lambda: amb.servico_equipamentos.atualizar(ANA, TORNO, "", "GL 240"),
    )
    assert _usuario(amb, BRUNO).nome == "Bruno Lima"
    amb.servico_usuarios.atualizar_dados(ANA, BRUNO, email="novo@empresa.com")  # outros campos ok


@pytest.mark.parametrize(
    ("horas", "intervencao", "codigo"),
    [
        (0.0, "Troca", CodigoErro.HORAS_NAO_POSITIVAS),
        (-1.0, "Troca", CodigoErro.HORAS_NEGATIVAS),
        (1.0, "", CodigoErro.CAMPO_OBRIGATORIO),
        (1.0, "   ", CodigoErro.CAMPO_OBRIGATORIO),
    ],
)
def test_dlt08_apontamento_invalido_nao_altera_a_os_nem_inicia_a_execucao(
    amb: Ambiente, horas: float, intervencao: str, codigo: CodigoErro
) -> None:
    numero = atribuida(amb, BRUNO)
    _recusado(
        amb,
        ViolacaoDeRegraError,
        codigo,
        lambda: amb.servico_ordens.apontar_reparo(BRUNO, numero, horas, intervencao),
    )
    assert guardada(amb, numero).status is StatusOS.ATRIBUIDA


def test_dlt08_peca_com_quantidade_nao_positiva_continua_recusada(amb: Ambiente) -> None:
    numero = atribuida(amb, BRUNO)
    for quantidade in (0, -1):
        _recusado(
            amb,
            ViolacaoDeRegraError,
            CodigoErro.QUANTIDADE_INVALIDA,
            lambda quantidade=quantidade: amb.servico_ordens.apontar_reparo(  # type: ignore[misc]
                BRUNO, numero, 1.0, "Troca", [PecaInformada("Rolamento", quantidade)]
            ),
        )


def test_dlt08_diagnostico_reprovacao_e_cancelamento_vazios_sao_recusados(
    amb: Ambiente,
) -> None:
    numero = atribuida(amb, BRUNO)
    _recusado(
        amb,
        ViolacaoDeRegraError,
        CodigoErro.CAMPO_OBRIGATORIO,
        lambda: amb.servico_ordens.registrar_diagnostico(BRUNO, numero, "", "causa"),
    )
    _recusado(
        amb,
        ViolacaoDeRegraError,
        CodigoErro.CAMPO_OBRIGATORIO,
        lambda: amb.servico_ordens.cancelar(ANA, numero, "  "),
    )
    aprovacao = aguardando_aprovacao(amb)
    _recusado(
        amb,
        ViolacaoDeRegraError,
        CodigoErro.CAMPO_OBRIGATORIO,
        lambda: amb.servico_ordens.reprovar(ANA, aprovacao, ""),
    )
    assert guardada(amb, aprovacao).status is StatusOS.AGUARDANDO_APROVACAO


def test_dlt08_a_autorizacao_vem_antes_da_validacao(amb: Ambiente) -> None:
    _recusado(
        amb,
        PermissaoNegadaError,
        CodigoErro.SEM_PERMISSAO,
        lambda: amb.servico_equipamentos.cadastrar(BRUNO, "", "M1"),
    )
    _recusado(
        amb,
        PermissaoNegadaError,
        CodigoErro.SEM_PERMISSAO,
        lambda: amb.servico_usuarios.cadastrar(BRUNO, "", CARGO_TECNICO, papel=Papel.TECNICO),
    )


# =========================================================================================
# DLT-09 — usuário ativo ou inativo
# =========================================================================================


def test_dlt09_os_usuarios_nascem_ativos(amb: Ambiente) -> None:
    novo = amb.servico_usuarios.cadastrar(ANA, "Diego", CARGO_TECNICO, papel=Papel.TECNICO)
    assert novo.ativo is True
    assert all(u.ativo for u in amb.usuarios.listar())


def test_dlt09_desativar_exige_gerir_usuarios_e_a_recusa_nao_altera_nada(amb: Ambiente) -> None:
    _recusado(
        amb,
        PermissaoNegadaError,
        CodigoErro.SEM_PERMISSAO,
        lambda: amb.servico_usuarios.desativar(BRUNO, CARLA),
    )
    _recusado(
        amb,
        PermissaoNegadaError,
        CodigoErro.SEM_PERMISSAO,
        lambda: amb.servico_usuarios.reativar(BRUNO, CARLA),
    )
    with pytest.raises(NaoEncontradoError):  # ator inexistente (DLT-17)
        amb.servico_usuarios.desativar(INEXISTENTE, CARLA)
    _recusado(  # a autorização vem antes de procurar o alvo (DLT-16)
        amb,
        PermissaoNegadaError,
        CodigoErro.SEM_PERMISSAO,
        lambda: amb.servico_usuarios.desativar(BRUNO, INEXISTENTE),
    )
    with pytest.raises(NaoEncontradoError):
        amb.servico_usuarios.desativar(ANA, INEXISTENTE)


def test_dlt09_ninguem_desativa_a_si_mesmo(amb: Ambiente) -> None:
    erro = _recusado(
        amb,
        RegraDeAplicacaoError,
        CodigoErroAplicacao.AUTOREMOCAO_DE_ACESSO_DE_GESTAO,
        lambda: amb.servico_usuarios.desativar(ANA, ANA),
    )
    assert "próprio usuário" in str(erro)
    assert _usuario(amb, ANA).ativo is True


def test_dlt09_desativar_e_reativar_sao_idempotentes_e_guardados(amb: Ambiente) -> None:
    amb.servico_usuarios.desativar(ANA, BRUNO)
    amb.servico_usuarios.desativar(ANA, BRUNO)
    assert _usuario(amb, BRUNO).ativo is False
    amb.servico_usuarios.reativar(ANA, BRUNO)
    amb.servico_usuarios.reativar(ANA, BRUNO)
    assert _usuario(amb, BRUNO).ativo is True


def test_dlt09_usuario_inativo_nao_opera_nenhum_caso_de_uso(amb: Ambiente) -> None:
    numero = em_execucao(amb, BRUNO)
    aprovacao = aguardando_aprovacao(amb)
    equipamento = amb.servico_equipamentos
    ordens, usuarios = amb.servico_ordens, amb.servico_usuarios
    nova = amb.servico_usuarios.cadastrar(ANA, "Eva", CARGO_GESTOR, papel=Papel.GESTOR).id
    # Bruno tem OS ativas, e o serviço não o desativaria (REG-E-04): o estado "inativo com OS"
    # (de uma base anterior à regra) é montado direto no repositório, para provar que ele não opera.
    bruno = _usuario(amb, BRUNO)
    bruno.desativar()
    amb.usuarios.salvar(bruno)
    for quem in (CARLA, nova):
        amb.servico_usuarios.desativar(ANA, quem)
    operacoes: tuple[Operacao, ...] = (
        lambda: ordens.abrir(CARLA, TORNO, "x", Criticidade.BAIXA),
        lambda: ordens.consultar(CARLA, numero),
        lambda: ordens.listar(BRUNO),
        lambda: ordens.adicionar_apontamento(BRUNO, numero, "x"),
        lambda: ordens.registrar_diagnostico(BRUNO, numero, "p", "c"),
        lambda: ordens.apontar_reparo(BRUNO, numero, 1.0, "i"),
        lambda: ordens.alterar_status(BRUNO, numero, StatusOS.AGUARDANDO_PECA),
        lambda: ordens.concluir_tecnicamente(BRUNO, numero, "t", True),
        lambda: equipamento.listar(CARLA),
        lambda: amb.servico_disponibilidade.consultar(CARLA),
        lambda: amb.servico_disponibilidade.alterar_minha_disponibilidade(
            BRUNO, Disponibilidade.AUSENTE
        ),
        lambda: usuarios.listar(nova),
        lambda: ordens.aprovar(nova, aprovacao),
        lambda: ordens.atribuir(nova, numero, CARLA),
    )
    for operacao in operacoes:
        _recusado(amb, PermissaoNegadaError, CodigoErro.USUARIO_INATIVO, operacao)


def test_dlt09_o_ator_inativo_e_recusado_antes_da_verificacao_de_permissao(
    amb: Ambiente,
) -> None:
    amb.servico_usuarios.desativar(ANA, BRUNO)
    _sem(amb, CARGO_TECNICO, Permissao.VER_EQUIPAMENTOS)
    _recusado(
        amb,
        PermissaoNegadaError,
        CodigoErro.USUARIO_INATIVO,
        lambda: amb.servico_equipamentos.listar(BRUNO),
    )
    with pytest.raises(NaoEncontradoError):  # inexistente continua sendo "não encontrado"
        amb.servico_equipamentos.listar(INEXISTENTE)


def test_dlt09_tecnico_inativo_sai_da_lista_e_nao_recebe_os(amb: Ambiente) -> None:
    amb.servico_usuarios.desativar(ANA, BRUNO)
    assert [t.id for t in amb.projecoes.tecnicos()] == [CARLA]
    assert [linha.id for linha in amb.servico_disponibilidade.consultar(ANA)] == [CARLA]
    numero = aberta(amb)
    erro = _recusado(
        amb,
        ViolacaoDeRegraError,
        CodigoErro.USUARIO_INATIVO,
        lambda: amb.servico_ordens.atribuir(ANA, numero, BRUNO, confirmar_ausente=True),
    )
    assert "inativo" in str(erro)
    amb.servico_usuarios.reativar(ANA, BRUNO)
    amb.servico_ordens.atribuir(ANA, numero, BRUNO)
    assert guardada(amb, numero).tecnico_atribuido == _usuario(amb, BRUNO)


def test_dlt09_desativar_preserva_o_historico_e_nao_reatribui_as_os(amb: Ambiente) -> None:
    # Só quem não tem OS ativa é desativado (REG-E-04): aqui a OS já foi concluída.
    numero = aguardando_aprovacao(amb)
    amb.servico_ordens.aprovar(ANA, numero)
    antes = guardada(amb, numero)
    amb.servico_usuarios.desativar(ANA, BRUNO)
    depois = guardada(amb, numero)
    assert depois.tecnico_atribuido == _usuario(amb, BRUNO)  # nenhuma reatribuição automática
    assert (depois.status, depois.servicos) == (antes.status, antes.servicos)
    assert amb.projecoes.carga_do_tecnico(BRUNO) == 0
    assert _usuario(amb, BRUNO).nome == "Bruno Lima"  # a referência histórica mantém o nome


def test_dlt09_usuario_com_historico_continua_sem_poder_ser_excluido_mas_pode_ser_desativado(
    amb: Ambiente,
) -> None:
    amb.servico_ordens.aprovar(ANA, aguardando_aprovacao(amb))  # histórico, sem OS ativa
    _recusado(
        amb,
        RegraDeAplicacaoError,
        CodigoErroAplicacao.USUARIO_COM_HISTORICO,
        lambda: amb.servico_usuarios.excluir(ANA, BRUNO),
    )
    amb.servico_usuarios.desativar(ANA, BRUNO)
    assert amb.usuarios.obter(BRUNO) is not None  # o histórico não perde a referência
    assert BRUNO in [u.id for u in amb.servico_usuarios.listar(ANA)]  # listagem completa


def test_dlt09_reativar_restaura_a_operacao(amb: Ambiente) -> None:
    amb.servico_usuarios.desativar(ANA, CARLA)
    _recusado(
        amb,
        PermissaoNegadaError,
        CodigoErro.USUARIO_INATIVO,
        lambda: amb.servico_ordens.abrir(CARLA, TORNO, "x", Criticidade.BAIXA),
    )
    amb.servico_usuarios.reativar(ANA, CARLA)
    assert amb.servico_ordens.abrir(CARLA, TORNO, "x", Criticidade.BAIXA).numero == 1


def test_dlt09_nenhuma_regra_de_negocio_alem_das_aprovadas_foi_criada(amb: Ambiente) -> None:
    """A desativação não muda o papel, o cargo nem as permissões; as OS não são movidas."""
    antes = _usuario(amb, BRUNO)
    amb.servico_usuarios.desativar(ANA, BRUNO)
    depois = _usuario(amb, BRUNO)
    assert (depois.papel, depois.cargo.id) == (antes.papel, antes.cargo.id)
    cargo = amb.cargos.obter(CARGO_TECNICO)
    assert cargo is not None
    assert cargo.permissoes.tem(Permissao.APONTAR_REPARO)
