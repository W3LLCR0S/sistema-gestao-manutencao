"""Painel inicial: contagens e visão geral, só leitura (``ver_os``).

Uma projeção da aplicação: reúne números que a interface mostra na primeira tela, sem regra nova.
As contagens vêm do repositório (``contar``), nenhuma OS é carregada para contar.
"""

from dataclasses import dataclass

from manutencao.application.dto import DisponibilidadeDoTecnico
from manutencao.application.portas.repositorios import (
    FiltroDeOrdens,
    OrdemServicoRepository,
    UsuarioRepository,
)
from manutencao.application.servicos.comum import carregar_ator
from manutencao.application.servicos.projecoes import Projecoes
from manutencao.domain.enums import Criticidade, StatusOS
from manutencao.domain.ordem_servico import OrdemServico
from manutencao.domain.permissoes import Permissao

QUANTIDADE_DE_RECENTES = 5


@dataclass(frozen=True)
class Painel:
    total: int
    em_aberto: int
    encerradas: int
    minhas_em_aberto: int
    por_status: tuple[tuple[StatusOS, int], ...]
    por_criticidade_em_aberto: tuple[tuple[Criticidade, int], ...]
    recentes: tuple[OrdemServico, ...]
    tecnicos: tuple[DisponibilidadeDoTecnico, ...] | None  # None: o ator não vê disponibilidade


class ServicoDePainel:
    def __init__(
        self,
        usuarios: UsuarioRepository,
        ordens: OrdemServicoRepository,
        projecoes: Projecoes,
    ) -> None:
        self._usuarios = usuarios
        self._ordens = ordens
        self._projecoes = projecoes

    def consultar(self, ator_id: int) -> Painel:
        ator = carregar_ator(self._usuarios, ator_id)
        ator.exigir(Permissao.VER_OS)
        contar = self._ordens.contar
        total = contar()
        recentes = () if total == 0 else self._ordens.listar()[-QUANTIDADE_DE_RECENTES:]
        return Painel(
            total=total,
            em_aberto=contar(FiltroDeOrdens(encerrada=False)),
            encerradas=contar(FiltroDeOrdens(encerrada=True)),
            minhas_em_aberto=contar(FiltroDeOrdens(tecnico_id=ator.id, encerrada=False)),
            por_status=tuple((s, contar(FiltroDeOrdens(status=s))) for s in StatusOS),
            por_criticidade_em_aberto=tuple(
                (c, contar(FiltroDeOrdens(criticidade=c, encerrada=False))) for c in Criticidade
            ),
            recentes=tuple(reversed(recentes)),
            tecnicos=(
                self._projecoes.disponibilidade_dos_tecnicos()
                if ator.pode(Permissao.VER_DISPONIBILIDADE)
                else None
            ),
        )
