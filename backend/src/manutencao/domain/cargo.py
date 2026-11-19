"""Cargo: nome e permissões (compartilhadas por todos os usuários do cargo)."""

from manutencao.domain.permissoes import Permissoes


class Cargo:
    """Entidade identificada por ``id``."""

    def __init__(self, id: int, nome: str, permissoes: Permissoes) -> None:
        self.id = id
        self.nome = nome
        self.permissoes = permissoes

    def __eq__(self, outro: object) -> bool:
        if not isinstance(outro, Cargo):
            return NotImplemented
        return self.id == outro.id

    def __hash__(self) -> int:
        return hash(self.id)

    def __str__(self) -> str:
        return self.nome
