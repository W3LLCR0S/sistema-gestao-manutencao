"""Equipamentos: cadastro, consulta, edição, inativação e exclusão (regras nos serviços)."""

from fastapi import APIRouter, Response, status

from manutencao.api import esquemas as e
from manutencao.api.mapeamento import equipamento_saida
from manutencao.api.paginacao import Deslocamento, Limite, paginar
from manutencao.api.seguranca import PROTEGIDO, Autenticado, Contexto

roteador = APIRouter(prefix="/equipamentos", tags=["Equipamentos"], dependencies=PROTEGIDO)


@roteador.get(
    "", response_model=e.Pagina[e.EquipamentoSaida], summary="Lista equipamentos (ver_equipamentos)"
)
def listar(
    autenticado: Autenticado,
    contexto: Contexto,
    apenas_ativos: bool = False,
    limite: Limite = 100,
    deslocamento: Deslocamento = 0,
) -> e.Pagina[e.EquipamentoSaida]:
    todos = contexto.equipamentos.listar(autenticado.usuario.id, apenas_ativos=apenas_ativos)
    return paginar(todos, equipamento_saida, limite, deslocamento)


@roteador.post(
    "",
    response_model=e.EquipamentoSaida,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastra um equipamento (gerir_equipamentos)",
)
def cadastrar(
    corpo: e.EquipamentoEntrada, autenticado: Autenticado, contexto: Contexto
) -> e.EquipamentoSaida:
    return equipamento_saida(
        contexto.equipamentos.cadastrar(autenticado.usuario.id, corpo.nome, corpo.modelo)
    )


@roteador.get("/{equipamento_id}", response_model=e.EquipamentoSaida, summary="Detalha")
def consultar(
    equipamento_id: int, autenticado: Autenticado, contexto: Contexto
) -> e.EquipamentoSaida:
    return equipamento_saida(
        contexto.equipamentos.consultar(autenticado.usuario.id, equipamento_id)
    )


@roteador.put("/{equipamento_id}", response_model=e.EquipamentoSaida, summary="Atualiza")
def atualizar(
    equipamento_id: int,
    corpo: e.EquipamentoEntrada,
    autenticado: Autenticado,
    contexto: Contexto,
) -> e.EquipamentoSaida:
    return equipamento_saida(
        contexto.equipamentos.atualizar(
            autenticado.usuario.id, equipamento_id, corpo.nome, corpo.modelo
        )
    )


@roteador.post("/{equipamento_id}/inativar", response_model=e.EquipamentoSaida, summary="Inativa")
def inativar(
    equipamento_id: int, autenticado: Autenticado, contexto: Contexto
) -> e.EquipamentoSaida:
    return equipamento_saida(contexto.equipamentos.inativar(autenticado.usuario.id, equipamento_id))


@roteador.post("/{equipamento_id}/reativar", response_model=e.EquipamentoSaida, summary="Reativa")
def reativar(
    equipamento_id: int, autenticado: Autenticado, contexto: Contexto
) -> e.EquipamentoSaida:
    return equipamento_saida(contexto.equipamentos.reativar(autenticado.usuario.id, equipamento_id))


@roteador.delete(
    "/{equipamento_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Exclui um equipamento sem OS (com OS, só inativar)",
)
def excluir(equipamento_id: int, autenticado: Autenticado, contexto: Contexto) -> Response:
    contexto.equipamentos.excluir(autenticado.usuario.id, equipamento_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
