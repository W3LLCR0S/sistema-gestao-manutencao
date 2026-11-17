"""Fixtures da camada de aplicação."""

import pytest

from tests.apoio.ambiente import Ambiente, criar_ambiente


@pytest.fixture
def amb() -> Ambiente:
    """Ambiente novo e isolado com a base inicial do legado."""
    return criar_ambiente()
