"""Configuração da API por variáveis de ambiente (nenhum segredo no código ou no Git).

- ``MANUTENCAO_API_COOKIE_SECURE`` (``false``): ``true`` quando servida por HTTPS (``Secure``);
- ``MANUTENCAO_API_ORIGENS`` (vazio): origens do frontend (CORS e ``Origin``), por vírgula;
- ``MANUTENCAO_API_DOCS`` (``true``): expõe ``/docs``, ``/redoc`` e ``/openapi.json``;
- ``MANUTENCAO_SESSAO_HORAS`` (``8``): validade absoluta da sessão (1 a 72 horas);
- ``MANUTENCAO_API_COOKIE_NOME`` (``manutencao_sessao``): nome do cookie de sessão.

Origem ``*`` é recusada: CORS com credenciais exige origens explícitas.
"""

import os
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import timedelta
from urllib.parse import urlsplit

from manutencao.api.contexto import ConfiguracaoDaApi


class ConfiguracaoDaApiInvalidaError(Exception):
    """Valor inválido em uma variável de configuração da API."""


@dataclass(frozen=True)
class ConfiguracaoDoServidor:
    api: ConfiguracaoDaApi
    validade_da_sessao: timedelta


def _booleano(env: Mapping[str, str], nome: str, padrao: bool) -> bool:
    texto = env.get(nome, "").strip().casefold()
    if not texto:
        return padrao
    if texto in ("1", "true", "sim", "yes"):
        return True
    if texto in ("0", "false", "nao", "não", "no"):
        return False
    raise ConfiguracaoDaApiInvalidaError(f"{nome} deve ser 'true' ou 'false'.")


def _origens(texto: str) -> tuple[str, ...]:
    origens: list[str] = []
    for parte in texto.split(","):
        origem = parte.strip().rstrip("/")
        if not origem:
            continue
        partes = urlsplit(origem)
        if origem == "*" or partes.scheme not in ("http", "https") or not partes.netloc:
            raise ConfiguracaoDaApiInvalidaError(
                "MANUTENCAO_API_ORIGENS aceita só origens http(s)://host[:porta] explícitas "
                "(nunca '*')."
            )
        if partes.path or partes.query or partes.fragment:
            raise ConfiguracaoDaApiInvalidaError(
                "MANUTENCAO_API_ORIGENS deve conter só esquema, host e porta."
            )
        origens.append(origem)
    return tuple(origens)


def configuracao_do_ambiente(env: Mapping[str, str] | None = None) -> ConfiguracaoDoServidor:
    valores: Mapping[str, str] = os.environ if env is None else env
    horas_texto = valores.get("MANUTENCAO_SESSAO_HORAS", "").strip() or "8"
    if not horas_texto.isdigit() or not 1 <= int(horas_texto) <= 72:
        raise ConfiguracaoDaApiInvalidaError("MANUTENCAO_SESSAO_HORAS deve ser de 1 a 72.")
    nome = valores.get("MANUTENCAO_API_COOKIE_NOME", "").strip() or "manutencao_sessao"
    return ConfiguracaoDoServidor(
        api=ConfiguracaoDaApi(
            cookie_nome=nome,
            cookie_seguro=_booleano(valores, "MANUTENCAO_API_COOKIE_SECURE", False),
            origens_permitidas=_origens(valores.get("MANUTENCAO_API_ORIGENS", "")),
            documentacao=_booleano(valores, "MANUTENCAO_API_DOCS", True),
        ),
        validade_da_sessao=timedelta(hours=int(horas_texto)),
    )
