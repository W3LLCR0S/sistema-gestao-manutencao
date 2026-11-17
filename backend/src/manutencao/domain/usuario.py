"""Usuário: identificação, cargo (de onde vêm as permissões) e disponibilidade."""

from manutencao.domain.cargo import Cargo
from manutencao.domain.enums import Disponibilidade
from manutencao.domain.erros import CodigoErro, PermissaoNegadaError
from manutencao.domain.permissoes import Permissao


class Usuario:
    """Entidade identificada por ``id``.

    As permissões vêm do cargo. Ser técnico continua significando ter a permissão
    ``apontar_reparo`` (comportamento do legado, AUD-20); o papel explícito é a D-02, da Operação E.
    """

    def __init__(
        self,
        id: int,
        nome: str,
        cargo: Cargo,
        email: str = "",
        escala: str = "",
        disponibilidade: Disponibilidade = Disponibilidade.DISPONIVEL,
    ) -> None:
        self.id = id
        self.nome = nome
        self.cargo = cargo
        self.email = email
        self.escala = escala
        self.disponibilidade = disponibilidade

    def __eq__(self, outro: object) -> bool:
        if not isinstance(outro, Usuario):
            return NotImplemented
        return self.id == outro.id

    def __hash__(self) -> int:
        return hash(self.id)

    def __str__(self) -> str:
        return self.nome

    def pode(self, permissao: Permissao) -> bool:
        return self.cargo.permissoes.tem(permissao)

    def exigir(self, permissao: Permissao) -> None:
        if not self.pode(permissao):
            raise PermissaoNegadaError(
                CodigoErro.SEM_PERMISSAO, f"Sem permissão: {permissao.descricao}."
            )

    @property
    def e_tecnico(self) -> bool:
        """Técnico = quem pode apontar reparos."""
        return self.pode(Permissao.APONTAR_REPARO)
