"""O que a API recebe pronto da raiz de composição: serviços, limitador e configuração.

A API **não** monta serviços nem escolhe repositórios (e não importa ``infrastructure`` nem
``composicao``): a composição entrega este contexto, e as rotas só traduzem HTTP para chamadas de
serviço. Não há estado global: cada ``criar_app`` recebe o seu contexto.
"""

from collections.abc import Callable
from dataclasses import dataclass

from manutencao.application.servicos.autenticacao import ServicoDeAutenticacao
from manutencao.application.servicos.contas import ServicoDeContas
from manutencao.application.servicos.disponibilidade import ServicoDeDisponibilidade
from manutencao.application.servicos.equipamentos import ServicoDeEquipamentos
from manutencao.application.servicos.limitador import LimitadorDeTentativas
from manutencao.application.servicos.ordens import ServicoDeOrdens
from manutencao.application.servicos.painel import ServicoDePainel
from manutencao.application.servicos.usuarios import ServicoDeUsuarios


@dataclass(frozen=True)
class ConfiguracaoDaApi:
    """Configuração da borda HTTP (lida do ambiente pela composição)."""

    cookie_nome: str = "manutencao_sessao"
    cookie_seguro: bool = False  # True quando a API é servida por HTTPS (atributo Secure)
    origens_permitidas: tuple[
        str, ...
    ] = ()  # CORS e verificação de Origin; vazio = só mesma origem
    documentacao: bool = True  # expõe /docs, /redoc e /openapi.json


@dataclass(frozen=True)
class ContextoDaApi:
    autenticacao: ServicoDeAutenticacao
    contas: ServicoDeContas
    usuarios: ServicoDeUsuarios
    equipamentos: ServicoDeEquipamentos
    ordens: ServicoDeOrdens
    disponibilidade: ServicoDeDisponibilidade
    painel: ServicoDePainel
    limitador: LimitadorDeTentativas
    configuracao: ConfiguracaoDaApi
    banco_disponivel: Callable[[], bool]  # verificação de saúde (a composição sabe como)
