"""Usuários, cargos, permissões e disponibilidade.

As rotas só traduzem HTTP: o ator vem da sessão e toda regra (permissão, último gestor, OS ativas,
autoproteção) está nos serviços da aplicação.
"""

from typing import Annotated

from fastapi import APIRouter, Query, Response, status

from manutencao.api import esquemas as e
from manutencao.api.mapeamento import cargo_saida, disponibilidade_saida, usuario_saida
from manutencao.api.paginacao import Deslocamento, Limite, paginar
from manutencao.api.seguranca import PROTEGIDO, Autenticado, Contexto
from manutencao.domain.enums import Papel
from manutencao.domain.permissoes import Permissao

usuarios = APIRouter(tags=["Usuários"], dependencies=PROTEGIDO)
cargos = APIRouter(tags=["Cargos e permissões"], dependencies=PROTEGIDO)
disponibilidade = APIRouter(tags=["Disponibilidade"], dependencies=PROTEGIDO)

SEM_CONTEUDO = status.HTTP_204_NO_CONTENT


# --------------------------------------------------------------------------------------- usuários
@usuarios.get(
    "/usuarios", response_model=e.Pagina[e.UsuarioSaida], summary="Lista usuários (gerir_usuarios)"
)
def listar(
    autenticado: Autenticado,
    contexto: Contexto,
    limite: Limite = 100,
    deslocamento: Deslocamento = 0,
    ativo: Annotated[bool | None, Query(description="Filtra por situação")] = None,
    papel: Annotated[Papel | None, Query(description="Filtra por papel")] = None,
    busca: Annotated[
        str | None,
        Query(max_length=100, description="Pesquisa por matrícula, nome ou e-mail (parcial)"),
    ] = None,
) -> e.Pagina[e.UsuarioSaida]:
    todos = contexto.usuarios.listar(autenticado.usuario.id)
    termo = (busca or "").strip().casefold()
    filtrados = [
        u
        for u in todos
        if (ativo is None or u.ativo == ativo)
        and (papel is None or u.papel == papel)
        and (
            not termo
            or termo in (u.matricula or "").casefold()
            or termo in u.nome.casefold()
            or termo in u.email.casefold()
        )
    ]
    return paginar(filtrados, usuario_saida, limite, deslocamento)


@usuarios.post(
    "/usuarios",
    response_model=e.UsuarioSaida,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastra um usuário; a matrícula é gerada e devolvida (e, opcionalmente, a senha)",
)
def cadastrar(
    corpo: e.UsuarioCriarEntrada, autenticado: Autenticado, contexto: Contexto
) -> e.UsuarioSaida:
    usuario = contexto.contas.cadastrar(
        autenticado.usuario.id,
        corpo.nome,
        corpo.cargo_id,
        corpo.email,
        corpo.escala,
        papel=corpo.papel,
        senha=corpo.senha,
    )
    return usuario_saida(usuario)


@usuarios.get("/usuarios/{usuario_id}", response_model=e.UsuarioSaida, summary="Detalha um usuário")
def consultar(usuario_id: int, autenticado: Autenticado, contexto: Contexto) -> e.UsuarioSaida:
    return usuario_saida(contexto.usuarios.consultar(autenticado.usuario.id, usuario_id))


@usuarios.patch(
    "/usuarios/{usuario_id}",
    response_model=e.UsuarioSaida,
    summary="Atualiza nome, e-mail e escala",
)
def atualizar(
    usuario_id: int,
    corpo: e.UsuarioAtualizarEntrada,
    autenticado: Autenticado,
    contexto: Contexto,
) -> e.UsuarioSaida:
    usuario = contexto.usuarios.atualizar_dados(
        autenticado.usuario.id, usuario_id, nome=corpo.nome, email=corpo.email, escala=corpo.escala
    )
    return usuario_saida(usuario)


@usuarios.put(
    "/usuarios/{usuario_id}/cargo", response_model=e.UsuarioSaida, summary="Altera o cargo"
)
def alterar_cargo(
    usuario_id: int, corpo: e.CargoAlterarEntrada, autenticado: Autenticado, contexto: Contexto
) -> e.UsuarioSaida:
    return usuario_saida(
        contexto.usuarios.alterar_cargo(autenticado.usuario.id, usuario_id, corpo.cargo_id)
    )


@usuarios.put(
    "/usuarios/{usuario_id}/papel",
    response_model=e.UsuarioSaida,
    summary="Altera o papel (Gestor ou Técnico); só o Gestor",
)
def alterar_papel(
    usuario_id: int, corpo: e.PapelAlterarEntrada, autenticado: Autenticado, contexto: Contexto
) -> e.UsuarioSaida:
    return usuario_saida(
        contexto.usuarios.alterar_papel(autenticado.usuario.id, usuario_id, corpo.papel)
    )


@usuarios.post(
    "/usuarios/{usuario_id}/desativar",
    response_model=e.UsuarioSaida,
    summary="Desativa (revoga as sessões do usuário)",
)
def desativar(usuario_id: int, autenticado: Autenticado, contexto: Contexto) -> e.UsuarioSaida:
    return usuario_saida(contexto.contas.desativar(autenticado.usuario.id, usuario_id))


@usuarios.post(
    "/usuarios/{usuario_id}/reativar", response_model=e.UsuarioSaida, summary="Reativa o usuário"
)
def reativar(usuario_id: int, autenticado: Autenticado, contexto: Contexto) -> e.UsuarioSaida:
    return usuario_saida(contexto.usuarios.reativar(autenticado.usuario.id, usuario_id))


@usuarios.delete(
    "/usuarios/{usuario_id}",
    status_code=SEM_CONTEUDO,
    summary="Exclui um usuário sem histórico em OS",
)
def excluir(usuario_id: int, autenticado: Autenticado, contexto: Contexto) -> Response:
    contexto.contas.excluir(autenticado.usuario.id, usuario_id)
    return Response(status_code=SEM_CONTEUDO)


@usuarios.put(
    "/usuarios/{usuario_id}/credencial",
    status_code=SEM_CONTEUDO,
    summary="Define ou redefine a senha (a matrícula não muda; revoga as sessões)",
)
def definir_credencial(
    usuario_id: int, corpo: e.CredencialEntrada, autenticado: Autenticado, contexto: Contexto
) -> Response:
    contexto.autenticacao.definir_credencial(autenticado.usuario.id, usuario_id, corpo.senha)
    return Response(status_code=SEM_CONTEUDO)


# ------------------------------------------------------------------------------ cargos e permissões
@cargos.get(
    "/cargos", response_model=list[e.CargoSaida], summary="Lista os cargos (gerir_usuarios)"
)
def listar_cargos(autenticado: Autenticado, contexto: Contexto) -> list[e.CargoSaida]:
    return [cargo_saida(c) for c in contexto.usuarios.listar_cargos(autenticado.usuario.id)]


@cargos.put(
    "/cargos/{cargo_id}/permissoes",
    response_model=e.CargoSaida,
    summary="Define as permissões do cargo (tudo ou nada)",
)
def definir_permissoes(
    cargo_id: int, corpo: e.PermissoesDefinirEntrada, autenticado: Autenticado, contexto: Contexto
) -> e.CargoSaida:
    return cargo_saida(
        contexto.usuarios.definir_permissoes_do_cargo(
            autenticado.usuario.id, cargo_id, corpo.permissoes
        )
    )


@cargos.get(
    "/permissoes",
    response_model=list[e.PermissaoSaida],
    summary="Catálogo de permissões do sistema",
)
def catalogo_de_permissoes(_: Autenticado) -> list[e.PermissaoSaida]:
    return [e.PermissaoSaida(nome=p, descricao=p.descricao) for p in Permissao]


# ------------------------------------------------------------------------------ disponibilidade
@disponibilidade.get(
    "/disponibilidade",
    response_model=list[e.DisponibilidadeDoTecnicoSaida],
    summary="Disponibilidade derivada e carga dos técnicos (ver_disponibilidade)",
)
def consultar_disponibilidade(
    autenticado: Autenticado,
    contexto: Contexto,
    ordenar_por_carga: bool = False,
) -> list[e.DisponibilidadeDoTecnicoSaida]:
    linhas = contexto.disponibilidade.consultar(
        autenticado.usuario.id, ordenar_por_carga=ordenar_por_carga
    )
    return [disponibilidade_saida(d) for d in linhas]


@disponibilidade.put(
    "/me/disponibilidade",
    response_model=e.UsuarioSaida,
    summary="Altera a própria disponibilidade manual (Disponível ou Ausente)",
)
def alterar_minha_disponibilidade(
    corpo: e.DisponibilidadeAlterarEntrada, autenticado: Autenticado, contexto: Contexto
) -> e.UsuarioSaida:
    return usuario_saida(
        contexto.disponibilidade.alterar_minha_disponibilidade(
            autenticado.usuario.id, corpo.disponibilidade
        )
    )


@disponibilidade.put(
    "/usuarios/{usuario_id}/disponibilidade",
    response_model=e.UsuarioSaida,
    summary="Altera a disponibilidade manual de outro usuário (gerir_usuarios)",
)
def alterar_disponibilidade(
    usuario_id: int,
    corpo: e.DisponibilidadeAlterarEntrada,
    autenticado: Autenticado,
    contexto: Contexto,
) -> e.UsuarioSaida:
    return usuario_saida(
        contexto.disponibilidade.alterar_disponibilidade(
            autenticado.usuario.id, usuario_id, corpo.disponibilidade
        )
    )
