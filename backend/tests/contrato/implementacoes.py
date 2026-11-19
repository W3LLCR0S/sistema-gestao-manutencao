"""Implementações das portas de repositório submetidas à suíte de contrato.

Cada entrada de ``IMPLEMENTACOES`` constrói um conjunto **novo e vazio** dos quatro repositórios,
ligados entre si. A suíte (``test_contrato_*.py``) roda inteira contra cada entrada: é assim que a
substituição de uma implementação por outra (LSP) fica demonstrada. A implementação sobre o
PostgreSQL (Fase 03) foi acrescentada aqui sem alterar nenhum teste.
"""

from collections.abc import Callable
from dataclasses import dataclass

import pytest

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
from manutencao.infrastructure.postgres import (
    Banco,
    CargosNoBanco,
    EquipamentosNoBanco,
    OrdensNoBanco,
    UsuariosNoBanco,
)


@dataclass(frozen=True)
class Repositorios:
    """Os quatro repositórios de uma implementação, vistos só pelas portas."""

    equipamentos: EquipamentoRepository
    cargos: CargoRepository
    usuarios: UsuarioRepository
    ordens: OrdemServicoRepository


def _em_memoria(_pedido: pytest.FixtureRequest) -> Repositorios:
    cargos = CargosEmMemoria()
    return Repositorios(
        EquipamentosEmMemoria(), cargos, UsuariosEmMemoria(cargos), OrdensEmMemoria()
    )


def _no_postgres(pedido: pytest.FixtureRequest) -> Repositorios:
    """Repositórios sobre um PostgreSQL real, migrado e vazio (fixture ``banco_limpo``)."""
    banco: Banco = pedido.getfixturevalue("banco_limpo")
    cargos = CargosNoBanco(banco)
    return Repositorios(
        EquipamentosNoBanco(banco), cargos, UsuariosNoBanco(banco, cargos), OrdensNoBanco(banco)
    )


IMPLEMENTACOES: dict[str, Callable[[pytest.FixtureRequest], Repositorios]] = {
    "memoria": _em_memoria,
    "postgres": _no_postgres,
}
