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
  mostra o instante normalizado em UTC no formato ``dd/mm/aaaa hh:mm`` (``traducao.texto_legado``).
  Não há conversão para ``America/Sao_Paulo``: isso é apresentação (Fase 04).

**Numeração.** O adaptador **não gera identificadores**: a entidade precisa de um número, mas quem
o decide é a sequência que o teste injeta (``numeracao``), a mesma política do repositório em
memória (DLT-10). A cadeia de decisão da numeração é coberta pelo adaptador dos serviços.

Operações cuja responsabilidade o domínio puro não tem (cadastro e identificadores, exclusão,
disponibilidade derivada, persistência) chamam ``diante_da_ausencia``; o teste decide, pelo
registro de ``aplicabilidade.py``, se pula (cenário registrado) ou falha (cenário não registrado).

As recusas são classificadas pelo **código** do erro de domínio (``traducao``), não pelo texto.
"""

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any, NoReturn, Protocol, TypeVar

from manutencao.domain.cargo import Cargo
from manutencao.domain.enums import Criticidade, Disponibilidade, Papel, StatusOS
from manutencao.domain.equipamento import Equipamento
from manutencao.domain.erros import DominioError
from manutencao.domain.ordem_servico import OrdemServico
from manutencao.domain.peca_material import PecaMaterial
from manutencao.domain.permissoes import Permissao, Permissoes
from manutencao.domain.usuario import Usuario
from tests.caracterizacao.aplicabilidade import Responsabilidade
from tests.caracterizacao.fachada import (
    CargoSnap,
    EquipamentoSnap,
    OsSnap,
    Peca,
    RelogioFixo,
    Resultado,
    UsuarioSnap,
)
from tests.caracterizacao.traducao import (
    RECUSA_POR_CODIGO,
    snap_cargo,
    snap_equipamento,
    snap_os,
    snap_usuario,
)

DiantedaAusencia = Callable[[Responsabilidade], NoReturn]
T = TypeVar("T")


class Numeracao(Protocol):
    """A política de identificadores (do repositório), não do adaptador."""

    def proximo(self) -> int: ...

    def registrar(self, identificador: int) -> None: ...


def _sem_ausencia(responsabilidade: Responsabilidade) -> NoReturn:
    raise NotImplementedError(f"O domínio puro não tem a responsabilidade '{responsabilidade}'.")


class AdaptadorDominio:
    """Implementa a ``Fachada`` de caracterização sobre ``manutencao.domain``."""

    def __init__(
        self,
        relogio: RelogioFixo | None = None,
        diante_da_ausencia: DiantedaAusencia = _sem_ausencia,
        *,
        numeracao: Numeracao,
    ) -> None:
        self.relogio = relogio or RelogioFixo()
        self._ausente = diante_da_ausencia
        self._numeracao = numeracao
        # A mesma base inicial do legado (``_popular_exemplo``), em memória.
        gestor = Cargo(1, "Gestor", Permissoes.padrao_gestor())
        tecnico = Cargo(2, "Técnico", Permissoes.padrao_tecnico())
        self._cargos = [gestor, tecnico]
        self._usuarios = [
            Usuario(
                1, "Ana Souza", gestor, "ana@empresa.com", "Seg-Sex 08h-17h", papel=Papel.GESTOR
            ),
            Usuario(
                2,
                "Bruno Lima",
                tecnico,
                "bruno@empresa.com",
                "Seg-Sex 07h-16h",
                papel=Papel.TECNICO,
            ),
            Usuario(
                3,
                "Carla Mendes",
                tecnico,
                "carla@empresa.com",
                "Seg-Sex 13h-22h",
                papel=Papel.TECNICO,
            ),
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
            # Consulta o próximo número, abre e só então inclui na base e consome o número: uma
            # abertura recusada não gasta número (CAR-04).
            os_ = OrdemServico.abrir(
                self._numeracao.proximo(),
                self._equipamento(equipamento),
                falha,
                Criticidade(criticidade),
                self._usuario(solicitante),
                quando=self._instante(),
            )
            self._ordens.append(os_)
            self._numeracao.registrar(os_.numero)
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

    def definir_disponibilidade(self, usuario: int, valor: str, *, solicitante: int) -> Resultado:
        """Como na tela do legado: atribuição direta ao atributo da entidade.

        O domínio puro não tem regra sobre quem altera a disponibilidade (a política é da camada de
        aplicação, DLT-15): o ``solicitante`` é informado, mas não consultado, como no legado.
        """
        self._usuario(usuario).disponibilidade = Disponibilidade(valor)
        return Resultado(True)

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

    def _carga(self, u: Usuario) -> int:
        """OS ativas atribuídas ao usuário (projeção só de leitura sobre as entidades)."""
        return sum(1 for o in self._ordens if o.esta_com(u) and not o.encerrada)

    def os(self, numero: int) -> OsSnap | None:
        achada = next((o for o in self._ordens if o.numero == numero), None)
        return None if achada is None else snap_os(achada)

    def todas_as_os(self) -> tuple[OsSnap, ...]:
        return tuple(snap_os(o) for o in self._ordens)

    def usuario(self, id: int) -> UsuarioSnap | None:
        achado = next((u for u in self._usuarios if u.id == id), None)
        return None if achado is None else snap_usuario(achado, self._carga(achado))

    def usuarios(self) -> tuple[UsuarioSnap, ...]:
        return tuple(snap_usuario(u, self._carga(u)) for u in self._usuarios)

    def tecnicos(self) -> tuple[int, ...]:
        return tuple(u.id for u in self._usuarios if u.atribuivel)

    def equipamento(self, id: int) -> EquipamentoSnap | None:
        achado = next((e for e in self._equipamentos if e.id == id), None)
        return None if achado is None else snap_equipamento(achado)

    def equipamentos(self) -> tuple[EquipamentoSnap, ...]:
        return tuple(snap_equipamento(e) for e in self._equipamentos)

    def ordens_do_equipamento(self, equipamento: int) -> tuple[int, ...]:
        alvo = self._equipamento(equipamento)
        return tuple(o.numero for o in self._ordens if o.equipamento == alvo)

    def cargos(self) -> tuple[CargoSnap, ...]:
        return tuple(snap_cargo(c) for c in self._cargos)

    # -------------------------------------------------------------------------------- persistência
    def salvar_e_recarregar(self) -> None:
        self._ausente(Responsabilidade.PERSISTENCIA)
