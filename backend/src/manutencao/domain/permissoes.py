"""Permissões tipadas (DLT-11; ADR-0003) e o conjunto de permissões de um cargo.

No legado, a permissão era um texto livre: um nome errado era negado em silêncio e nomes
desconhecidos eram ignorados ao definir as permissões de um cargo (AUD-03). Aqui cada permissão é
um membro de :class:`Permissao` e um valor que não seja membro é um erro detectável.

Os **nomes** (valores do enum), a **ordem** do sistema, as **descrições** e os **perfis padrão**
são exatamente os do legado: as permissões efetivas não mudam.
"""

from collections.abc import Iterable
from enum import StrEnum

from manutencao.domain.erros import CodigoErro, ViolacaoDeRegraError


class Permissao(StrEnum):
    """Um acesso do sistema. A ordem de declaração é a ordem do sistema (a mesma do legado)."""

    # Acessos compartilhados
    VER_EQUIPAMENTOS = "ver_equipamentos"
    VER_OS = "ver_os"
    ABRIR_OS = "abrir_os"
    VER_DISPONIBILIDADE = "ver_disponibilidade"
    REGISTRAR_APONTAMENTO = "registrar_apontamento"
    # Acessos de técnico
    DIAGNOSTICAR = "diagnosticar"
    APONTAR_REPARO = "apontar_reparo"
    ATUALIZAR_STATUS = "atualizar_status"
    CONCLUIR_OS = "concluir_os"
    # Acessos de gestor
    GERIR_EQUIPAMENTOS = "gerir_equipamentos"
    GERIR_USUARIOS = "gerir_usuarios"
    ATRIBUIR_OS = "atribuir_os"
    APROVAR_OS = "aprovar_os"

    @classmethod
    def de_nome(cls, nome: str) -> "Permissao":
        """Converte o nome textual (ex.: vindo de uma borda) em permissão; inválido é erro."""
        try:
            return cls(nome)
        except ValueError:
            raise ViolacaoDeRegraError(
                CodigoErro.PERMISSAO_INVALIDA, f"Permissão desconhecida: '{nome}'."
            ) from None

    @property
    def descricao(self) -> str:
        return _DESCRICOES[self]


_DESCRICOES: dict[Permissao, str] = {
    Permissao.VER_EQUIPAMENTOS: "Visualizar equipamentos",
    Permissao.VER_OS: "Consultar ordens de serviço",
    Permissao.ABRIR_OS: "Abrir chamados (OS)",
    Permissao.VER_DISPONIBILIDADE: "Consultar disponibilidade dos técnicos",
    Permissao.REGISTRAR_APONTAMENTO: "Incluir apontamentos no histórico",
    Permissao.DIAGNOSTICAR: "Registrar diagnóstico",
    Permissao.APONTAR_REPARO: "Registrar horas, intervenções e peças",
    Permissao.ATUALIZAR_STATUS: "Atualizar status operacional da OS",
    Permissao.CONCLUIR_OS: "Conclusão técnica da OS",
    Permissao.GERIR_EQUIPAMENTOS: "Cadastrar/editar/inativar/excluir equipamentos",
    Permissao.GERIR_USUARIOS: "Gerenciar usuários, cargos e permissões",
    Permissao.ATRIBUIR_OS: "Atribuir/reatribuir OS a técnicos",
    Permissao.APROVAR_OS: "Aprovar, cancelar e encerrar OS",
}

_COMUNS = (
    Permissao.VER_EQUIPAMENTOS,
    Permissao.VER_OS,
    Permissao.ABRIR_OS,
    Permissao.VER_DISPONIBILIDADE,
    Permissao.REGISTRAR_APONTAMENTO,
)


def _como_permissao(valor: object) -> Permissao:
    """Aceita só membros de :class:`Permissao`; um texto solto (mesmo correto) é recusado."""
    if not isinstance(valor, Permissao):
        raise ViolacaoDeRegraError(
            CodigoErro.PERMISSAO_INVALIDA,
            f"Permissão inválida: {valor!r}; use um membro de Permissao.",
        )
    return valor


class Permissoes:
    """Conjunto de permissões liberadas a um cargo."""

    def __init__(self, ativas: Iterable[Permissao] = ()) -> None:
        self._ativas: frozenset[Permissao] = frozenset()
        self.definir(ativas)

    def tem(self, permissao: Permissao) -> bool:
        return _como_permissao(permissao) in self._ativas

    def ativas(self) -> tuple[Permissao, ...]:
        """As permissões liberadas, na ordem do sistema."""
        return tuple(p for p in Permissao if p in self._ativas)

    def definir(self, permissoes: Iterable[Permissao]) -> None:
        """Liga apenas as permissões informadas e desliga as demais (tudo ou nada)."""
        self._ativas = frozenset(_como_permissao(p) for p in permissoes)

    @classmethod
    def padrao_tecnico(cls) -> "Permissoes":
        return cls(
            (
                *_COMUNS,
                Permissao.DIAGNOSTICAR,
                Permissao.APONTAR_REPARO,
                Permissao.ATUALIZAR_STATUS,
                Permissao.CONCLUIR_OS,
            )
        )

    @classmethod
    def padrao_gestor(cls) -> "Permissoes":
        return cls(
            (
                *_COMUNS,
                Permissao.GERIR_EQUIPAMENTOS,
                Permissao.GERIR_USUARIOS,
                Permissao.ATRIBUIR_OS,
                Permissao.APROVAR_OS,
            )
        )
