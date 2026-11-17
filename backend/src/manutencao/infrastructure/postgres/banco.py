"""Conexão e transações (SQLAlchemy). Cada operação de repositório é **atômica**.

``Banco.transacao()`` abre uma sessão, confirma ao final e **desfaz tudo** se algo falhar. Se já
houver uma transação aberta no mesmo contexto, a chamada **participa dela** sem confirmar nem
desfazer por conta própria: assim um caso de uso que precisar gravar em mais de um repositório
pode envolver as chamadas num único ``with banco.transacao():`` e obter tudo-ou-nada.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar

from sqlalchemy import Engine, create_engine
from sqlalchemy.engine import URL
from sqlalchemy.orm import Session, sessionmaker


class Banco:
    """Engine, fábrica de sessões e controle de transação. Uma instância por aplicação/teste.

    Os instantes são ``timestamptz`` (o banco guarda o **momento**, não um texto): o fuso da sessão
    só muda como ele é devolvido, e o domínio normaliza todo instante para UTC (D-11).
    """

    def __init__(self, url: URL | str, *, echo: bool = False) -> None:
        self._engine: Engine = create_engine(
            url,
            echo=echo,
            pool_pre_ping=True,
        )
        self._sessoes: sessionmaker[Session] = sessionmaker(self._engine, expire_on_commit=False)
        self._atual: ContextVar[Session | None] = ContextVar("sessao_atual", default=None)

    @property
    def engine(self) -> Engine:
        return self._engine

    @contextmanager
    def transacao(self) -> Iterator[Session]:
        """Uma transação: confirma se o bloco terminar bem, desfaz se levantar qualquer erro."""
        existente = self._atual.get()
        if existente is not None:
            yield existente  # participa da transação externa; ela decide confirmar ou desfazer
            return
        with self._sessoes() as sessao:
            ficha = self._atual.set(sessao)
            try:
                yield sessao
                sessao.commit()
            except BaseException:
                sessao.rollback()
                raise
            finally:
                self._atual.reset(ficha)

    def encerrar(self) -> None:
        """Libera o pool de conexões."""
        self._engine.dispose()
