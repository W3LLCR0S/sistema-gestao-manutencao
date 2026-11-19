"""Carregamento do ambiente local (``backend/.env``), usado pelos comandos e pelo servidor."""

import os
from pathlib import Path

from manutencao.infrastructure.postgres import migracoes
from manutencao.infrastructure.postgres.configuracao import carregar_arquivo_env


def carregar_ambiente_local() -> None:
    """Lê ``backend/.env`` (ou o arquivo de ``MANUTENCAO_ENV_FILE``; vazio = nenhum).

    Nunca sobrescreve variáveis já definidas e nunca imprime valores.
    """
    arquivo = os.environ.get("MANUTENCAO_ENV_FILE")
    if arquivo is None:
        carregar_arquivo_env(migracoes.RAIZ_DO_BACKEND / ".env")
    elif arquivo:
        carregar_arquivo_env(Path(arquivo))
