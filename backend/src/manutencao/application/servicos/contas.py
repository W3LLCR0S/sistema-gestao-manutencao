"""Operações que unem **usuário e acesso** e por isso precisam ser atômicas (D-01).

``ServicoDeUsuarios`` cuida do cadastro e das regras de gestão; ``ServicoDeAutenticacao``, das
credenciais e sessões. Aqui ficam só as composições: cadastrar já com acesso, desativar revogando
as sessões e excluir removendo a credencial. Nenhuma regra é reimplementada: cada passo chama o
serviço dono da regra, dentro de uma transação (``UnidadeDeTrabalho``).
"""

from manutencao.application.erros import EntradaInvalidaError
from manutencao.application.portas.autenticacao import CredencialRepository, UnidadeDeTrabalho
from manutencao.application.portas.repositorios import UsuarioRepository
from manutencao.application.servicos.autenticacao import ServicoDeAutenticacao, validar_senha
from manutencao.application.servicos.comum import carregar_ator
from manutencao.application.servicos.usuarios import ServicoDeUsuarios
from manutencao.domain.enums import Papel
from manutencao.domain.permissoes import Permissao
from manutencao.domain.usuario import Usuario


class ServicoDeContas:
    def __init__(
        self,
        usuarios: UsuarioRepository,
        servico_usuarios: ServicoDeUsuarios,
        autenticacao: ServicoDeAutenticacao,
        credenciais: CredencialRepository,
        unidade: UnidadeDeTrabalho,
    ) -> None:
        self._usuarios = usuarios
        self._servico_usuarios = servico_usuarios
        self._autenticacao = autenticacao
        self._credenciais = credenciais
        self._unidade = unidade

    def cadastrar(
        self,
        ator_id: int,
        nome: str,
        cargo_id: int,
        email: str = "",
        escala: str = "",
        *,
        papel: Papel,
        login: str | None = None,
        senha: str | None = None,
    ) -> Usuario:
        """Cadastra o usuário e, se ``login`` e ``senha`` vierem, o acesso dele: tudo ou nada."""
        carregar_ator(self._usuarios, ator_id).exigir(Permissao.GERIR_USUARIOS)
        if (login is None) != (senha is None):
            raise EntradaInvalidaError("Informe login e senha juntos, ou nenhum dos dois.")
        if login is not None and senha is not None:
            normal = self._autenticacao.exigir_login_livre(login)
            validar_senha(senha, normal)
        with self._unidade.transacao():
            usuario = self._servico_usuarios.cadastrar(
                ator_id, nome, cargo_id, email, escala, papel=papel
            )
            if login is not None and senha is not None:
                self._autenticacao.definir_credencial_administrativa(usuario.id, login, senha)
        return usuario

    def desativar(self, ator_id: int, usuario_id: int) -> Usuario:
        """Desativa e **revoga as sessões** do usuário (a revogação também ocorre a cada
        requisição: um usuário inativo nunca autentica)."""
        with self._unidade.transacao():
            usuario = self._servico_usuarios.desativar(ator_id, usuario_id)
            self._autenticacao.revogar_sessoes(usuario_id)
        return usuario

    def excluir(self, ator_id: int, usuario_id: int) -> None:
        with self._unidade.transacao():
            self._servico_usuarios.excluir(ator_id, usuario_id)
            self._credenciais.remover(usuario_id)
            self._autenticacao.revogar_sessoes(usuario_id)
