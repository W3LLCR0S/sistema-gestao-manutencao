"""Ambiente de teste da camada de aplicação: repositórios em memória, relógio fixo e serviços.

Os serviços são montados **à mão, pelo construtor**, com as portas (não com classes concretas): é
a prova de que o caso de uso só conhece abstrações. A base é a do legado, cadastrada por
``semear_dados_de_exemplo``: cargos 1 Gestor e 2 Técnico; usuários 1 Ana (gestora), 2 Bruno e
3 Carla (técnicos); equipamentos 1 Torno CNC, 2 Compressor de Ar e 3 Empilhadeira Elétrica.
"""

from dataclasses import dataclass

from manutencao.application.portas.repositorios import (
    CargoRepository,
    EquipamentoRepository,
    OrdemServicoRepository,
    UsuarioRepository,
)
from manutencao.application.servicos.disponibilidade import ServicoDeDisponibilidade
from manutencao.application.servicos.equipamentos import ServicoDeEquipamentos
from manutencao.application.servicos.ordens import ServicoDeOrdens
from manutencao.application.servicos.projecoes import Projecoes
from manutencao.application.servicos.usuarios import ServicoDeUsuarios
from manutencao.composicao.fabrica import semear_dados_de_exemplo
from manutencao.infrastructure.memoria import (
    CargosEmMemoria,
    EquipamentosEmMemoria,
    OrdensEmMemoria,
    UsuariosEmMemoria,
)
from tests.apoio.relogio import RelogioFixo

CARGO_GESTOR, CARGO_TECNICO = 1, 2
ANA, BRUNO, CARLA = 1, 2, 3
TORNO, COMPRESSOR, EMPILHADEIRA = 1, 2, 3


@dataclass
class Ambiente:
    """Tudo o que um teste de aplicação precisa, visto pelas portas."""

    relogio: RelogioFixo
    equipamentos: EquipamentoRepository
    cargos: CargoRepository
    usuarios: UsuarioRepository
    ordens: OrdemServicoRepository
    servico_equipamentos: ServicoDeEquipamentos
    servico_usuarios: ServicoDeUsuarios
    servico_ordens: ServicoDeOrdens
    projecoes: Projecoes
    servico_disponibilidade: ServicoDeDisponibilidade


def criar_ambiente() -> Ambiente:
    """Um ambiente novo e isolado, com a base do legado."""
    fixo = RelogioFixo()
    equipamentos = EquipamentosEmMemoria()
    cargos = CargosEmMemoria()
    usuarios = UsuariosEmMemoria(cargos)
    ordens = OrdensEmMemoria()
    projecoes = Projecoes(usuarios, ordens)
    semear_dados_de_exemplo(equipamentos, cargos, usuarios)
    return Ambiente(
        relogio=fixo,
        equipamentos=equipamentos,
        cargos=cargos,
        usuarios=usuarios,
        ordens=ordens,
        servico_equipamentos=ServicoDeEquipamentos(equipamentos, usuarios, ordens),
        servico_usuarios=ServicoDeUsuarios(usuarios, cargos, ordens),
        servico_ordens=ServicoDeOrdens(ordens, usuarios, equipamentos, fixo),
        projecoes=projecoes,
        servico_disponibilidade=ServicoDeDisponibilidade(usuarios, projecoes),
    )
