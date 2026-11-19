"""Servico: cada ação registrada no histórico de uma OS.

A lista de serviços de uma OS é o histórico sequencial (abertura, atribuição, diagnóstico, reparos,
mudanças de status, encerramento...). O registro é imutável. O instante é sempre fornecido por
quem chama (o legado lia o relógio do sistema, AUD-07) e é guardado em UTC (D-11): um instante sem
fuso é recusado. Não há texto de data nem ``__str__``: a apresentação não pertence ao domínio.
"""

from dataclasses import dataclass
from datetime import datetime

from manutencao.domain.enums import TipoServico
from manutencao.domain.peca_material import PecaMaterial
from manutencao.domain.tempo import garantir_utc
from manutencao.domain.usuario import Usuario


@dataclass(frozen=True)
class Servico:
    numero: int  # sequência dentro da OS (1, 2, 3...)
    tipo: TipoServico
    descricao: str
    responsavel: Usuario | None
    data: datetime
    horas: float = 0.0
    pecas: tuple[PecaMaterial, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "data", garantir_utc(self.data))  # normaliza para UTC (frozen)
