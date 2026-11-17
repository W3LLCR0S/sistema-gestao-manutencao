"""Configuração compartilhada dos testes do backend."""

from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy.engine import URL

from manutencao.infrastructure.postgres import Banco
from manutencao.infrastructure.postgres.migracoes import aplicar
from tests.apoio.postgres import banco_temporario, esvaziar, servidor
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
    {"caracterizacao", "dominio", "aplicacao", "integracao", "contrato", "arquitetura", "api"}
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


# ------------------------------------------------------------------------------- PostgreSQL
@pytest.fixture(scope="session")
def url_do_servidor_de_teste() -> Iterator[URL]:
    """URL de administração do servidor PostgreSQL dos testes (``pgserver`` ou o informado em
    ``MANUTENCAO_TEST_SERVER_URL``; ver ``tests/apoio/postgres.py``). Só sobe se alguém pedir."""
    with servidor() as admin:
        yield admin


@pytest.fixture(scope="session")
def url_do_banco_de_teste(url_do_servidor_de_teste: URL) -> Iterator[URL]:
    """Um banco PostgreSQL exclusivo da sessão, já migrado (Alembic ``head``)."""
    with banco_temporario(url_do_servidor_de_teste) as url:
        aplicar(url)
        yield url


@pytest.fixture
def banco_limpo(url_do_banco_de_teste: URL) -> Iterator[Banco]:
    """O banco migrado e **vazio** (dados e sequências zerados) para um teste."""
    esvaziar(url_do_banco_de_teste)
    banco = Banco(url_do_banco_de_teste)
    try:
        yield banco
    finally:
        banco.encerrar()
