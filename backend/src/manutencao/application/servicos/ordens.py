"""Casos de uso do ciclo de vida da ordem de serviço.

Cada caso de uso faz três coisas: **carrega** o contexto (ator, OS, técnico, equipamento),
**delega** à entidade e **salva**. A permissão, a posse da OS (só o técnico responsável opera) e a
ordem das verificações continuam nos métodos de ``OrdemServico``, exatamente como no legado: nada é
reimplementado aqui, para não haver duas versões da mesma regra. O domínio recusa **antes** de
alterar qualquer coisa; como o serviço só salva depois que a entidade aceitou, uma recusa nunca
deixa a OS nem o histórico pela metade.

O instante vem da porta ``Relogio``, lido **uma vez** por caso de uso e entregue ao domínio.

**Autorização primeiro (DLT-16).** Todo caso de uso protegido exige a permissão **antes** de
procurar a OS, o equipamento ou o técnico (``_autorizar``); um ator inexistente é
``NaoEncontradoError`` (DLT-17). A posse da OS (técnico responsável) continua no domínio.

Fora do escopo desta operação (Operação E): papéis explícitos (D-02), recusa de atribuição a técnico
ausente (D-03), nova política de observações (D-04), diagnóstico obrigatório (D-06) e validações.
"""

from collections.abc import Sequence

from manutencao.application.dto import PecaInformada
from manutencao.application.portas.relogio import Relogio
from manutencao.application.portas.repositorios import (
    EquipamentoRepository,
    FiltroDeOrdens,
    OrdemServicoRepository,
    UsuarioRepository,
)
from manutencao.application.servicos.comum import carregar_ator, exigir_encontrado
from manutencao.domain.enums import Criticidade, StatusOS
from manutencao.domain.ordem_servico import OrdemServico
from manutencao.domain.peca_material import PecaMaterial
from manutencao.domain.permissoes import Permissao
from manutencao.domain.servico import Servico
from manutencao.domain.usuario import Usuario


class ServicoDeOrdens:
    """Abertura, consulta, execução técnica e administração das OS."""

    def __init__(
        self,
        ordens: OrdemServicoRepository,
        usuarios: UsuarioRepository,
        equipamentos: EquipamentoRepository,
        relogio: Relogio,
    ) -> None:
        self._ordens = ordens
        self._usuarios = usuarios
        self._equipamentos = equipamentos
        self._relogio = relogio

    def _carregar(self, numero: int) -> OrdemServico:
        return exigir_encontrado("Ordem de serviço", numero, self._ordens.obter(numero))

    def _autorizar(self, ator_id: int, permissao: Permissao) -> Usuario:
        """Primeira verificação funcional de todo caso de uso protegido (DLT-16).

        Carrega o ator (inexistente: ``NaoEncontradoError``, DLT-17) e exige a permissão **antes**
        de procurar a OS, o equipamento ou o técnico, para que a falta de permissão prevaleça
        sobre qualquer outro impedimento. É a mesma permissão que a entidade exige primeiro: o
        domínio segue verificando (nada é reimplementado), e a ordem interna das suas regras não
        muda. Só a posse da OS (técnico responsável) depende da OS e continua no domínio.
        """
        ator = carregar_ator(self._usuarios, ator_id)
        ator.exigir(permissao)
        return ator

    # ------------------------------------------------------------------------------ consultas
    def consultar(self, ator_id: int, numero: int) -> OrdemServico:
        carregar_ator(self._usuarios, ator_id).exigir(Permissao.VER_OS)
        return self._carregar(numero)

    def listar(
        self, ator_id: int, filtro: FiltroDeOrdens | None = None
    ) -> tuple[OrdemServico, ...]:
        carregar_ator(self._usuarios, ator_id).exigir(Permissao.VER_OS)
        return self._ordens.listar(filtro)

    def historico(self, ator_id: int, numero: int) -> tuple[Servico, ...]:
        """O histórico sequencial da OS (registros numerados de 1 a N, na ordem de inclusão)."""
        carregar_ator(self._usuarios, ator_id).exigir(Permissao.VER_OS)
        return self._carregar(numero).servicos

    # ----------------------------------------------------------------------- abertura (todos)
    def abrir(
        self, ator_id: int, equipamento_id: int, falha: str, criticidade: Criticidade
    ) -> OrdemServico:
        """Abre uma OS. Uma abertura recusada não consome número (CAR-04)."""
        ator = self._autorizar(ator_id, Permissao.ABRIR_OS)
        equipamento = exigir_encontrado(
            "Equipamento", equipamento_id, self._equipamentos.obter(equipamento_id)
        )
        ordem = OrdemServico.abrir(
            self._ordens.proximo_numero(),
            equipamento,
            falha,
            criticidade,
            ator,
            quando=self._relogio.agora(),
        )
        self._ordens.adicionar(ordem)
        return ordem

    def adicionar_apontamento(self, ator_id: int, numero: int, texto: str) -> None:
        ator = self._autorizar(ator_id, Permissao.REGISTRAR_APONTAMENTO)
        ordem = self._carregar(numero)
        ordem.adicionar_apontamento(ator, texto, quando=self._relogio.agora())
        self._ordens.salvar(ordem)

    # ----------------------------------------------------------------------------- técnico
    def registrar_diagnostico(
        self, ator_id: int, numero: int, parecer: str, causa_raiz: str
    ) -> None:
        tecnico = self._autorizar(ator_id, Permissao.DIAGNOSTICAR)
        ordem = self._carregar(numero)
        ordem.registrar_diagnostico(tecnico, parecer, causa_raiz, quando=self._relogio.agora())
        self._ordens.salvar(ordem)

    def apontar_reparo(
        self,
        ator_id: int,
        numero: int,
        horas: float,
        intervencao: str,
        pecas: Sequence[PecaInformada] = (),
    ) -> None:
        # A autorização vem primeiro (DLT-16); depois, como na tela do legado, as peças são criadas
        # (e a quantidade validada) antes da operação.
        tecnico = self._autorizar(ator_id, Permissao.APONTAR_REPARO)
        materiais = [PecaMaterial(p.descricao, p.quantidade) for p in pecas]
        ordem = self._carregar(numero)
        ordem.apontar_reparo(tecnico, horas, intervencao, materiais, quando=self._relogio.agora())
        self._ordens.salvar(ordem)

    def alterar_status(self, ator_id: int, numero: int, novo_status: StatusOS) -> None:
        tecnico = self._autorizar(ator_id, Permissao.ATUALIZAR_STATUS)
        ordem = self._carregar(numero)
        ordem.alterar_status(tecnico, novo_status, quando=self._relogio.agora())
        self._ordens.salvar(ordem)

    def concluir_tecnicamente(
        self, ator_id: int, numero: int, teste: str, passou_no_teste: bool
    ) -> bool:
        """Submete à aprovação. Teste reprovado devolve ``False``, mas **o registro do teste fica
        no histórico**, então a OS é salva nos dois casos."""
        tecnico = self._autorizar(ator_id, Permissao.CONCLUIR_OS)
        ordem = self._carregar(numero)
        submetida = ordem.concluir_tecnicamente(
            tecnico, teste, passou_no_teste, quando=self._relogio.agora()
        )
        self._ordens.salvar(ordem)
        return submetida

    # ------------------------------------------------------------------------------- gestor
    def atribuir(self, ator_id: int, numero: int, tecnico_id: int) -> Usuario | None:
        """Atribui ou reatribui. Devolve o técnico anterior (``None`` na primeira atribuição)."""
        gestor = self._autorizar(ator_id, Permissao.ATRIBUIR_OS)
        ordem = self._carregar(numero)
        tecnico = exigir_encontrado("Usuário", tecnico_id, self._usuarios.obter(tecnico_id))
        anterior = ordem.atribuir(tecnico, gestor, quando=self._relogio.agora())
        self._ordens.salvar(ordem)
        return anterior

    def aprovar(self, ator_id: int, numero: int) -> None:
        gestor = self._autorizar(ator_id, Permissao.APROVAR_OS)
        ordem = self._carregar(numero)
        ordem.aprovar(gestor, quando=self._relogio.agora())
        self._ordens.salvar(ordem)

    def reprovar(self, ator_id: int, numero: int, motivo: str) -> None:
        gestor = self._autorizar(ator_id, Permissao.APROVAR_OS)
        ordem = self._carregar(numero)
        ordem.reprovar(gestor, motivo, quando=self._relogio.agora())
        self._ordens.salvar(ordem)

    def cancelar(self, ator_id: int, numero: int, motivo: str) -> None:
        gestor = self._autorizar(ator_id, Permissao.APROVAR_OS)
        ordem = self._carregar(numero)
        ordem.cancelar(gestor, motivo, quando=self._relogio.agora())
        self._ordens.salvar(ordem)
