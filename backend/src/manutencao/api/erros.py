"""Tradução centralizada de erros em respostas HTTP ``{codigo, mensagem}``.

Mapeamento (docs/MAPEAMENTO_API_FRONTEND.md §1): ``PermissaoNegadaError`` 403;
``NaoEncontradoError``
404; ``ConflitoDeEstadoError``, ``IdentificadorJaEmitidoError`` e ``RegraDeAplicacaoError`` 409;
``ViolacaoDeRegraError`` e entrada inválida 422; não autenticado 401; excesso de tentativas 429. O
``codigo`` é o estável do domínio/aplicação. Erros inesperados viram 500 genérico: a causa vai para
o log do servidor e **nunca** para o cliente (nem valores de entrada, nem SQL, nem hash).
"""

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from manutencao.api.contexto import ConfiguracaoDaApi
from manutencao.application.erros import (
    EntradaInvalidaError,
    IdentificadorJaEmitidoError,
    MuitasTentativasError,
    NaoAutenticadoError,
    NaoEncontradoError,
    RegraDeAplicacaoError,
)
from manutencao.domain.erros import (
    ConflitoDeEstadoError,
    PermissaoNegadaError,
    ViolacaoDeRegraError,
)

_registro = logging.getLogger("manutencao.api")


class CsrfInvalidoError(Exception):
    """O cabeçalho ``X-CSRF-Token`` falta ou não confere com o da sessão (HTTP 403)."""


def resposta_de_erro(
    status: int,
    codigo: str,
    mensagem: str,
    *,
    detalhes: list[dict[str, Any]] | None = None,
    cabecalhos: dict[str, str] | None = None,
) -> JSONResponse:
    corpo: dict[str, Any] = {"codigo": codigo, "mensagem": mensagem}
    if detalhes is not None:
        corpo["detalhes"] = detalhes
    return JSONResponse(corpo, status_code=status, headers=cabecalhos)


def _campo(local: tuple[Any, ...]) -> str:
    return ".".join(str(parte) for parte in local if parte not in ("body", "query", "path"))


def registrar_tratadores(app: FastAPI, configuracao: ConfiguracaoDaApi) -> None:
    @app.exception_handler(NaoAutenticadoError)
    async def _nao_autenticado(_: Request, erro: NaoAutenticadoError) -> JSONResponse:
        resposta = resposta_de_erro(401, erro.codigo.value, erro.mensagem)
        resposta.delete_cookie(configuracao.cookie_nome, path="/")
        return resposta

    @app.exception_handler(MuitasTentativasError)
    async def _muitas_tentativas(_: Request, erro: MuitasTentativasError) -> JSONResponse:
        return resposta_de_erro(
            429, erro.codigo.value, erro.mensagem, cabecalhos={"Retry-After": str(erro.segundos)}
        )

    @app.exception_handler(PermissaoNegadaError)
    async def _permissao(_: Request, erro: PermissaoNegadaError) -> JSONResponse:
        return resposta_de_erro(403, erro.codigo.value, erro.mensagem)

    @app.exception_handler(NaoEncontradoError)
    async def _nao_encontrado(_: Request, erro: NaoEncontradoError) -> JSONResponse:
        return resposta_de_erro(404, erro.codigo.value, erro.mensagem)

    @app.exception_handler(ConflitoDeEstadoError)
    async def _conflito_de_estado(_: Request, erro: ConflitoDeEstadoError) -> JSONResponse:
        return resposta_de_erro(409, erro.codigo.value, erro.mensagem)

    @app.exception_handler(IdentificadorJaEmitidoError)
    async def _id_emitido(_: Request, erro: IdentificadorJaEmitidoError) -> JSONResponse:
        return resposta_de_erro(409, erro.codigo.value, erro.mensagem)

    @app.exception_handler(RegraDeAplicacaoError)
    async def _regra_de_aplicacao(_: Request, erro: RegraDeAplicacaoError) -> JSONResponse:
        return resposta_de_erro(409, erro.codigo.value, erro.mensagem)

    @app.exception_handler(ViolacaoDeRegraError)
    async def _violacao(_: Request, erro: ViolacaoDeRegraError) -> JSONResponse:
        return resposta_de_erro(422, erro.codigo.value, erro.mensagem)

    @app.exception_handler(EntradaInvalidaError)
    async def _entrada_invalida(_: Request, erro: EntradaInvalidaError) -> JSONResponse:
        return resposta_de_erro(422, erro.codigo.value, erro.mensagem)

    @app.exception_handler(CsrfInvalidoError)
    async def _csrf(_: Request, __: CsrfInvalidoError) -> JSONResponse:
        return resposta_de_erro(403, "csrf_invalido", "Token CSRF ausente ou inválido.")

    @app.exception_handler(RequestValidationError)
    async def _validacao(_: Request, erro: RequestValidationError) -> JSONResponse:
        # Só campo e mensagem: o valor recebido (``input``) pode ser uma senha e nunca é devolvido.
        detalhes = [
            {"campo": _campo(tuple(e["loc"])), "mensagem": str(e["msg"])} for e in erro.errors()
        ]
        return resposta_de_erro(
            422, "entrada_invalida", "Dados de entrada inválidos.", detalhes=detalhes
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, erro: StarletteHTTPException) -> JSONResponse:
        codigo = {404: "rota_nao_encontrada", 405: "metodo_nao_permitido"}.get(
            erro.status_code, "erro_http"
        )
        mensagem = {404: "Recurso não encontrado.", 405: "Método não permitido."}.get(
            erro.status_code, "Requisição não atendida."
        )
        return resposta_de_erro(erro.status_code, codigo, mensagem)

    @app.exception_handler(Exception)
    async def _inesperado(_: Request, erro: Exception) -> JSONResponse:
        _registro.error("Erro inesperado na API", exc_info=erro)
        return resposta_de_erro(500, "erro_interno", "Erro interno do servidor.")
