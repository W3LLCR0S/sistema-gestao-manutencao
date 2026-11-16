"""Configuração compartilhada dos testes do backend."""

from collections.abc import Iterator
from pathlib import Path

import pytest

from tests.guardas_ambiente import (
    RAIZ_BACKEND,
    RAIZ_REPOSITORIO,
    instalar_bloqueio_de_rede,
    instalar_protecao_de_dados,
    instantaneo_de_dados,
)

DIRETORIO_TESTES = Path(__file__).resolve().parent

# Diretório de testes -> marcador registrado em pyproject.toml.
MARCADORES_POR_DIRETORIO = frozenset(
    {"caracterizacao", "dominio", "aplicacao", "integracao", "contrato", "arquitetura"}
)


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Aplica o marcador correspondente ao diretório (``pytest -m arquitetura``, etc.)."""
    for item in items:
        partes = item.path.resolve().relative_to(DIRETORIO_TESTES).parts
        if len(partes) > 1 and partes[0] in MARCADORES_POR_DIRETORIO:
            item.add_marker(partes[0])


@pytest.fixture(autouse=True)
def _sem_rede_externa(monkeypatch: pytest.MonkeyPatch) -> None:
    instalar_bloqueio_de_rede(monkeypatch)


@pytest.fixture(autouse=True)
def _sem_acesso_a_dados_reais(monkeypatch: pytest.MonkeyPatch) -> None:
    instalar_protecao_de_dados(monkeypatch)


@pytest.fixture(scope="session", autouse=True)
def _dados_reais_intactos() -> Iterator[None]:
    """Falha a sessão se algo em ``dados/`` mudar (nomes, tamanhos ou datas; sem ler conteúdo)."""
    antes = instantaneo_de_dados()
    yield
    depois = instantaneo_de_dados()
    assert depois == antes, "O conteúdo do diretório dados/ foi alterado durante os testes."


@pytest.fixture(scope="session")
def raiz_backend() -> Path:
    return RAIZ_BACKEND


@pytest.fixture(scope="session")
def raiz_repositorio() -> Path:
    return RAIZ_REPOSITORIO
