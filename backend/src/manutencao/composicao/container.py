"""O contêiner: o conjunto de portas e serviços já ligados, e a função que os liga.

``montar`` só conhece **abstrações** (as portas): quem escolhe as implementações é a fábrica
(``fabrica.py``) ou o teste. Não há framework de injeção, localizador de serviços nem estado
global: cada chamada devolve um contêiner novo e independente (ADR-0005).
"""

from dataclasses import dataclass

from manutencao.application.portas.relogio import Relogio
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


@dataclass(frozen=True)
class Container:
    """Portas e serviços de uma instância da aplicação."""

    relogio: Relogio
    equipamentos: EquipamentoRepository
    cargos: CargoRepository
    usuarios: UsuarioRepository
    ordens: OrdemServicoRepository
    projecoes: Projecoes
    servico_equipamentos: ServicoDeEquipamentos
    servico_usuarios: ServicoDeUsuarios
    servico_ordens: ServicoDeOrdens
    servico_disponibilidade: ServicoDeDisponibilidade


def montar(
    *,
    relogio: Relogio,
    equipamentos: EquipamentoRepository,
    cargos: CargoRepository,
    usuarios: UsuarioRepository,
    ordens: OrdemServicoRepository,
) -> Container:
    """Liga os serviços às portas recebidas (injeção por construtor)."""
    projecoes = Projecoes(usuarios, ordens)
    return Container(
        relogio=relogio,
        equipamentos=equipamentos,
        cargos=cargos,
        usuarios=usuarios,
        ordens=ordens,
        projecoes=projecoes,
        servico_equipamentos=ServicoDeEquipamentos(equipamentos, usuarios, ordens),
        servico_usuarios=ServicoDeUsuarios(usuarios, cargos, ordens),
        servico_ordens=ServicoDeOrdens(ordens, usuarios, equipamentos, relogio),
        servico_disponibilidade=ServicoDeDisponibilidade(usuarios, ordens, projecoes),
    )
