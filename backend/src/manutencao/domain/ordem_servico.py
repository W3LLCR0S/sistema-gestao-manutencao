"""OrdemServico: a entidade central. Todas as regras do ciclo de vida ficam nos seus métodos.

Reproduz o comportamento do legado (``models/ordem_servico.py``), incluindo a **ordem das
verificações** de cada operação: permissão, depois responsável pela OS, depois estado e, por fim,
as validações de valores. Toda verificação ocorre antes de qualquer alteração, de modo que uma
recusa nunca deixa a OS (nem o histórico) pela metade.

Diferenças deliberadas, e só estas:

* **Instantes** (D-11, DLT-07): o legado lia o relógio dentro da entidade; aqui cada operação que
  registra algo recebe ``quando`` (palavra-chave obrigatória), com fuso, e as datas são ``datetime``
  em UTC. O instante é validado por :func:`garantir_utc` **depois** de todas as verificações
  funcionais e **antes** da primeira alteração: a precedência do legado se mantém (um instante
  inválido nunca mascara uma recusa funcional) e a recusa por instante também não deixa nada
  alterado. É a única recusa nova em relação ao legado.
* **Permissões tipadas** (DLT-11): :class:`Permissao` no lugar de texto.
* **Sem serialização** (``to_dict``/``from_dict``) e sem acesso a repositório.

Mudanças funcionais aprovadas na Operação E (ver ``backend/tests/caracterizacao/deltas.py``):

* **D-03 / DLT-02**: atribuir a técnico ``Ausente`` é recusado, salvo confirmação explícita
  (``confirmar_ausente``); o histórico registra que o técnico estava ausente.
* **D-04 / DLT-03, DLT-04**: observações só em OS ativa; registram Gestor, técnico responsável e
  quem abriu a OS. O autor da abertura não ganha capacidade técnica.
* **D-06 / DLT-06**: o diagnóstico é exigido antes de ``Reparo Finalizado``.
* **DLT-08**: campos obrigatórios e horas maiores que zero (``domain.validacao``).
* **DLT-09**: um usuário inativo não opera (``Usuario.exigir``) e não é atribuível.

A posse da OS continua exigida pelos métodos como no legado. Os novos requisitos são verificados
**depois** das verificações antigas e **antes** de qualquer alteração, de modo que uma recusa nunca
deixa a OS (nem o histórico) pela metade.
"""

from collections.abc import Sequence
from datetime import datetime

from manutencao.domain.enums import Criticidade, Disponibilidade, StatusOS, TipoServico
from manutencao.domain.equipamento import Equipamento
from manutencao.domain.erros import (
    CodigoErro,
    ConflitoDeEstadoError,
    PermissaoNegadaError,
    ViolacaoDeRegraError,
)
from manutencao.domain.peca_material import PecaMaterial
from manutencao.domain.permissoes import Permissao
from manutencao.domain.servico import Servico
from manutencao.domain.tempo import garantir_utc
from manutencao.domain.transicoes import (
    STATUS_ATENDIMENTO,
    STATUS_ORIGEM_TECNICO,
    STATUS_TECNICO,
    encerrada,
    transicao_permitida,
)
from manutencao.domain.usuario import Usuario
from manutencao.domain.validacao import exigir_horas_positivas, exigir_texto


class OrdemServico:
    """Entidade identificada por ``numero``. Nasce em ``Aberta`` com o registro de abertura."""

    def __init__(
        self,
        numero: int,
        equipamento: Equipamento,
        falha: str,
        criticidade: Criticidade,
        aberta_por: Usuario,
        data_abertura: datetime,
    ) -> None:
        self._numero = numero
        self._equipamento = equipamento
        self._falha = falha
        self._criticidade = criticidade
        self._aberta_por = aberta_por
        self._data_abertura = garantir_utc(data_abertura)
        self._status = StatusOS.ABERTA
        self._tecnico_atribuido: Usuario | None = None
        self._diagnostico = ""
        self._causa_raiz = ""
        self._horas_trabalhadas = 0.0
        self._intervencoes_realizadas: list[str] = []
        self._pecas_utilizadas: list[PecaMaterial] = []
        self._data_conclusao: datetime | None = None
        self._teste_funcional = ""
        self._motivo_cancelamento = ""
        self._servicos: list[Servico] = []

    # ======================== identidade e leitura ========================
    def __eq__(self, outro: object) -> bool:
        if not isinstance(outro, OrdemServico):
            return NotImplemented
        return self._numero == outro._numero

    def __hash__(self) -> int:
        return hash(self._numero)

    @property
    def numero(self) -> int:
        return self._numero

    @property
    def status(self) -> StatusOS:
        return self._status

    @property
    def equipamento(self) -> Equipamento:
        return self._equipamento

    @property
    def falha(self) -> str:
        return self._falha

    @property
    def criticidade(self) -> Criticidade:
        return self._criticidade

    @property
    def aberta_por(self) -> Usuario:
        return self._aberta_por

    @property
    def tecnico_atribuido(self) -> Usuario | None:
        return self._tecnico_atribuido

    @property
    def diagnostico(self) -> str:
        return self._diagnostico

    @property
    def causa_raiz(self) -> str:
        return self._causa_raiz

    @property
    def horas_trabalhadas(self) -> float:
        return self._horas_trabalhadas

    @property
    def intervencoes_realizadas(self) -> tuple[str, ...]:
        return tuple(self._intervencoes_realizadas)

    @property
    def pecas_utilizadas(self) -> tuple[PecaMaterial, ...]:
        return tuple(self._pecas_utilizadas)

    @property
    def data_abertura(self) -> datetime:
        return self._data_abertura

    @property
    def data_conclusao(self) -> datetime | None:
        return self._data_conclusao

    @property
    def teste_funcional(self) -> str:
        return self._teste_funcional

    @property
    def motivo_cancelamento(self) -> str:
        return self._motivo_cancelamento

    @property
    def servicos(self) -> tuple[Servico, ...]:
        """Histórico em ordem de inclusão, numerado de 1 a N."""
        return tuple(self._servicos)

    @property
    def encerrada(self) -> bool:
        return encerrada(self._status)

    def esta_com(self, tecnico: Usuario) -> bool:
        return self._tecnico_atribuido is not None and self._tecnico_atribuido == tecnico

    # ======================== auxiliares ========================
    def _registrar_servico(
        self,
        tipo: TipoServico,
        descricao: str,
        responsavel: Usuario,
        quando: datetime,
        horas: float = 0.0,
        pecas: tuple[PecaMaterial, ...] = (),
    ) -> None:
        self._servicos.append(
            Servico(len(self._servicos) + 1, tipo, descricao, responsavel, quando, horas, pecas)
        )

    def _mudar_status(self, novo: StatusOS, responsavel: Usuario, quando: datetime) -> None:
        # Invariante interna: toda mudança de status existe na tabela de transições.
        if not transicao_permitida(self._status, novo):
            raise ConflitoDeEstadoError(
                CodigoErro.ESTADO_INVALIDO, f"Operação não permitida com a OS em '{self._status}'."
            )
        self._registrar_servico(
            TipoServico.MUDANCA_STATUS, f"{self._status} → {novo}", responsavel, quando
        )
        self._status = novo

    def _exigir_status(self, *validos: StatusOS) -> None:
        if self._status not in validos:
            raise ConflitoDeEstadoError(
                CodigoErro.ESTADO_INVALIDO, f"Operação não permitida com a OS em '{self._status}'."
            )

    def _exigir_tecnico_da_os(self, tecnico: Usuario) -> None:
        if not self.esta_com(tecnico):
            raise PermissaoNegadaError(
                CodigoErro.NAO_RESPONSAVEL, "Esta OS não está atribuída a você."
            )

    # ======================== abertura (todos) ========================
    @classmethod
    def abrir(
        cls,
        numero: int,
        equipamento: Equipamento,
        falha: str,
        criticidade: Criticidade,
        usuario: Usuario,
        *,
        quando: datetime,
    ) -> "OrdemServico":
        usuario.exigir(Permissao.ABRIR_OS)
        if not equipamento.ativo:
            raise ViolacaoDeRegraError(
                CodigoErro.EQUIPAMENTO_INATIVO,
                "Não é possível abrir OS para equipamento inativo.",
            )
        exigir_texto(falha, "a descrição da falha")
        quando = garantir_utc(quando)
        os_ = cls(numero, equipamento, falha, criticidade, usuario, quando)
        os_._registrar_servico(TipoServico.ABERTURA, f"[{criticidade}] {falha}", usuario, quando)
        return os_

    def pode_registrar_observacao(self, usuario: Usuario) -> bool:
        """Quem pode observar uma OS ativa (D-04, DLT-04): o Gestor, o técnico responsável e quem
        a abriu. É vínculo com a OS; a permissão ``registrar_apontamento`` é exigida à parte."""
        return usuario.e_gestor or self.esta_com(usuario) or self._aberta_por == usuario

    def adicionar_apontamento(self, usuario: Usuario, texto: str, *, quando: datetime) -> None:
        """Observação da OS (D-04): comentário livre que **não altera o status**.

        Ordem: permissão, vínculo com a OS (quem não pode agir não aprende nada sobre o estado) e,
        por fim, o estado: uma OS Concluída ou Cancelada é imutável (DLT-03).
        """
        usuario.exigir(Permissao.REGISTRAR_APONTAMENTO)
        if not self.pode_registrar_observacao(usuario):
            raise PermissaoNegadaError(
                CodigoErro.SEM_VINCULO_COM_A_OS,
                "Só o gestor, o técnico responsável ou quem abriu a OS pode registrar observações.",
            )
        if self.encerrada:
            raise ConflitoDeEstadoError(CodigoErro.OS_ENCERRADA, "A OS já está encerrada.")
        quando = garantir_utc(quando)
        self._registrar_servico(TipoServico.APONTAMENTO, texto, usuario, quando)

    # ======================== técnico ========================
    def registrar_diagnostico(
        self, tecnico: Usuario, parecer: str, causa_raiz: str, *, quando: datetime
    ) -> None:
        tecnico.exigir(Permissao.DIAGNOSTICAR)
        self._exigir_tecnico_da_os(tecnico)
        self._exigir_status(*STATUS_ATENDIMENTO)
        exigir_texto(parecer, "o parecer técnico")
        exigir_texto(causa_raiz, "a causa-raiz")
        quando = garantir_utc(quando)
        self._diagnostico = parecer
        self._causa_raiz = causa_raiz
        self._registrar_servico(
            TipoServico.DIAGNOSTICO, f"{parecer} | Causa-raiz: {causa_raiz}", tecnico, quando
        )

    def apontar_reparo(
        self,
        tecnico: Usuario,
        horas: float,
        intervencao: str,
        pecas: Sequence[PecaMaterial],
        *,
        quando: datetime,
    ) -> None:
        tecnico.exigir(Permissao.APONTAR_REPARO)
        self._exigir_tecnico_da_os(tecnico)
        self._exigir_status(*STATUS_ATENDIMENTO)
        exigir_horas_positivas(horas)
        exigir_texto(intervencao, "a intervenção realizada")
        quando = garantir_utc(quando)
        if self._status == StatusOS.ATRIBUIDA:
            self._mudar_status(StatusOS.EM_EXECUCAO, tecnico, quando)
        self._horas_trabalhadas += horas
        self._intervencoes_realizadas.append(intervencao)
        self._pecas_utilizadas.extend(pecas)
        self._registrar_servico(
            TipoServico.REPARO, intervencao, tecnico, quando, horas=horas, pecas=tuple(pecas)
        )

    def alterar_status(self, tecnico: Usuario, novo: StatusOS, *, quando: datetime) -> None:
        tecnico.exigir(Permissao.ATUALIZAR_STATUS)
        self._exigir_tecnico_da_os(tecnico)
        self._exigir_status(*STATUS_ORIGEM_TECNICO)
        if novo not in STATUS_TECNICO:
            raise ViolacaoDeRegraError(
                CodigoErro.STATUS_NAO_PERMITIDO, f"O técnico não pode definir o status '{novo}'."
            )
        if novo == self._status:
            raise ConflitoDeEstadoError(CodigoErro.JA_NESSE_STATUS, "A OS já está nesse status.")
        if novo == StatusOS.REPARO_FINALIZADO and not self._intervencoes_realizadas:
            raise ViolacaoDeRegraError(
                CodigoErro.SEM_INTERVENCAO,
                "Registre ao menos uma intervenção antes de finalizar o reparo.",
            )
        if novo == StatusOS.REPARO_FINALIZADO and not self._diagnostico:
            raise ViolacaoDeRegraError(
                CodigoErro.SEM_DIAGNOSTICO,
                "Registre o diagnóstico técnico antes de finalizar o reparo.",
            )
        self._mudar_status(novo, tecnico, garantir_utc(quando))

    def concluir_tecnicamente(
        self, tecnico: Usuario, teste: str, passou_no_teste: bool, *, quando: datetime
    ) -> bool:
        """Submete a OS para aprovação. Devolve ``False`` se o teste funcional falhou."""
        tecnico.exigir(Permissao.CONCLUIR_OS)
        self._exigir_tecnico_da_os(tecnico)
        self._exigir_status(StatusOS.REPARO_FINALIZADO)
        if not self._diagnostico:
            raise ViolacaoDeRegraError(
                CodigoErro.SEM_DIAGNOSTICO, "Registre o diagnóstico antes de concluir."
            )
        quando = garantir_utc(quando)
        if not passou_no_teste:
            self._registrar_servico(
                TipoServico.TESTE_FUNCIONAL, f"Reprovado: {teste}", tecnico, quando
            )
            return False
        self._teste_funcional = teste
        self._registrar_servico(
            TipoServico.CONCLUSAO_TECNICA, f"Teste aprovado: {teste}", tecnico, quando
        )
        self._mudar_status(StatusOS.AGUARDANDO_APROVACAO, tecnico, quando)
        return True

    # ======================== gestor ========================
    def atribuir(
        self,
        tecnico: Usuario,
        gestor: Usuario,
        *,
        quando: datetime,
        confirmar_ausente: bool = False,
    ) -> Usuario | None:
        """Atribui ou reatribui a OS. Devolve o técnico anterior (ou ``None``).

        Um técnico inativo nunca é atribuível (DLT-09). Atribuir a um técnico ``Ausente`` é recusado
        (conflito) a menos que ``confirmar_ausente`` seja verdadeiro (D-03, DLT-02); a confirmação
        só vale para quem tem a permissão de atribuir (verificada antes) e a atribuição feita assim
        fica registrada no histórico.
        """
        gestor.exigir(Permissao.ATRIBUIR_OS)
        if self.encerrada or self._status == StatusOS.AGUARDANDO_APROVACAO:
            raise ConflitoDeEstadoError(
                CodigoErro.ESTADO_INVALIDO, f"Não é possível atribuir uma OS em '{self._status}'."
            )
        if not tecnico.e_tecnico:
            raise ViolacaoDeRegraError(CodigoErro.NAO_E_TECNICO, f"{tecnico.nome} não é técnico.")
        if not tecnico.ativo:
            raise ViolacaoDeRegraError(
                CodigoErro.USUARIO_INATIVO, f"{tecnico.nome} está inativo e não pode receber OS."
            )
        if self.esta_com(tecnico):
            raise ConflitoDeEstadoError(
                CodigoErro.JA_ATRIBUIDA, "A OS já está atribuída a este técnico."
            )
        ausente = tecnico.disponibilidade is Disponibilidade.AUSENTE
        if ausente and not confirmar_ausente:
            raise ConflitoDeEstadoError(
                CodigoErro.TECNICO_AUSENTE,
                f"{tecnico.nome} está ausente; confirme a atribuição para prosseguir.",
            )
        quando = garantir_utc(quando)
        sufixo = " (técnico ausente; atribuição confirmada pelo gestor)" if ausente else ""
        anterior = self._tecnico_atribuido
        self._tecnico_atribuido = tecnico
        if anterior is not None:
            self._registrar_servico(
                TipoServico.REATRIBUICAO,
                f"{anterior.nome} → {tecnico.nome}{sufixo}",
                gestor,
                quando,
            )
        else:
            self._registrar_servico(
                TipoServico.ATRIBUICAO, f"Atribuída a {tecnico.nome}{sufixo}", gestor, quando
            )
        if self._status == StatusOS.ABERTA:
            self._mudar_status(StatusOS.ATRIBUIDA, gestor, quando)
        return anterior

    def aprovar(self, gestor: Usuario, *, quando: datetime) -> None:
        gestor.exigir(Permissao.APROVAR_OS)
        self._exigir_status(StatusOS.AGUARDANDO_APROVACAO)
        quando = garantir_utc(quando)
        self._data_conclusao = quando
        self._registrar_servico(
            TipoServico.ENCERRAMENTO, "Reparo validado e OS encerrada.", gestor, quando
        )
        self._mudar_status(StatusOS.CONCLUIDA, gestor, quando)

    def reprovar(self, gestor: Usuario, motivo: str, *, quando: datetime) -> None:
        gestor.exigir(Permissao.APROVAR_OS)
        self._exigir_status(StatusOS.AGUARDANDO_APROVACAO)
        exigir_texto(motivo, "o motivo da reprovação")
        quando = garantir_utc(quando)
        self._registrar_servico(
            TipoServico.REPROVACAO, f"Devolvida ao técnico: {motivo}", gestor, quando
        )
        self._mudar_status(StatusOS.EM_EXECUCAO, gestor, quando)

    def cancelar(self, gestor: Usuario, motivo: str, *, quando: datetime) -> None:
        gestor.exigir(Permissao.APROVAR_OS)
        if self.encerrada:
            raise ConflitoDeEstadoError(CodigoErro.OS_ENCERRADA, "A OS já está encerrada.")
        exigir_texto(motivo, "o motivo do cancelamento")
        quando = garantir_utc(quando)
        self._motivo_cancelamento = motivo
        self._data_conclusao = quando
        self._registrar_servico(TipoServico.CANCELAMENTO, motivo, gestor, quando)
        self._mudar_status(StatusOS.CANCELADA, gestor, quando)
