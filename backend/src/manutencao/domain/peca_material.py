"""Peça ou material utilizado em um serviço da OS."""

from dataclasses import dataclass

from manutencao.domain.erros import CodigoErro, ViolacaoDeRegraError


@dataclass(frozen=True)
class PecaMaterial:
    """Valor imutável: descrição e quantidade (sempre maior que zero)."""

    descricao: str
    quantidade: float

    def __post_init__(self) -> None:
        if self.quantidade <= 0:
            raise ViolacaoDeRegraError(
                CodigoErro.QUANTIDADE_INVALIDA, "A quantidade deve ser maior que zero."
            )

    def __str__(self) -> str:
        return f"{self.quantidade:g}x {self.descricao}"
