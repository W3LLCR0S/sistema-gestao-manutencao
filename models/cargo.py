"""Classe Cargo: nome + permissões."""

from __future__ import annotations

from models.permissoes import Permissoes


class Cargo:
    def __init__(self, id: int, nome: str, permissoes: Permissoes):
        self.id = id
        self.nome = nome
        self.permissoes = permissoes

    def __str__(self):
        return self.nome

    def to_dict(self) -> dict:
        return {"id": self.id, "nome": self.nome, "permissoes": self.permissoes.to_dict()}

    @classmethod
    def from_dict(cls, d: dict) -> Cargo:
        return cls(d["id"], d["nome"], Permissoes.from_dict(d["permissoes"]))
