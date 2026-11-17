"""Casos de uso de usuários, cargos e permissões (gestão).

Preservam as permissões efetivas do legado: tudo aqui exige ``gerir_usuarios`` (o menu e
``gerenciar_usuarios``/``gerenciar_cargos`` da CLI) e as proteções que só a interface aplicava
(AUD-09) passam a ser verificadas no caso de uso: não excluir a si mesmo, não excluir quem tem
histórico em OS e não remover do próprio cargo o acesso de gestão. A autorização é a primeira
verificação de cada caso de uso, antes de procurar o recurso (DLT-16); a autoproteção do gestor é
DLT-12, a exigência de ``gerir_usuarios`` nas consultas e na gestão, DLT-13 e DLT-14, e um ator
inexistente é ``NaoEncontradoError`` (DLT-17).

**Operação E.** O **papel** (Gestor ou Técnico) é explícito (D-02, DLT-01): informado no cadastro e
alterado só por ``alterar_papel``, restrito ao Gestor. Mudar o papel **não** reatribui OS (a
política para OS ativas não foi decidida). Usuários podem ser **desativados** sem perder o histórico
(DLT-09), nunca por si mesmos; a desativação também não reatribui OS. Nomes obrigatórios (DLT-08).
"""

from collections.abc import Iterable

from manutencao.application.erros import CodigoErroAplicacao, RegraDeAplicacaoError
from manutencao.application.portas.repositorios import (
    CargoRepository,
    OrdemServicoRepository,
    UsuarioRepository,
)
from manutencao.application.servicos.comum import carregar_ator, exigir_encontrado
from manutencao.domain.cargo import Cargo
from manutencao.domain.enums import Disponibilidade, Papel
from manutencao.domain.erros import CodigoErro, PermissaoNegadaError
from manutencao.domain.permissoes import Permissao
from manutencao.domain.usuario import Usuario
from manutencao.domain.validacao import exigir_texto


class ServicoDeUsuarios:
    """Cadastro e consulta de usuários, troca de cargo e permissões dos cargos."""

    def __init__(
        self,
        usuarios: UsuarioRepository,
        cargos: CargoRepository,
        ordens: OrdemServicoRepository,
    ) -> None:
        self._usuarios = usuarios
        self._cargos = cargos
        self._ordens = ordens

    def _gestor(self, ator_id: int) -> Usuario:
        ator = carregar_ator(self._usuarios, ator_id)
        ator.exigir(Permissao.GERIR_USUARIOS)
        return ator

    def _carregar(self, usuario_id: int) -> Usuario:
        return exigir_encontrado("Usuário", usuario_id, self._usuarios.obter(usuario_id))

    def _carregar_cargo(self, cargo_id: int) -> Cargo:
        return exigir_encontrado("Cargo", cargo_id, self._cargos.obter(cargo_id))

    # ------------------------------------------------------------------------------ consultas
    def consultar(self, ator_id: int, usuario_id: int) -> Usuario:
        self._gestor(ator_id)
        return self._carregar(usuario_id)

    def listar(self, ator_id: int) -> tuple[Usuario, ...]:
        self._gestor(ator_id)
        return self._usuarios.listar()

    def listar_cargos(self, ator_id: int) -> tuple[Cargo, ...]:
        self._gestor(ator_id)
        return self._cargos.listar()

    # ----------------------------------------------------------------------------------- gestão
    def cadastrar(
        self,
        ator_id: int,
        nome: str,
        cargo_id: int,
        email: str = "",
        escala: str = "",
        *,
        papel: Papel,
    ) -> Usuario:
        """Cadastra um usuário ativo e ``Disponível``, com o **papel informado** (D-02).

        O id vem da sequência do repositório. Uma recusa não consome identificador.
        """
        self._gestor(ator_id)
        cargo = self._carregar_cargo(cargo_id)
        exigir_texto(nome, "o nome")
        usuario = Usuario(self._usuarios.proximo_id(), nome, cargo, email, escala, papel=papel)
        self._usuarios.adicionar(usuario)
        return usuario

    def atualizar_dados(
        self,
        ator_id: int,
        usuario_id: int,
        *,
        nome: str | None = None,
        email: str | None = None,
        escala: str | None = None,
    ) -> Usuario:
        """Altera só os campos informados."""
        self._gestor(ator_id)
        usuario = self._carregar(usuario_id)
        if nome is not None:
            exigir_texto(nome, "o nome")
            usuario.nome = nome
        if email is not None:
            usuario.email = email
        if escala is not None:
            usuario.escala = escala
        self._usuarios.salvar(usuario)
        return usuario

    def alterar_cargo(self, ator_id: int, usuario_id: int, cargo_id: int) -> Usuario:
        """Troca o cargo (e, com ele, as permissões). Ninguém tira de si o acesso de gestão."""
        ator = self._gestor(ator_id)
        usuario = self._carregar(usuario_id)
        cargo = self._carregar_cargo(cargo_id)
        if ator.id == usuario.id and not cargo.permissoes.tem(Permissao.GERIR_USUARIOS):
            raise RegraDeAplicacaoError(
                CodigoErroAplicacao.AUTOREMOCAO_DE_ACESSO_DE_GESTAO,
                "Você não pode remover o próprio acesso de gestão.",
            )
        usuario.cargo = cargo
        self._usuarios.salvar(usuario)
        return usuario

    def alterar_papel(self, ator_id: int, usuario_id: int, papel: Papel) -> Usuario:
        """Muda o papel de um usuário: operação explícita, restrita ao Gestor (D-02).

        Exige o papel Gestor **e** a permissão ``gerir_usuarios``. Ninguém deixa de ser Gestor por
        conta própria (autoproteção, como na DLT-12). **Não** reatribui as OS do usuário: a política
        para OS ativas não foi decidida.
        """
        ator = self._gestor(ator_id)
        if not ator.e_gestor:
            raise PermissaoNegadaError(
                CodigoErro.SEM_PERMISSAO, "Apenas o gestor pode alterar o papel de um usuário."
            )
        usuario = self._carregar(usuario_id)
        if ator.id == usuario.id and papel is not Papel.GESTOR:
            raise RegraDeAplicacaoError(
                CodigoErroAplicacao.AUTOREMOCAO_DE_ACESSO_DE_GESTAO,
                "Você não pode deixar de ser gestor por conta própria.",
            )
        usuario.papel = papel
        self._usuarios.salvar(usuario)
        return usuario

    def desativar(self, ator_id: int, usuario_id: int) -> Usuario:
        """Desativa o usuário sem excluir o histórico (DLT-09). Idempotente.

        O usuário inativo não opera nem é atribuível. Ninguém desativa a si mesmo (preserva a
        autoproteção do gestor, DLT-12). As OS atribuídas a ele **não** são reatribuídas.
        """
        ator = self._gestor(ator_id)
        usuario = self._carregar(usuario_id)
        if usuario.id == ator.id:
            raise RegraDeAplicacaoError(
                CodigoErroAplicacao.AUTOREMOCAO_DE_ACESSO_DE_GESTAO,
                "Você não pode desativar o próprio usuário.",
            )
        usuario.desativar()
        self._usuarios.salvar(usuario)
        return usuario

    def reativar(self, ator_id: int, usuario_id: int) -> Usuario:
        self._gestor(ator_id)
        usuario = self._carregar(usuario_id)
        usuario.reativar()
        self._usuarios.salvar(usuario)
        return usuario

    def definir_disponibilidade(
        self, ator_id: int, usuario_id: int, disponibilidade: Disponibilidade
    ) -> Usuario:
        """O gestor ajusta a disponibilidade de um usuário (o próprio usuário usa
        ``ServicoDeDisponibilidade.alterar_minha_disponibilidade``)."""
        self._gestor(ator_id)
        usuario = self._carregar(usuario_id)
        usuario.disponibilidade = disponibilidade
        self._usuarios.salvar(usuario)
        return usuario

    def excluir(self, ator_id: int, usuario_id: int) -> None:
        """Exclui um usuário sem histórico, e nunca o próprio ator."""
        ator = self._gestor(ator_id)
        usuario = self._carregar(usuario_id)
        if usuario.id == ator.id:
            raise RegraDeAplicacaoError(
                CodigoErroAplicacao.AUTOEXCLUSAO, "Você não pode excluir o próprio usuário."
            )
        if self._ordens.usuario_tem_participacao(usuario.id):
            raise RegraDeAplicacaoError(
                CodigoErroAplicacao.USUARIO_COM_HISTORICO,
                "Usuário possui histórico em OS; não pode ser excluído.",
            )
        self._usuarios.remover(usuario.id)

    # ------------------------------------------------------------------------------- permissões
    def definir_permissoes_do_cargo(
        self, ator_id: int, cargo_id: int, permissoes: Iterable[Permissao]
    ) -> Cargo:
        """Liga só as permissões informadas (tudo ou nada). Um valor que não seja ``Permissao``
        é erro (DLT-11), e o gestor não tira de **seu próprio** cargo o acesso de gestão."""
        ator = self._gestor(ator_id)
        cargo = self._carregar_cargo(cargo_id)
        selecao = tuple(permissoes)
        cargo.permissoes.definir(selecao)  # recusa o que não for membro de Permissao
        if ator.cargo.id == cargo.id and not cargo.permissoes.tem(Permissao.GERIR_USUARIOS):
            raise RegraDeAplicacaoError(
                CodigoErroAplicacao.AUTOREMOCAO_DE_ACESSO_DE_GESTAO,
                "Você não pode remover do seu próprio cargo o acesso de gestão.",
            )
        self._cargos.salvar(cargo)
        return cargo
