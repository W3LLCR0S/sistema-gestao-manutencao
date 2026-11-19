"""Limite simples de tentativas de login (proteção básica contra força bruta).

Em memória **de processo** (por isso vale por instância da API; ver docs/API.md): conta falhas por
chave (``ip|login``) numa janela deslizante e bloqueia por um período. Não guarda sessão nem
segredo. A chave inclui o IP para que um terceiro não bloqueie a conta de outra pessoa.
"""

import math
from datetime import timedelta

from manutencao.application.erros import MuitasTentativasError
from manutencao.application.portas.relogio import Relogio

MAXIMO_DE_CHAVES = 10_000


class LimitadorDeTentativas:
    def __init__(
        self,
        relogio: Relogio,
        *,
        maximo: int = 5,
        janela: timedelta = timedelta(minutes=15),
    ) -> None:
        self._relogio = relogio
        self._maximo = maximo
        self._janela = janela
        self._falhas: dict[str, list[float]] = {}

    def _recentes(self, chave: str) -> list[float]:
        corte = (self._relogio.agora() - self._janela).timestamp()
        recentes = [t for t in self._falhas.get(chave, []) if t > corte]
        if recentes:
            self._falhas[chave] = recentes
        else:
            self._falhas.pop(chave, None)
        return recentes

    def verificar(self, chave: str) -> None:
        """``MuitasTentativasError`` se a chave atingiu o limite dentro da janela."""
        recentes = self._recentes(chave)
        if len(recentes) >= self._maximo:
            liberado = recentes[0] + self._janela.total_seconds()
            faltam = math.ceil(liberado - self._relogio.agora().timestamp())
            raise MuitasTentativasError(max(faltam, 1))

    def registrar_falha(self, chave: str) -> None:
        if len(self._falhas) >= MAXIMO_DE_CHAVES:
            for antiga in list(self._falhas):
                self._recentes(antiga)
            if len(self._falhas) >= MAXIMO_DE_CHAVES:
                self._falhas.clear()  # prefere esquecer a crescer sem limite
        self._recentes(chave)
        self._falhas.setdefault(chave, []).append(self._relogio.agora().timestamp())

    def limpar(self, chave: str) -> None:
        self._falhas.pop(chave, None)
