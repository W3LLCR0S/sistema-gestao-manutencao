"""Peça ou material utilizado em um serviço da OS."""

from dataclasses import dataclass

from manutencao.domain.erros import CodigoErro, ViolacaoDeRegraError
from manutencao.domain.validacao import exigir_texto


@dataclass(frozen=True)
class PecaMaterial:
    """Valor imutável: descrição (texto não vazio, REG-E-05) e quantidade (maior que zero).

    A quantidade é verificada primeiro (ordem herdada do legado); depois, a descrição.
    """

    descricao: str
    quantidade: float

    def __post_init__(self) -> None:
        if self.quantidade <= 0:
            raise ViolacaoDeRegraError(
                CodigoErro.QUANTIDADE_INVALIDA, "A quantidade deve ser maior que zero."
            )
        exigir_texto(self.descricao, "a descrição da peça")

    def __str__(self) -> str:
        return f"{self.quantidade:g}x {self.descricao}"
