"""Adaptador da fachada de caracterização sobre o **código legado** (Entrega 1).

Este é o único módulo do backend autorizado a importar ``models/`` e ``persistencia/`` (ADR-0008);
o teste de arquitetura impede o resto. Garantias de isolamento:

* o repositório legado **sempre** recebe um caminho temporário explícito (nunca o padrão do
  construtor, que apontaria para ``dados/dados.json``); um caminho dentro de ``dados/`` é recusado;
* a raiz do repositório entra em ``sys.path`` só durante a importação e é retirada em seguida;
* nenhum arquivo ``.pyc`` é gravado dentro do legado;
* o relógio do legado (``datetime.now()`` em ``models.servico`` e ``models.ordem_servico``) é
  substituído por um relógio controlado pelo teste, restaurado ao fechar o adaptador. O relógio do
  sistema operacional nunca é alterado.

As operações reproduzem o que a interface do legado faz (``ui/``): é ela que numera a OS, cria as
peças e chama o domínio. Regras que existem só na interface não são reproduzidas aqui; ver
``test_legado_defeitos.py``.
"""

import importlib
import sys
from datetime import datetime, tzinfo
from pathlib import Path
from types import ModuleType
from typing import Any, ClassVar

from tests.caracterizacao.fachada import (
    CargoSnap,
    EquipamentoSnap,
    OsSnap,
    Peca,
    PecaSnap,
    Recusa,
    RelogioFixo,
    Resultado,
    ServicoSnap,
    UsuarioSnap,
)
from tests.guardas_ambiente import RAIZ_REPOSITORIO, caminho_em_dados

# Mensagens do legado -> categoria estável. Só este módulo conhece o texto; os testes usam a
# categoria. A ordem importa (a primeira correspondência vence).
_CATEGORIAS: tuple[tuple[str, Recusa], ...] = (
    ("Sem permissão", Recusa.SEM_PERMISSAO),
    ("Não é possível abrir OS para equipamento inativo", Recusa.EQUIPAMENTO_INATIVO),
    ("Esta OS não está atribuída a você", Recusa.NAO_RESPONSAVEL),
    ("Operação não permitida com a OS em", Recusa.ESTADO_INVALIDO),
    ("Não é possível atribuir uma OS em", Recusa.ESTADO_INVALIDO),
    ("Horas trabalhadas não podem ser negativas", Recusa.HORAS_NEGATIVAS),
    ("O técnico não pode definir o status", Recusa.STATUS_NAO_PERMITIDO),
    ("A OS já está nesse status", Recusa.JA_NESSE_STATUS),
    ("Registre ao menos uma intervenção", Recusa.SEM_INTERVENCAO),
    ("Registre o diagnóstico antes de concluir", Recusa.SEM_DIAGNOSTICO),
    ("não é técnico", Recusa.NAO_E_TECNICO),
    ("A OS já está atribuída a este técnico", Recusa.JA_ATRIBUIDA),
    ("A OS já está encerrada", Recusa.OS_ENCERRADA),
    ("A quantidade deve ser maior que zero", Recusa.QUANTIDADE_INVALIDA),
    ("Equipamento possui OS vinculadas", Recusa.EQUIPAMENTO_COM_OS),
    ("Usuário possui histórico em OS", Recusa.USUARIO_COM_HISTORICO),
    ("Você não pode excluir o próprio usuário", Recusa.AUTOEXCLUSAO),
)


def categorizar(mensagem: str) -> Recusa:
    for trecho, categoria in _CATEGORIAS:
        if trecho in mensagem:
            return categoria
    return Recusa.DESCONHECIDA


# --- importação do legado


def _importar_legado() -> tuple[ModuleType, ModuleType]:
    """Importa ``models`` e ``persistencia`` sem deixar rastros em ``sys.path`` nem ``.pyc``."""
    raiz = str(RAIZ_REPOSITORIO)
    gravar_pyc = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    sys.path.insert(0, raiz)
    try:
        return importlib.import_module("models"), importlib.import_module("persistencia")
    finally:
        sys.path.remove(raiz)
        sys.dont_write_bytecode = gravar_pyc


# --- relógio


class _DatetimeControlado(datetime):
    """``datetime`` cujo ``now()`` devolve o instante do relógio de teste ativo."""

    relogio: RelogioFixo | None = None

    @classmethod
    def now(cls, tz: tzinfo | None = None) -> datetime:  # type: ignore[override]
        assert cls.relogio is not None, "nenhum relógio de teste instalado"
        return cls.relogio.agora()


class _PatchRelogio:
    """Substitui ``datetime`` nos módulos do legado que leem o relógio (contando usos)."""

    _usos = 0
    _originais: ClassVar[dict[str, Any]] = {}

    @classmethod
    def instalar(cls, relogio: RelogioFixo, servico: ModuleType, ordem: ModuleType) -> None:
        if cls._usos == 0:
            cls._originais = {
                "servico": getattr(servico, "datetime"),  # noqa: B009
                "ordem": getattr(ordem, "datetime"),  # noqa: B009
            }
            setattr(servico, "datetime", _DatetimeControlado)  # noqa: B010
            setattr(ordem, "datetime", _DatetimeControlado)  # noqa: B010
        _DatetimeControlado.relogio = relogio
        cls._usos += 1

    @classmethod
    def restaurar(cls, servico: ModuleType, ordem: ModuleType) -> None:
        cls._usos -= 1
        if cls._usos == 0:
            setattr(servico, "datetime", cls._originais["servico"])  # noqa: B010
            setattr(ordem, "datetime", cls._originais["ordem"])  # noqa: B010
            _DatetimeControlado.relogio = None


# --- adaptador


class AdaptadorLegado:
    """Implementa a ``Fachada`` de caracterização sobre ``models/`` e ``persistencia/``."""

    def __init__(self, caminho: Path, relogio: RelogioFixo | None = None) -> None:
        if caminho_em_dados(caminho):
            raise ValueError(f"O adaptador não aceita caminhos dentro de dados/: {caminho}")
        self.caminho = caminho
        self.relogio = relogio or RelogioFixo()
        self._models, self._persistencia = _importar_legado()
        self._servico_mod = importlib.import_module("models.servico")
        self._ordem_mod = importlib.import_module("models.ordem_servico")
        _PatchRelogio.instalar(self.relogio, self._servico_mod, self._ordem_mod)
        self._aberto = True
        # Caminho SEMPRE explícito: nunca o ARQUIVO_PADRAO (dados/dados.json) do construtor.
        self.repo: Any = self._persistencia.Repositorio(str(caminho))

    def fechar(self) -> None:
        if self._aberto:
            _PatchRelogio.restaurar(self._servico_mod, self._ordem_mod)
            self._aberto = False

    # ------------------------------------------------------------------------------ utilidades
    def _m(self) -> Any:
        return self._models

    def _usuario(self, id: int) -> Any:
        encontrado = self.repo.buscar_usuario(id)
        if encontrado is None:
            raise LookupError(f"Usuário {id} inexistente na base de teste")
        return encontrado

    def _os(self, numero: int) -> Any:
        encontrada = self.repo.buscar_os(numero)
        if encontrada is None:
            raise LookupError(f"OS {numero} inexistente na base de teste")
        return encontrada

    def _equipamento(self, id: int) -> Any:
        encontrado = self.repo.buscar_equipamento(id)
        if encontrado is None:
            raise LookupError(f"Equipamento {id} inexistente na base de teste")
        return encontrado

    def _cargo(self, id: int) -> Any:
        encontrado = self.repo.buscar_cargo(id)
        if encontrado is None:
            raise LookupError(f"Cargo {id} inexistente na base de teste")
        return encontrado

    def _executar(self, acao: Any) -> Resultado:
        try:
            valor = acao()
        except self._m().RegraNegocioError as erro:
            mensagem = str(erro)
            return Resultado(False, categorizar(mensagem), mensagem)
        return Resultado(True, valor=valor)

    # --------------------------------------------------------------------- OS: abertura e gestão
    def abrir_os(
        self, solicitante: int, equipamento: int, falha: str, criticidade: str
    ) -> Resultado:
        m = self._m()

        def acao() -> int:
            # Mesmo fluxo de ui/tela_ordens.py: numera, abre e só então adiciona.
            os_ = m.OrdemServico.abrir(
                self.repo.proximo_numero_os(),
                self._equipamento(equipamento),
                falha,
                m.Criticidade(criticidade),
                self._usuario(solicitante),
            )
            self.repo.adicionar_os(os_)
            return int(os_.numero)

        return self._executar(acao)

    def atribuir(self, os: int, tecnico: int, gestor: int) -> Resultado:
        def acao() -> int | None:
            anterior = self._os(os).atribuir(self._usuario(tecnico), self._usuario(gestor))
            return int(anterior.id) if anterior else None

        return self._executar(acao)

    def aprovar(self, os: int, gestor: int) -> Resultado:
        return self._executar(lambda: self._os(os).aprovar(self._usuario(gestor)))

    def reprovar(self, os: int, gestor: int, motivo: str) -> Resultado:
        return self._executar(lambda: self._os(os).reprovar(self._usuario(gestor), motivo))

    def cancelar(self, os: int, gestor: int, motivo: str) -> Resultado:
        return self._executar(lambda: self._os(os).cancelar(self._usuario(gestor), motivo))

    def adicionar_observacao(self, os: int, usuario: int, texto: str) -> Resultado:
        return self._executar(
            lambda: self._os(os).adicionar_apontamento(self._usuario(usuario), texto)
        )

    # ------------------------------------------------------------------------ OS: execução técnica
    def registrar_diagnostico(self, os: int, tecnico: int, parecer: str, causa: str) -> Resultado:
        return self._executar(
            lambda: self._os(os).registrar_diagnostico(self._usuario(tecnico), parecer, causa)
        )

    def apontar_reparo(
        self, os: int, tecnico: int, horas: float, intervencao: str, pecas: tuple[Peca, ...] = ()
    ) -> Resultado:
        m = self._m()

        def acao() -> None:
            # Como na tela: as peças são criadas (e validadas) antes de chamar o domínio.
            objetos = [m.PecaMaterial(p.descricao, p.quantidade) for p in pecas]
            self._os(os).apontar_reparo(self._usuario(tecnico), horas, intervencao, objetos)

        return self._executar(acao)

    def alterar_status(self, os: int, tecnico: int, status: str) -> Resultado:
        m = self._m()
        return self._executar(
            lambda: self._os(os).alterar_status(self._usuario(tecnico), m.StatusOS(status))
        )

    def concluir_tecnicamente(self, os: int, tecnico: int, teste: str, passou: bool) -> Resultado:
        return self._executar(
            lambda: bool(self._os(os).concluir_tecnicamente(self._usuario(tecnico), teste, passou))
        )

    # --- disponibilidade
    def atualizar_disponibilidades(self) -> None:
        self.repo.atualizar_disponibilidades()

    def definir_disponibilidade(self, usuario: int, valor: str) -> None:
        # ui/tela_ordens.py atribui direto ao atributo: não há método de domínio.
        self._usuario(usuario).disponibilidade = self._m().Disponibilidade(valor)

    # ---------------------------------------------------------------------------------- cadastros
    def cadastrar_usuario(self, nome: str, cargo: int, email: str = "", escala: str = "") -> int:
        novo = self._m().Usuario(
            self.repo.proximo_id_usuario(), nome, self._cargo(cargo), email, escala
        )
        self.repo.adicionar_usuario(novo)
        return int(novo.id)

    def editar_usuario(
        self,
        usuario: int,
        *,
        nome: str | None = None,
        email: str | None = None,
        escala: str | None = None,
        cargo: int | None = None,
    ) -> None:
        alvo = self._usuario(usuario)
        if nome is not None:
            alvo.nome = nome
        if email is not None:
            alvo.email = email
        if escala is not None:
            alvo.escala = escala
        if cargo is not None:
            alvo.cargo = self._cargo(cargo)

    def remover_usuario(self, usuario: int, solicitante: int) -> Resultado:
        return self._executar(
            lambda: self.repo.remover_usuario(self._usuario(usuario), self._usuario(solicitante))
        )

    def cadastrar_equipamento(self, nome: str, modelo: str) -> int:
        novo = self._m().Equipamento(self.repo.proximo_id_equipamento(), nome, modelo)
        self.repo.adicionar_equipamento(novo)
        return int(novo.id)

    def editar_equipamento(self, equipamento: int, *, nome: str, modelo: str) -> None:
        alvo = self._equipamento(equipamento)
        alvo.nome = nome
        alvo.modelo = modelo

    def inativar_equipamento(self, equipamento: int) -> None:
        self._equipamento(equipamento).inativar()

    def reativar_equipamento(self, equipamento: int) -> None:
        self._equipamento(equipamento).reativar()

    def remover_equipamento(self, equipamento: int) -> Resultado:
        return self._executar(lambda: self.repo.remover_equipamento(self._equipamento(equipamento)))

    def definir_permissoes_cargo(self, cargo: int, permissoes: tuple[str, ...]) -> None:
        self._cargo(cargo).permissoes.definir(list(permissoes))

    # --------------------------------------------------------------------------------- permissões
    def usuario_pode(self, usuario: int, permissao: str) -> bool:
        return bool(self._usuario(usuario).pode(permissao))

    def exigir_permissao(self, usuario: int, permissao: str) -> Resultado:
        return self._executar(lambda: self._usuario(usuario).exigir(permissao))

    # ------------------------------------------------------------------------------------ consultas
    def _peca(self, p: Any) -> PecaSnap:
        return PecaSnap(str(p.descricao), float(p.quantidade))

    def _snap_os(self, o: Any) -> OsSnap:
        def uid(u: Any) -> int | None:
            return int(u.id) if u is not None else None

        historico = tuple(
            ServicoSnap(
                int(s.numero),
                str(s.tipo.value),
                str(s.descricao),
                uid(s.responsavel),
                str(s.data),
                float(s.horas),
                tuple(self._peca(p) for p in s.pecas),
            )
            for s in o.servicos
        )
        return OsSnap(
            numero=int(o.numero),
            status=str(o.status.value),
            equipamento_id=int(o.equipamento.id),
            falha=str(o.falha),
            criticidade=str(o.criticidade.value),
            aberta_por_id=uid(o.aberta_por),
            tecnico_id=uid(o.tecnico_atribuido),
            diagnostico=str(o.diagnostico),
            causa_raiz=str(o.causa_raiz),
            horas_trabalhadas=float(o.horas_trabalhadas),
            intervencoes=tuple(str(i) for i in o.intervencoes_realizadas),
            pecas=tuple(self._peca(p) for p in o.pecas_utilizadas),
            data_abertura=str(o.data_abertura),
            data_conclusao=None if o.data_conclusao is None else str(o.data_conclusao),
            teste_funcional=str(o.teste_funcional),
            motivo_cancelamento=str(o.motivo_cancelamento),
            historico=historico,
        )

    def _snap_usuario(self, u: Any) -> UsuarioSnap:
        return UsuarioSnap(
            id=int(u.id),
            nome=str(u.nome),
            cargo_id=int(u.cargo.id),
            cargo=str(u.cargo.nome),
            email=str(u.email),
            escala=str(u.escala),
            disponibilidade=str(u.disponibilidade.value),
            carga=int(self.repo.carga(u)),
        )

    def os(self, numero: int) -> OsSnap | None:
        encontrada = self.repo.buscar_os(numero)
        return None if encontrada is None else self._snap_os(encontrada)

    def todas_as_os(self) -> tuple[OsSnap, ...]:
        return tuple(self._snap_os(o) for o in self.repo.ordens)

    def usuario(self, id: int) -> UsuarioSnap | None:
        encontrado = self.repo.buscar_usuario(id)
        return None if encontrado is None else self._snap_usuario(encontrado)

    def usuarios(self) -> tuple[UsuarioSnap, ...]:
        return tuple(self._snap_usuario(u) for u in self.repo.usuarios)

    def tecnicos(self) -> tuple[int, ...]:
        return tuple(int(u.id) for u in self.repo.tecnicos())

    def equipamento(self, id: int) -> EquipamentoSnap | None:
        e = self.repo.buscar_equipamento(id)
        return (
            None
            if e is None
            else EquipamentoSnap(int(e.id), str(e.nome), str(e.modelo), bool(e.ativo))
        )

    def equipamentos(self) -> tuple[EquipamentoSnap, ...]:
        return tuple(
            EquipamentoSnap(int(e.id), str(e.nome), str(e.modelo), bool(e.ativo))
            for e in self.repo.equipamentos
        )

    def ordens_do_equipamento(self, equipamento: int) -> tuple[int, ...]:
        ordens = self.repo.ordens_do_equipamento(self._equipamento(equipamento))
        return tuple(int(o.numero) for o in ordens)

    def cargos(self) -> tuple[CargoSnap, ...]:
        return tuple(
            CargoSnap(int(c.id), str(c.nome), tuple(c.permissoes.ativas()))
            for c in self.repo.cargos
        )

    # -------------------------------------------------------------------------------- persistência
    def salvar_e_recarregar(self) -> None:
        self.repo.salvar()
        self.repo = self._persistencia.Repositorio(str(self.caminho))
