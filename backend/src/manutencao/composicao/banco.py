"""Administração do banco por linha de comando (a partir de ``backend/``).

    python -m manutencao.composicao.banco estado
    python -m manutencao.composicao.banco migrar
    python -m manutencao.composicao.banco semear
    python -m manutencao.composicao.banco reverter [destino]   # padrão: -1 (uma revisão)

A conexão vem das variáveis de ambiente (``MANUTENCAO_DATABASE_URL`` ou ``MANUTENCAO_DB_*``) e,
se existir, de ``backend/.env`` (ignorado pelo Git; ``MANUTENCAO_ENV_FILE`` indica outro).
Nenhum comando exibe a senha. ``reverter`` **apaga dados** das tabelas desfeitas: exige
``--confirmo`` e só deve ser usado em banco descartável ou depois de um backup (``pg_dump``;
ver docs/PERSISTENCIA.md).
"""

import argparse
import os
import sys
from collections.abc import Sequence
from pathlib import Path

from manutencao.composicao.demonstracao import BancoNaoVazioError, semear_demonstracao
from manutencao.composicao.fabrica import criar_container_postgres
from manutencao.infrastructure.postgres import (
    Banco,
    ConfiguracaoDoBanco,
    ConfiguracaoInvalidaError,
    migracoes,
)
from manutencao.infrastructure.postgres.configuracao import carregar_arquivo_env


def _configuracao() -> ConfiguracaoDoBanco:
    # MANUTENCAO_ENV_FILE troca o arquivo (vazio = não ler nenhum); o padrão é backend/.env.
    arquivo = os.environ.get("MANUTENCAO_ENV_FILE")
    if arquivo is None:
        carregar_arquivo_env(migracoes.RAIZ_DO_BACKEND / ".env")
    elif arquivo:
        carregar_arquivo_env(Path(arquivo))
    return ConfiguracaoDoBanco.do_ambiente()


def _estado(config: ConfiguracaoDoBanco) -> int:
    atual = migracoes.revisao_atual(config.url)
    print(f"Banco: {config}")
    recente = migracoes.revisao_mais_recente()
    print(f"Revisão aplicada: {atual or '(nenhuma)'}; mais recente: {recente}")
    if atual is not None:
        banco = Banco(config.url)
        try:
            c = criar_container_postgres(banco)
            print(
                f"Cargos: {len(c.cargos.listar())}; usuários: {len(c.usuarios.listar())}; "
                f"equipamentos: {len(c.equipamentos.listar())}; OS: {c.ordens.contar()}"
            )
        finally:
            banco.encerrar()
    return 0


def _semear(config: ConfiguracaoDoBanco) -> int:
    if migracoes.revisao_atual(config.url) != migracoes.revisao_mais_recente():
        print("O esquema não está atualizado: rode 'migrar' antes.", file=sys.stderr)
        return 2
    banco = Banco(config.url)
    try:
        resumo = semear_demonstracao(criar_container_postgres(banco))
    except BancoNaoVazioError as erro:
        print(str(erro), file=sys.stderr)
        return 3
    finally:
        banco.encerrar()
    print(
        f"Demonstração criada: {resumo.cargos} cargos, {resumo.usuarios} usuários, "
        f"{resumo.equipamentos} equipamentos, {resumo.ordens} OS."
    )
    return 0


def principal(argumentos: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m manutencao.composicao.banco")
    comandos = parser.add_subparsers(dest="comando", required=True)
    comandos.add_parser("estado", help="mostra a revisão do esquema e as contagens")
    comandos.add_parser("migrar", help="aplica as migrações até a revisão mais recente")
    comandos.add_parser("semear", help="cria os dados fictícios de demonstração (banco vazio)")
    reverter = comandos.add_parser("reverter", help="desfaz migrações (APAGA dados dessas tabelas)")
    reverter.add_argument("destino", nargs="?", default="-1")
    reverter.add_argument("--confirmo", action="store_true", help="confirma a perda de dados")
    dado = parser.parse_args(argumentos)

    try:
        config = _configuracao()
    except ConfiguracaoInvalidaError as erro:
        print(f"Erro de configuração: {erro}", file=sys.stderr)
        return 1

    if dado.comando == "estado":
        return _estado(config)
    if dado.comando == "migrar":
        migracoes.aplicar(config.url)
        print(f"Esquema na revisão {migracoes.revisao_atual(config.url)}.")
        return 0
    if dado.comando == "semear":
        return _semear(config)
    if not dado.confirmo:
        print(
            "'reverter' apaga dados: repita com --confirmo (e faça backup antes).", file=sys.stderr
        )
        return 2
    migracoes.reverter(config.url, dado.destino)
    print(f"Esquema na revisão {migracoes.revisao_atual(config.url) or '(base)'}.")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
