"""Classe PecaMaterial: peça ou material utilizado em um serviço da OS."""

from __future__ import annotations

from models.excecoes import RegraNegocioError


class PecaMaterial:
    def __init__(self, descricao: str, quantidade: float):
        if quantidade <= 0:
            raise RegraNegocioError("A quantidade deve ser maior que zero.")
        self.descricao = descricao
        self.quantidade = quantidade

    def __str__(self):
        return f"{self.quantidade:g}x {self.descricao}"

    def to_dict(self) -> dict:
        return {"descricao": self.descricao, "quantidade": self.quantidade}

    @classmethod
    def from_dict(cls, d: dict) -> PecaMaterial:
        return cls(d["descricao"], d["quantidade"])
