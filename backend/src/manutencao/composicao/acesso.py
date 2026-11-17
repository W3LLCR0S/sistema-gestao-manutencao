"""Procedimentos **administrativos** de acesso (D-01): fora da API, na máquina do servidor.

* ``criar_gestor_inicial``: cria o primeiro Gestor com login e senha. Só roda se ainda não existe
  nenhum Gestor administrativamente apto **com acesso** (depois, o Gestor cria os demais pela API).
* ``definir_acesso``: cria ou redefine o acesso de um usuário existente (recuperação de senha sem
  e-mail: quem administra o servidor redefine) e revoga as sessões dele.

Nenhuma senha é lida de argumento, variável de ambiente ou arquivo; a linha de comando as pede ao
terminal (``getpass``) ou, para automação, à entrada padrão. Nenhuma credencial fixa existe no
código.
"""

from manutencao.application.portas.autenticacao import CredencialRepository, UnidadeDeTrabalho
from manutencao.application.servicos.autenticacao import ServicoDeAutenticacao, validar_senha
from manutencao.composicao.container import Container
from manutencao.domain.cargo import Cargo
from manutencao.domain.enums import Papel
from manutencao.domain.permissoes import Permissao, Permissoes
from manutencao.domain.usuario import Usuario


class GestorJaExisteError(Exception):
    """Já há um Gestor com acesso: o procedimento inicial não se aplica."""


class CargoDeGestaoAusenteError(Exception):
    """Não há um cargo de gestão utilizável para o gestor inicial."""


def _cargo_de_gestor(container: Container) -> Cargo:
    cargos = container.cargos
    existentes = cargos.listar()
    for cargo in existentes:
        if cargo.nome == "Gestor" and cargo.permissoes.tem(Permissao.GERIR_USUARIOS):
            return cargo
    if not existentes:
        gestor = Cargo(cargos.proximo_id(), "Gestor", Permissoes.padrao_gestor())
        cargos.adicionar(gestor)
        cargos.adicionar(Cargo(cargos.proximo_id(), "Técnico", Permissoes.padrao_tecnico()))
        return gestor
    raise CargoDeGestaoAusenteError(
        "O banco tem cargos, mas nenhum chamado 'Gestor' com a permissão gerir_usuarios; "
        "ajuste os cargos antes de criar o gestor inicial."
    )


def _ha_gestor_com_acesso(container: Container, credenciais: CredencialRepository) -> bool:
    return any(
        u.e_gestor_administrativo and credenciais.obter_por_usuario(u.id) is not None
        for u in container.usuarios.listar()
    )


def criar_gestor_inicial(
    container: Container,
    credenciais: CredencialRepository,
    autenticacao: ServicoDeAutenticacao,
    unidade: UnidadeDeTrabalho,
    *,
    nome: str,
    login: str,
    senha: str,
    email: str = "",
) -> Usuario:
    """Cria o primeiro Gestor (e os cargos padrão, se o banco ainda não tem cargos)."""
    if _ha_gestor_com_acesso(container, credenciais):
        raise GestorJaExisteError(
            "Já existe um Gestor com acesso. Use 'definir-acesso' para redefinir uma senha."
        )
    # Valida **antes** de criar e cria de forma atômica: nunca sobra um usuário sem acesso.
    normal = autenticacao.exigir_login_livre(login)
    validar_senha(senha, normal)
    if not nome.strip():
        raise ValueError("Informe o nome do gestor.")
    with unidade.transacao():
        cargo = _cargo_de_gestor(container)
        usuario = Usuario(
            container.usuarios.proximo_id(), nome.strip(), cargo, email, "", papel=Papel.GESTOR
        )
        container.usuarios.adicionar(usuario)
        autenticacao.definir_credencial_administrativa(usuario.id, login, senha)
    return usuario


def definir_acesso(
    autenticacao: ServicoDeAutenticacao, usuario_id: int, login: str, senha: str
) -> None:
    """Cria ou redefine login e senha de um usuário existente; revoga as sessões dele."""
    autenticacao.definir_credencial_administrativa(usuario_id, login, senha)
