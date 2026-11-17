"""Legado e serviços lado a lado na regularização da Operação E (REG-E-01, 04, 05 e 06).

Como ``test_operacao_e_servicos.py``: o **mesmo roteiro** roda no legado e nos serviços e mostra que
o legado **aceitava** o que a decisão regularizada muda, que os serviços **recusam sem alterar o
estado** e que **o que não muda é idêntico** nos dois. Testes de infraestrutura da caracterização
(sem marcador ``cenario``); o comportamento antigo está caracterizado nos testes de cenário citados
em ``deltas.py``.

* DLT-18 (REG-E-01): o último gestor administrativamente apto não é eliminado.
* DLT-21 (REG-E-04): OS ativas impedem desativar e deixar o papel Técnico.
* DLT-22 (REG-E-05): observação e descrição de peça obrigatórias.
* DLT-23 (REG-E-06): disponibilidade manual só ``Disponível`` e ``Ausente``.
"""

from collections.abc import Callable

import pytest

from manutencao.application.erros import CodigoErroAplicacao, RegraDeAplicacaoError
from manutencao.domain.enums import Papel
from tests.caracterizacao.adaptador_servicos import AdaptadorServicos
from tests.caracterizacao.cenarios import (
    ALTA,
    ANA,
    AUSENTE,
    BRUNO,
    CARGO_GESTOR,
    CARGO_TECNICO,
    CARLA,
    DISPONIVEL,
    EM_ATENDIMENTO,
    PERMISSOES_PADRAO_TECNICO,
    TORNO,
)
from tests.caracterizacao.fachada import Fachada, Peca, Recusa
from tests.caracterizacao.fluxos import (
    aceitar,
    estado_global,
    os_atribuida,
    os_cancelada,
    os_em_execucao,
    os_snap,
    recusada,
)
from tests.caracterizacao.pares import Par


def _disp(f: Fachada, usuario: int) -> str:
    snap = f.usuario(usuario)
    assert snap is not None
    return snap.disponibilidade


def _servicos(par: Par) -> AdaptadorServicos:
    return par.servicos


# =========================================================================================
# DLT-18 — último gestor administrativamente apto (REG-E-01)
# =========================================================================================


def _dar_gestao_ao_tecnico(par: Par) -> None:
    """Bruno passa a poder gerir usuários sem ser gestor: um solicitante que não é o alvo."""
    for f in (par.legado, par.servicos):
        f.definir_permissoes_cargo(CARGO_TECNICO, (*PERMISSOES_PADRAO_TECNICO, "gerir_usuarios"))


def test_dlt18_eliminar_o_unico_gestor_o_legado_aceita_e_os_servicos_recusam(par: Par) -> None:
    _dar_gestao_ao_tecnico(par)
    antes = estado_global(par.servicos)
    recusada(par.servicos.remover_usuario(ANA, solicitante=BRUNO), Recusa.ULTIMO_GESTOR)
    recusada(
        par.servicos.definir_permissoes_cargo_por(BRUNO, CARGO_GESTOR, ()), Recusa.ULTIMO_GESTOR
    )
    assert estado_global(par.servicos) == antes  # nenhuma mutação, nenhum usuário criado
    aceitar(par.legado.definir_permissoes_cargo_por(BRUNO, CARGO_GESTOR, ()))  # o legado aceita
    aceitar(par.legado.remover_usuario(ANA, solicitante=BRUNO))
    assert par.legado.usuario(ANA) is None


def test_dlt18_com_outro_gestor_apto_a_operacao_e_aceita_nos_dois(par: Par) -> None:
    _dar_gestao_ao_tecnico(par)
    for f in (par.legado, par.servicos):
        f.cadastrar_usuario("Eva", CARGO_GESTOR)
    for f in (par.legado, par.servicos):
        aceitar(f.remover_usuario(ANA, solicitante=BRUNO))
    assert par.legado.usuarios() == par.servicos.usuarios()


# =========================================================================================
# DLT-21 — OS ativas impedem desativar e deixar o papel Técnico (REG-E-04)
# =========================================================================================


def test_dlt21_trocar_o_tecnico_de_papel_com_os_ativa_o_legado_aceita_e_os_servicos_recusam(
    par: Par,
) -> None:
    """No legado o papel é a permissão: trocar o cargo de Bruno (com OS ativa) para o de gestor o
    tira da lista de técnicos e deixa a OS com quem já não é técnico. Nos serviços o papel é
    explícito: a mudança é uma operação própria e, com OS ativa, é recusada; desativar também."""
    for f in (par.legado, par.servicos):
        os_atribuida(f, tecnico=BRUNO)
    aceitar(par.legado.alterar_cargo_por(ANA, BRUNO, CARGO_GESTOR))
    assert par.legado.tecnicos() == (CARLA,)  # Bruno deixou de ser técnico
    assert os_snap(par.legado, 1).tecnico_id == BRUNO  # e a OS continua com ele
    servicos = _servicos(par)._c
    antes = estado_global(par.servicos)
    operacoes: tuple[Callable[[], object], ...] = (
        lambda: servicos.servico_usuarios.alterar_papel(ANA, BRUNO, Papel.GESTOR),
        lambda: servicos.servico_usuarios.desativar(ANA, BRUNO),
    )
    for operacao in operacoes:
        with pytest.raises(RegraDeAplicacaoError) as capturado:
            operacao()
        assert capturado.value.codigo is CodigoErroAplicacao.USUARIO_COM_OS_ATIVAS
    assert estado_global(par.servicos) == antes
    assert os_snap(par.servicos, 1).tecnico_id == BRUNO  # nada foi reatribuído nem cancelado


def test_dlt21_com_a_os_encerrada_a_desativacao_e_aceita_nos_servicos(par: Par) -> None:
    os_cancelada(par.servicos, atribuida=True, tecnico=BRUNO)
    servicos = _servicos(par)._c
    servicos.servico_usuarios.desativar(ANA, BRUNO)
    servicos.servico_usuarios.alterar_papel(ANA, CARLA, Papel.GESTOR)
    assert os_snap(par.servicos, 1).tecnico_id == BRUNO  # o histórico não é tocado


# =========================================================================================
# DLT-22 — observação e descrição de peça obrigatórias (REG-E-05)
# =========================================================================================


def test_dlt22_observacao_vazia_o_legado_aceita_e_os_servicos_recusam(par: Par) -> None:
    for f in (par.legado, par.servicos):
        os_em_execucao(f, tecnico=BRUNO)
    aceitar(par.legado.adicionar_observacao(1, CARLA, ""))
    aceitar(par.legado.adicionar_observacao(1, ANA, "   "))
    assert [s.descricao for s in os_snap(par.legado, 1).historico[-2:]] == ["", "   "]
    antes = estado_global(par.servicos)
    for autor, texto in ((CARLA, ""), (ANA, "   "), (BRUNO, "\t\n")):
        recusada(par.servicos.adicionar_observacao(1, autor, texto), Recusa.CAMPO_OBRIGATORIO)
    assert estado_global(par.servicos) == antes  # nenhuma mutação parcial


def test_dlt22_peca_sem_descricao_o_legado_aceita_e_os_servicos_recusam(par: Par) -> None:
    for f in (par.legado, par.servicos):
        os_atribuida(f, tecnico=BRUNO)
    aceitar(par.legado.apontar_reparo(1, BRUNO, 1.0, "Troca", (Peca("", 1),)))
    assert os_snap(par.legado, 1).pecas[0].descricao == ""
    antes = estado_global(par.servicos)
    for descricao in ("", "   "):
        resultado = recusada(
            par.servicos.apontar_reparo(1, BRUNO, 1.0, "Troca", (Peca(descricao, 1),)),
            Recusa.CAMPO_OBRIGATORIO,
        )
        assert "descrição da peça" in resultado.mensagem
    assert estado_global(par.servicos) == antes
    assert os_snap(par.servicos, 1).status == "Atribuída"  # não iniciou a execução


def test_dlt22_com_texto_valido_o_resultado_e_o_estado_sao_iguais_nos_dois(par: Par) -> None:
    for f in (par.legado, par.servicos):
        numero = aceitar(f.abrir_os(CARLA, TORNO, "Falha real", ALTA)).valor
        aceitar(f.atribuir(numero, BRUNO, ANA))
        aceitar(f.apontar_reparo(numero, BRUNO, 1.0, "Troca", (Peca("Rolamento", 2),)))
        aceitar(f.adicionar_observacao(numero, CARLA, "Ruído no eixo"))
    assert par.legado.todas_as_os() == par.servicos.todas_as_os()


def test_dlt22_quantidade_nao_positiva_continua_igual_nos_dois(par: Par) -> None:
    for f in (par.legado, par.servicos):
        os_atribuida(f, tecnico=BRUNO)
        resultado = recusada(
            f.apontar_reparo(1, BRUNO, 1.0, "i", (Peca("", 0),)), Recusa.QUANTIDADE_INVALIDA
        )
        assert resultado.mensagem == "A quantidade deve ser maior que zero."  # antes da descrição
    assert estado_global(par.legado) == estado_global(par.servicos)


# =========================================================================================
# DLT-23 — disponibilidade manual (REG-E-06)
# =========================================================================================


def test_dlt23_em_atendimento_manual_o_legado_aceita_e_os_servicos_recusam(par: Par) -> None:
    aceitar(par.legado.definir_disponibilidade(CARLA, EM_ATENDIMENTO, solicitante=CARLA))
    assert _disp(par.legado, CARLA) == EM_ATENDIMENTO  # o legado grava o valor manual
    antes = estado_global(par.servicos)
    for solicitante, alvo in ((CARLA, CARLA), (ANA, CARLA), (ANA, ANA)):
        resultado = recusada(
            par.servicos.definir_disponibilidade(alvo, EM_ATENDIMENTO, solicitante=solicitante),
            Recusa.DISPONIBILIDADE_MANUAL_INVALIDA,
        )
        assert "derivado" in resultado.mensagem
    assert estado_global(par.servicos) == antes
    assert _disp(par.servicos, CARLA) == DISPONIVEL


def test_dlt23_disponivel_e_ausente_manuais_sao_iguais_nos_dois(par: Par) -> None:
    for f in (par.legado, par.servicos):
        aceitar(f.definir_disponibilidade(BRUNO, AUSENTE, solicitante=BRUNO))
        aceitar(f.definir_disponibilidade(CARLA, AUSENTE, solicitante=ANA))
    assert (_disp(par.legado, BRUNO), _disp(par.legado, CARLA)) == (AUSENTE, AUSENTE)
    for f in (par.legado, par.servicos):
        aceitar(f.definir_disponibilidade(BRUNO, DISPONIVEL, solicitante=BRUNO))
    assert _disp(par.legado, BRUNO) == _disp(par.servicos, BRUNO) == DISPONIVEL


def test_dlt23_a_ausencia_manual_prevalece_sobre_a_os_em_execucao_nos_servicos(par: Par) -> None:
    os_em_execucao(par.servicos, tecnico=BRUNO)
    assert _disp(par.servicos, BRUNO) == EM_ATENDIMENTO  # derivado
    aceitar(par.servicos.definir_disponibilidade(BRUNO, AUSENTE, solicitante=BRUNO))
    assert _disp(par.servicos, BRUNO) == AUSENTE
