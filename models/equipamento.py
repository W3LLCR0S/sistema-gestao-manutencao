"""Classe Equipamento: item do inventário que recebe manutenção."""

from __future__ import annotations


class Equipamento:
    def __init__(self, id: int, nome: str, modelo: str, ativo: bool = True):
        self.id = id
        self.nome = nome
        self.modelo = modelo
        self.ativo = ativo          # necessário para a função "inativar" do gestor

    def __str__(self):
        return f"{self.nome} ({self.modelo})"

    def inativar(self) -> None:
        self.ativo = False

    def reativar(self) -> None:
        self.ativo = True

    @property
    def situacao(self) -> str:
        return "Ativo" if self.ativo else "Inativo"

    def to_dict(self) -> dict:
        return {"id": self.id, "nome": self.nome, "modelo": self.modelo, "ativo": self.ativo}

    @classmethod
    def from_dict(cls, d: dict) -> Equipamento:
        return cls(d["id"], d["nome"], d["modelo"], d.get("ativo", True))
