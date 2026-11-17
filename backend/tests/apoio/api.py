"""Apoio dos testes da API: aplicação montada, base inicial com acesso e cliente autenticado.

A senha abaixo é **só de teste** (vive apenas nesta suíte; nada igual existe na aplicação).
O hash usa parâmetros mínimos do Argon2id para acelerar a suíte; em execução real vale o padrão.
"""

from dataclasses import dataclass, field
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx2 import Response

from manutencao.api import ConfiguracaoDaApi, criar_app
from manutencao.composicao.aplicacao import Aplicacao
from manutencao.composicao.fabrica import semear_dados_de_exemplo
from manutencao.infrastructure.seguranca import HasherArgon2
from tests.apoio.ambiente import ANA, BRUNO, CARLA
from tests.apoio.relogio import RelogioFixo

PREFIXO = "/api/v1"
SENHA = "senha-de-teste-123"
LOGINS = {ANA: "ana", BRUNO: "bruno", CARLA: "carla"}
HASHER_RAPIDO = HasherArgon2(time_cost=1, memory_cost=8, parallelism=1)


def semear_com_acesso(aplicacao: Aplicacao) -> None:
    """Base do legado (cargos, 3 usuários, 3 equipamentos) e login/senha para os três usuários."""
    c = aplicacao.container
    semear_dados_de_exemplo(c.equipamentos, c.cargos, c.usuarios)
    for usuario_id, login in LOGINS.items():
        aplicacao.autenticacao.definir_credencial_administrativa(usuario_id, login, SENHA)


class ClienteLogado:
    """Um navegador com sessão: guarda o cookie (no ``TestClient``) e envia o CSRF nas escritas."""

    def __init__(self, http: TestClient, csrf: str) -> None:
        self.http = http
        self.csrf = csrf

    def _cabecalhos(self, extras: dict[str, str] | None) -> dict[str, str]:
        return {"X-CSRF-Token": self.csrf, **(extras or {})}

    def get(self, caminho: str, **kw: Any) -> Response:
        return self.http.get(PREFIXO + caminho, **kw)

    def post(self, caminho: str, json: Any = None, **kw: Any) -> Response:
        cab = self._cabecalhos(kw.pop("headers", None))
        return self.http.post(PREFIXO + caminho, json=json, headers=cab, **kw)

    def put(self, caminho: str, json: Any = None, **kw: Any) -> Response:
        cab = self._cabecalhos(kw.pop("headers", None))
        return self.http.put(PREFIXO + caminho, json=json, headers=cab, **kw)

    def patch(self, caminho: str, json: Any = None, **kw: Any) -> Response:
        cab = self._cabecalhos(kw.pop("headers", None))
        return self.http.patch(PREFIXO + caminho, json=json, headers=cab, **kw)

    def delete(self, caminho: str, **kw: Any) -> Response:
        cab = self._cabecalhos(kw.pop("headers", None))
        return self.http.delete(PREFIXO + caminho, headers=cab, **kw)


@dataclass
class Mundo:
    """A aplicação sob teste (em memória ou sobre PostgreSQL) e o relógio que a governa."""

    nome: str
    aplicacao: Aplicacao
    relogio: RelogioFixo
    configuracao: ConfiguracaoDaApi
    app: FastAPI
    _abertos: list[TestClient] = field(default_factory=list)

    def navegador(self) -> TestClient:
        """Um cliente HTTP novo e **sem** sessão (jarra de cookies própria)."""
        http = TestClient(self.app, raise_server_exceptions=False)
        self._abertos.append(http)
        return http

    def entrar(self, usuario_id: int, senha: str = SENHA) -> ClienteLogado:
        http = self.navegador()
        resposta = http.post(
            f"{PREFIXO}/auth/login", json={"login": LOGINS[usuario_id], "senha": senha}
        )
        assert resposta.status_code == 200, resposta.text
        return ClienteLogado(http, resposta.json()["csrf_token"])

    def fechar(self) -> None:
        for http in self._abertos:
            http.close()


def montar_mundo(nome: str, aplicacao: Aplicacao, relogio: RelogioFixo) -> Mundo:
    semear_com_acesso(aplicacao)
    cfg = aplicacao.contexto.configuracao
    return Mundo(nome, aplicacao, relogio, cfg, criar_app(aplicacao.contexto))
