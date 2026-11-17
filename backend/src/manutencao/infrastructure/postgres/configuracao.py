"""Configuração da conexão por variáveis de ambiente (nada de credencial no código ou no Git).

Duas formas, nesta ordem de precedência:

1. ``MANUTENCAO_DATABASE_URL`` — URL completa (``postgresql://usuario:senha@host:5432/banco``);
2. partes: ``MANUTENCAO_DB_NAME`` e ``MANUTENCAO_DB_USER`` (obrigatórias), ``MANUTENCAO_DB_HOST``
   (padrão ``localhost``), ``MANUTENCAO_DB_PORT`` (padrão ``5432``) e ``MANUTENCAO_DB_PASSWORD``.

O driver é sempre o psycopg 3 (``postgresql+psycopg``). A senha nunca aparece em ``repr``/``str``.
Os valores podem vir do ambiente ou de um arquivo ``.env`` local (ignorado pelo Git), lido por
:func:`carregar_arquivo_env` **sem sobrescrever** variáveis já definidas.
"""

import os
from collections.abc import Mapping, MutableMapping
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import ArgumentError

VARIAVEL_URL = "MANUTENCAO_DATABASE_URL"
DRIVER = "postgresql+psycopg"


class ConfiguracaoInvalidaError(Exception):
    """A configuração do banco está ausente ou malformada (a mensagem nunca traz a senha)."""


@dataclass(frozen=True)
class ConfiguracaoDoBanco:
    """URL de conexão já validada, com senha oculta na representação textual."""

    url: URL

    @classmethod
    def de_url(cls, texto: str) -> "ConfiguracaoDoBanco":
        try:
            url = make_url(texto)
        except ArgumentError:
            raise ConfiguracaoInvalidaError(
                f"{VARIAVEL_URL} não é uma URL de banco válida."
            ) from None
        if url.get_backend_name() != "postgresql":
            raise ConfiguracaoInvalidaError("Só PostgreSQL é suportado (postgresql://...).")
        if not url.database:
            raise ConfiguracaoInvalidaError("A URL do banco precisa informar o nome do banco.")
        return cls(url.set(drivername=DRIVER))

    @classmethod
    def do_ambiente(cls, ambiente: Mapping[str, str] | None = None) -> "ConfiguracaoDoBanco":
        """Lê a configuração de ``ambiente`` (padrão: ``os.environ``)."""
        env: Mapping[str, str] = os.environ if ambiente is None else ambiente
        texto = env.get(VARIAVEL_URL, "").strip()
        if texto:
            return cls.de_url(texto)
        nome = env.get("MANUTENCAO_DB_NAME", "").strip()
        usuario = env.get("MANUTENCAO_DB_USER", "").strip()
        faltando = [
            variavel
            for variavel, valor in (
                ("MANUTENCAO_DB_NAME", nome),
                ("MANUTENCAO_DB_USER", usuario),
            )
            if not valor
        ]
        if faltando:
            raise ConfiguracaoInvalidaError(
                f"Banco não configurado: defina {VARIAVEL_URL} ou {' e '.join(faltando)}."
            )
        porta_texto = env.get("MANUTENCAO_DB_PORT", "5432").strip() or "5432"
        if not porta_texto.isdigit():
            raise ConfiguracaoInvalidaError("MANUTENCAO_DB_PORT deve ser um número.")
        url = URL.create(
            DRIVER,
            username=usuario,
            password=env.get("MANUTENCAO_DB_PASSWORD") or None,
            host=env.get("MANUTENCAO_DB_HOST", "").strip() or "localhost",
            port=int(porta_texto),
            database=nome,
        )
        return cls(url)

    def __repr__(self) -> str:
        return f"ConfiguracaoDoBanco({self.url.render_as_string(hide_password=True)})"

    __str__ = __repr__


def carregar_arquivo_env(
    caminho: Path, ambiente: MutableMapping[str, str] | None = None
) -> list[str]:
    """Lê ``CHAVE=valor`` de um arquivo ``.env`` e define o que ainda não estiver no ambiente.

    Linhas vazias e comentários (``#``) são ignorados; aspas simples ou duplas ao redor do valor
    são removidas. Devolve só os **nomes** das variáveis definidas (nunca os valores). Arquivo
    inexistente não é erro.
    """
    destino: MutableMapping[str, str] = os.environ if ambiente is None else ambiente
    if not caminho.is_file():
        return []
    definidas: list[str] = []
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        texto = linha.strip()
        if not texto or texto.startswith("#") or "=" not in texto:
            continue
        chave, _, valor = texto.partition("=")
        chave, valor = chave.strip(), valor.strip()
        if len(valor) >= 2 and valor[0] == valor[-1] and valor[0] in ("'", '"'):
            valor = valor[1:-1]
        if chave and chave not in destino:
            destino[chave] = valor
            definidas.append(chave)
    return definidas
