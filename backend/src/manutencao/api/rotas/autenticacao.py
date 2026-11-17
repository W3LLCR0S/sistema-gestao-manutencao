"""Autenticação: login, logout, sessão, usuário atual e permissões (D-01)."""

from fastapi import APIRouter, Request, Response, status

from manutencao.api import esquemas as e
from manutencao.api.mapeamento import usuario_atual_saida
from manutencao.api.seguranca import PROTEGIDO, Autenticado, Contexto, conferir_csrf
from manutencao.application.erros import CredenciaisInvalidasError, NaoAutenticadoError
from manutencao.domain.permissoes import Permissao

publico = APIRouter(prefix="/auth", tags=["Autenticação"])
protegido = APIRouter(prefix="/auth", tags=["Autenticação"], dependencies=PROTEGIDO)


def _chave_de_tentativas(request: Request, login: str) -> str:
    origem = request.client.host if request.client is not None else "?"
    return f"{origem}|{login.strip().casefold()}"


@publico.post(
    "/login",
    response_model=e.SessaoSaida,
    summary="Abre uma sessão (cookie HttpOnly) com login e senha",
)
def login(
    corpo: e.LoginEntrada, request: Request, response: Response, contexto: Contexto
) -> e.SessaoSaida:
    chave = _chave_de_tentativas(request, corpo.login)
    contexto.limitador.verificar(chave)
    try:
        iniciada = contexto.autenticacao.login(corpo.login, corpo.senha)
    except CredenciaisInvalidasError:
        contexto.limitador.registrar_falha(chave)
        raise
    contexto.limitador.limpar(chave)
    cfg = contexto.configuracao
    response.set_cookie(
        cfg.cookie_nome,
        iniciada.token,
        max_age=int(contexto.autenticacao.validade.total_seconds()),
        httponly=True,
        samesite="lax",
        secure=cfg.cookie_seguro,
        path="/",
    )
    return e.SessaoSaida(
        usuario=usuario_atual_saida(
            iniciada.usuario, contexto.autenticacao.login_do_usuario(iniciada.usuario.id)
        ),
        csrf_token=iniciada.sessao.csrf,
        expira_em=iniciada.sessao.expira_em,
    )


@publico.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Encerra a sessão (idempotente; revoga no servidor)",
)
def logout(request: Request, contexto: Contexto) -> Response:
    token = request.cookies.get(contexto.configuracao.cookie_nome)
    if token:
        try:
            autenticacao = contexto.autenticacao.autenticar(token)
        except NaoAutenticadoError:
            autenticacao = None  # sessão inexistente ou expirada: o logout é idempotente
        if autenticacao is not None:
            # Com sessão válida, encerrar também exige o CSRF (terceiros não encerram a sessão).
            conferir_csrf(request, autenticacao.sessao.csrf)
        contexto.autenticacao.logout(token)
    resposta = Response(status_code=status.HTTP_204_NO_CONTENT)
    resposta.delete_cookie(contexto.configuracao.cookie_nome, path="/")
    return resposta


@protegido.get("/me", response_model=e.SessaoSaida, summary="Usuário autenticado e token CSRF")
def eu(autenticado: Autenticado, contexto: Contexto) -> e.SessaoSaida:
    usuario = autenticado.usuario
    return e.SessaoSaida(
        usuario=usuario_atual_saida(usuario, contexto.autenticacao.login_do_usuario(usuario.id)),
        csrf_token=autenticado.sessao.csrf,
        expira_em=autenticado.sessao.expira_em,
    )


@protegido.get(
    "/sessao", response_model=e.VerificacaoDeSessaoSaida, summary="Verifica se a sessão é válida"
)
def sessao(autenticado: Autenticado) -> e.VerificacaoDeSessaoSaida:
    return e.VerificacaoDeSessaoSaida(
        autenticado=True, usuario_id=autenticado.usuario.id, expira_em=autenticado.sessao.expira_em
    )


@protegido.get(
    "/permissoes/{permissao}",
    response_model=e.PermissaoVerificadaSaida,
    summary="Verifica se o usuário autenticado tem a permissão",
)
def verificar_permissao(
    permissao: Permissao, autenticado: Autenticado
) -> e.PermissaoVerificadaSaida:
    return e.PermissaoVerificadaSaida(
        permissao=permissao, concedida=autenticado.usuario.pode(permissao)
    )


@protegido.post(
    "/alterar-senha",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Troca a própria senha (revoga as outras sessões)",
)
def alterar_senha(
    corpo: e.SenhaAlterarEntrada, autenticado: Autenticado, contexto: Contexto
) -> Response:
    contexto.autenticacao.alterar_propria_senha(autenticado, corpo.senha_atual, corpo.nova_senha)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
