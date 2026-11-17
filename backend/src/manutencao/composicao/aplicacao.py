"""Composição da aplicação web: liga serviços, persistência de acesso e API.

Duas composições, sem que a API saiba qual está em uso: **PostgreSQL** (execução real e
demonstração) e **em memória** (testes rápidos; nunca na demonstração).
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import timedelta

from manutencao.api.contexto import ConfiguracaoDaApi, ContextoDaApi
from manutencao.application.portas.autenticacao import (
    CredencialRepository,
    HasherDeSenha,
    SessaoRepository,
    UnidadeDeTrabalho,
)
from manutencao.application.portas.relogio import Relogio
from manutencao.application.servicos.autenticacao import ServicoDeAutenticacao
from manutencao.application.servicos.contas import ServicoDeContas
from manutencao.application.servicos.limitador import LimitadorDeTentativas
from manutencao.application.servicos.painel import ServicoDePainel
from manutencao.composicao.container import Container
from manutencao.composicao.fabrica import criar_container_em_memoria, criar_container_postgres
from manutencao.infrastructure.memoria import CredenciaisEmMemoria, SemTransacao, SessoesEmMemoria
from manutencao.infrastructure.postgres import Banco, CredenciaisNoBanco, SessoesNoBanco
from manutencao.infrastructure.relogio import RelogioDeSistema
from manutencao.infrastructure.seguranca import HasherArgon2


@dataclass(frozen=True)
class Aplicacao:
    """O que a execução (e os testes) precisam: o contexto da API e as peças por baixo dele."""

    contexto: ContextoDaApi
    container: Container
    credenciais: CredencialRepository
    sessoes: SessaoRepository
    autenticacao: ServicoDeAutenticacao
    unidade: UnidadeDeTrabalho


def _montar(
    container: Container,
    credenciais: CredencialRepository,
    sessoes: SessaoRepository,
    unidade: UnidadeDeTrabalho,
    banco_disponivel: Callable[[], bool],
    *,
    hasher: HasherDeSenha,
    configuracao: ConfiguracaoDaApi,
    validade: timedelta | None,
) -> Aplicacao:
    autenticacao = ServicoDeAutenticacao(
        credenciais,
        sessoes,
        container.usuarios,
        hasher,
        container.relogio,
        unidade,
        validade=validade,
    )
    contas = ServicoDeContas(
        container.usuarios, container.servico_usuarios, autenticacao, credenciais, unidade
    )
    contexto = ContextoDaApi(
        autenticacao=autenticacao,
        contas=contas,
        usuarios=container.servico_usuarios,
        equipamentos=container.servico_equipamentos,
        ordens=container.servico_ordens,
        disponibilidade=container.servico_disponibilidade,
        painel=ServicoDePainel(container.usuarios, container.ordens, container.projecoes),
        limitador=LimitadorDeTentativas(container.relogio),
        configuracao=configuracao,
        banco_disponivel=banco_disponivel,
    )
    return Aplicacao(contexto, container, credenciais, sessoes, autenticacao, unidade)


def criar_aplicacao_em_memoria(
    *,
    relogio: Relogio | None = None,
    hasher: HasherDeSenha | None = None,
    configuracao: ConfiguracaoDaApi | None = None,
    validade: timedelta | None = None,
) -> Aplicacao:
    """Aplicação toda em memória (testes). Sem dados: o teste cadastra o que precisar."""
    relogio = relogio if relogio is not None else RelogioDeSistema()
    return _montar(
        criar_container_em_memoria(relogio=relogio),
        CredenciaisEmMemoria(),
        SessoesEmMemoria(),
        SemTransacao(),
        lambda: True,
        hasher=hasher if hasher is not None else HasherArgon2(),
        configuracao=configuracao if configuracao is not None else ConfiguracaoDaApi(),
        validade=validade,
    )


def criar_aplicacao_postgres(
    banco: Banco,
    *,
    relogio: Relogio | None = None,
    hasher: HasherDeSenha | None = None,
    configuracao: ConfiguracaoDaApi | None = None,
    validade: timedelta | None = None,
) -> Aplicacao:
    """Aplicação sobre o PostgreSQL de ``banco`` (esquema já migrado até a revisão mais recente)."""
    relogio = relogio if relogio is not None else RelogioDeSistema()
    return _montar(
        criar_container_postgres(banco, relogio=relogio),
        CredenciaisNoBanco(banco),
        SessoesNoBanco(banco),
        banco,
        banco.disponivel,
        hasher=hasher if hasher is not None else HasherArgon2(),
        configuracao=configuracao if configuracao is not None else ConfiguracaoDaApi(),
        validade=validade,
    )
