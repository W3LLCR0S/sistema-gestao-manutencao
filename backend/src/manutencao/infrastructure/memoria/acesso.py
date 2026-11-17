"""Credenciais e sessões em memória (testes; a demonstração usa o PostgreSQL)."""

from collections.abc import Iterator
from contextlib import contextmanager

from manutencao.application.erros import CodigoErroAplicacao, RegraDeAplicacaoError
from manutencao.application.portas.autenticacao import Credencial, Instante, Sessao


class CredenciaisEmMemoria:
    def __init__(self) -> None:
        self._por_usuario: dict[int, Credencial] = {}

    def obter_por_login(self, login: str) -> Credencial | None:
        alvo = login.casefold()
        return next((c for c in self._por_usuario.values() if c.login.casefold() == alvo), None)

    def obter_por_usuario(self, usuario_id: int) -> Credencial | None:
        return self._por_usuario.get(usuario_id)

    def salvar(self, credencial: Credencial) -> None:
        existente = self.obter_por_login(credencial.login)
        if existente is not None and existente.usuario_id != credencial.usuario_id:
            raise RegraDeAplicacaoError(
                CodigoErroAplicacao.LOGIN_EM_USO, "Esse login já está em uso."
            )
        self._por_usuario[credencial.usuario_id] = credencial

    def remover(self, usuario_id: int) -> None:
        self._por_usuario.pop(usuario_id, None)


class SessoesEmMemoria:
    def __init__(self) -> None:
        self._itens: dict[str, Sessao] = {}

    def adicionar(self, sessao: Sessao) -> None:
        self._itens[sessao.id_hash] = sessao

    def obter(self, id_hash: str) -> Sessao | None:
        return self._itens.get(id_hash)

    def remover(self, id_hash: str) -> None:
        self._itens.pop(id_hash, None)

    def remover_do_usuario(self, usuario_id: int, *, exceto: str | None = None) -> int:
        alvo = [h for h, s in self._itens.items() if s.usuario_id == usuario_id and h != exceto]
        for h in alvo:
            del self._itens[h]
        return len(alvo)

    def remover_expiradas(self, agora: Instante) -> int:
        alvo = [h for h, s in self._itens.items() if s.expira_em <= agora]
        for h in alvo:
            del self._itens[h]
        return len(alvo)


class SemTransacao:
    """``UnidadeDeTrabalho`` em memória: não há atomicidade (só testes; ver PostgreSQL)."""

    @contextmanager
    def transacao(self) -> Iterator[None]:
        yield
