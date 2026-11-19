"""API: rotas e esquemas. Depende de application e domain; nunca importa infrastructure."""

from manutencao.api.app import criar_app
from manutencao.api.contexto import ConfiguracaoDaApi, ContextoDaApi

__all__ = ["ConfiguracaoDaApi", "ContextoDaApi", "criar_app"]
