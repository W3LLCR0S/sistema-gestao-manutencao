"""Casos de uso de equipamentos (gestão e consulta).

Preservam as permissões efetivas do legado: consultar exige ``ver_equipamentos`` e gerir exige
``gerir_equipamentos`` (o menu da CLI as aplicava; aqui são verificadas no caso de uso, AUD-02;
DLT-13 e DLT-14), sempre antes de procurar o recurso (DLT-16); ator inexistente é recusado (DLT-17).
Nenhuma validação nova de campos (DLT-08 é da Operação E).
"""

from manutencao.application.erros import CodigoErroAplicacao, RegraDeAplicacaoError
from manutencao.application.portas.repositorios import (
    EquipamentoRepository,
    FiltroDeOrdens,
    OrdemServicoRepository,
    UsuarioRepository,
)
from manutencao.application.servicos.comum import carregar_ator, exigir_encontrado
from manutencao.domain.equipamento import Equipamento
from manutencao.domain.permissoes import Permissao


class ServicoDeEquipamentos:
    """Cadastro, consulta, edição, inativação e exclusão de equipamentos."""

    def __init__(
        self,
        equipamentos: EquipamentoRepository,
        usuarios: UsuarioRepository,
        ordens: OrdemServicoRepository,
    ) -> None:
        self._equipamentos = equipamentos
        self._usuarios = usuarios
        self._ordens = ordens

    def _carregar(self, equipamento_id: int) -> Equipamento:
        return exigir_encontrado(
            "Equipamento", equipamento_id, self._equipamentos.obter(equipamento_id)
        )

    # ------------------------------------------------------------------------------ consultas
    def consultar(self, ator_id: int, equipamento_id: int) -> Equipamento:
        carregar_ator(self._usuarios, ator_id).exigir(Permissao.VER_EQUIPAMENTOS)
        return self._carregar(equipamento_id)

    def listar(self, ator_id: int, *, apenas_ativos: bool = False) -> tuple[Equipamento, ...]:
        carregar_ator(self._usuarios, ator_id).exigir(Permissao.VER_EQUIPAMENTOS)
        todos = self._equipamentos.listar()
        return tuple(e for e in todos if e.ativo or not apenas_ativos)

    # ----------------------------------------------------------------------------------- gestão
    def cadastrar(self, ator_id: int, nome: str, modelo: str) -> Equipamento:
        carregar_ator(self._usuarios, ator_id).exigir(Permissao.GERIR_EQUIPAMENTOS)
        equipamento = Equipamento(self._equipamentos.proximo_id(), nome, modelo)
        self._equipamentos.adicionar(equipamento)
        return equipamento

    def atualizar(self, ator_id: int, equipamento_id: int, nome: str, modelo: str) -> Equipamento:
        carregar_ator(self._usuarios, ator_id).exigir(Permissao.GERIR_EQUIPAMENTOS)
        equipamento = self._carregar(equipamento_id)
        equipamento.nome = nome
        equipamento.modelo = modelo
        self._equipamentos.salvar(equipamento)
        return equipamento

    def inativar(self, ator_id: int, equipamento_id: int) -> Equipamento:
        """Inativa (idempotente). As OS já abertas seguem o seu curso; só novas OS são recusadas."""
        carregar_ator(self._usuarios, ator_id).exigir(Permissao.GERIR_EQUIPAMENTOS)
        equipamento = self._carregar(equipamento_id)
        equipamento.inativar()
        self._equipamentos.salvar(equipamento)
        return equipamento

    def reativar(self, ator_id: int, equipamento_id: int) -> Equipamento:
        carregar_ator(self._usuarios, ator_id).exigir(Permissao.GERIR_EQUIPAMENTOS)
        equipamento = self._carregar(equipamento_id)
        equipamento.reativar()
        self._equipamentos.salvar(equipamento)
        return equipamento

    def excluir(self, ator_id: int, equipamento_id: int) -> None:
        """Exclui um equipamento sem OS; com OS (em qualquer estado) só é possível inativar."""
        carregar_ator(self._usuarios, ator_id).exigir(Permissao.GERIR_EQUIPAMENTOS)
        self._carregar(equipamento_id)
        if self._ordens.contar(FiltroDeOrdens(equipamento_id=equipamento_id)) > 0:
            raise RegraDeAplicacaoError(
                CodigoErroAplicacao.EQUIPAMENTO_COM_OS,
                "Equipamento possui OS vinculadas; use Inativar para preservar o histórico.",
            )
        self._equipamentos.remover(equipamento_id)
