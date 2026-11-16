"""Guardas que impedem os testes de tocar rede externa ou dados reais.

Duas proteções, ativadas automaticamente por ``conftest.py``:

* **Rede:** conexões e resoluções de nome para destinos que não sejam loopback ou socket local
  falham com :class:`RedeBloqueadaError` antes de qualquer tráfego.
* **Dados reais:** qualquer abertura de arquivo dentro do diretório ``dados/`` do repositório falha
  com :class:`AcessoADadosReaisError` antes de o arquivo ser aberto (o conteúdo nunca é lido).
"""

import builtins
import io
import os
import socket
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

RAIZ_BACKEND = Path(__file__).resolve().parents[1]
RAIZ_REPOSITORIO = RAIZ_BACKEND.parent
DIRETORIO_DADOS = RAIZ_REPOSITORIO / "dados"

HOSTS_LOCAIS = frozenset({"localhost", "127.0.0.1", "::1"})


class RedeBloqueadaError(AssertionError):
    """Um teste tentou usar a rede para um destino externo."""


class AcessoADadosReaisError(PermissionError):
    """Um teste tentou abrir um arquivo dentro de ``dados/``."""


# ---------------------------------------------------------------------------------------- rede


def destino_permitido(endereco: object) -> bool:
    """Indica se um endereço de socket é local (loopback ou socket de arquivo)."""
    if isinstance(endereco, str | bytes | os.PathLike):
        return True  # AF_UNIX: caminho de arquivo, sem rede
    if isinstance(endereco, tuple) and endereco:
        host = endereco[0]
        if isinstance(host, bytes):
            host = host.decode("ascii", "replace")
        return isinstance(host, str) and host.lower() in HOSTS_LOCAIS
    return False


def _bloquear_rede(destino: object) -> None:
    raise RedeBloqueadaError(f"Acesso à rede bloqueado nos testes: {destino!r}")


def instalar_bloqueio_de_rede(monkeypatch: pytest.MonkeyPatch) -> None:
    """Faz conexões e resoluções de nome externas falharem imediatamente."""
    conectar_original: Callable[..., Any] = socket.socket.connect
    conectar_ex_original: Callable[..., Any] = socket.socket.connect_ex
    enviar_para_original: Callable[..., Any] = socket.socket.sendto
    resolver_original: Callable[..., Any] = socket.getaddrinfo

    def connect(self: socket.socket, endereco: Any) -> Any:
        if not destino_permitido(endereco):
            _bloquear_rede(endereco)
        return conectar_original(self, endereco)

    def connect_ex(self: socket.socket, endereco: Any) -> Any:
        if not destino_permitido(endereco):
            _bloquear_rede(endereco)
        return conectar_ex_original(self, endereco)

    def sendto(self: socket.socket, dados: Any, *args: Any) -> Any:
        if not destino_permitido(args[-1]):
            _bloquear_rede(args[-1])
        return enviar_para_original(self, dados, *args)

    def getaddrinfo(host: Any, *args: Any, **kwargs: Any) -> Any:
        if not destino_permitido((host,)):
            _bloquear_rede(host)
        return resolver_original(host, *args, **kwargs)

    monkeypatch.setattr(socket.socket, "connect", connect)
    monkeypatch.setattr(socket.socket, "connect_ex", connect_ex)
    monkeypatch.setattr(socket.socket, "sendto", sendto)
    monkeypatch.setattr(socket, "getaddrinfo", getaddrinfo)


# ----------------------------------------------------------------------------- dados reais


def caminho_em_dados(caminho: object) -> bool:
    """Indica se ``caminho`` está dentro de ``dados/`` (sem tocar o sistema de arquivos)."""
    if isinstance(caminho, int):
        return False  # descritor de arquivo já aberto
    if not isinstance(caminho, str | bytes | os.PathLike):
        return False
    absoluto = Path(os.path.abspath(os.fsdecode(caminho)))  # noqa: PTH100 - sem seguir links
    return absoluto == DIRETORIO_DADOS or DIRETORIO_DADOS in absoluto.parents


def instalar_protecao_de_dados(monkeypatch: pytest.MonkeyPatch) -> None:
    """Impede abrir qualquer arquivo dentro de ``dados/`` durante os testes."""
    abrir_builtin: Callable[..., Any] = builtins.open
    abrir_io: Callable[..., Any] = io.open
    abrir_os: Callable[..., Any] = os.open

    def _verificar(caminho: object) -> None:
        if caminho_em_dados(caminho):
            raise AcessoADadosReaisError(
                f"Os testes não podem acessar dados reais (diretório dados/): {caminho!r}"
            )

    def open_protegido(arquivo: Any, *args: Any, **kwargs: Any) -> Any:
        _verificar(arquivo)
        return abrir_builtin(arquivo, *args, **kwargs)

    def io_open_protegido(arquivo: Any, *args: Any, **kwargs: Any) -> Any:
        _verificar(arquivo)
        return abrir_io(arquivo, *args, **kwargs)

    def os_open_protegido(caminho: Any, *args: Any, **kwargs: Any) -> Any:
        _verificar(caminho)
        return abrir_os(caminho, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", open_protegido)
    monkeypatch.setattr(io, "open", io_open_protegido)
    monkeypatch.setattr(os, "open", os_open_protegido)


def instantaneo_de_dados() -> dict[str, tuple[int, int] | None]:
    """Metadados (nunca o conteúdo) dos itens de ``dados/``: nome -> (tamanho, mtime_ns)."""
    if not DIRETORIO_DADOS.is_dir():
        return {}
    resultado: dict[str, tuple[int, int] | None] = {}
    for item in sorted(os.listdir(DIRETORIO_DADOS)):  # noqa: PTH208 - só os nomes
        estado = (DIRETORIO_DADOS / item).stat()
        resultado[item] = (estado.st_size, estado.st_mtime_ns)
    return resultado
