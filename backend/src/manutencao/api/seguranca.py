"""Dependências de segurança: sessão, ator, CSRF e permissões.

* O **ator** de toda operação é ``autenticado.usuario.id``, vindo da sessão (cookie ``HttpOnly``).
  Nenhum corpo, consulta ou cabeçalho do cliente nomeia o ator.
* Operações que **modificam dados** (``POST``, ``PUT``, ``PATCH``, ``DELETE``) exigem o cabeçalho
  ``X-CSRF-Token`` igual ao segredo da sessão (padrão *synchronizer token*), além do cookie
  ``SameSite=Lax`` e da verificação de ``Origin`` (ver ``app.py``).
"""

import secrets
from typing import Annotated

from fastapi import Depends, Request

from manutencao.api.contexto import ContextoDaApi
from manutencao.api.erros import CsrfInvalidoError
from manutencao.application.servicos.autenticacao import Autenticacao

METODOS_SEGUROS = frozenset({"GET", "HEAD", "OPTIONS"})
CABECALHO_CSRF = "X-CSRF-Token"


def obter_contexto(request: Request) -> ContextoDaApi:
    contexto: ContextoDaApi = request.app.state.contexto
    return contexto


Contexto = Annotated[ContextoDaApi, Depends(obter_contexto)]


def autenticar(request: Request, contexto: Contexto) -> Autenticacao:
    """Resolve a sessão do cookie. Sem sessão válida: 401 (o tratador apaga o cookie)."""
    return contexto.autenticacao.autenticar(request.cookies.get(contexto.configuracao.cookie_nome))


Autenticado = Annotated[Autenticacao, Depends(autenticar)]


def conferir_csrf(request: Request, esperado: str) -> None:
    """``CsrfInvalidoError`` se o cabeçalho falta ou difere (comparação em tempo constante)."""
    enviado = request.headers.get(CABECALHO_CSRF, "")
    if not enviado or not secrets.compare_digest(enviado.encode("utf-8"), esperado.encode("utf-8")):
        raise CsrfInvalidoError


def exigir_csrf(request: Request, autenticado: Autenticado) -> None:
    """401 antes de 403: primeiro autentica; depois confere o CSRF nos métodos que escrevem."""
    if request.method not in METODOS_SEGUROS:
        conferir_csrf(request, autenticado.sessao.csrf)


# Router de rotas autenticadas: ``dependencies=PROTEGIDO``.
PROTEGIDO = [Depends(exigir_csrf)]
