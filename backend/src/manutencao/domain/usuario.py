"""Usuário: identificação, papel, cargo (de onde vêm as permissões), situação e disponibilidade."""

from manutencao.domain.cargo import Cargo
from manutencao.domain.disponibilidade import exigir_disponibilidade_manual
from manutencao.domain.enums import Disponibilidade, Papel
from manutencao.domain.erros import CodigoErro, PermissaoNegadaError
from manutencao.domain.matricula import exigir_matricula_valida
from manutencao.domain.permissoes import Permissao


class Usuario:
    """Entidade identificada por ``id``.

    * **Papel** (D-02, DLT-01): ``Gestor`` ou ``Técnico``, explícito e obrigatório. Responde "quem
      é o usuário" (pode receber OS, aparece entre os técnicos, tem carga e disponibilidade) e **não
      depende de nenhuma permissão**: retirar ``apontar_reparo`` de um Técnico não o torna outro
      papel, e conceder uma permissão técnica a um Gestor não o torna Técnico.
    * **Permissões** vêm do cargo e respondem "o que o usuário pode executar".
    * **Ativo** (DLT-09): um usuário inativo não opera e não é atribuível; o histórico o preserva.
    * **Matrícula** (``AA999999``): identificador de login, gerado pelo sistema e **imutável**. Só é
      atribuída uma vez (``atribuir_matricula``, usada pelo cadastro e pelos repositórios); não há
      como alterá-la depois. ``None`` apenas num objeto ainda não cadastrado.
    * ``disponibilidade`` é o valor **manual** (a ausência); a efetiva é derivada das OS
      (``derivar_disponibilidade``, D-05).
    """

    def __init__(
        self,
        id: int,
        nome: str,
        cargo: Cargo,
        email: str = "",
        escala: str = "",
        disponibilidade: Disponibilidade = Disponibilidade.DISPONIVEL,
        *,
        papel: Papel,
        ativo: bool = True,
        matricula: str | None = None,
    ) -> None:
        self.id = id
        self.nome = nome
        self.cargo = cargo
        self.email = email
        self.escala = escala
        self.disponibilidade = disponibilidade
        self.papel = papel
        self.ativo = ativo
        self._matricula: str | None = None
        if matricula is not None:
            self.atribuir_matricula(matricula)

    @property
    def matricula(self) -> str | None:
        return self._matricula

    def atribuir_matricula(self, matricula: str) -> None:
        """Define a matrícula **uma única vez**. Repetir o mesmo valor é aceito; trocar, não."""
        valida = exigir_matricula_valida(matricula)
        if self._matricula is not None and self._matricula != valida:
            raise PermissaoNegadaError(
                CodigoErro.SEM_PERMISSAO, "A matrícula é imutável e não pode ser alterada."
            )
        self._matricula = valida

    def __eq__(self, outro: object) -> bool:
        if not isinstance(outro, Usuario):
            return NotImplemented
        return self.id == outro.id

    def __hash__(self) -> int:
        return hash(self.id)

    def __str__(self) -> str:
        return self.nome

    def pode(self, permissao: Permissao) -> bool:
        """Um usuário inativo não tem permissão efetiva alguma."""
        tem = self.cargo.permissoes.tem(permissao)  # valida o tipo mesmo para um usuário inativo
        return self.ativo and tem

    def exigir_ativo(self) -> None:
        if not self.ativo:
            raise PermissaoNegadaError(
                CodigoErro.USUARIO_INATIVO, f"{self.nome} está inativo e não pode operar."
            )

    def exigir(self, permissao: Permissao) -> None:
        """Recusa um usuário inativo e quem não tem a permissão (nesta ordem)."""
        self.exigir_ativo()
        if not self.cargo.permissoes.tem(permissao):
            raise PermissaoNegadaError(
                CodigoErro.SEM_PERMISSAO, f"Sem permissão: {permissao.descricao}."
            )

    @property
    def e_tecnico(self) -> bool:
        """Técnico = quem tem o **papel** Técnico (D-02); nenhuma permissão entra na conta."""
        return self.papel is Papel.TECNICO

    @property
    def e_gestor(self) -> bool:
        return self.papel is Papel.GESTOR

    @property
    def e_gestor_administrativo(self) -> bool:
        """Gestor **administrativamente apto** (REG-E-01): papel Gestor, ativo e com a permissão
        efetiva ``gerir_usuarios``. É esta condição, e não só o papel, que o sistema nunca pode
        perder em todos os usuários ao mesmo tempo."""
        return self.e_gestor and self.pode(Permissao.GERIR_USUARIOS)

    @property
    def atribuivel(self) -> bool:
        """Pode receber OS: papel Técnico e usuário ativo."""
        return self.e_tecnico and self.ativo

    def definir_disponibilidade_manual(self, valor: Disponibilidade) -> None:
        """Grava a disponibilidade **manual**: só ``Disponível`` ou ``Ausente`` (REG-E-06).
        ``Em atendimento`` é derivado das OS e recusado aqui, sem alterar o usuário."""
        exigir_disponibilidade_manual(valor)
        self.disponibilidade = Disponibilidade(valor)

    def desativar(self) -> None:
        self.ativo = False

    def reativar(self) -> None:
        self.ativo = True
