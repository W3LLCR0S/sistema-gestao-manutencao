"""Adaptadores PostgreSQL das portas de repositório (Fase 03; D-12, ADR-0004).

SQLAlchemy 2.0 sobre psycopg 3, com o esquema versionado por Alembic (``backend/migrations``).
Os repositórios só **traduzem** entre linhas e entidades: nenhuma regra de negócio mora aqui.
"""

from manutencao.infrastructure.postgres.acesso import CredenciaisNoBanco, SessoesNoBanco
from manutencao.infrastructure.postgres.banco import Banco
from manutencao.infrastructure.postgres.cargos import CargosNoBanco
from manutencao.infrastructure.postgres.configuracao import (
    ConfiguracaoDoBanco,
    ConfiguracaoInvalidaError,
)
from manutencao.infrastructure.postgres.equipamentos import EquipamentosNoBanco
from manutencao.infrastructure.postgres.ordens import OrdensNoBanco
from manutencao.infrastructure.postgres.usuarios import UsuariosNoBanco

__all__ = [
    "Banco",
    "CargosNoBanco",
    "ConfiguracaoDoBanco",
    "ConfiguracaoInvalidaError",
    "CredenciaisNoBanco",
    "EquipamentosNoBanco",
    "OrdensNoBanco",
    "SessoesNoBanco",
    "UsuariosNoBanco",
]
