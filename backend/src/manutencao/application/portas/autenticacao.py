"""Portas da autenticação (D-01): credenciais, sessões, hash de senha e transação.

Nada aqui conhece cookie, HTTP, banco ou biblioteca de hash. Só **hashes** atravessam estas
portas: a senha em texto e o token de sessão em texto nunca são armazenados (o token é guardado
como ``sha256``; o texto só existe no cookie do navegador).
"""

from contextlib import AbstractContextManager
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, runtime_checkable

Instante = datetime  # o instante (com fuso, UTC) que o relógio da aplicação fornece


@dataclass(frozen=True)
class Credencial:
    """Como um usuário se identifica: ``login`` (único, em minúsculas) e o hash da senha."""

    usuario_id: int
    login: str
    senha_hash: str

    def __repr__(self) -> str:  # o hash não aparece em log nem em traceback
        return f"Credencial(usuario_id={self.usuario_id}, login={self.login!r}, senha_hash=***)"


@dataclass(frozen=True)
class Sessao:
    """Sessão iniciada. ``id_hash`` é o sha256 do token do cookie; ``csrf`` é o segredo que o
    cliente devolve no cabeçalho das operações que modificam dados."""

    id_hash: str
    usuario_id: int
    csrf: str
    criada_em: datetime
    expira_em: datetime

    def __repr__(self) -> str:
        return f"Sessao(usuario_id={self.usuario_id}, expira_em={self.expira_em!r})"


@runtime_checkable
class CredencialRepository(Protocol):
    """Credenciais de acesso. Uma por usuário; o ``login`` é único (sem diferenciar maiúsculas)."""

    def obter_por_login(self, login: str) -> Credencial | None: ...

    def obter_por_usuario(self, usuario_id: int) -> Credencial | None: ...

    def salvar(self, credencial: Credencial) -> None:
        """Cria ou substitui a credencial do usuário. ``RegraDeAplicacaoError`` (``login_em_uso``)
        se o login pertence a outro usuário."""
        ...

    def remover(self, usuario_id: int) -> None:
        """Remove a credencial do usuário, se houver (idempotente)."""
        ...


@runtime_checkable
class SessaoRepository(Protocol):
    """Sessões do servidor (persistentes; nunca um dicionário global em memória de processo)."""

    def adicionar(self, sessao: Sessao) -> None: ...

    def obter(self, id_hash: str) -> Sessao | None: ...

    def remover(self, id_hash: str) -> None:
        """Idempotente."""
        ...

    def remover_do_usuario(self, usuario_id: int, *, exceto: str | None = None) -> int:
        """Revoga as sessões do usuário (menos ``exceto``); devolve quantas foram removidas."""
        ...

    def remover_expiradas(self, agora: datetime) -> int:
        """Apaga as sessões vencidas; devolve quantas."""
        ...


class HasherDeSenha(Protocol):
    """Função de hash de senhas (Argon2id na infraestrutura)."""

    def gerar(self, senha: str) -> str: ...

    def verificar(self, senha_hash: str, senha: str) -> bool:
        """``True`` só se a senha confere; qualquer hash inválido é ``False`` (não levanta)."""
        ...

    def precisa_renovar(self, senha_hash: str) -> bool:
        """Se o hash usa parâmetros antigos e deve ser regerado no próximo login."""
        ...


class UnidadeDeTrabalho(Protocol):
    """Transação que envolve vários repositórios: tudo ou nada (``Banco.transacao``)."""

    def transacao(self) -> AbstractContextManager[object]: ...
