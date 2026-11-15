"""Classe Usuario: ID, nome e cargo (+ dados cadastrais e disponibilidade)."""

from __future__ import annotations

from models.cargo import Cargo
from models.enums import Disponibilidade
from models.excecoes import RegraNegocioError
from models.permissoes import Permissoes


class Usuario:
    def __init__(self, id: int, nome: str, cargo: Cargo, email: str = "", escala: str = "",
                 disponibilidade: Disponibilidade = Disponibilidade.DISPONIVEL):
        self.id = id
        self.nome = nome
        self.cargo = cargo
        self.email = email
        self.escala = escala
        self.disponibilidade = disponibilidade

    def __str__(self):
        return self.nome

    # ------------------------ permissões ------------------------
    def pode(self, acesso: str) -> bool:
        return self.cargo.permissoes.tem(acesso)

    def exigir(self, acesso: str) -> None:
        if not self.pode(acesso):
            raise RegraNegocioError(f"Sem permissão: {Permissoes.DESCRICOES.get(acesso, acesso)}.")

    @property
    def e_tecnico(self) -> bool:
        """Técnico = quem pode apontar reparos."""
        return self.pode("apontar_reparo")

    # ------------------------ persistência ------------------------
    def to_dict(self) -> dict:
        return {"id": self.id, "nome": self.nome, "cargo_id": self.cargo.id, "email": self.email,
                "escala": self.escala, "disponibilidade": self.disponibilidade.value}

    @classmethod
    def from_dict(cls, d: dict, cargos: dict[int, Cargo]) -> Usuario:
        return cls(d["id"], d["nome"], cargos[d["cargo_id"]], d.get("email", ""),
                   d.get("escala", ""), Disponibilidade(d["disponibilidade"]))
