"""Validações de entrada do domínio (DLT-08, AUD-12): campos obrigatórios e valores mínimos.

O legado só validava na interface (``ui/entrada.py``); o domínio aceitava textos vazios e zero
hora. Aqui a regra vale para qualquer interface. As funções **só verificam**: nunca alteram nem
normalizam o valor (o texto é guardado como foi informado), para que uma recusa não deixe nada pela
metade e o valor aceito seja idêntico ao do legado.
"""

import math

from manutencao.domain.erros import CodigoErro, ViolacaoDeRegraError


def exigir_texto(valor: str, rotulo: str) -> None:
    """Recusa texto vazio ou só com espaços. ``rotulo`` nomeia o campo (ex.: "a descrição da
    falha"), sem artigo fixo, para que a mensagem não dependa do gênero."""
    if not isinstance(valor, str) or not valor.strip():
        raise ViolacaoDeRegraError(CodigoErro.CAMPO_OBRIGATORIO, f"Campo obrigatório: {rotulo}.")


def exigir_horas_positivas(horas: float) -> None:
    """Horas negativas mantêm a recusa do legado; zero e valores não finitos passam a ser
    recusados (DLT-08)."""
    if horas < 0:
        raise ViolacaoDeRegraError(
            CodigoErro.HORAS_NEGATIVAS, "Horas trabalhadas não podem ser negativas."
        )
    if horas == 0 or not math.isfinite(horas):
        raise ViolacaoDeRegraError(
            CodigoErro.HORAS_NAO_POSITIVAS, "As horas trabalhadas devem ser maiores que zero."
        )
