"""Contrato de ``EquipamentoRepository``: busca, listagem, escrita, ausência e cópia."""

import pytest

from manutencao.application.erros import NaoEncontradoError
from manutencao.domain.equipamento import Equipamento
from tests.contrato.implementacoes import Repositorios


def _equipamento(id: int = 1, nome: str = "Torno CNC") -> Equipamento:
    return Equipamento(id, nome, "GL 240")


def test_repositorio_novo_esta_vazio_e_o_primeiro_id_e_1(repos: Repositorios) -> None:
    assert repos.equipamentos.listar() == ()
    assert repos.equipamentos.proximo_id() == 1


def test_adicionar_e_obter_por_identificador(repos: Repositorios) -> None:
    repos.equipamentos.adicionar(_equipamento())
    achado = repos.equipamentos.obter(1)
    assert achado is not None
    assert (achado.id, achado.nome, achado.modelo, achado.ativo) == (1, "Torno CNC", "GL 240", True)


def test_obter_inexistente_devolve_none(repos: Repositorios) -> None:
    assert repos.equipamentos.obter(99) is None


def test_listar_devolve_em_ordem_crescente_de_id(repos: Repositorios) -> None:
    for id in (1, 2, 5):
        repos.equipamentos.adicionar(_equipamento(id, f"E{id}"))
    assert [e.id for e in repos.equipamentos.listar()] == [1, 2, 5]


def test_adicionar_guarda_copia_do_que_recebeu(repos: Repositorios) -> None:
    original = _equipamento()
    repos.equipamentos.adicionar(original)
    original.nome = "Alterado depois de adicionar"
    original.inativar()
    guardado = repos.equipamentos.obter(1)
    assert guardado is not None
    assert (guardado.nome, guardado.ativo) == ("Torno CNC", True)


def test_obter_devolve_copia_independente_do_armazenado(repos: Repositorios) -> None:
    repos.equipamentos.adicionar(_equipamento())
    primeira = repos.equipamentos.obter(1)
    segunda = repos.equipamentos.obter(1)
    assert primeira is not None
    assert segunda is not None
    assert primeira is not segunda
    assert primeira == segunda  # a igualdade é por identificador
    primeira.nome = "mudou"
    primeira.inativar()
    de_novo = repos.equipamentos.obter(1)
    assert de_novo is not None
    assert (de_novo.nome, de_novo.ativo) == ("Torno CNC", True)


def test_listar_devolve_copias_independentes(repos: Repositorios) -> None:
    repos.equipamentos.adicionar(_equipamento())
    repos.equipamentos.listar()[0].inativar()
    assert repos.equipamentos.listar()[0].ativo is True


def test_alteracao_so_vale_depois_de_salvar(repos: Repositorios) -> None:
    repos.equipamentos.adicionar(_equipamento())
    editado = repos.equipamentos.obter(1)
    assert editado is not None
    editado.nome = "Torno 2"
    editado.inativar()
    antes = repos.equipamentos.obter(1)
    assert antes is not None
    assert (antes.nome, antes.ativo) == ("Torno CNC", True)
    repos.equipamentos.salvar(editado)
    depois = repos.equipamentos.obter(1)
    assert depois is not None
    assert (depois.nome, depois.ativo) == ("Torno 2", False)


def test_salvar_inexistente_levanta_nao_encontrado_e_nao_cria(repos: Repositorios) -> None:
    with pytest.raises(NaoEncontradoError):
        repos.equipamentos.salvar(_equipamento(7))
    assert repos.equipamentos.obter(7) is None
    assert repos.equipamentos.listar() == ()


def test_remover_exclui_so_o_indicado(repos: Repositorios) -> None:
    for id in (1, 2, 3):
        repos.equipamentos.adicionar(_equipamento(id))
    repos.equipamentos.remover(2)
    assert repos.equipamentos.obter(2) is None
    assert [e.id for e in repos.equipamentos.listar()] == [1, 3]


def test_remover_inexistente_levanta_nao_encontrado(repos: Repositorios) -> None:
    repos.equipamentos.adicionar(_equipamento())
    with pytest.raises(NaoEncontradoError):
        repos.equipamentos.remover(2)
    assert [e.id for e in repos.equipamentos.listar()] == [1]
