"""Autenticação por login e senha com sessões do servidor (D-01).

* Senha: só o **hash** (Argon2id, porta ``HasherDeSenha``) é guardado; nunca é registrada nem
  devolvida.
* Sessão: token aleatório de 256 bits entregue ao navegador (cookie ``HttpOnly``); o servidor guarda
  só o ``sha256`` dele, com expiração absoluta e um segredo CSRF por sessão. Logout, desativação do
  usuário, troca ou redefinição de senha **revogam** sessões.
* Quem é o ator é decidido **aqui**, pela sessão. A borda nunca aceita um identificador do cliente.
* Login desconhecido, senha errada e usuário inativo produzem a **mesma** recusa e o mesmo trabalho
  de hash (sem enumeração de usuários por mensagem ou tempo).

A criação da primeira conta é um procedimento **administrativo** (``composicao.acesso``), não um
endpoint: não existe credencial fixa no código.
"""

import hashlib
import re
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta

from manutencao.application.erros import (
    CodigoErroAplicacao,
    CredenciaisInvalidasError,
    EntradaInvalidaError,
    NaoAutenticadoError,
    RegraDeAplicacaoError,
    SenhaAtualIncorretaError,
)
from manutencao.application.portas.autenticacao import (
    Credencial,
    CredencialRepository,
    HasherDeSenha,
    Sessao,
    SessaoRepository,
    UnidadeDeTrabalho,
)
from manutencao.application.portas.relogio import Relogio
from manutencao.application.portas.repositorios import UsuarioRepository
from manutencao.application.servicos.comum import carregar_ator, exigir_encontrado
from manutencao.domain.permissoes import Permissao
from manutencao.domain.usuario import Usuario

VALIDADE_PADRAO_EM_HORAS = 8
TAMANHO_MINIMO_DA_SENHA = 10
TAMANHO_MAXIMO_DA_SENHA = 128
_PADRAO_DE_LOGIN = r"[\w.@+\-]{3,100}"
# Senha só para gastar o mesmo tempo de hash quando o login não existe (não é uma credencial).
_SENHA_DE_ISCA = "isca-sem-conta-" + "x" * 16


@dataclass(frozen=True)
class SessaoIniciada:
    """Resultado do login: o ``token`` só existe aqui e no cookie; nunca é guardado em texto."""

    token: str
    sessao: Sessao
    usuario: Usuario

    def __repr__(self) -> str:
        return f"SessaoIniciada(usuario_id={self.usuario.id}, token=***)"


@dataclass(frozen=True)
class Autenticacao:
    """O resultado de autenticar uma requisição: quem é e qual é a sessão."""

    usuario: Usuario
    sessao: Sessao


def normalizar_login(login: str) -> str:
    return login.strip().casefold()


def validar_login(login: str) -> str:
    normal = normalizar_login(login)
    if not re.fullmatch(_PADRAO_DE_LOGIN, normal):
        raise EntradaInvalidaError(
            "O login deve ter de 3 a 100 caracteres (letras, números, '.', '@', '+', '-' ou '_')."
        )
    return normal


def validar_senha(senha: str, login: str = "") -> None:
    if len(senha) < TAMANHO_MINIMO_DA_SENHA:
        raise EntradaInvalidaError(
            f"A senha deve ter pelo menos {TAMANHO_MINIMO_DA_SENHA} caracteres."
        )
    if len(senha) > TAMANHO_MAXIMO_DA_SENHA:
        raise EntradaInvalidaError(
            f"A senha deve ter no máximo {TAMANHO_MAXIMO_DA_SENHA} caracteres."
        )
    if login and senha.casefold() == login.casefold():
        raise EntradaInvalidaError("A senha não pode ser igual ao login.")


def hash_do_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class ServicoDeAutenticacao:
    """Login, autenticação de requisições, logout, senhas e revogação de sessões."""

    def __init__(
        self,
        credenciais: CredencialRepository,
        sessoes: SessaoRepository,
        usuarios: UsuarioRepository,
        hasher: HasherDeSenha,
        relogio: Relogio,
        unidade: UnidadeDeTrabalho,
        *,
        validade: timedelta | None = None,
    ) -> None:
        self._credenciais = credenciais
        self._sessoes = sessoes
        self._usuarios = usuarios
        self._hasher = hasher
        self._relogio = relogio
        self._unidade = unidade
        self._validade = timedelta(hours=VALIDADE_PADRAO_EM_HORAS) if validade is None else validade
        self._hash_de_isca = hasher.gerar(_SENHA_DE_ISCA)

    @property
    def validade(self) -> timedelta:
        return self._validade

    # ------------------------------------------------------------------------------ sessões
    def login(self, login: str, senha: str) -> SessaoIniciada:
        """Abre uma sessão. Qualquer falha é ``CredenciaisInvalidasError`` (mensagem única)."""
        if not login.strip() or not senha or len(senha) > TAMANHO_MAXIMO_DA_SENHA:
            self._hasher.verificar(self._hash_de_isca, _SENHA_DE_ISCA)
            raise CredenciaisInvalidasError
        credencial = self._credenciais.obter_por_login(normalizar_login(login))
        alvo = credencial.senha_hash if credencial is not None else self._hash_de_isca
        confere = self._hasher.verificar(alvo, senha)
        usuario = self._usuarios.obter(credencial.usuario_id) if credencial is not None else None
        if credencial is None or not confere or usuario is None or not usuario.ativo:
            raise CredenciaisInvalidasError
        agora = self._relogio.agora()
        token = secrets.token_urlsafe(32)
        sessao = Sessao(
            id_hash=hash_do_token(token),
            usuario_id=usuario.id,
            csrf=secrets.token_urlsafe(32),
            criada_em=agora,
            expira_em=agora + self._validade,
        )
        with self._unidade.transacao():
            if self._hasher.precisa_renovar(credencial.senha_hash):
                self._credenciais.salvar(
                    Credencial(usuario.id, credencial.login, self._hasher.gerar(senha))
                )
            self._sessoes.remover_expiradas(agora)
            self._sessoes.adicionar(sessao)
        return SessaoIniciada(token, sessao, usuario)

    def autenticar(self, token: str | None) -> Autenticacao:
        """A sessão do token e o usuário **atual** (cargo e permissões lidos a cada requisição).

        Sessão ausente, inexistente ou expirada: ``NaoAutenticadoError``. Usuário excluído ou
        desativado: as sessões dele são revogadas e a resposta é a mesma.
        """
        if not token:
            raise NaoAutenticadoError
        sessao = self._sessoes.obter(hash_do_token(token))
        if sessao is None:
            raise NaoAutenticadoError
        if sessao.expira_em <= self._relogio.agora():
            self._sessoes.remover(sessao.id_hash)
            raise NaoAutenticadoError
        usuario = self._usuarios.obter(sessao.usuario_id)
        if usuario is None or not usuario.ativo:
            self._sessoes.remover_do_usuario(sessao.usuario_id)
            raise NaoAutenticadoError
        return Autenticacao(usuario, sessao)

    def logout(self, token: str | None) -> None:
        """Revoga a sessão do token (idempotente)."""
        if token:
            self._sessoes.remover(hash_do_token(token))

    def revogar_sessoes(self, usuario_id: int) -> int:
        return self._sessoes.remover_do_usuario(usuario_id)

    # ------------------------------------------------------------------------------ senhas
    def alterar_propria_senha(self, autenticacao: Autenticacao, atual: str, nova: str) -> None:
        """Troca a senha de quem está autenticado. Revoga as **outras** sessões do usuário."""
        usuario = autenticacao.usuario
        credencial = self._credenciais.obter_por_usuario(usuario.id)
        confere = self._hasher.verificar(
            credencial.senha_hash if credencial is not None else self._hash_de_isca, atual
        )
        if credencial is None or not confere:
            raise SenhaAtualIncorretaError
        validar_senha(nova, credencial.login)
        with self._unidade.transacao():
            self._credenciais.salvar(
                Credencial(usuario.id, credencial.login, self._hasher.gerar(nova))
            )
            self._sessoes.remover_do_usuario(usuario.id, exceto=autenticacao.sessao.id_hash)

    def definir_credencial(self, ator_id: int, usuario_id: int, login: str, senha: str) -> None:
        """O Gestor (``gerir_usuarios``) cria ou redefine o acesso de um usuário.

        Substitui senha e login e **revoga as sessões** do usuário. A recusa por permissão vem
        antes de procurar o alvo (como em todos os casos de uso).
        """
        carregar_ator(self._usuarios, ator_id).exigir(Permissao.GERIR_USUARIOS)
        exigir_encontrado("Usuário", usuario_id, self._usuarios.obter(usuario_id))
        self._gravar_credencial(usuario_id, login, senha)

    def definir_credencial_administrativa(self, usuario_id: int, login: str, senha: str) -> None:
        """Procedimento **administrativo** (linha de comando): sem ator. Nunca exposto pela API."""
        exigir_encontrado("Usuário", usuario_id, self._usuarios.obter(usuario_id))
        self._gravar_credencial(usuario_id, login, senha)

    def exigir_login_livre(self, login: str, *, usuario_id: int | None = None) -> str:
        """Valida o login e confirma que não pertence a outro usuário; devolve o login normal."""
        normal = validar_login(login)
        existente = self._credenciais.obter_por_login(normal)
        if existente is not None and existente.usuario_id != usuario_id:
            raise RegraDeAplicacaoError(
                CodigoErroAplicacao.LOGIN_EM_USO, "Esse login já está em uso."
            )
        return normal

    def _gravar_credencial(self, usuario_id: int, login: str, senha: str) -> None:
        normal = self.exigir_login_livre(login, usuario_id=usuario_id)
        validar_senha(senha, normal)
        senha_hash = self._hasher.gerar(senha)
        with self._unidade.transacao():
            self._credenciais.salvar(Credencial(usuario_id, normal, senha_hash))
            self._sessoes.remover_do_usuario(usuario_id)

    def login_do_usuario(self, usuario_id: int) -> str | None:
        credencial = self._credenciais.obter_por_usuario(usuario_id)
        return None if credencial is None else credencial.login

    def agora(self) -> datetime:
        return self._relogio.agora()
