"""Legado e serviços lado a lado na regularização da Operação E (REG-E-01, 04, 05 e 06).

Como ``test_operacao_e_servicos.py``: o **mesmo roteiro** roda no legado e nos serviços e mostra que
o legado **aceitava** o que a decisão regularizada muda, que os serviços **recusam sem alterar o
estado** e que **o que não muda é idêntico** nos dois. Testes de infraestrutura da caracterização
(sem marcador ``cenario``); o comportamento antigo está caracterizado nos testes de cenário citados
em ``deltas.py``.

* DLT-22 (REG-E-05): observação e descrição de peça obrigatórias.
* DLT-23 (REG-E-06): disponibilidade manual só ``Disponível`` e ``Ausente``.
"""

from tests.caracterizacao.cenarios import (
    ALTA,
    ANA,
    AUSENTE,
    BRUNO,
    CARLA,
    DISPONIVEL,
    EM_ATENDIMENTO,
    TORNO,
)
from tests.caracterizacao.fachada import Fachada, Peca, Recusa
from tests.caracterizacao.fluxos import (
    aceitar,
    estado_global,
    os_atribuida,
    os_em_execucao,
    os_snap,
    recusada,
)
from tests.caracterizacao.pares import Par


def _disp(f: Fachada, usuario: int) -> str:
    snap = f.usuario(usuario)
    assert snap is not None
    return snap.disponibilidade


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
