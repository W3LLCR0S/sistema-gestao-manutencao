"""Ambiente de teste da camada de aplicação: repositórios em memória, relógio fixo e serviços.

Os serviços são montados **à mão, pelo construtor**, com as portas (não com classes concretas): é
a prova de que o caso de uso só conhece abstrações. A base é a mesma do legado
(``_popular_exemplo``): cargos 1 Gestor e 2 Técnico; usuários 1 Ana (gestora), 2 Bruno e 3 Carla
(técnicos); equipamentos 1 Torno CNC, 2 Compressor de Ar e 3 Empilhadeira Elétrica.
"""

from dataclasses import dataclass

from manutencao.application.portas.repositorios import (
    CargoRepository,
    EquipamentoRepository,
    OrdemServicoRepository,
    UsuarioRepository,
)
from manutencao.application.servicos.equipamentos import ServicoDeEquipamentos
from manutencao.application.servicos.usuarios import ServicoDeUsuarios
from manutencao.domain.cargo import Cargo
from manutencao.domain.equipamento import Equipamento
from manutencao.domain.permissoes import Permissoes
from manutencao.domain.usuario import Usuario
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


def semear(
    equipamentos: EquipamentoRepository,
    cargos: CargoRepository,
    usuarios: UsuarioRepository,
) -> None:
    """A base inicial do legado, cadastrada pelas portas (os ids saem da sequência)."""
    gestor = Cargo(cargos.proximo_id(), "Gestor", Permissoes.padrao_gestor())
    cargos.adicionar(gestor)
    tecnico = Cargo(cargos.proximo_id(), "Técnico", Permissoes.padrao_tecnico())
    cargos.adicionar(tecnico)
    for nome, cargo, email, escala in (
        ("Ana Souza", gestor, "ana@empresa.com", "Seg-Sex 08h-17h"),
        ("Bruno Lima", tecnico, "bruno@empresa.com", "Seg-Sex 07h-16h"),
        ("Carla Mendes", tecnico, "carla@empresa.com", "Seg-Sex 13h-22h"),
    ):
        usuarios.adicionar(Usuario(usuarios.proximo_id(), nome, cargo, email, escala))
    for nome, modelo in (
        ("Torno CNC", "GL 240"),
        ("Compressor de Ar", "CSW 40"),
        ("Empilhadeira Elétrica", "PT 1650"),
    ):
        equipamentos.adicionar(Equipamento(equipamentos.proximo_id(), nome, modelo))


def criar_ambiente() -> Ambiente:
    """Um ambiente novo e isolado, com a base do legado."""
    fixo = RelogioFixo()
    equipamentos = EquipamentosEmMemoria()
    cargos = CargosEmMemoria()
    usuarios = UsuariosEmMemoria(cargos)
    ordens = OrdensEmMemoria()
    semear(equipamentos, cargos, usuarios)
    return Ambiente(
        relogio=fixo,
        equipamentos=equipamentos,
        cargos=cargos,
        usuarios=usuarios,
        ordens=ordens,
        servico_equipamentos=ServicoDeEquipamentos(equipamentos, usuarios, ordens),
        servico_usuarios=ServicoDeUsuarios(usuarios, cargos, ordens),
    )
