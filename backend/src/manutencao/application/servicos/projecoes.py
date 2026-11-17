"""Projeções de leitura: consultas que combinam OS e usuários e que os casos de uso reutilizam.

Reproduzem o que o ``Repositorio`` do legado calculava (``tecnicos``, ``carga``,
``ordens_do_equipamento``) e que **não** pertence a uma entidade isolada nem a um repositório de
um só agregado. São **somente leitura** e **não verificam permissão**: quem as chama (um caso de
uso, depois de autorizar) é que decide quem pode ver o quê. Por isso **não** são ponto de entrada
de interface: uma rota ou tela deve usar o serviço, que autoriza.
"""

from manutencao.application.dto import DisponibilidadeDoTecnico
from manutencao.application.portas.repositorios import (
    FiltroDeOrdens,
    OrdemServicoRepository,
    UsuarioRepository,
)
from manutencao.domain.ordem_servico import OrdemServico
from manutencao.domain.usuario import Usuario


class Projecoes:
    """Leituras de técnicos, carga de trabalho e OS por técnico ou equipamento."""

    def __init__(self, usuarios: UsuarioRepository, ordens: OrdemServicoRepository) -> None:
        self._usuarios = usuarios
        self._ordens = ordens

    def tecnicos(self) -> tuple[Usuario, ...]:
        """Os usuários que são técnicos (quem tem ``apontar_reparo``; AUD-20, preservado)."""
        return tuple(u for u in self._usuarios.listar() if u.e_tecnico)

    def carga_do_tecnico(self, tecnico_id: int) -> int:
        """Número de OS ativas (não encerradas) atribuídas ao técnico."""
        return self._ordens.contar(FiltroDeOrdens(tecnico_id=tecnico_id, encerrada=False))

    def ordens_do_tecnico(self, tecnico_id: int) -> tuple[OrdemServico, ...]:
        """Todas as OS atribuídas ao técnico (encerradas ou não)."""
        return self._ordens.listar(FiltroDeOrdens(tecnico_id=tecnico_id))

    def ordens_do_equipamento(self, equipamento_id: int) -> tuple[OrdemServico, ...]:
        """Todas as OS do equipamento, em qualquer estado."""
        return self._ordens.listar(FiltroDeOrdens(equipamento_id=equipamento_id))

    def disponibilidade_dos_tecnicos(
        self, *, ordenar_por_carga: bool = False
    ) -> tuple[DisponibilidadeDoTecnico, ...]:
        """Disponibilidade **armazenada** e carga de cada técnico.

        ``ordenar_por_carga`` reproduz a lista da tela de atribuição (menor carga primeiro, com a
        ordem de cadastro como desempate), usada para balancear o trabalho.
        """
        linhas = [
            DisponibilidadeDoTecnico(
                t.id, t.nome, t.escala, t.disponibilidade, self.carga_do_tecnico(t.id)
            )
            for t in self.tecnicos()
        ]
        if ordenar_por_carga:
            linhas.sort(key=lambda linha: linha.carga)  # estável: empates mantêm a ordem
        return tuple(linhas)
