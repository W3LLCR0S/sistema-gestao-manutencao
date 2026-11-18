"""Matrícula: identificador único de login do usuário, no formato ``AA999999``.

* Duas letras **maiúsculas** de A a Z seguidas de seis dígitos de 0 a 9 (oito caracteres).
* Gerada **só pelo sistema**, com fonte de aleatoriedade criptográfica (``secrets``); nunca é
  informada nem editada por quem opera o sistema.
* A unicidade é garantida em duas camadas: a geração consulta se o valor já existe e sorteia de
  novo em caso de colisão; a restrição ``UNIQUE`` do PostgreSQL é a garantia final contra corrida.
* A matrícula **não é segredo** (aparece em listagens para o Gestor) e **nunca** serve de senha.
"""

import re
import secrets
from collections.abc import Callable

from manutencao.domain.erros import CodigoErro, ViolacaoDeRegraError

PADRAO_DA_MATRICULA = r"[A-Z]{2}[0-9]{6}"
TAMANHO_DA_MATRICULA = 8
_LETRAS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
_DIGITOS = "0123456789"
TENTATIVAS_DE_GERACAO = 100

Sorteio = Callable[[str], str]  # recebe o alfabeto, devolve um caractere dele


def matricula_valida(valor: object) -> bool:
    """``True`` só para ``str`` que segue **exatamente** o padrão (sem espaços nem minúsculas)."""
    return isinstance(valor, str) and re.fullmatch(PADRAO_DA_MATRICULA, valor) is not None


def exigir_matricula_valida(valor: object) -> str:
    if not matricula_valida(valor):
        raise ViolacaoDeRegraError(
            CodigoErro.MATRICULA_INVALIDA,
            "Matrícula inválida: use duas letras maiúsculas e seis dígitos (AA999999).",
        )
    assert isinstance(valor, str)
    return valor


def sortear_caractere(alfabeto: str) -> str:
    """Um caractere do alfabeto, da fonte criptográfica do sistema operacional."""
    return secrets.choice(alfabeto)


def sortear_matricula(sorteio: Sorteio = sortear_caractere) -> str:
    """Uma matrícula aleatória válida (sem verificar unicidade)."""
    return "".join(sorteio(_LETRAS) for _ in range(2)) + "".join(
        sorteio(_DIGITOS) for _ in range(6)
    )


def gerar_matricula_unica(
    existe: Callable[[str], bool],
    *,
    sorteio: Sorteio = sortear_caractere,
    tentativas: int = TENTATIVAS_DE_GERACAO,
) -> str:
    """Sorteia até achar uma matrícula que ``existe`` diz estar livre (colisão: sorteia de novo).

    ``ViolacaoDeRegraError`` (``matricula_indisponivel``) se todas as tentativas colidirem.
    """
    for _ in range(tentativas):
        candidata = sortear_matricula(sorteio)
        if not existe(candidata):
            return candidata
    raise ViolacaoDeRegraError(
        CodigoErro.MATRICULA_INDISPONIVEL,
        "Não foi possível gerar uma matrícula livre; tente novamente.",
    )
