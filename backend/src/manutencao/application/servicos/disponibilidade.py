"""Disponibilidade dos técnicos: consulta, ajuste manual e a rotina de atualização do legado.

Reproduz o comportamento **atual**: a disponibilidade é um valor armazenado que só muda por ação
manual (``alterar_minha_disponibilidade``) ou pela rotina ``atualizar_disponibilidades``. Uma
consulta feita antes da rotina vê o valor antigo (AUD-13). **Não** aplica a D-05 (disponibilidade
derivada, com ``Ausente`` à parte), que é a Operação E: aqui nada recalcula sozinho.
"""

from manutencao.application.dto import DisponibilidadeDoTecnico
from manutencao.application.portas.repositorios import (
    FiltroDeOrdens,
    OrdemServicoRepository,
    UsuarioRepository,
)
from manutencao.application.servicos.comum import carregar_ator
from manutencao.application.servicos.projecoes import Projecoes
from manutencao.domain.enums import Disponibilidade, StatusOS
from manutencao.domain.permissoes import Permissao
from manutencao.domain.usuario import Usuario


class ServicoDeDisponibilidade:
    """Consulta de disponibilidade e carga; ajuste manual; rotina de atualização."""

    def __init__(
        self,
        usuarios: UsuarioRepository,
        ordens: OrdemServicoRepository,
        projecoes: Projecoes,
    ) -> None:
        self._usuarios = usuarios
        self._ordens = ordens
        self._projecoes = projecoes

    def consultar(
        self, ator_id: int, *, ordenar_por_carga: bool = False
    ) -> tuple[DisponibilidadeDoTecnico, ...]:
        """Escala, disponibilidade armazenada e carga de cada técnico (``ver_disponibilidade``)."""
        carregar_ator(self._usuarios, ator_id).exigir(Permissao.VER_DISPONIBILIDADE)
        return self._projecoes.disponibilidade_dos_tecnicos(ordenar_por_carga=ordenar_por_carga)

    def alterar_minha_disponibilidade(self, ator_id: int, valor: Disponibilidade) -> Usuario:
        """Cada usuário ajusta a **própria** disponibilidade; não exige permissão (legado)."""
        ator = carregar_ator(self._usuarios, ator_id)
        ator.disponibilidade = valor
        self._usuarios.salvar(ator)
        return ator

    def atualizar_disponibilidades(self) -> None:
        """Rotina do sistema (não é ação de usuário): recalcula a disponibilidade dos técnicos.

        Técnico com OS **Em Execução** fica ``Em atendimento``; sem OS em execução, ``Disponível``;
        quem está ``Ausente`` só muda manualmente. Só técnicos são recalculados. No legado a
        interface a executava depois de cada ação; hoje quem a dispara é a borda.
        """
        for tecnico in self._projecoes.tecnicos():
            if tecnico.disponibilidade is Disponibilidade.AUSENTE:
                continue
            em_campo = (
                self._ordens.contar(
                    FiltroDeOrdens(tecnico_id=tecnico.id, status=StatusOS.EM_EXECUCAO)
                )
                > 0
            )
            nova = Disponibilidade.EM_ATENDIMENTO if em_campo else Disponibilidade.DISPONIVEL
            if nova is not tecnico.disponibilidade:
                tecnico.disponibilidade = nova
                self._usuarios.salvar(tecnico)
