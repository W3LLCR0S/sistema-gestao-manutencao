"""Aplicação das migrações Alembic por código (usada pela administração do banco e pelos testes).

O diretório ``backend/migrations`` é localizado a partir deste arquivo, então os comandos funcionam
de qualquer diretório de trabalho, desde que o repositório esteja inteiro (execução a partir do
código-fonte, como documentado).
"""

from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine
from sqlalchemy.engine import URL

RAIZ_DO_BACKEND = Path(__file__).resolve().parents[4]
DIRETORIO_DAS_MIGRACOES = RAIZ_DO_BACKEND / "migrations"


def _configuracao(url: URL | str) -> Config:
    configuracao = Config()
    configuracao.set_main_option("script_location", str(DIRETORIO_DAS_MIGRACOES))
    configuracao.attributes["url"] = url
    return configuracao


def aplicar(url: URL | str, destino: str = "head") -> None:
    """Leva o banco até ``destino`` (``head`` = a revisão mais recente)."""
    command.upgrade(_configuracao(url), destino)


def reverter(url: URL | str, destino: str = "-1") -> None:
    """Desfaz até ``destino`` (``-1`` = uma revisão; ``base`` = tudo)."""
    command.downgrade(_configuracao(url), destino)


def revisao_atual(url: URL | str) -> str | None:
    """A revisão aplicada ao banco (``None`` se nenhuma)."""
    engine = create_engine(url)
    try:
        with engine.connect() as conexao:
            return MigrationContext.configure(conexao).get_current_revision()
    finally:
        engine.dispose()


def revisao_mais_recente() -> str | None:
    """A revisão mais recente disponível no código."""
    return ScriptDirectory(str(DIRETORIO_DAS_MIGRACOES)).get_current_head()
