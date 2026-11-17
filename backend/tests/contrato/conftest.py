"""Fixtures da suíte de contrato: cada teste roda contra todas as implementações registradas."""

import pytest

from tests.contrato.implementacoes import IMPLEMENTACOES, Repositorios


@pytest.fixture(params=sorted(IMPLEMENTACOES))
def repos(request: pytest.FixtureRequest) -> Repositorios:
    """Repositórios novos e vazios da implementação em teste."""
    repositorios: Repositorios = IMPLEMENTACOES[request.param](request)
    return repositorios
