"""Disponibilidade dos técnicos: consulta derivada e ajuste manual da ausência.

**Derivada (D-05, DLT-05).** A disponibilidade de atendimento sai das OS a cada consulta: uma OS
``Em Execução`` caracteriza atendimento, ``Aguardando Peça`` não, e a **ausência manual** prevalece.
Não há rotina de atualização nem processo em segundo plano: a rotina
``atualizar_disponibilidades`` do legado (AUD-13) deixou de existir. O ajuste manual
(``alterar_disponibilidade``; DLT-15: a própria ou, com ``gerir_usuarios``, a de outro) grava só o
valor manual, de onde vem a ausência, e só aceita ``Disponível`` e ``Ausente`` (REG-E-06).
"""

from manutencao.application.dto import DisponibilidadeDoTecnico
from manutencao.application.portas.repositorios import UsuarioRepository
from manutencao.application.servicos.comum import carregar_ator
from manutencao.application.servicos.politica_de_disponibilidade import (
    alterar_disponibilidade_manual,
)
from manutencao.application.servicos.projecoes import Projecoes
from manutencao.domain.enums import Disponibilidade
from manutencao.domain.permissoes import Permissao
from manutencao.domain.usuario import Usuario


class ServicoDeDisponibilidade:
    """Consulta de disponibilidade e carga; ajuste manual; rotina de atualização."""

    def __init__(self, usuarios: UsuarioRepository, projecoes: Projecoes) -> None:
        self._usuarios = usuarios
        self._projecoes = projecoes

    def consultar(
        self, ator_id: int, *, ordenar_por_carga: bool = False
    ) -> tuple[DisponibilidadeDoTecnico, ...]:
        """Escala, disponibilidade derivada e carga de cada técnico (``ver_disponibilidade``)."""
        carregar_ator(self._usuarios, ator_id).exigir(Permissao.VER_DISPONIBILIDADE)
        return self._projecoes.disponibilidade_dos_tecnicos(ordenar_por_carga=ordenar_por_carga)

    def alterar_disponibilidade(
        self, ator_id: int, usuario_id: int, valor: Disponibilidade
    ) -> Usuario:
        """Ajuste **manual** da disponibilidade de ``usuario_id`` (DLT-15, REG-E-06).

        Mesma política de ``ServicoDeUsuarios.definir_disponibilidade`` (ver
        ``politica_de_disponibilidade``): o usuário altera a **própria**; ``gerir_usuarios`` altera
        a de **outro**; sem essa permissão a recusa vem antes de procurar o alvo (DLT-16) e sem
        mutação; só ``Disponível`` e ``Ausente`` são aceitos (``Em atendimento`` é derivado).
        """
        return alterar_disponibilidade_manual(self._usuarios, ator_id, usuario_id, valor)

    def alterar_minha_disponibilidade(self, ator_id: int, valor: Disponibilidade) -> Usuario:
        """Cada usuário ajusta a **própria** disponibilidade; não exige permissão (legado)."""
        return self.alterar_disponibilidade(ator_id, ator_id, valor)
