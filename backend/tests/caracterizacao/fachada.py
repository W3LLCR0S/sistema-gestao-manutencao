"""Fachada comportamental da caracterização (ADR-0006, seção 3).

Define **o que** os cenários de caracterização podem fazer e observar, sem expor nenhuma entidade
interna. Os testes só falam com esta interface; quem a implementa (hoje o adaptador do legado em
``adaptador_legado.py``; no futuro, adaptadores do domínio e dos serviços novos) decide **como**.

Convenções:

* Atores e alvos são identificados por ``int`` (id de usuário, número de OS, id de equipamento).
* Operações que podem ser recusadas devolvem :class:`Resultado`; nunca levantam exceção de regra.
* Consultas devolvem *snapshots* imutáveis. Datas são as exibidas pelo legado (``dd/mm/aaaa hh:mm``,
  sem fuso); a D-11 as substituirá por instantes UTC, e esse é um delta registrado em ``deltas.py``.
* Uma recusa carrega uma :class:`Recusa` (categoria estável) **e** a mensagem original; os testes
  verificam a categoria e só usam a mensagem quando o texto em si é o comportamento observado.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Any, Protocol

# ---------------------------------------------------------------------------------------- recusas


class Recusa(StrEnum):
    """Categoria estável de uma recusa (o legado só tem uma exceção; ver AUD-14)."""

    SEM_PERMISSAO = "sem_permissao"
    ESTADO_INVALIDO = "estado_invalido"
    OS_ENCERRADA = "os_encerrada"
    NAO_RESPONSAVEL = "nao_responsavel"
    EQUIPAMENTO_INATIVO = "equipamento_inativo"
    NAO_E_TECNICO = "nao_e_tecnico"
    JA_ATRIBUIDA = "ja_atribuida"
    STATUS_NAO_PERMITIDO = "status_nao_permitido"
    JA_NESSE_STATUS = "ja_nesse_status"
    SEM_INTERVENCAO = "sem_intervencao"
    SEM_DIAGNOSTICO = "sem_diagnostico"
    HORAS_NEGATIVAS = "horas_negativas"
    QUANTIDADE_INVALIDA = "quantidade_invalida"
    EQUIPAMENTO_COM_OS = "equipamento_com_os"
    USUARIO_COM_HISTORICO = "usuario_com_historico"
    AUTOEXCLUSAO = "autoexclusao"
    DESCONHECIDA = "desconhecida"  # nenhuma regra conhecida: um teste que a vê deve falhar


@dataclass(frozen=True)
class Resultado:
    """Resultado de uma operação: aceita ou recusada (com categoria e mensagem)."""

    aceito: bool
    recusa: Recusa | None = None
    mensagem: str = ""
    valor: Any = None  # retorno da operação (ex.: número da OS criada), quando houver

    @property
    def recusado(self) -> bool:
        return not self.aceito


# --------------------------------------------------------------------------------------- snapshots


@dataclass(frozen=True)
class PecaSnap:
    descricao: str
    quantidade: float


@dataclass(frozen=True)
class ServicoSnap:
    """Um registro do histórico da OS."""

    numero: int
    tipo: str
    descricao: str
    responsavel_id: int | None
    data: str
    horas: float
    pecas: tuple[PecaSnap, ...]


@dataclass(frozen=True)
class OsSnap:
    numero: int
    status: str
    equipamento_id: int
    falha: str
    criticidade: str
    aberta_por_id: int | None
    tecnico_id: int | None
    diagnostico: str
    causa_raiz: str
    horas_trabalhadas: float
    intervencoes: tuple[str, ...]
    pecas: tuple[PecaSnap, ...]
    data_abertura: str
    data_conclusao: str | None
    teste_funcional: str
    motivo_cancelamento: str
    historico: tuple[ServicoSnap, ...]

    @property
    def tipos_do_historico(self) -> tuple[str, ...]:
        return tuple(s.tipo for s in self.historico)


@dataclass(frozen=True)
class UsuarioSnap:
    id: int
    nome: str
    cargo_id: int
    cargo: str
    email: str
    escala: str
    disponibilidade: str  # valor armazenado (não recalculado)
    carga: int  # OS ativas atribuídas


@dataclass(frozen=True)
class EquipamentoSnap:
    id: int
    nome: str
    modelo: str
    ativo: bool


@dataclass(frozen=True)
class CargoSnap:
    id: int
    nome: str
    permissoes: tuple[str, ...]  # nomes das permissões liberadas, na ordem do sistema


# ------------------------------------------------------------------------------------------ relógio


class RelogioFixo:
    """Instante controlado pelo teste (ADR-0007). Nunca altera o relógio do sistema operacional."""

    def __init__(self, inicio: datetime | None = None) -> None:
        self._agora = inicio or datetime(2026, 3, 10, 9, 0)  # o legado é ingênuo (sem fuso)

    def agora(self) -> datetime:
        return self._agora

    def definir(self, instante: datetime) -> None:
        self._agora = instante

    def avancar(self, **kwargs: float) -> None:
        self._agora += timedelta(**kwargs)


# ------------------------------------------------------------------------------------------ fachada


@dataclass(frozen=True)
class Peca:
    """Peça informada ao apontar um reparo."""

    descricao: str
    quantidade: float


class Fachada(Protocol):
    """Operações e consultas comportamentais. Implementada por cada adaptador."""

    relogio: RelogioFixo

    # -- ordens de serviço: abertura e administração
    def abrir_os(
        self, solicitante: int, equipamento: int, falha: str, criticidade: str
    ) -> Resultado: ...

    def atribuir(self, os: int, tecnico: int, gestor: int) -> Resultado: ...

    def aprovar(self, os: int, gestor: int) -> Resultado: ...

    def reprovar(self, os: int, gestor: int, motivo: str) -> Resultado: ...

    def cancelar(self, os: int, gestor: int, motivo: str) -> Resultado: ...

    def adicionar_observacao(self, os: int, usuario: int, texto: str) -> Resultado: ...

    # -- ordens de serviço: execução técnica
    def registrar_diagnostico(
        self, os: int, tecnico: int, parecer: str, causa: str
    ) -> Resultado: ...

    def apontar_reparo(
        self, os: int, tecnico: int, horas: float, intervencao: str, pecas: tuple[Peca, ...] = ()
    ) -> Resultado: ...

    def alterar_status(self, os: int, tecnico: int, status: str) -> Resultado: ...

    def concluir_tecnicamente(
        self, os: int, tecnico: int, teste: str, passou: bool
    ) -> Resultado: ...

    # -- disponibilidade
    def atualizar_disponibilidades(self) -> None: ...

    def definir_disponibilidade(self, usuario: int, valor: str) -> None: ...

    # -- cadastros
    def cadastrar_usuario(
        self, nome: str, cargo: int, email: str = "", escala: str = ""
    ) -> int: ...

    def editar_usuario(
        self,
        usuario: int,
        *,
        nome: str | None = None,
        email: str | None = None,
        escala: str | None = None,
        cargo: int | None = None,
    ) -> None: ...

    def remover_usuario(self, usuario: int, solicitante: int) -> Resultado: ...

    def cadastrar_equipamento(self, nome: str, modelo: str) -> int: ...

    def editar_equipamento(self, equipamento: int, *, nome: str, modelo: str) -> None: ...

    def inativar_equipamento(self, equipamento: int) -> None: ...

    def reativar_equipamento(self, equipamento: int) -> None: ...

    def remover_equipamento(self, equipamento: int) -> Resultado: ...

    def definir_permissoes_cargo(self, cargo: int, permissoes: tuple[str, ...]) -> None: ...

    # -- permissões
    def usuario_pode(self, usuario: int, permissao: str) -> bool: ...

    def exigir_permissao(self, usuario: int, permissao: str) -> Resultado: ...

    # -- consultas
    def os(self, numero: int) -> OsSnap | None: ...

    def todas_as_os(self) -> tuple[OsSnap, ...]: ...

    def usuario(self, id: int) -> UsuarioSnap | None: ...

    def usuarios(self) -> tuple[UsuarioSnap, ...]: ...

    def tecnicos(self) -> tuple[int, ...]: ...

    def equipamento(self, id: int) -> EquipamentoSnap | None: ...

    def equipamentos(self) -> tuple[EquipamentoSnap, ...]: ...

    def ordens_do_equipamento(self, equipamento: int) -> tuple[int, ...]: ...

    def cargos(self) -> tuple[CargoSnap, ...]: ...

    # -- persistência (o novo sistema pode implementar como no-op)
    def salvar_e_recarregar(self) -> None: ...
