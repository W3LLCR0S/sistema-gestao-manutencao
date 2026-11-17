"""Implementações das portas de repositório submetidas à suíte de contrato.

Cada entrada de ``IMPLEMENTACOES`` constrói um conjunto **novo e vazio** dos quatro repositórios,
ligados entre si. A suíte (``test_contrato_*.py``) roda inteira contra cada entrada: é assim que a
substituição de uma implementação por outra (LSP) fica demonstrada. A Fase 03 acrescentará aqui a
implementação sobre o banco, sem alterar nenhum teste.
"""

from collections.abc import Callable
from dataclasses import dataclass

from manutencao.application.portas.repositorios import (
    CargoRepository,
    EquipamentoRepository,
    OrdemServicoRepository,
    UsuarioRepository,
)
from manutencao.infrastructure.memoria import (
    CargosEmMemoria,
    EquipamentosEmMemoria,
    OrdensEmMemoria,
    UsuariosEmMemoria,
)


@dataclass(frozen=True)
class Repositorios:
    """Os quatro repositórios de uma implementação, vistos só pelas portas."""

    equipamentos: EquipamentoRepository
    cargos: CargoRepository
    usuarios: UsuarioRepository
    ordens: OrdemServicoRepository


def _em_memoria() -> Repositorios:
    cargos = CargosEmMemoria()
    return Repositorios(
        EquipamentosEmMemoria(), cargos, UsuariosEmMemoria(cargos), OrdensEmMemoria()
    )


IMPLEMENTACOES: dict[str, Callable[[], Repositorios]] = {"memoria": _em_memoria}
