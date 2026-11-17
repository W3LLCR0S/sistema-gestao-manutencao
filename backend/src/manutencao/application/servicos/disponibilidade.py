"""Disponibilidade dos técnicos: consulta derivada e ajuste manual da ausência.

**Derivada (D-05, DLT-05).** A disponibilidade de atendimento sai das OS a cada consulta: uma OS
``Em Execução`` caracteriza atendimento, ``Aguardando Peça`` não, e a **ausência manual** prevalece.
Não há rotina de atualização nem processo em segundo plano: a rotina
``atualizar_disponibilidades`` do legado (AUD-13) deixou de existir. O ajuste manual
(``alterar_disponibilidade``; DLT-15: a própria ou, com ``gerir_usuarios``, a de outro) grava só o
valor manual, de onde vem a ausência.
"""

from manutencao.application.dto import DisponibilidadeDoTecnico
from manutencao.application.portas.repositorios import UsuarioRepository
from manutencao.application.servicos.comum import carregar_ator, exigir_encontrado
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
        """Ajuste **manual** da disponibilidade de ``usuario_id`` (DLT-15).

        * O usuário altera a **própria** disponibilidade, sem exigir permissão (como no legado).
        * Quem tem ``gerir_usuarios`` altera a de **outro** usuário.
        * Quem não tem essa permissão não altera a de terceiros: recusa por autorização, antes de
          procurar o alvo (DLT-16) e sem mutação.

        Trata de **quem** pode alterar o valor manual. A disponibilidade efetiva continua sendo a
        derivada das OS (``consultar``), com a ausência manual prevalecendo (D-05).
        """
        ator = carregar_ator(self._usuarios, ator_id)
        if usuario_id == ator.id:
            alvo = ator
        else:
            ator.exigir(Permissao.GERIR_USUARIOS)
            alvo = exigir_encontrado("Usuário", usuario_id, self._usuarios.obter(usuario_id))
        alvo.disponibilidade = valor
        self._usuarios.salvar(alvo)
        return alvo

    def alterar_minha_disponibilidade(self, ator_id: int, valor: Disponibilidade) -> Usuario:
        """Cada usuário ajusta a **própria** disponibilidade; não exige permissão (legado)."""
        return self.alterar_disponibilidade(ator_id, ator_id, valor)
