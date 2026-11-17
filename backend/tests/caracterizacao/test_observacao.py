"""Apontamento (observação) no histórico da OS: ``OrdemServico.adicionar_apontamento``.

Neste legado "apontamento" é um comentário livre (``TipoServico.APONTAMENTO``); a D-04 o chama de
*observação* para distingui-lo de ``apontar_reparo``. Os defeitos de OS encerrada (AUD-11) estão
em ``test_legado_defeitos.py``.
"""

from collections.abc import Callable

import pytest

from tests.caracterizacao.cenarios import (
    ANA,
    BRUNO,
    CARGO_GESTOR,
    CARGO_TECNICO,
    CARLA,
)
from tests.caracterizacao.fachada import Fachada, Recusa, RelogioFixo
from tests.caracterizacao.fluxos import (
    aceitar,
    estado_global,
    os_aberta,
    os_aguardando_aprovacao,
    os_aguardando_peca,
    os_atribuida,
    os_em_execucao,
    os_reparo_finalizado,
    os_snap,
    recusada,
)


@pytest.mark.cenario("CAR-38")
def test_observacao_cria_registro_do_tipo_apontamento_com_autor_texto_e_data(
    f: Fachada, relogio: RelogioFixo
) -> None:
    numero = os_aberta(f)
    relogio.avancar(hours=2)
    aceitar(f.adicionar_observacao(numero, BRUNO, "Peça solicitada ao almoxarifado"))

    registro = os_snap(f, numero).historico[-1]
    assert registro.numero == 2
    assert (registro.tipo, registro.descricao) == ("Apontamento", "Peça solicitada ao almoxarifado")
    assert (registro.responsavel_id, registro.data) == (BRUNO, "10/03/2026 11:00")
    assert (registro.horas, registro.pecas) == (0.0, ())


@pytest.mark.cenario("CAR-38")
@pytest.mark.parametrize(
    "construir",
    [
        os_aberta,
        os_atribuida,
        os_em_execucao,
        os_aguardando_peca,
        os_reparo_finalizado,
        os_aguardando_aprovacao,
    ],
)
def test_observacao_nao_altera_o_status_nem_os_dados_tecnicos(
    f: Fachada, construir: Callable[[Fachada], int]
) -> None:
    numero = construir(f)
    antes = os_snap(f, numero)
    aceitar(f.adicionar_observacao(numero, CARLA, "nota"))
    depois = os_snap(f, numero)
    assert depois.status == antes.status
    assert depois.tecnico_id == antes.tecnico_id
    assert (depois.diagnostico, depois.horas_trabalhadas, depois.intervencoes, depois.pecas) == (
        antes.diagnostico,
        antes.horas_trabalhadas,
        antes.intervencoes,
        antes.pecas,
    )
    assert len(depois.historico) == len(antes.historico) + 1


@pytest.mark.cenario("CAR-39")
@pytest.mark.parametrize("autor", [ANA, BRUNO, CARLA])
def test_qualquer_usuario_com_registrar_apontamento_inclui_observacao(
    f: Fachada, autor: int
) -> None:
    """Preservar: o legado não confere responsável nem autoria da abertura (D-04 muda isso)."""
    numero = os_atribuida(f, tecnico=BRUNO)  # aberta por Carla, de Bruno; Ana é gestora
    aceitar(f.adicionar_observacao(numero, autor, f"nota de {autor}"))
    assert os_snap(f, numero).historico[-1].responsavel_id == autor


@pytest.mark.cenario("CAR-39")
def test_observacao_de_quem_nao_e_responsavel_nem_abriu_a_os_e_aceita(f: Fachada) -> None:
    """D-04 (modifica): tecnico que não é o responsável nem o autor da abertura também registra."""
    numero = os_atribuida(f, tecnico=BRUNO)
    outro = f.cadastrar_usuario("Diego", 2)  # técnico sem relação com a OS
    aceitar(f.adicionar_observacao(numero, outro, "Passando por aqui"))
    assert os_snap(f, numero).historico[-1].responsavel_id == outro


@pytest.mark.cenario("CAR-40")
def test_observacao_sem_a_permissao_registrar_apontamento_e_recusada(f: Fachada) -> None:
    numero = os_aberta(f)
    f.definir_permissoes_cargo(CARGO_TECNICO, ("ver_os", "abrir_os"))
    antes = estado_global(f)
    resultado = recusada(f.adicionar_observacao(numero, CARLA, "nota"), Recusa.SEM_PERMISSAO)
    assert "Incluir apontamentos no histórico" in resultado.mensagem
    assert estado_global(f) == antes


@pytest.mark.cenario("CAR-40")
def test_permissao_de_observacao_independe_das_permissoes_tecnicas(f: Fachada) -> None:
    """Só ``registrar_apontamento`` conta: um cargo apenas com ela já inclui observações."""
    numero = os_aberta(f)
    f.definir_permissoes_cargo(CARGO_GESTOR, ("registrar_apontamento",))
    aceitar(f.adicionar_observacao(numero, ANA, "nota da gestão"))
    assert os_snap(f, numero).historico[-1].tipo == "Apontamento"
