"""Servidor PostgreSQL para os testes de integração e de contrato.

Fonte do servidor, nesta ordem:

1. ``MANUTENCAO_TEST_SERVER_URL`` — um PostgreSQL já existente (contêiner, serviço do Windows, CI);
   o papel informado precisa poder criar bancos. **Nunca** aponte para o banco de uso real: os
   testes criam e removem bancos próprios (``manutencao_teste_*``) e jamais tocam em outros.
2. o pacote de desenvolvimento ``pgserver`` (PostgreSQL real embutido), numa pasta temporária
   descartável: é o caminho que não exige instalar nada no computador.

Cada sessão de testes cria um banco novo, aplica as migrações Alembic e, antes de cada teste, o
esvazia (``TRUNCATE`` + sequências zeradas).
"""

import os
import shutil
import tempfile
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL, make_url

VARIAVEL_SERVIDOR = "MANUTENCAO_TEST_SERVER_URL"
TABELAS = ("ordens_servico", "usuarios", "equipamentos", "cargos")  # CASCADE leva o resto


def _como_psycopg(url: URL) -> URL:
    return url.set(drivername="postgresql+psycopg")


@contextmanager
def servidor() -> Iterator[URL]:
    """URL de administração (banco ``postgres``) de um servidor disponível para os testes."""
    externo = os.environ.get(VARIAVEL_SERVIDOR, "").strip()
    if externo:
        yield _como_psycopg(make_url(externo))
        return
    import pgserver  # dependência só de desenvolvimento (requirements-dev.txt)

    pasta = Path(tempfile.mkdtemp(prefix="manutencao_pg_"))
    instancia = pgserver.get_server(pasta, cleanup_mode="stop")
    try:
        yield _como_psycopg(make_url(instancia.get_uri()))
    finally:
        instancia.cleanup()
        shutil.rmtree(pasta, ignore_errors=True)


@contextmanager
def banco_temporario(admin: URL) -> Iterator[URL]:
    """Cria um banco UTF-8 exclusivo, devolve sua URL e o remove ao final."""
    nome = f"manutencao_teste_{uuid.uuid4().hex[:12]}"
    engine = create_engine(admin, isolation_level="AUTOCOMMIT")
    try:
        with engine.connect() as conexao:
            conexao.execute(text(f"CREATE DATABASE \"{nome}\" ENCODING 'UTF8' TEMPLATE template0"))
        yield admin.set(database=nome)
    finally:
        with engine.connect() as conexao:
            conexao.execute(text(f'DROP DATABASE IF EXISTS "{nome}" WITH (FORCE)'))
        engine.dispose()


def esvaziar(url: URL) -> None:
    """Apaga todos os dados e zera as sequências (o esquema permanece)."""
    engine = create_engine(url)
    try:
        with engine.begin() as conexao:
            conexao.execute(text(f"TRUNCATE {', '.join(TABELAS)} CASCADE"))
            conexao.execute(text("UPDATE sequencias SET ultimo = 0"))
    finally:
        engine.dispose()
