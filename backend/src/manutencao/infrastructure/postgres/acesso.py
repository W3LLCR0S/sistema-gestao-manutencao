"""Credenciais e sessões no PostgreSQL (portas ``CredencialRepository`` e ``SessaoRepository``).

Só traduzem entre linhas e valores: nenhuma regra mora aqui. Excluir um usuário apaga o acesso e as
sessões dele (``ON DELETE CASCADE``).
"""

from datetime import datetime
from typing import Any, cast

from sqlalchemy import CursorResult, delete, func

from manutencao.application.portas.autenticacao import Credencial, Sessao
from manutencao.domain.tempo import garantir_utc
from manutencao.infrastructure.postgres.banco import Banco
from manutencao.infrastructure.postgres.modelos import CredencialModelo, SessaoModelo


def _apagadas(resultado: object) -> int:
    """Linhas afetadas por um ``DELETE`` (o resultado de DML é um ``CursorResult``)."""
    return cast("CursorResult[Any]", resultado).rowcount


class CredenciaisNoBanco:
    def __init__(self, banco: Banco) -> None:
        self._banco = banco

    @staticmethod
    def _credencial(modelo: CredencialModelo) -> Credencial:
        return Credencial(modelo.usuario_id, modelo.senha_hash)

    def obter_por_usuario(self, usuario_id: int) -> Credencial | None:
        with self._banco.transacao() as sessao:
            modelo = sessao.get(CredencialModelo, usuario_id, populate_existing=True)
            return None if modelo is None else self._credencial(modelo)

    def salvar(self, credencial: Credencial) -> None:
        with self._banco.transacao() as sessao:
            modelo = sessao.get(CredencialModelo, credencial.usuario_id)
            if modelo is None:
                modelo = CredencialModelo(usuario_id=credencial.usuario_id)
                sessao.add(modelo)
            modelo.senha_hash = credencial.senha_hash
            modelo.atualizada_em = func.now()
            sessao.flush()

    def remover(self, usuario_id: int) -> None:
        with self._banco.transacao() as sessao:
            sessao.execute(
                delete(CredencialModelo).where(CredencialModelo.usuario_id == usuario_id)
            )


class SessoesNoBanco:
    def __init__(self, banco: Banco) -> None:
        self._banco = banco

    @staticmethod
    def _sessao(modelo: SessaoModelo) -> Sessao:
        return Sessao(
            modelo.id_hash,
            modelo.usuario_id,
            modelo.csrf,
            garantir_utc(modelo.criada_em),
            garantir_utc(modelo.expira_em),
        )

    def adicionar(self, sessao: Sessao) -> None:
        with self._banco.transacao() as s:
            s.add(
                SessaoModelo(
                    id_hash=sessao.id_hash,
                    usuario_id=sessao.usuario_id,
                    csrf=sessao.csrf,
                    criada_em=sessao.criada_em,
                    expira_em=sessao.expira_em,
                )
            )

    def obter(self, id_hash: str) -> Sessao | None:
        with self._banco.transacao() as s:
            modelo = s.get(SessaoModelo, id_hash, populate_existing=True)
            return None if modelo is None else self._sessao(modelo)

    def remover(self, id_hash: str) -> None:
        with self._banco.transacao() as s:
            s.execute(delete(SessaoModelo).where(SessaoModelo.id_hash == id_hash))

    def remover_do_usuario(self, usuario_id: int, *, exceto: str | None = None) -> int:
        with self._banco.transacao() as s:
            comando = delete(SessaoModelo).where(SessaoModelo.usuario_id == usuario_id)
            if exceto is not None:
                comando = comando.where(SessaoModelo.id_hash != exceto)
            return _apagadas(s.execute(comando))

    def remover_expiradas(self, agora: datetime) -> int:
        with self._banco.transacao() as s:
            return _apagadas(s.execute(delete(SessaoModelo).where(SessaoModelo.expira_em <= agora)))
