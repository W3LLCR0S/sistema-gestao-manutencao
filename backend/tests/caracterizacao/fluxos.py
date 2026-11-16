"""Caminhos reutilizáveis até cada estado da OS, escritos **somente** contra a fachada.

Cada função exige que as operações do caminho sejam aceitas: se o comportamento do legado
mudar, o teste falha na preparação, não em silêncio.
"""

from tests.caracterizacao.cenarios import (
    ALTA,
    ANA,
    BRUNO,
    CARLA,
    STATUS_REPARO_FINALIZADO,
    TORNO,
)
from tests.caracterizacao.fachada import Fachada, Peca, Resultado


def aceitar(resultado: Resultado) -> Resultado:
    """Garante que uma etapa de preparação foi aceita (e devolve o resultado)."""
    assert resultado.aceito, f"preparação recusada: {resultado.recusa} - {resultado.mensagem}"
    return resultado


def os_aberta(f: Fachada, *, solicitante: int = CARLA, equipamento: int = TORNO) -> int:
    resultado = aceitar(f.abrir_os(solicitante, equipamento, "Torno parado", ALTA))
    return int(resultado.valor)


def os_atribuida(f: Fachada, *, tecnico: int = BRUNO) -> int:
    numero = os_aberta(f)
    aceitar(f.atribuir(numero, tecnico, ANA))
    return numero


def os_em_execucao(f: Fachada, *, tecnico: int = BRUNO) -> int:
    """Atribuída -> Em Execução pelo primeiro apontamento de reparo (1,5 h, uma peça)."""
    numero = os_atribuida(f, tecnico=tecnico)
    aceitar(f.apontar_reparo(numero, tecnico, 1.5, "Troca do rolamento", (Peca("Rolamento", 2),)))
    return numero


def os_reparo_finalizado(f: Fachada, *, tecnico: int = BRUNO, com_diagnostico: bool = True) -> int:
    numero = os_atribuida(f, tecnico=tecnico)
    if com_diagnostico:
        aceitar(f.registrar_diagnostico(numero, tecnico, "Rolamento gasto", "Falta de graxa"))
    aceitar(f.apontar_reparo(numero, tecnico, 1.5, "Troca do rolamento", (Peca("Rolamento", 2),)))
    aceitar(f.alterar_status(numero, tecnico, STATUS_REPARO_FINALIZADO))
    return numero


def os_aguardando_aprovacao(f: Fachada, *, tecnico: int = BRUNO) -> int:
    numero = os_reparo_finalizado(f, tecnico=tecnico)
    aceitar(f.concluir_tecnicamente(numero, tecnico, "Funcionou sob carga", True))
    return numero


def os_concluida(f: Fachada, *, tecnico: int = BRUNO) -> int:
    numero = os_aguardando_aprovacao(f, tecnico=tecnico)
    aceitar(f.aprovar(numero, ANA))
    return numero


def os_cancelada(f: Fachada) -> int:
    numero = os_aberta(f)
    aceitar(f.cancelar(numero, ANA, "Chamado indevido"))
    return numero
