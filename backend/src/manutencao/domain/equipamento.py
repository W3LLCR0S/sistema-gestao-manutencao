"""Equipamento: item do inventário que recebe manutenção."""


class Equipamento:
    """Entidade identificada por ``id``. Equipamento inativo não recebe novas OS."""

    def __init__(self, id: int, nome: str, modelo: str, ativo: bool = True) -> None:
        self.id = id
        self.nome = nome
        self.modelo = modelo
        self.ativo = ativo

    def __eq__(self, outro: object) -> bool:
        if not isinstance(outro, Equipamento):
            return NotImplemented
        return self.id == outro.id

    def __hash__(self) -> int:
        return hash(self.id)

    def __str__(self) -> str:
        return f"{self.nome} ({self.modelo})"

    def inativar(self) -> None:
        self.ativo = False

    def reativar(self) -> None:
        self.ativo = True

    @property
    def situacao(self) -> str:
        return "Ativo" if self.ativo else "Inativo"
