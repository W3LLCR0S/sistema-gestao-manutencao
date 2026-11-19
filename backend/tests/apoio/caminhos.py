"""Caminhos até cada estado da OS, percorridos **pelos serviços** (nunca pelas entidades)."""

from manutencao.application.dto import PecaInformada
from manutencao.domain.enums import Criticidade, StatusOS
from manutencao.domain.ordem_servico import OrdemServico
from tests.apoio.ambiente import ANA, BRUNO, CARLA, TORNO, Ambiente

PECAS = [PecaInformada("Rolamento", 2)]


def aberta(amb: Ambiente, solicitante: int = CARLA, equipamento: int = TORNO) -> int:
    return amb.servico_ordens.abrir(
        solicitante, equipamento, "Torno parado", Criticidade.ALTA
    ).numero


def atribuida(amb: Ambiente, tecnico: int = BRUNO) -> int:
    numero = aberta(amb)
    amb.servico_ordens.atribuir(ANA, numero, tecnico)
    return numero


def em_execucao(amb: Ambiente, tecnico: int = BRUNO) -> int:
    numero = atribuida(amb, tecnico)
    amb.servico_ordens.apontar_reparo(tecnico, numero, 1.5, "Troca do rolamento", PECAS)
    return numero


def reparo_finalizado(amb: Ambiente, tecnico: int = BRUNO, *, diagnostico: bool = True) -> int:
    numero = atribuida(amb, tecnico)
    if diagnostico:
        amb.servico_ordens.registrar_diagnostico(
            tecnico, numero, "Rolamento gasto", "Falta de graxa"
        )
    amb.servico_ordens.apontar_reparo(tecnico, numero, 1.5, "Troca do rolamento", PECAS)
    amb.servico_ordens.alterar_status(tecnico, numero, StatusOS.REPARO_FINALIZADO)
    return numero


def aguardando_aprovacao(amb: Ambiente) -> int:
    numero = reparo_finalizado(amb)
    assert amb.servico_ordens.concluir_tecnicamente(BRUNO, numero, "Funcionou", True)
    return numero


def guardada(amb: Ambiente, numero: int) -> OrdemServico:
    achada = amb.ordens.obter(numero)
    assert achada is not None
    return achada
