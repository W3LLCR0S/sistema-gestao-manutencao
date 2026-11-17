"""Adaptadores em memória das portas de repositório (D-10: sem arquivo, sem banco).

Cada instância tem estado próprio; nada é global nem persistido. São determinísticos: a única
fonte de identificadores é a sequência do próprio repositório.
"""

from manutencao.infrastructure.memoria.cargos import CargosEmMemoria
from manutencao.infrastructure.memoria.equipamentos import EquipamentosEmMemoria
from manutencao.infrastructure.memoria.ordens import OrdensEmMemoria
from manutencao.infrastructure.memoria.usuarios import UsuariosEmMemoria

__all__ = ["CargosEmMemoria", "EquipamentosEmMemoria", "OrdensEmMemoria", "UsuariosEmMemoria"]
