"""Construtores de apoio dos testes de domínio (sem repositório, sem relógio do sistema)."""

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from manutencao.domain.cargo import Cargo
from manutencao.domain.enums import Criticidade, StatusOS
from manutencao.domain.equipamento import Equipamento
from manutencao.domain.ordem_servico import OrdemServico
from manutencao.domain.peca_material import PecaMaterial
from manutencao.domain.permissoes import Permissoes
from manutencao.domain.usuario import Usuario

INICIO = datetime(2026, 3, 10, 9, 0, tzinfo=UTC)


@dataclass
class Relogio:
    """Instante controlado pelo teste; cada ``proximo()`` avança um minuto."""

    agora: datetime = INICIO

    def proximo(self) -> datetime:
        self.agora += timedelta(minutes=1)
        return self.agora


def sem_acesso() -> Usuario:
    """Usuário cujo cargo não tem nenhuma permissão."""
    return Usuario(9, "Visitante", Cargo(9, "Sem acesso", Permissoes()))


@dataclass
class Mundo:
    """Os mesmos cargos, usuários e equipamentos da base inicial do legado."""

    gestor: Cargo = field(default_factory=lambda: Cargo(1, "Gestor", Permissoes.padrao_gestor()))
    tecnico: Cargo = field(default_factory=lambda: Cargo(2, "Técnico", Permissoes.padrao_tecnico()))
    relogio: Relogio = field(default_factory=Relogio)

    def __post_init__(self) -> None:
        self.ana = Usuario(1, "Ana Souza", self.gestor)
        self.bruno = Usuario(2, "Bruno Lima", self.tecnico)
        self.carla = Usuario(3, "Carla Mendes", self.tecnico)
        self.torno = Equipamento(1, "Torno CNC", "GL 240")
        self.compressor = Equipamento(2, "Compressor de Ar", "CSW 40")

    def quando(self) -> datetime:
        return self.relogio.proximo()

    # ------------------------------------------------------------- caminhos até cada estado
    def aberta(self, numero: int = 1) -> OrdemServico:
        return OrdemServico.abrir(
            numero, self.torno, "Torno parado", Criticidade.ALTA, self.carla, quando=self.quando()
        )

    def atribuida(self, tecnico: Usuario | None = None) -> OrdemServico:
        os_ = self.aberta()
        os_.atribuir(tecnico or self.bruno, self.ana, quando=self.quando())
        return os_

    def _apontar_troca_de_rolamento(self, os_: OrdemServico) -> None:
        pecas = [PecaMaterial("Rolamento", 2)]
        os_.apontar_reparo(self.bruno, 1.5, "Troca do rolamento", pecas, quando=self.quando())

    def em_execucao(self) -> OrdemServico:
        os_ = self.atribuida()
        self._apontar_troca_de_rolamento(os_)
        return os_

    def aguardando_peca(self) -> OrdemServico:
        os_ = self.em_execucao()
        os_.alterar_status(self.bruno, StatusOS.AGUARDANDO_PECA, quando=self.quando())
        return os_

    def reparo_finalizado(self, *, com_diagnostico: bool = True) -> OrdemServico:
        os_ = self.atribuida()
        if com_diagnostico:
            os_.registrar_diagnostico(
                self.bruno, "Rolamento gasto", "Falta de graxa", quando=self.quando()
            )
        self._apontar_troca_de_rolamento(os_)
        os_.alterar_status(self.bruno, StatusOS.REPARO_FINALIZADO, quando=self.quando())
        return os_

    def aguardando_aprovacao(self) -> OrdemServico:
        os_ = self.reparo_finalizado()
        os_.concluir_tecnicamente(self.bruno, "Funcionou sob carga", True, quando=self.quando())
        return os_

    def concluida(self) -> OrdemServico:
        os_ = self.aguardando_aprovacao()
        os_.aprovar(self.ana, quando=self.quando())
        return os_

    def cancelada(self, *, atribuida: bool = False) -> OrdemServico:
        os_ = self.atribuida() if atribuida else self.aberta()
        os_.cancelar(self.ana, "Chamado indevido", quando=self.quando())
        return os_

    def em_status(self, status: StatusOS) -> OrdemServico:
        """Uma OS no estado pedido, pelo caminho normal."""
        construtores: dict[StatusOS, Callable[[], OrdemServico]] = {
            StatusOS.ABERTA: self.aberta,
            StatusOS.ATRIBUIDA: self.atribuida,
            StatusOS.EM_EXECUCAO: self.em_execucao,
            StatusOS.AGUARDANDO_PECA: self.aguardando_peca,
            StatusOS.REPARO_FINALIZADO: self.reparo_finalizado,
            StatusOS.AGUARDANDO_APROVACAO: self.aguardando_aprovacao,
            StatusOS.CONCLUIDA: self.concluida,
            StatusOS.CANCELADA: self.cancelada,
        }
        os_ = construtores[status]()
        assert os_.status is status
        return os_


def instantaneo(os_: OrdemServico) -> tuple[object, ...]:
    """Tudo o que a OS expõe, para provar que uma recusa não alterou nada."""
    return (
        os_.numero,
        os_.status,
        os_.equipamento,
        os_.falha,
        os_.criticidade,
        os_.aberta_por,
        os_.tecnico_atribuido,
        os_.diagnostico,
        os_.causa_raiz,
        os_.horas_trabalhadas,
        os_.intervencoes_realizadas,
        os_.pecas_utilizadas,
        os_.data_abertura,
        os_.data_conclusao,
        os_.teste_funcional,
        os_.motivo_cancelamento,
        os_.servicos,
    )
