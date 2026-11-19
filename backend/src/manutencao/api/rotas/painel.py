"""Painel inicial e verificação de saúde."""

from fastapi import APIRouter

from manutencao.api import esquemas as e
from manutencao.api.mapeamento import painel_saida
from manutencao.api.seguranca import PROTEGIDO, Autenticado, Contexto

painel = APIRouter(prefix="/painel", tags=["Painel"], dependencies=PROTEGIDO)
saude = APIRouter(tags=["Saúde"])


@painel.get("", response_model=e.PainelSaida, summary="Contagens e visão geral (ver_os)")
def consultar(autenticado: Autenticado, contexto: Contexto) -> e.PainelSaida:
    return painel_saida(contexto.painel.consultar(autenticado.usuario.id))


@saude.get("/saude", response_model=e.SaudeSaida, summary="Verifica a API e a conexão com o banco")
def verificar(contexto: Contexto) -> e.SaudeSaida:
    banco = contexto.banco_disponivel()
    return e.SaudeSaida(
        status="ok" if banco else "degradado", banco="ok" if banco else "indisponivel"
    )
