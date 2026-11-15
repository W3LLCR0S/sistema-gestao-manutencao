"""Classe Servico: cada serviço/ação registrado dentro de uma OS.

A lista de serviços de uma OS forma o histórico sequencial de intervenções
(abertura, atribuição, diagnóstico, reparos, mudanças de status, encerramento...).
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional, TYPE_CHECKING

from models.enums import TipoServico
from models.peca_material import PecaMaterial

if TYPE_CHECKING:
    from models.usuario import Usuario


class Servico:
    def __init__(self, numero: int, tipo: TipoServico, descricao: str,
                 responsavel: Optional[Usuario], data: Optional[str] = None,
                 horas: float = 0.0, pecas: Optional[list[PecaMaterial]] = None):
        self.numero = numero                  # sequência dentro da OS (1, 2, 3...)
        self.tipo = tipo
        self.descricao = descricao
        self.responsavel = responsavel
        self.data = data or datetime.now().strftime("%d/%m/%Y %H:%M")
        self.horas = horas
        self.pecas = pecas or []

    def __str__(self):
        extra = ""
        if self.horas:
            extra += f" ({self.horas:g} h)"
        if self.pecas:
            extra += " [peças: " + ", ".join(str(p) for p in self.pecas) + "]"
        nome = self.responsavel.nome if self.responsavel else "—"
        return f"#{self.numero:<3} {self.data} | {nome} | {self.tipo}: {self.descricao}{extra}"

    def to_dict(self) -> dict:
        return {
            "numero": self.numero,
            "tipo": self.tipo.value,
            "descricao": self.descricao,
            "responsavel_id": self.responsavel.id if self.responsavel else None,
            "data": self.data,
            "horas": self.horas,
            "pecas": [p.to_dict() for p in self.pecas],
        }

    @classmethod
    def from_dict(cls, d: dict, usuarios: dict[int, Usuario]) -> Servico:
        return cls(d["numero"], TipoServico(d["tipo"]), d["descricao"],
                   usuarios.get(d["responsavel_id"]), d["data"], d.get("horas", 0.0),
                   [PecaMaterial.from_dict(p) for p in d.get("pecas", [])])
