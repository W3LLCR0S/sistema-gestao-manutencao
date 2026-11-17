"""Adaptador da fachada de caracterização sobre o **domínio puro** (Operação C6).

Executa os cenários de caracterização contra ``manutencao.domain``, sem importar o legado, sem
infraestrutura concreta e sem criar Repository nem camada de serviços (isso é a Operação D). O que
este módulo guarda é só a **base de teste em memória**: as entidades que o cenário usa, para que a
fachada possa se referir a elas por id.

Duas conversões explícitas, as únicas diferenças em relação ao adaptador do legado:

* **Relógio.** O ``RelogioFixo`` dos testes é ingênuo (o legado não tem fuso). Aqui ele é lido como
  UTC (``_instante``) e entregue às operações como ``datetime`` com fuso, que é o que o domínio
  exige (D-11).
* **Datas nos snapshots.** O domínio guarda instantes UTC; o snapshot compatível com o legado
  mostra o instante normalizado em UTC no formato ``dd/mm/aaaa hh:mm`` (``_texto_legado``). Não há
  conversão para ``America/Sao_Paulo``: isso é apresentação (Fase 04).

Operações cuja responsabilidade o domínio puro não tem (cadastro e identificadores, exclusão,
disponibilidade derivada, persistência) chamam ``diante_da_ausencia``; o teste decide, pelo
registro de ``aplicabilidade.py``, se pula (cenário registrado) ou falha (cenário não registrado).

As recusas são classificadas pelo **código** do erro de domínio, não pelo texto: a categoria de
cada recusa é a mesma do adaptador do legado, que a deriva da mensagem.
"""

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any, NoReturn, TypeVar

from manutencao.domain.cargo import Cargo
from manutencao.domain.enums import Criticidade, Disponibilidade, StatusOS
from manutencao.domain.equipamento import Equipamento
from manutencao.domain.erros import CodigoErro, DominioError
from manutencao.domain.ordem_servico import OrdemServico
from manutencao.domain.peca_material import PecaMaterial
from manutencao.domain.permissoes import Permissao, Permissoes
from manutencao.domain.servico import Servico
from manutencao.domain.usuario import Usuario
from tests.caracterizacao.aplicabilidade import Responsabilidade
from tests.caracterizacao.fachada import (
    CargoSnap,
    EquipamentoSnap,
    OsSnap,
    Peca,
    PecaSnap,
    Recusa,
    RelogioFixo,
    Resultado,
    ServicoSnap,
    UsuarioSnap,
)

RECUSA_POR_CODIGO: dict[CodigoErro, Recusa] = {
    CodigoErro.SEM_PERMISSAO: Recusa.SEM_PERMISSAO,
    CodigoErro.NAO_RESPONSAVEL: Recusa.NAO_RESPONSAVEL,
    CodigoErro.ESTADO_INVALIDO: Recusa.ESTADO_INVALIDO,
    CodigoErro.OS_ENCERRADA: Recusa.OS_ENCERRADA,
    CodigoErro.JA_ATRIBUIDA: Recusa.JA_ATRIBUIDA,
    CodigoErro.JA_NESSE_STATUS: Recusa.JA_NESSE_STATUS,
    CodigoErro.EQUIPAMENTO_INATIVO: Recusa.EQUIPAMENTO_INATIVO,
    CodigoErro.NAO_E_TECNICO: Recusa.NAO_E_TECNICO,
    CodigoErro.STATUS_NAO_PERMITIDO: Recusa.STATUS_NAO_PERMITIDO,
    CodigoErro.SEM_INTERVENCAO: Recusa.SEM_INTERVENCAO,
    CodigoErro.SEM_DIAGNOSTICO: Recusa.SEM_DIAGNOSTICO,
    CodigoErro.HORAS_NEGATIVAS: Recusa.HORAS_NEGATIVAS,
    CodigoErro.QUANTIDADE_INVALIDA: Recusa.QUANTIDADE_INVALIDA,
    # Sem equivalente no legado: se aparecer num cenário, o teste deve falhar.
    CodigoErro.PERMISSAO_INVALIDA: Recusa.DESCONHECIDA,
    CodigoErro.INSTANTE_INVALIDO: Recusa.DESCONHECIDA,
}

DiantedaAusencia = Callable[[Responsabilidade], NoReturn]
T = TypeVar("T")


def _texto_legado(instante: datetime) -> str:
    """Instante UTC no formato de texto do legado (``dd/mm/aaaa hh:mm``, sem fuso)."""
    return instante.astimezone(UTC).strftime("%d/%m/%Y %H:%M")


def _sem_ausencia(responsabilidade: Responsabilidade) -> NoReturn:
    raise NotImplementedError(f"O domínio puro não tem a responsabilidade '{responsabilidade}'.")


class AdaptadorDominio:
    """Implementa a ``Fachada`` de caracterização sobre ``manutencao.domain``."""

    def __init__(
        self,
        relogio: RelogioFixo | None = None,
        diante_da_ausencia: DiantedaAusencia = _sem_ausencia,
    ) -> None:
        self.relogio = relogio or RelogioFixo()
        self._ausente = diante_da_ausencia
        # A mesma base inicial do legado (``_popular_exemplo``), em memória.
        gestor = Cargo(1, "Gestor", Permissoes.padrao_gestor())
        tecnico = Cargo(2, "Técnico", Permissoes.padrao_tecnico())
        self._cargos = [gestor, tecnico]
        self._usuarios = [
            Usuario(1, "Ana Souza", gestor, "ana@empresa.com", "Seg-Sex 08h-17h"),
            Usuario(2, "Bruno Lima", tecnico, "bruno@empresa.com", "Seg-Sex 07h-16h"),
            Usuario(3, "Carla Mendes", tecnico, "carla@empresa.com", "Seg-Sex 13h-22h"),
        ]
        self._equipamentos = [
            Equipamento(1, "Torno CNC", "GL 240"),
            Equipamento(2, "Compressor de Ar", "CSW 40"),
            Equipamento(3, "Empilhadeira Elétrica", "PT 1650"),
        ]
        self._ordens: list[OrdemServico] = []

    # ------------------------------------------------------------------------------ utilidades
    def _instante(self) -> datetime:
        """O relógio fixo (ingênuo) lido como UTC: o instante que o domínio recebe."""
        agora = self.relogio.agora()
        return agora.replace(tzinfo=UTC) if agora.tzinfo is None else agora

    @staticmethod
    def _achar(itens: list[T], chave: Callable[[T], int], valor: int, nome: str) -> T:
        for item in itens:
            if chave(item) == valor:
                return item
        raise LookupError(f"{nome} {valor} inexistente na base de teste")

    def _usuario(self, id: int) -> Usuario:
        return self._achar(self._usuarios, lambda u: u.id, id, "Usuário")

    def _os(self, numero: int) -> OrdemServico:
        return self._achar(self._ordens, lambda o: o.numero, numero, "OS")

    def _equipamento(self, id: int) -> Equipamento:
        return self._achar(self._equipamentos, lambda e: e.id, id, "Equipamento")

    def _cargo(self, id: int) -> Cargo:
        return self._achar(self._cargos, lambda c: c.id, id, "Cargo")

    @staticmethod
    def _executar(acao: Callable[[], Any]) -> Resultado:
        try:
            valor = acao()
        except DominioError as erro:
            return Resultado(False, RECUSA_POR_CODIGO[erro.codigo], erro.mensagem)
        return Resultado(True, valor=valor)

    # --------------------------------------------------------------------- OS: abertura e gestão
    def abrir_os(
        self, solicitante: int, equipamento: int, falha: str, criticidade: str
    ) -> Resultado:
        def acao() -> int:
            # Como a tela do legado: numera (máximo + 1), abre e só então inclui na base de teste.
            numero = max((o.numero for o in self._ordens), default=0) + 1
            os_ = OrdemServico.abrir(
                numero,
                self._equipamento(equipamento),
                falha,
                Criticidade(criticidade),
                self._usuario(solicitante),
                quando=self._instante(),
            )
            self._ordens.append(os_)
            return os_.numero

        return self._executar(acao)

    def atribuir(self, os: int, tecnico: int, gestor: int) -> Resultado:
        def acao() -> int | None:
            anterior = self._os(os).atribuir(
                self._usuario(tecnico), self._usuario(gestor), quando=self._instante()
            )
            return None if anterior is None else anterior.id

        return self._executar(acao)

    def aprovar(self, os: int, gestor: int) -> Resultado:
        return self._executar(
            lambda: self._os(os).aprovar(self._usuario(gestor), quando=self._instante())
        )

    def reprovar(self, os: int, gestor: int, motivo: str) -> Resultado:
        return self._executar(
            lambda: self._os(os).reprovar(self._usuario(gestor), motivo, quando=self._instante())
        )

    def cancelar(self, os: int, gestor: int, motivo: str) -> Resultado:
        return self._executar(
            lambda: self._os(os).cancelar(self._usuario(gestor), motivo, quando=self._instante())
        )

    def adicionar_observacao(self, os: int, usuario: int, texto: str) -> Resultado:
        return self._executar(
            lambda: self._os(os).adicionar_apontamento(
                self._usuario(usuario), texto, quando=self._instante()
            )
        )

    # ------------------------------------------------------------------------ OS: execução técnica
    def registrar_diagnostico(self, os: int, tecnico: int, parecer: str, causa: str) -> Resultado:
        return self._executar(
            lambda: self._os(os).registrar_diagnostico(
                self._usuario(tecnico), parecer, causa, quando=self._instante()
            )
        )

    def apontar_reparo(
        self, os: int, tecnico: int, horas: float, intervencao: str, pecas: tuple[Peca, ...] = ()
    ) -> Resultado:
        def acao() -> None:
            # Como na tela: as peças são criadas (e validadas) antes de chamar o domínio.
            objetos = [PecaMaterial(p.descricao, p.quantidade) for p in pecas]
            self._os(os).apontar_reparo(
                self._usuario(tecnico), horas, intervencao, objetos, quando=self._instante()
            )

        return self._executar(acao)

    def alterar_status(self, os: int, tecnico: int, status: str) -> Resultado:
        return self._executar(
            lambda: self._os(os).alterar_status(
                self._usuario(tecnico), StatusOS(status), quando=self._instante()
            )
        )

    def concluir_tecnicamente(self, os: int, tecnico: int, teste: str, passou: bool) -> Resultado:
        return self._executar(
            lambda: self._os(os).concluir_tecnicamente(
                self._usuario(tecnico), teste, passou, quando=self._instante()
            )
        )

    # --- disponibilidade
    def atualizar_disponibilidades(self) -> None:
        self._ausente(Responsabilidade.DISPONIBILIDADE_DERIVADA)

    def definir_disponibilidade(self, usuario: int, valor: str) -> None:
        # Como na tela do legado: atribuição direta ao atributo da entidade.
        self._usuario(usuario).disponibilidade = Disponibilidade(valor)

    # ---------------------------------------------------------------------------------- cadastros
    def cadastrar_usuario(self, nome: str, cargo: int, email: str = "", escala: str = "") -> int:
        self._ausente(Responsabilidade.CADASTRO_E_IDENTIFICADORES)

    def editar_usuario(
        self,
        usuario: int,
        *,
        nome: str | None = None,
        email: str | None = None,
        escala: str | None = None,
        cargo: int | None = None,
    ) -> None:
        alvo = self._usuario(usuario)
        if nome is not None:
            alvo.nome = nome
        if email is not None:
            alvo.email = email
        if escala is not None:
            alvo.escala = escala
        if cargo is not None:
            alvo.cargo = self._cargo(cargo)

    def remover_usuario(self, usuario: int, solicitante: int) -> Resultado:
        self._ausente(Responsabilidade.REGRAS_DE_EXCLUSAO)

    def cadastrar_equipamento(self, nome: str, modelo: str) -> int:
        self._ausente(Responsabilidade.CADASTRO_E_IDENTIFICADORES)

    def editar_equipamento(self, equipamento: int, *, nome: str, modelo: str) -> None:
        alvo = self._equipamento(equipamento)
        alvo.nome = nome
        alvo.modelo = modelo

    def inativar_equipamento(self, equipamento: int) -> None:
        self._equipamento(equipamento).inativar()

    def reativar_equipamento(self, equipamento: int) -> None:
        self._equipamento(equipamento).reativar()

    def remover_equipamento(self, equipamento: int) -> Resultado:
        self._ausente(Responsabilidade.REGRAS_DE_EXCLUSAO)

    def definir_permissoes_cargo(self, cargo: int, permissoes: tuple[str, ...]) -> None:
        self._cargo(cargo).permissoes.definir(Permissao.de_nome(nome) for nome in permissoes)

    # --------------------------------------------------------------------------------- permissões
    def usuario_pode(self, usuario: int, permissao: str) -> bool:
        return self._usuario(usuario).pode(Permissao.de_nome(permissao))

    def exigir_permissao(self, usuario: int, permissao: str) -> Resultado:
        return self._executar(lambda: self._usuario(usuario).exigir(Permissao.de_nome(permissao)))

    # ------------------------------------------------------------------------------------ consultas
    def entidade(self, numero: int) -> OrdemServico:
        """A entidade de domínio por trás do snapshot (para testes que inspecionam o fuso)."""
        return self._os(numero)

    @staticmethod
    def _peca(p: PecaMaterial) -> PecaSnap:
        return PecaSnap(p.descricao, float(p.quantidade))

    def _snap_servico(self, s: Servico) -> ServicoSnap:
        return ServicoSnap(
            s.numero,
            s.tipo.value,
            s.descricao,
            None if s.responsavel is None else s.responsavel.id,
            _texto_legado(s.data),
            float(s.horas),
            tuple(self._peca(p) for p in s.pecas),
        )

    def _snap_os(self, o: OrdemServico) -> OsSnap:
        return OsSnap(
            numero=o.numero,
            status=o.status.value,
            equipamento_id=o.equipamento.id,
            falha=o.falha,
            criticidade=o.criticidade.value,
            aberta_por_id=o.aberta_por.id,
            tecnico_id=None if o.tecnico_atribuido is None else o.tecnico_atribuido.id,
            diagnostico=o.diagnostico,
            causa_raiz=o.causa_raiz,
            horas_trabalhadas=float(o.horas_trabalhadas),
            intervencoes=o.intervencoes_realizadas,
            pecas=tuple(self._peca(p) for p in o.pecas_utilizadas),
            data_abertura=_texto_legado(o.data_abertura),
            data_conclusao=None if o.data_conclusao is None else _texto_legado(o.data_conclusao),
            teste_funcional=o.teste_funcional,
            motivo_cancelamento=o.motivo_cancelamento,
            historico=tuple(self._snap_servico(s) for s in o.servicos),
        )

    def _carga(self, u: Usuario) -> int:
        """OS ativas atribuídas ao usuário (projeção só de leitura sobre as entidades)."""
        return sum(1 for o in self._ordens if o.esta_com(u) and not o.encerrada)

    def _snap_usuario(self, u: Usuario) -> UsuarioSnap:
        return UsuarioSnap(
            id=u.id,
            nome=u.nome,
            cargo_id=u.cargo.id,
            cargo=u.cargo.nome,
            email=u.email,
            escala=u.escala,
            disponibilidade=u.disponibilidade.value,
            carga=self._carga(u),
        )

    @staticmethod
    def _snap_equipamento(e: Equipamento) -> EquipamentoSnap:
        return EquipamentoSnap(e.id, e.nome, e.modelo, e.ativo)

    def os(self, numero: int) -> OsSnap | None:
        achada = next((o for o in self._ordens if o.numero == numero), None)
        return None if achada is None else self._snap_os(achada)

    def todas_as_os(self) -> tuple[OsSnap, ...]:
        return tuple(self._snap_os(o) for o in self._ordens)

    def usuario(self, id: int) -> UsuarioSnap | None:
        achado = next((u for u in self._usuarios if u.id == id), None)
        return None if achado is None else self._snap_usuario(achado)

    def usuarios(self) -> tuple[UsuarioSnap, ...]:
        return tuple(self._snap_usuario(u) for u in self._usuarios)

    def tecnicos(self) -> tuple[int, ...]:
        return tuple(u.id for u in self._usuarios if u.e_tecnico)

    def equipamento(self, id: int) -> EquipamentoSnap | None:
        achado = next((e for e in self._equipamentos if e.id == id), None)
        return None if achado is None else self._snap_equipamento(achado)

    def equipamentos(self) -> tuple[EquipamentoSnap, ...]:
        return tuple(self._snap_equipamento(e) for e in self._equipamentos)

    def ordens_do_equipamento(self, equipamento: int) -> tuple[int, ...]:
        alvo = self._equipamento(equipamento)
        return tuple(o.numero for o in self._ordens if o.equipamento == alvo)

    def cargos(self) -> tuple[CargoSnap, ...]:
        return tuple(
            CargoSnap(c.id, c.nome, tuple(p.value for p in c.permissoes.ativas()))
            for c in self._cargos
        )

    # -------------------------------------------------------------------------------- persistência
    def salvar_e_recarregar(self) -> None:
        self._ausente(Responsabilidade.PERSISTENCIA)
