"""Equipamentos pela API: cadastro, listagem paginada, inativação e exclusão."""

import pytest

from tests.apoio.ambiente import ANA, BRUNO
from tests.apoio.api import Mundo

NOVO = {"nome": "Prensa Hidráulica", "modelo": "PH-200"}


def test_tecnico_consulta_mas_nao_gerencia(mundo: Mundo) -> None:
    bruno = mundo.entrar(BRUNO)
    lista = bruno.get("/equipamentos")
    assert lista.status_code == 200
    assert lista.json()["total"] == 3
    assert bruno.get("/equipamentos/1").json()["nome"] == "Torno CNC"
    for resposta in (
        bruno.post("/equipamentos", NOVO),
        bruno.put("/equipamentos/1", NOVO),
        bruno.post("/equipamentos/1/inativar"),
        bruno.post("/equipamentos/1/reativar"),
        bruno.delete("/equipamentos/1"),
    ):
        assert resposta.status_code == 403
        assert resposta.json()["codigo"] == "sem_permissao"


def test_cadastrar_consultar_atualizar(mundo: Mundo) -> None:
    ana = mundo.entrar(ANA)
    criado = ana.post("/equipamentos", NOVO)
    assert criado.status_code == 201
    assert criado.json() == {"id": 4, "ativo": True, "situacao": "Ativo", **NOVO}
    assert ana.get("/equipamentos/4").json()["modelo"] == "PH-200"
    atualizado = ana.put("/equipamentos/4", {"nome": "Prensa", "modelo": "PH-300"})
    assert atualizado.status_code == 200
    assert atualizado.json()["modelo"] == "PH-300"


@pytest.mark.parametrize(
    ("corpo", "codigo"),
    [
        ({"nome": "  ", "modelo": "x"}, "campo_obrigatorio"),
        ({"nome": "x"}, "entrada_invalida"),
        ({"nome": "x", "modelo": "y", "ativo": False}, "entrada_invalida"),
        ({"nome": "x" * 201, "modelo": "y"}, "entrada_invalida"),
        ({"nome": 10, "modelo": "y"}, "entrada_invalida"),
    ],
)
def test_cadastro_invalido(mundo: Mundo, corpo: dict[str, object], codigo: str) -> None:
    r = mundo.entrar(ANA).post("/equipamentos", corpo)
    assert r.status_code == 422
    assert r.json()["codigo"] == codigo
    assert mundo.entrar(ANA).get("/equipamentos").json()["total"] == 3


def test_recusa_nao_consome_identificador(mundo: Mundo) -> None:
    ana = mundo.entrar(ANA)
    ana.post("/equipamentos", {"nome": " ", "modelo": "x"})
    assert ana.post("/equipamentos", NOVO).json()["id"] == 4


def test_equipamento_inexistente_responde_404_em_todas_as_operacoes(mundo: Mundo) -> None:
    ana = mundo.entrar(ANA)
    for r in (
        ana.get("/equipamentos/99"),
        ana.put("/equipamentos/99", NOVO),
        ana.post("/equipamentos/99/inativar"),
        ana.post("/equipamentos/99/reativar"),
        ana.delete("/equipamentos/99"),
    ):
        assert r.status_code == 404
        assert r.json()["codigo"] == "nao_encontrado"


def test_identificador_nao_numerico_e_422(mundo: Mundo) -> None:
    assert mundo.entrar(ANA).get("/equipamentos/abc").status_code == 422


def test_inativar_reativar_e_filtro_de_ativos(mundo: Mundo) -> None:
    ana = mundo.entrar(ANA)
    r = ana.post("/equipamentos/2/inativar")
    assert r.status_code == 200
    assert r.json()["ativo"] is False
    assert r.json()["situacao"] == "Inativo"
    assert ana.post("/equipamentos/2/inativar").status_code == 200  # idempotente
    ativos = ana.get("/equipamentos?apenas_ativos=true").json()
    assert [e["id"] for e in ativos["itens"]] == [1, 3]
    assert ativos["total"] == 2
    assert ana.get("/equipamentos").json()["total"] == 3
    assert ana.post("/equipamentos/2/reativar").json()["ativo"] is True


def test_equipamento_inativo_nao_recebe_nova_os_mas_as_abertas_seguem(mundo: Mundo) -> None:
    ana = mundo.entrar(ANA)
    ana.post("/ordens", {"equipamento_id": 1, "falha": "Falha", "criticidade": "Alta"})
    ana.post("/equipamentos/1/inativar")
    r = ana.post("/ordens", {"equipamento_id": 1, "falha": "Outra", "criticidade": "Alta"})
    assert r.status_code == 422
    assert r.json()["codigo"] == "equipamento_inativo"
    assert ana.get("/ordens/1").status_code == 200


def test_excluir_sem_os_e_com_os(mundo: Mundo) -> None:
    ana = mundo.entrar(ANA)
    ana.post("/ordens", {"equipamento_id": 1, "falha": "Falha", "criticidade": "Alta"})
    r = ana.delete("/equipamentos/1")
    assert r.status_code == 409
    assert r.json()["codigo"] == "equipamento_com_os"
    assert ana.delete("/equipamentos/2").status_code == 204
    assert ana.get("/equipamentos/2").status_code == 404
    assert ana.post("/equipamentos", NOVO).json()["id"] == 4  # o id 2 não é reaproveitado


def test_paginacao_de_equipamentos(mundo: Mundo) -> None:
    ana = mundo.entrar(ANA)
    for n in range(4, 8):
        ana.post("/equipamentos", {"nome": f"Máquina {n}", "modelo": "M"})
    pagina = ana.get("/equipamentos?limite=3&deslocamento=3").json()
    assert [e["id"] for e in pagina["itens"]] == [4, 5, 6]
    assert pagina["total"] == 7
    assert pagina["limite"] == 3
    assert pagina["deslocamento"] == 3
    assert ana.get("/equipamentos?limite=500").status_code == 422
