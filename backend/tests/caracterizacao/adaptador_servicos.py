"""Adaptador da fachada de caracterização sobre os **serviços de aplicação** (Operação D7).

Executa os cenários contra o contêiner da raiz de composição (``criar_container_em_memoria``:
serviços, repositórios em memória e relógio injetado), sem importar o legado nem a infraestrutura.
Cada operação da fachada é um caso de uso; as recusas vêm dos erros de domínio e de aplicação.

Decisões de projeto do adaptador:

* **Quem age.** Operações com ator na fachada (abrir, atribuir, aprovar,
  ``definir_disponibilidade``, ``remover_usuario``, as operações ``*_por``...) usam
  **exatamente** o ator informado: nunca o alvo, nunca um administrador. As operações **de
  preparação** do cenário que no legado não têm
  ator (``PREPARACOES_COMO_ADMINISTRADOR``: cadastrar, editar, inativar e reativar equipamento;
  cadastrar e editar usuário; remover equipamento) agem como ``ADMINISTRADOR`` (Ana, a gestora da
  base inicial) **pelos mesmos casos de uso e com a mesma verificação de permissão**: nada é
  concedido implicitamente. Um cenário que tira a permissão da Ana e depois prepara com ela falha,
  e a autorização em si é testada pelas operações ``*_por``, que recebem o solicitante (DLT-12 a
  DLT-17). Um teste impede que outro método passe a usar o administrador em silêncio.
* **Preparação de cenário.** ``definir_permissoes_cargo`` escreve direto no repositório de cargos,
  como os outros adaptadores escrevem direto nas entidades: é a forma de montar o cenário (inclusive
  tirar a permissão da própria Ana), não um caso de uso sob teste. O caso de uso real, com as suas
  proteções, é testado em ``tests/aplicacao``.
* **Observação.** As consultas da fachada (snapshots, ``tecnicos``, carga, OS por equipamento) leem
  pelas portas e pelas projeções de aplicação, sem ator, porque o cenário precisa observar o estado
  mesmo depois de alterar permissões.

O relógio fixo da fachada é ingênuo (o legado não tem fuso): é lido como UTC e entregue à porta
``Relogio`` com fuso (D-11). A numeração das OS e dos cadastros é a do repositório (DLT-10).
"""

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any, NoReturn

from manutencao.application.dto import PecaInformada
from manutencao.application.erros import (
    CodigoErroAplicacao,
    NaoEncontradoError,
    RegraDeAplicacaoError,
)
from manutencao.composicao.fabrica import criar_container_em_memoria
from manutencao.domain.enums import Criticidade, Disponibilidade, StatusOS
from manutencao.domain.erros import DominioError
from manutencao.domain.permissoes import Permissao
from tests.caracterizacao.aplicabilidade import Responsabilidade
from tests.caracterizacao.fachada import (
    CargoSnap,
    EquipamentoSnap,
    OsSnap,
    Peca,
    Recusa,
    RelogioFixo,
    Resultado,
    UsuarioSnap,
)
from tests.caracterizacao.traducao import (
    RECUSA_POR_CODIGO,
    snap_cargo,
    snap_equipamento,
    snap_os,
    snap_usuario,
)

ADMINISTRADOR = 1  # Ana Souza, a gestora da base inicial

# Os únicos métodos que agem como ADMINISTRADOR: preparação de cenário (ver a docstring do módulo).
PREPARACOES_COMO_ADMINISTRADOR = frozenset(
    {
        "cadastrar_usuario",
        "editar_usuario",
        "cadastrar_equipamento",
        "editar_equipamento",
        "inativar_equipamento",
        "reativar_equipamento",
        "remover_equipamento",
    }
)

RECUSA_POR_CODIGO_DE_APLICACAO: dict[CodigoErroAplicacao, Recusa] = {
    CodigoErroAplicacao.EQUIPAMENTO_COM_OS: Recusa.EQUIPAMENTO_COM_OS,
    CodigoErroAplicacao.USUARIO_COM_HISTORICO: Recusa.USUARIO_COM_HISTORICO,
    CodigoErroAplicacao.AUTOEXCLUSAO: Recusa.AUTOEXCLUSAO,
    # Sem equivalente na fachada do legado: se aparecer num cenário, o teste deve falhar.
    CodigoErroAplicacao.AUTOREMOCAO_DE_ACESSO_DE_GESTAO: Recusa.AUTOREMOCAO_DE_ACESSO_DE_GESTAO,
    CodigoErroAplicacao.NAO_ENCONTRADO: Recusa.NAO_ENCONTRADO,
    CodigoErroAplicacao.IDENTIFICADOR_JA_EMITIDO: Recusa.DESCONHECIDA,
}

DiantedaAusencia = Callable[[Responsabilidade], NoReturn]


def _sem_ausencia(responsabilidade: Responsabilidade) -> NoReturn:
    raise NotImplementedError(f"Os serviços não têm a responsabilidade '{responsabilidade}'.")


class _RelogioDaFachada:
    """Implementa a porta ``Relogio`` sobre o relógio fixo (ingênuo) da fachada, lido como UTC."""

    def __init__(self, relogio: RelogioFixo) -> None:
        self._relogio = relogio

    def agora(self) -> datetime:
        instante = self._relogio.agora()
        return instante.replace(tzinfo=UTC) if instante.tzinfo is None else instante


class AdaptadorServicos:
    """Implementa a ``Fachada`` de caracterização sobre os serviços de aplicação."""

    def __init__(
        self,
        relogio: RelogioFixo | None = None,
        diante_da_ausencia: DiantedaAusencia = _sem_ausencia,
    ) -> None:
        self.relogio = relogio or RelogioFixo()
        self._ausente = diante_da_ausencia
        self._c = criar_container_em_memoria(
            relogio=_RelogioDaFachada(self.relogio), com_dados_de_exemplo=True
        )

    @staticmethod
    def _executar(acao: Callable[[], Any]) -> Resultado:
        try:
            valor = acao()
        except DominioError as erro:
            return Resultado(False, RECUSA_POR_CODIGO[erro.codigo], erro.mensagem)
        except RegraDeAplicacaoError as erro:
            return Resultado(False, RECUSA_POR_CODIGO_DE_APLICACAO[erro.codigo], erro.mensagem)
        except NaoEncontradoError as erro:
            return Resultado(False, Recusa.NAO_ENCONTRADO, erro.mensagem)
        return Resultado(True, valor=valor)

    # --------------------------------------------------------------------- OS: abertura e gestão
    def abrir_os(
        self, solicitante: int, equipamento: int, falha: str, criticidade: str
    ) -> Resultado:
        return self._executar(
            lambda: (
                self._c.servico_ordens.abrir(
                    solicitante, equipamento, falha, Criticidade(criticidade)
                ).numero
            )
        )

    def atribuir(self, os: int, tecnico: int, gestor: int) -> Resultado:
        def acao() -> int | None:
            anterior = self._c.servico_ordens.atribuir(gestor, os, tecnico)
            return None if anterior is None else anterior.id

        return self._executar(acao)

    def aprovar(self, os: int, gestor: int) -> Resultado:
        return self._executar(lambda: self._c.servico_ordens.aprovar(gestor, os))

    def reprovar(self, os: int, gestor: int, motivo: str) -> Resultado:
        return self._executar(lambda: self._c.servico_ordens.reprovar(gestor, os, motivo))

    def cancelar(self, os: int, gestor: int, motivo: str) -> Resultado:
        return self._executar(lambda: self._c.servico_ordens.cancelar(gestor, os, motivo))

    def adicionar_observacao(self, os: int, usuario: int, texto: str) -> Resultado:
        return self._executar(
            lambda: self._c.servico_ordens.adicionar_apontamento(usuario, os, texto)
        )

    # ------------------------------------------------------------------------ OS: execução técnica
    def registrar_diagnostico(self, os: int, tecnico: int, parecer: str, causa: str) -> Resultado:
        return self._executar(
            lambda: self._c.servico_ordens.registrar_diagnostico(tecnico, os, parecer, causa)
        )

    def apontar_reparo(
        self, os: int, tecnico: int, horas: float, intervencao: str, pecas: tuple[Peca, ...] = ()
    ) -> Resultado:
        informadas = [PecaInformada(p.descricao, p.quantidade) for p in pecas]
        return self._executar(
            lambda: self._c.servico_ordens.apontar_reparo(
                tecnico, os, horas, intervencao, informadas
            )
        )

    def alterar_status(self, os: int, tecnico: int, status: str) -> Resultado:
        return self._executar(
            lambda: self._c.servico_ordens.alterar_status(tecnico, os, StatusOS(status))
        )

    def concluir_tecnicamente(self, os: int, tecnico: int, teste: str, passou: bool) -> Resultado:
        return self._executar(
            lambda: self._c.servico_ordens.concluir_tecnicamente(tecnico, os, teste, passou)
        )

    # --- disponibilidade
    def atualizar_disponibilidades(self) -> None:
        self._c.servico_disponibilidade.atualizar_disponibilidades()

    def definir_disponibilidade(self, usuario: int, valor: str, *, solicitante: int) -> Resultado:
        """Quem pede (``solicitante``), quem tem a disponibilidade alterada (``usuario``) e o valor
        são três informações distintas (DLT-15); o alvo nunca é o ator implícito."""
        return self._executar(
            lambda: self._c.servico_disponibilidade.alterar_disponibilidade(
                solicitante, usuario, Disponibilidade(valor)
            )
        )

    # ---------------------------------------------------------------------------------- cadastros
    def cadastrar_usuario(self, nome: str, cargo: int, email: str = "", escala: str = "") -> int:
        return self._c.servico_usuarios.cadastrar(ADMINISTRADOR, nome, cargo, email, escala).id

    def editar_usuario(
        self,
        usuario: int,
        *,
        nome: str | None = None,
        email: str | None = None,
        escala: str | None = None,
        cargo: int | None = None,
    ) -> None:
        servico = self._c.servico_usuarios
        servico.atualizar_dados(ADMINISTRADOR, usuario, nome=nome, email=email, escala=escala)
        if cargo is not None:
            servico.alterar_cargo(ADMINISTRADOR, usuario, cargo)

    def remover_usuario(self, usuario: int, solicitante: int) -> Resultado:
        return self._executar(lambda: self._c.servico_usuarios.excluir(solicitante, usuario))

    def cadastrar_equipamento(self, nome: str, modelo: str) -> int:
        return self._c.servico_equipamentos.cadastrar(ADMINISTRADOR, nome, modelo).id

    def editar_equipamento(self, equipamento: int, *, nome: str, modelo: str) -> None:
        self._c.servico_equipamentos.atualizar(ADMINISTRADOR, equipamento, nome, modelo)

    def inativar_equipamento(self, equipamento: int) -> None:
        self._c.servico_equipamentos.inativar(ADMINISTRADOR, equipamento)

    def reativar_equipamento(self, equipamento: int) -> None:
        self._c.servico_equipamentos.reativar(ADMINISTRADOR, equipamento)

    def remover_equipamento(self, equipamento: int) -> Resultado:
        return self._executar(
            lambda: self._c.servico_equipamentos.excluir(ADMINISTRADOR, equipamento)
        )

    def definir_permissoes_cargo(self, cargo: int, permissoes: tuple[str, ...]) -> None:
        """Preparação de cenário: direto no repositório (ver a docstring do módulo).

        Nunca substitui a operação testada: o caso de uso real (com permissão e autoproteção) é
        ``definir_permissoes_cargo_por``.
        """
        alvo = self._c.cargos.obter(cargo)
        assert alvo is not None, f"Cargo {cargo} inexistente na base de teste"
        alvo.permissoes.definir(Permissao.de_nome(nome) for nome in permissoes)
        self._c.cargos.salvar(alvo)

    # ------------------------------------------------------- operações com solicitante explícito
    def cadastrar_equipamento_por(self, solicitante: int, nome: str, modelo: str) -> Resultado:
        return self._executar(
            lambda: self._c.servico_equipamentos.cadastrar(solicitante, nome, modelo).id
        )

    def editar_equipamento_por(
        self, solicitante: int, equipamento: int, nome: str, modelo: str
    ) -> Resultado:
        return self._executar(
            lambda: (
                self._c.servico_equipamentos.atualizar(solicitante, equipamento, nome, modelo).id
            )
        )

    def inativar_equipamento_por(self, solicitante: int, equipamento: int) -> Resultado:
        return self._executar(
            lambda: self._c.servico_equipamentos.inativar(solicitante, equipamento).id
        )

    def reativar_equipamento_por(self, solicitante: int, equipamento: int) -> Resultado:
        return self._executar(
            lambda: self._c.servico_equipamentos.reativar(solicitante, equipamento).id
        )

    def remover_equipamento_por(self, solicitante: int, equipamento: int) -> Resultado:
        return self._executar(
            lambda: self._c.servico_equipamentos.excluir(solicitante, equipamento)
        )

    def cadastrar_usuario_por(self, solicitante: int, nome: str, cargo: int) -> Resultado:
        return self._executar(
            lambda: self._c.servico_usuarios.cadastrar(solicitante, nome, cargo).id
        )

    def editar_usuario_por(self, solicitante: int, usuario: int, nome: str) -> Resultado:
        return self._executar(
            lambda: self._c.servico_usuarios.atualizar_dados(solicitante, usuario, nome=nome).id
        )

    def alterar_cargo_por(self, solicitante: int, usuario: int, cargo: int) -> Resultado:
        return self._executar(
            lambda: self._c.servico_usuarios.alterar_cargo(solicitante, usuario, cargo).id
        )

    def definir_permissoes_cargo_por(
        self, solicitante: int, cargo: int, permissoes: tuple[str, ...]
    ) -> Resultado:
        return self._executar(
            lambda: (
                self._c.servico_usuarios.definir_permissoes_do_cargo(
                    solicitante, cargo, [Permissao.de_nome(nome) for nome in permissoes]
                ).id
            )
        )

    def consultar_equipamentos_por(self, solicitante: int) -> Resultado:
        return self._executar(
            lambda: tuple(
                snap_equipamento(e) for e in self._c.servico_equipamentos.listar(solicitante)
            )
        )

    def consultar_os_por(self, solicitante: int, numero: int) -> Resultado:
        return self._executar(
            lambda: snap_os(self._c.servico_ordens.consultar(solicitante, numero))
        )

    def listar_os_por(self, solicitante: int) -> Resultado:
        return self._executar(
            lambda: tuple(snap_os(o) for o in self._c.servico_ordens.listar(solicitante))
        )

    def consultar_disponibilidade_por(self, solicitante: int) -> Resultado:
        return self._executar(lambda: self._c.servico_disponibilidade.consultar(solicitante))

    def consultar_usuarios_por(self, solicitante: int) -> Resultado:
        return self._executar(
            lambda: tuple(
                snap_usuario(u, self._c.projecoes.carga_do_tecnico(u.id))
                for u in self._c.servico_usuarios.listar(solicitante)
            )
        )

    def listar_cargos_por(self, solicitante: int) -> Resultado:
        return self._executar(
            lambda: tuple(
                snap_cargo(c) for c in self._c.servico_usuarios.listar_cargos(solicitante)
            )
        )

    # --------------------------------------------------------------------------------- permissões
    def usuario_pode(self, usuario: int, permissao: str) -> bool:
        achado = self._c.usuarios.obter(usuario)
        assert achado is not None, f"Usuário {usuario} inexistente na base de teste"
        return achado.pode(Permissao.de_nome(permissao))

    def exigir_permissao(self, usuario: int, permissao: str) -> Resultado:
        achado = self._c.usuarios.obter(usuario)
        assert achado is not None, f"Usuário {usuario} inexistente na base de teste"
        return self._executar(lambda: achado.exigir(Permissao.de_nome(permissao)))

    # ------------------------------------------------------------------------------------ consultas
    def os(self, numero: int) -> OsSnap | None:
        achada = self._c.ordens.obter(numero)
        return None if achada is None else snap_os(achada)

    def todas_as_os(self) -> tuple[OsSnap, ...]:
        return tuple(snap_os(o) for o in self._c.ordens.listar())

    def _snap_usuario(self, usuario_id: int) -> UsuarioSnap | None:
        achado = self._c.usuarios.obter(usuario_id)
        if achado is None:
            return None
        return snap_usuario(achado, self._c.projecoes.carga_do_tecnico(achado.id))

    def usuario(self, id: int) -> UsuarioSnap | None:
        return self._snap_usuario(id)

    def usuarios(self) -> tuple[UsuarioSnap, ...]:
        return tuple(
            snap_usuario(u, self._c.projecoes.carga_do_tecnico(u.id))
            for u in self._c.usuarios.listar()
        )

    def tecnicos(self) -> tuple[int, ...]:
        return tuple(t.id for t in self._c.projecoes.tecnicos())

    def equipamento(self, id: int) -> EquipamentoSnap | None:
        achado = self._c.equipamentos.obter(id)
        return None if achado is None else snap_equipamento(achado)

    def equipamentos(self) -> tuple[EquipamentoSnap, ...]:
        return tuple(snap_equipamento(e) for e in self._c.equipamentos.listar())

    def ordens_do_equipamento(self, equipamento: int) -> tuple[int, ...]:
        return tuple(o.numero for o in self._c.projecoes.ordens_do_equipamento(equipamento))

    def cargos(self) -> tuple[CargoSnap, ...]:
        return tuple(snap_cargo(c) for c in self._c.cargos.listar())

    # -------------------------------------------------------------------------------- persistência
    def salvar_e_recarregar(self) -> None:
        self._ausente(Responsabilidade.PERSISTENCIA)
