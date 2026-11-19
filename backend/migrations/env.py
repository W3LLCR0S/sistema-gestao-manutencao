"""Ambiente do Alembic: usa a mesma configuração por variáveis de ambiente da aplicação.

A URL vem, nesta ordem, de ``config.attributes["url"]`` (usado pelos testes e pelo comando
``python -m manutencao.composicao.banco``) ou de ``MANUTENCAO_DATABASE_URL`` / ``MANUTENCAO_DB_*``.
Nenhuma credencial é lida de ``alembic.ini``.
"""

from alembic import context
from sqlalchemy import create_engine, pool
from sqlalchemy.engine import URL

from manutencao.infrastructure.postgres.configuracao import ConfiguracaoDoBanco
from manutencao.infrastructure.postgres.modelos import Base

config = context.config
target_metadata = Base.metadata


def _url() -> URL | str:
    informada = config.attributes.get("url")
    if informada is not None:
        return informada  # type: ignore[no-any-return]
    return ConfiguracaoDoBanco.do_ambiente().url


def run_migrations_offline() -> None:
    context.configure(
        url=_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    conexao_existente = config.attributes.get("connection")
    if conexao_existente is not None:
        _executar(conexao_existente)
        return
    engine = create_engine(_url(), poolclass=pool.NullPool)
    with engine.connect() as conexao:
        _executar(conexao)
    engine.dispose()


def _executar(conexao: object) -> None:
    context.configure(connection=conexao, target_metadata=target_metadata, compare_type=True)  # type: ignore[arg-type]
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
