"""Servidor da API: ``python -m manutencao.composicao.servidor`` (a partir de ``backend/``).

    python -m manutencao.composicao.servidor                  # 127.0.0.1:8000 (só este computador)
    python -m manutencao.composicao.servidor --rede           # 0.0.0.0: acessível na rede local
    python -m manutencao.composicao.servidor --porta 8001

Também serve ao uvicorn: ``uvicorn manutencao.composicao.servidor:criar --factory``. Exige o
PostgreSQL configurado (``backend/.env``) e o esquema na revisão mais recente (comando ``migrar``).
O banco **nunca** é exposto pela API nem por este servidor: só a porta HTTP da API escuta.
"""

import argparse
import sys
from collections.abc import Sequence

import uvicorn
from fastapi import FastAPI

from manutencao.api import criar_app
from manutencao.composicao.ambiente import carregar_ambiente_local
from manutencao.composicao.aplicacao import criar_aplicacao_postgres
from manutencao.composicao.configuracao_api import (
    ConfiguracaoDaApiInvalidaError,
    configuracao_do_ambiente,
)
from manutencao.infrastructure.postgres import Banco, ConfiguracaoDoBanco, migracoes
from manutencao.infrastructure.postgres.configuracao import ConfiguracaoInvalidaError


class EsquemaDesatualizadoError(RuntimeError):
    """O banco não está na revisão mais recente do esquema."""


def criar() -> FastAPI:
    """Monta a API sobre o PostgreSQL configurado; erro claro (sem segredos) se faltar algo."""
    carregar_ambiente_local()
    banco_cfg = ConfiguracaoDoBanco.do_ambiente()
    servidor_cfg = configuracao_do_ambiente()
    atual, recente = migracoes.revisao_atual(banco_cfg.url), migracoes.revisao_mais_recente()
    if atual != recente:
        raise EsquemaDesatualizadoError(
            f"Esquema na revisão {atual or '(nenhuma)'}, esperado {recente}: "
            "rode 'python -m manutencao.composicao.banco migrar'."
        )
    banco = Banco(banco_cfg.url)
    aplicacao = criar_aplicacao_postgres(
        banco, configuracao=servidor_cfg.api, validade=servidor_cfg.validade_da_sessao
    )
    return criar_app(aplicacao.contexto)


def principal(argumentos: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m manutencao.composicao.servidor")
    parser.add_argument("--porta", type=int, default=8000)
    parser.add_argument(
        "--rede",
        action="store_true",
        help="escuta em 0.0.0.0 (acesso pela rede local, ex.: celular); o padrão é 127.0.0.1",
    )
    parser.add_argument("--recarregar", action="store_true", help="reinicia ao mudar o código")
    dado = parser.parse_args(argumentos)
    try:
        criar()  # valida configuração e esquema antes de subir, com mensagem clara
    except (
        ConfiguracaoInvalidaError,
        ConfiguracaoDaApiInvalidaError,
        EsquemaDesatualizadoError,
    ) as erro:
        print(f"Erro: {erro}", file=sys.stderr)
        return 1
    host = "0.0.0.0" if dado.rede else "127.0.0.1"
    if dado.rede:
        print(
            "ATENÇÃO: a API está acessível na rede local por HTTP (sem criptografia). "
            "Use só em rede confiável; o PostgreSQL continua restrito a localhost.",
            file=sys.stderr,
        )
    uvicorn.run(
        "manutencao.composicao.servidor:criar",
        factory=True,
        host=host,
        port=dado.porta,
        reload=dado.recarregar,
        log_level="info",
    )
    return 0


if __name__ == "__main__":
    sys.exit(principal())
