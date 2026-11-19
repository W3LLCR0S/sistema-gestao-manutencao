"""Fábrica da aplicação FastAPI (``/api/v1``).

Camada fina e segura sobre os serviços da aplicação. Cada chamada de ``criar_app`` recebe o seu
``ContextoDaApi`` (serviços já ligados à persistência pela composição) e não guarda estado global.

Proteções transversais:

* ``Cache-Control: no-store`` e ``X-Content-Type-Options: nosniff`` em toda resposta;
* verificação de ``Origin`` nas operações que modificam dados (``Origin`` ausente é aceito: clientes
  que não são navegadores não o enviam; um navegador sempre o envia em ``POST``/``PUT``/``DELETE``);
* CORS **só** para as origens configuradas, com credenciais (nunca ``*``);
* documentação OpenAPI (``/docs``) opcional por configuração.
"""

from collections.abc import Awaitable, Callable
from urllib.parse import urlsplit

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from manutencao.api.contexto import ContextoDaApi
from manutencao.api.erros import registrar_tratadores, resposta_de_erro
from manutencao.api.rotas import autenticacao, equipamentos, ordens, painel, usuarios
from manutencao.api.seguranca import METODOS_SEGUROS

PREFIXO = "/api/v1"
VERSAO = "1.0.0"

DESCRICAO = """
API do Sistema de Gestão de Manutenção de Equipamentos (Entrega 2).

**Autenticação:** `POST /api/v1/auth/login` abre uma sessão por cookie `HttpOnly`. Toda operação que
modifica dados (`POST`, `PUT`, `PATCH`, `DELETE`) deve enviar o cabeçalho `X-CSRF-Token` com o valor
de `csrf_token` devolvido por `/auth/login` e `/auth/me`. O ator de cada operação é o usuário da
sessão: a API nunca aceita um identificador de ator enviado pelo cliente.

**Erros:** `{"codigo": "...", "mensagem": "..."}`; 401 não autenticado, 403 sem permissão ou CSRF,
404 não encontrado, 409 conflito de estado/regra, 422 entrada inválida, 429 excesso de tentativas.
Instantes em ISO 8601 UTC.
"""


def _origem_confiavel(request: Request, permitidas: tuple[str, ...]) -> bool:
    origem = request.headers.get("origin")
    if origem is None:
        return True
    if origem in permitidas:
        return True
    return urlsplit(origem).netloc == request.headers.get("host", "")


def criar_app(contexto: ContextoDaApi) -> FastAPI:
    cfg = contexto.configuracao
    app = FastAPI(
        title="Gestão de Manutenção de Equipamentos",
        version=VERSAO,
        description=DESCRICAO,
        docs_url="/docs" if cfg.documentacao else None,
        redoc_url="/redoc" if cfg.documentacao else None,
        openapi_url="/openapi.json" if cfg.documentacao else None,
    )
    app.state.contexto = contexto
    registrar_tratadores(app, cfg)

    @app.middleware("http")
    async def _protecoes(
        request: Request, proxima: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        resposta: Response
        if request.method not in METODOS_SEGUROS and not _origem_confiavel(
            request, cfg.origens_permitidas
        ):
            resposta = resposta_de_erro(
                403, "origem_nao_permitida", "Origem da requisição não permitida."
            )
        else:
            resposta = await proxima(request)
        resposta.headers["Cache-Control"] = "no-store"
        resposta.headers["X-Content-Type-Options"] = "nosniff"
        return resposta

    if cfg.origens_permitidas:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=list(cfg.origens_permitidas),
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
            allow_headers=["Content-Type", "X-CSRF-Token"],
        )

    for roteador in (
        autenticacao.publico,
        autenticacao.protegido,
        usuarios.usuarios,
        usuarios.cargos,
        usuarios.disponibilidade,
        equipamentos.roteador,
        ordens.roteador,
        painel.painel,
        painel.saude,
    ):
        app.include_router(roteador, prefix=PREFIXO)
    return app


__all__ = ["PREFIXO", "criar_app"]
