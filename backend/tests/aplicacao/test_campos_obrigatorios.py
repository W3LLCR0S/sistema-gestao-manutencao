"""Os campos documentados como obrigatórios (ou não) são exatamente os que os serviços validam.

Prova a lista de ``tests/apoio/campos.py`` (a mesma da documentação, REG-E-05 e REG-E-08): para cada
campo obrigatório, texto vazio e texto só com espaços são recusados com ``campo_obrigatorio`` e
**sem mutação**; para cada campo sem validação, o vazio continua aceito. A tabela é conferida contra
os pontos de entrada de texto dos serviços.

Cada campo é um par (preparar, executar): ``preparar`` leva o ambiente ao estado em que o campo é
pedido (e devolve o número da OS, quando há) e ``executar`` tenta a operação com o texto dado.
"""

from collections.abc import Callable

import pytest

from manutencao.application.dto import PecaInformada
from manutencao.domain.enums import Criticidade, Papel
from manutencao.domain.erros import CodigoErro, ViolacaoDeRegraError
from tests.apoio.ambiente import ANA, BRUNO, CARGO_TECNICO, CARLA, TORNO, Ambiente
from tests.apoio.caminhos import (
    aguardando_aprovacao,
    atribuida,
    em_execucao,
    reparo_finalizado,
)
from tests.apoio.campos import CAMPOS_OBRIGATORIOS, CAMPOS_SEM_VALIDACAO
from tests.dominio.fabrica import instantaneo

Preparar = Callable[[Ambiente], int]
Executar = Callable[[Ambiente, int, str], object]
Campo = tuple[Preparar, Executar]


def _nada(amb: Ambiente) -> int:
    return 0


OBRIGATORIOS: dict[str, Campo] = {
    "descrição da falha": (
        _nada,
        lambda amb, n, t: amb.servico_ordens.abrir(CARLA, TORNO, t, Criticidade.BAIXA),
    ),
    "parecer técnico": (
        atribuida,
        lambda amb, n, t: amb.servico_ordens.registrar_diagnostico(BRUNO, n, t, "causa"),
    ),
    "causa-raiz": (
        atribuida,
        lambda amb, n, t: amb.servico_ordens.registrar_diagnostico(BRUNO, n, "parecer", t),
    ),
    "intervenção realizada": (
        atribuida,
        lambda amb, n, t: amb.servico_ordens.apontar_reparo(BRUNO, n, 1.0, t),
    ),
    "motivo da reprovação": (
        aguardando_aprovacao,
        lambda amb, n, t: amb.servico_ordens.reprovar(ANA, n, t),
    ),
    "motivo do cancelamento": (
        atribuida,
        lambda amb, n, t: amb.servico_ordens.cancelar(ANA, n, t),
    ),
    "nome do usuário": (
        _nada,
        lambda amb, n, t: amb.servico_usuarios.cadastrar(
            ANA, t, CARGO_TECNICO, papel=Papel.TECNICO
        ),
    ),
    "nome do equipamento": (
        _nada,
        lambda amb, n, t: amb.servico_equipamentos.cadastrar(ANA, t, "modelo"),
    ),
    "texto da observação": (
        em_execucao,
        lambda amb, n, t: amb.servico_ordens.adicionar_apontamento(ANA, n, t),
    ),
    "descrição da peça": (
        atribuida,
        lambda amb, n, t: amb.servico_ordens.apontar_reparo(
            BRUNO, n, 1.0, "Troca", [PecaInformada(t, 1)]
        ),
    ),
}

OPCIONAIS: dict[str, Campo] = {
    "modelo do equipamento": (
        _nada,
        lambda amb, n, t: amb.servico_equipamentos.cadastrar(ANA, "Prensa", t),
    ),
    "teste funcional": (
        reparo_finalizado,
        lambda amb, n, t: amb.servico_ordens.concluir_tecnicamente(BRUNO, n, t, True),
    ),
    "e-mail do usuário": (
        _nada,
        lambda amb, n, t: amb.servico_usuarios.cadastrar(
            ANA, "Diego", CARGO_TECNICO, t, papel=Papel.TECNICO
        ),
    ),
    "escala do usuário": (
        _nada,
        lambda amb, n, t: amb.servico_usuarios.cadastrar(
            ANA, "Diego", CARGO_TECNICO, "", t, papel=Papel.TECNICO
        ),
    ),
}


def _estado(amb: Ambiente) -> tuple[object, ...]:
    return (
        [(u.id, u.nome, u.email, u.escala, u.papel, u.ativo) for u in amb.usuarios.listar()],
        [(e.id, e.nome, e.modelo) for e in amb.equipamentos.listar()],
        [instantaneo(o) for o in amb.ordens.listar()],
        amb.usuarios.proximo_id(),
        amb.equipamentos.proximo_id(),
        amb.ordens.proximo_numero(),
    )


def test_a_tabela_cobre_exatamente_os_campos_documentados() -> None:
    assert set(OBRIGATORIOS) == {rotulo for rotulo, _ in CAMPOS_OBRIGATORIOS}
    assert set(OPCIONAIS) == set(CAMPOS_SEM_VALIDACAO)


@pytest.mark.parametrize("texto", ["", "   ", "\t \n"])
@pytest.mark.parametrize("rotulo", [rotulo for rotulo, _ in CAMPOS_OBRIGATORIOS])
def test_campo_obrigatorio_vazio_ou_so_com_espacos_e_recusado_sem_mutacao(
    amb: Ambiente, rotulo: str, texto: str
) -> None:
    preparar, executar = OBRIGATORIOS[rotulo]
    numero = preparar(amb)
    antes = _estado(amb)
    with pytest.raises(ViolacaoDeRegraError) as capturado:
        executar(amb, numero, texto)
    assert capturado.value.codigo is CodigoErro.CAMPO_OBRIGATORIO
    assert "Campo obrigatório" in str(capturado.value)
    assert _estado(amb) == antes


@pytest.mark.parametrize("rotulo", [rotulo for rotulo, _ in CAMPOS_OBRIGATORIOS])
def test_campo_obrigatorio_com_texto_valido_e_aceito(amb: Ambiente, rotulo: str) -> None:
    preparar, executar = OBRIGATORIOS[rotulo]
    executar(amb, preparar(amb), "texto válido")


@pytest.mark.parametrize("rotulo", CAMPOS_SEM_VALIDACAO)
def test_campo_sem_validacao_continua_aceitando_o_vazio(amb: Ambiente, rotulo: str) -> None:
    preparar, executar = OPCIONAIS[rotulo]
    executar(amb, preparar(amb), "")
