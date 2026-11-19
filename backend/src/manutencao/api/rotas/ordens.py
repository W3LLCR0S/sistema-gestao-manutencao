"""Ordens de serviço: abertura, consulta, execução técnica, gestão e histórico.

Cada rota chama **um** caso de uso de ``ServicoDeOrdens`` com o ator da sessão e devolve a OS
atualizada. Permissão, posse da OS, transições de estado e demais regras são do domínio e da
aplicação; nenhuma é repetida aqui.
"""

from typing import Annotated

from fastapi import APIRouter, Query, status

from manutencao.api import esquemas as e
from manutencao.api.mapeamento import ordem_saida, servico_saida, usuario_resumo
from manutencao.api.paginacao import Deslocamento, Limite, paginar
from manutencao.api.seguranca import PROTEGIDO, Autenticado, Contexto
from manutencao.application.dto import PecaInformada
from manutencao.application.portas.repositorios import FiltroDeOrdens
from manutencao.domain.enums import Criticidade, StatusOS

roteador = APIRouter(prefix="/ordens", tags=["Ordens de serviço"], dependencies=PROTEGIDO)


@roteador.get("", response_model=e.Pagina[e.OrdemSaida], summary="Lista OS com filtros (ver_os)")
def listar(
    autenticado: Autenticado,
    contexto: Contexto,
    status_os: Annotated[StatusOS | None, Query(alias="status")] = None,
    criticidade: Criticidade | None = None,
    equipamento_id: int | None = None,
    tecnico_id: int | None = None,
    encerrada: Annotated[
        bool | None, Query(description="true: Concluída/Cancelada; false: em aberto")
    ] = None,
    mais_antigas_primeiro: Annotated[
        bool, Query(description="Por padrão as mais recentes (maior número) vêm primeiro")
    ] = False,
    limite: Limite = 50,
    deslocamento: Deslocamento = 0,
) -> e.Pagina[e.OrdemSaida]:
    filtro = FiltroDeOrdens(
        status=status_os,
        criticidade=criticidade,
        equipamento_id=equipamento_id,
        tecnico_id=tecnico_id,
        encerrada=encerrada,
    )
    ordens = contexto.ordens.listar(autenticado.usuario.id, filtro)
    return paginar(
        ordens if mais_antigas_primeiro else tuple(reversed(ordens)),
        ordem_saida,
        limite,
        deslocamento,
    )


@roteador.post(
    "",
    response_model=e.OrdemSaida,
    status_code=status.HTTP_201_CREATED,
    summary="Abre uma OS (abrir_os)",
)
def abrir(corpo: e.OrdemAbrirEntrada, autenticado: Autenticado, contexto: Contexto) -> e.OrdemSaida:
    ordem = contexto.ordens.abrir(
        autenticado.usuario.id, corpo.equipamento_id, corpo.falha, corpo.criticidade
    )
    return ordem_saida(ordem)


@roteador.get("/{numero}", response_model=e.OrdemSaida, summary="Detalha uma OS")
def consultar(numero: int, autenticado: Autenticado, contexto: Contexto) -> e.OrdemSaida:
    return ordem_saida(contexto.ordens.consultar(autenticado.usuario.id, numero))


@roteador.get(
    "/{numero}/historico",
    response_model=list[e.ServicoSaida],
    summary="Histórico da OS, em ordem de inclusão",
)
def historico(numero: int, autenticado: Autenticado, contexto: Contexto) -> list[e.ServicoSaida]:
    return [servico_saida(s) for s in contexto.ordens.historico(autenticado.usuario.id, numero)]


# ---------------------------------------------------------------------------- execução técnica
@roteador.post(
    "/{numero}/diagnostico", response_model=e.OrdemSaida, summary="Registra o diagnóstico"
)
def diagnosticar(
    numero: int, corpo: e.DiagnosticoEntrada, autenticado: Autenticado, contexto: Contexto
) -> e.OrdemSaida:
    ator = autenticado.usuario.id
    contexto.ordens.registrar_diagnostico(ator, numero, corpo.parecer, corpo.causa_raiz)
    return ordem_saida(contexto.ordens.consultar(ator, numero))


@roteador.post(
    "/{numero}/reparos",
    response_model=e.OrdemSaida,
    summary="Registra horas, intervenção e peças de um reparo",
)
def apontar_reparo(
    numero: int, corpo: e.ReparoEntrada, autenticado: Autenticado, contexto: Contexto
) -> e.OrdemSaida:
    ator = autenticado.usuario.id
    pecas = [PecaInformada(p.descricao, p.quantidade) for p in corpo.pecas]
    contexto.ordens.apontar_reparo(ator, numero, corpo.horas, corpo.intervencao, pecas)
    return ordem_saida(contexto.ordens.consultar(ator, numero))


@roteador.post(
    "/{numero}/status", response_model=e.OrdemSaida, summary="Altera o status operacional"
)
def alterar_status(
    numero: int, corpo: e.StatusEntrada, autenticado: Autenticado, contexto: Contexto
) -> e.OrdemSaida:
    ator = autenticado.usuario.id
    contexto.ordens.alterar_status(ator, numero, corpo.status)
    return ordem_saida(contexto.ordens.consultar(ator, numero))


@roteador.post(
    "/{numero}/conclusao-tecnica",
    response_model=e.ConclusaoTecnicaSaida,
    summary="Conclusão técnica: registra o teste e submete à aprovação se passou",
)
def concluir_tecnicamente(
    numero: int, corpo: e.ConclusaoTecnicaEntrada, autenticado: Autenticado, contexto: Contexto
) -> e.ConclusaoTecnicaSaida:
    ator = autenticado.usuario.id
    submetida = contexto.ordens.concluir_tecnicamente(ator, numero, corpo.teste, corpo.passou)
    return e.ConclusaoTecnicaSaida(
        submetida_a_aprovacao=submetida, ordem=ordem_saida(contexto.ordens.consultar(ator, numero))
    )


@roteador.post(
    "/{numero}/apontamentos",
    response_model=e.OrdemSaida,
    summary="Adiciona uma observação ao histórico (registrar_apontamento + vínculo com a OS)",
)
def adicionar_apontamento(
    numero: int, corpo: e.ApontamentoEntrada, autenticado: Autenticado, contexto: Contexto
) -> e.OrdemSaida:
    ator = autenticado.usuario.id
    contexto.ordens.adicionar_apontamento(ator, numero, corpo.texto)
    return ordem_saida(contexto.ordens.consultar(ator, numero))


# ------------------------------------------------------------------------------------- gestão
@roteador.post(
    "/{numero}/atribuicao",
    response_model=e.AtribuicaoSaida,
    summary="Atribui ou reatribui a um técnico (atribuir_os)",
)
def atribuir(
    numero: int, corpo: e.AtribuicaoEntrada, autenticado: Autenticado, contexto: Contexto
) -> e.AtribuicaoSaida:
    ator = autenticado.usuario.id
    anterior = contexto.ordens.atribuir(
        ator, numero, corpo.tecnico_id, confirmar_ausente=corpo.confirmar_ausente
    )
    return e.AtribuicaoSaida(
        ordem=ordem_saida(contexto.ordens.consultar(ator, numero)),
        tecnico_anterior=None if anterior is None else usuario_resumo(anterior),
    )


@roteador.post(
    "/{numero}/aprovacao", response_model=e.OrdemSaida, summary="Aprova e encerra (aprovar_os)"
)
def aprovar(numero: int, autenticado: Autenticado, contexto: Contexto) -> e.OrdemSaida:
    ator = autenticado.usuario.id
    contexto.ordens.aprovar(ator, numero)
    return ordem_saida(contexto.ordens.consultar(ator, numero))


@roteador.post(
    "/{numero}/reprovacao", response_model=e.OrdemSaida, summary="Reprova e devolve ao técnico"
)
def reprovar(
    numero: int, corpo: e.MotivoEntrada, autenticado: Autenticado, contexto: Contexto
) -> e.OrdemSaida:
    ator = autenticado.usuario.id
    contexto.ordens.reprovar(ator, numero, corpo.motivo)
    return ordem_saida(contexto.ordens.consultar(ator, numero))


@roteador.post("/{numero}/cancelamento", response_model=e.OrdemSaida, summary="Cancela a OS")
def cancelar(
    numero: int, corpo: e.MotivoEntrada, autenticado: Autenticado, contexto: Contexto
) -> e.OrdemSaida:
    ator = autenticado.usuario.id
    contexto.ordens.cancelar(ator, numero, corpo.motivo)
    return ordem_saida(contexto.ordens.consultar(ator, numero))
