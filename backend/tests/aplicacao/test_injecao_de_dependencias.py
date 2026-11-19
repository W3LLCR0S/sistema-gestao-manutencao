"""Injeção de dependências: os serviços recebem abstrações e aceitam qualquer implementação."""

import inspect
import typing
from typing import Any, cast

import pytest

from manutencao.application.portas.repositorios import (
    EquipamentoRepository,
    OrdemServicoRepository,
)
from manutencao.application.servicos.disponibilidade import ServicoDeDisponibilidade
from manutencao.application.servicos.equipamentos import ServicoDeEquipamentos
from manutencao.application.servicos.ordens import ServicoDeOrdens
from manutencao.application.servicos.projecoes import Projecoes
from manutencao.application.servicos.usuarios import ServicoDeUsuarios
from manutencao.domain.enums import Disponibilidade
from manutencao.domain.equipamento import Equipamento
from tests.apoio.ambiente import ANA, BRUNO, Ambiente

SERVICOS = [
    ServicoDeEquipamentos,
    ServicoDeUsuarios,
    ServicoDeOrdens,
    ServicoDeDisponibilidade,
    Projecoes,
]


def _eh_porta(tipo: object) -> bool:
    return bool(getattr(tipo, "_is_protocol", False))


@pytest.mark.parametrize("servico", SERVICOS, ids=lambda s: s.__name__)
def test_todo_parametro_do_construtor_e_uma_porta_ou_um_colaborador_da_aplicacao(
    servico: type,
) -> None:
    dicas = typing.get_type_hints(vars(servico)["__init__"])
    dicas.pop("return", None)
    assert dicas, f"{servico.__name__} não declara dependências"
    for nome, tipo in dicas.items():
        da_aplicacao = getattr(tipo, "__module__", "").startswith("manutencao.application")
        assert da_aplicacao, f"{servico.__name__}.{nome}: {tipo} fora da camada de aplicação"
        assert _eh_porta(tipo) or tipo is Projecoes, f"{servico.__name__}.{nome} não é uma porta"


@pytest.mark.parametrize("servico", SERVICOS, ids=lambda s: s.__name__)
def test_os_servicos_nao_constroem_as_proprias_dependencias(servico: type) -> None:
    """Sem valor padrão: quem monta o serviço é obrigado a entregar cada dependência."""
    parametros = inspect.signature(servico).parameters
    com_padrao = [n for n, p in parametros.items() if p.default is not inspect.Parameter.empty]
    assert com_padrao == []


class RepositorioDeEquipamentosComRegistro:
    """Outra implementação da porta: guarda em memória e registra cada chamada recebida."""

    def __init__(self) -> None:
        self.chamadas: list[str] = []
        self._itens: dict[int, Equipamento] = {}
        self._ultimo = 0

    def proximo_id(self) -> int:
        self.chamadas.append("proximo_id")
        return self._ultimo + 1

    def adicionar(self, equipamento: Equipamento) -> None:
        self.chamadas.append("adicionar")
        self._ultimo = max(self._ultimo, equipamento.id)
        self._itens[equipamento.id] = Equipamento(
            equipamento.id, equipamento.nome, equipamento.modelo, equipamento.ativo
        )

    def obter(self, id: int) -> Equipamento | None:
        self.chamadas.append("obter")
        achado = self._itens.get(id)
        return achado and Equipamento(achado.id, achado.nome, achado.modelo, achado.ativo)

    def listar(self) -> tuple[Equipamento, ...]:
        self.chamadas.append("listar")
        return tuple(self._itens[i] for i in sorted(self._itens))

    def salvar(self, equipamento: Equipamento) -> None:
        self.chamadas.append("salvar")
        self._itens[equipamento.id] = equipamento

    def remover(self, id: int) -> None:
        self.chamadas.append("remover")
        del self._itens[id]


def test_outra_implementacao_da_porta_substitui_a_de_memoria_sem_tocar_o_servico(
    amb: Ambiente,
) -> None:
    alternativa = RepositorioDeEquipamentosComRegistro()
    assert isinstance(alternativa, EquipamentoRepository)
    servico = ServicoDeEquipamentos(alternativa, amb.usuarios, amb.ordens)

    novo = servico.cadastrar(ANA, "Prensa", "P1")
    servico.inativar(ANA, novo.id)

    assert novo.id == 1  # a numeração é da implementação injetada, não do serviço
    assert alternativa.chamadas == ["proximo_id", "adicionar", "obter", "salvar"]
    assert len(amb.equipamentos.listar()) == 3  # a base em memória do ambiente não foi tocada


class PortaProibida:
    """Qualquer uso falha: prova que o caso de uso não toca uma porta de que não precisa (ISP)."""

    def __getattr__(self, nome: str) -> Any:
        raise AssertionError(f"a porta não deveria ser usada: {nome}")


def test_caso_de_uso_so_toca_as_portas_de_que_precisa(amb: Ambiente) -> None:
    sem_ordens = cast(OrdemServicoRepository, PortaProibida())
    servico = ServicoDeEquipamentos(amb.equipamentos, amb.usuarios, sem_ordens)
    assert len(servico.listar(ANA)) == 3  # leitura de equipamentos não consulta OS
    assert servico.cadastrar(ANA, "Prensa", "P1").id == 4


def test_a_disponibilidade_manual_nao_consulta_nenhuma_ordem(amb: Ambiente) -> None:
    ordens_proibidas = cast(OrdemServicoRepository, PortaProibida())
    servico = ServicoDeDisponibilidade(amb.usuarios, Projecoes(amb.usuarios, ordens_proibidas))
    servico.alterar_minha_disponibilidade(BRUNO, Disponibilidade.AUSENTE)
    bruno = amb.usuarios.obter(BRUNO)
    assert bruno is not None
    assert bruno.disponibilidade is Disponibilidade.AUSENTE
