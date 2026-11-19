"""Contrato HTTP: OpenAPI, nenhum endpoint sem autenticação, nada sensível nos esquemas, erros.

Estes testes percorrem **todas** as rotas registradas: uma rota nova sem proteção, ou com um campo
sensível no esquema, faz a suíte falhar sem que ninguém precise lembrar de escrever um teste.
"""

import re
from typing import Any

import pytest

from tests.apoio.ambiente import ANA, BRUNO
from tests.apoio.api import PREFIXO, Mundo

PUBLICAS = {
    ("POST", f"{PREFIXO}/auth/login"),
    ("POST", f"{PREFIXO}/auth/logout"),  # idempotente; com sessão válida exige CSRF
    ("GET", f"{PREFIXO}/saude"),
}
CAMPOS_PROIBIDOS_NA_ENTRADA = {
    "ator_id",
    "ator",
    "usuario_logado",
    "aberta_por",
    "senha_hash",
    "token",
}
CAMPOS_PROIBIDOS_NA_SAIDA = {
    "senha_hash",
    "hash",
    "token",
    "token_sessao",
    "id_hash",
    "senha",
    "segredo",
}


def _rotas(mundo: Mundo) -> list[tuple[str, str]]:
    """Todas as operações publicadas, lidas do **OpenAPI** (o contrato), não da tabela interna."""
    documento = mundo.app.openapi()
    return [
        (metodo.upper(), caminho)
        for caminho, operacoes in documento["paths"].items()
        for metodo in operacoes
    ]


def _preencher(caminho: str) -> str:
    return re.sub(r"\{[^}]+\}", "1", caminho)


def test_existem_rotas_suficientes_para_o_teste_ser_significativo(mundo: Mundo) -> None:
    assert len(_rotas(mundo)) >= 44  # as operações publicadas hoje; remover uma exige decidir


def test_toda_rota_exceto_login_logout_e_saude_exige_autenticacao(mundo: Mundo) -> None:
    http = mundo.navegador()
    for metodo, caminho in _rotas(mundo):
        if (metodo, caminho) in PUBLICAS:
            continue
        resposta = http.request(metodo, _preencher(caminho), json={} if metodo != "GET" else None)
        assert resposta.status_code == 401, f"{metodo} {caminho} -> {resposta.status_code}"
        assert resposta.json()["codigo"] == "nao_autenticado"


def test_toda_operacao_que_escreve_exige_csrf(mundo: Mundo) -> None:
    ana = mundo.entrar(ANA)
    for metodo, caminho in _rotas(mundo):
        if metodo == "GET" or (metodo, caminho) in PUBLICAS:
            continue
        resposta = ana.http.request(metodo, _preencher(caminho), json={})  # sem X-CSRF-Token
        assert resposta.status_code == 403, f"{metodo} {caminho} -> {resposta.status_code}"
        assert resposta.json()["codigo"] == "csrf_invalido"


def test_rotas_estao_sob_o_prefixo_versionado(mundo: Mundo) -> None:
    for _, caminho in _rotas(mundo):
        assert caminho.startswith(PREFIXO + "/"), caminho


# --------------------------------------------------------------------------------------- OpenAPI
def _esquemas(documento: dict[str, Any]) -> dict[str, Any]:
    return dict(documento["components"]["schemas"])


def _corpos_de_requisicao(documento: dict[str, Any]) -> set[str]:
    nomes = set()
    for operacoes in documento["paths"].values():
        for operacao in operacoes.values():
            corpo = operacao.get("requestBody")
            if corpo:
                ref = corpo["content"]["application/json"]["schema"]["$ref"]
                nomes.add(ref.rsplit("/", 1)[1])
    return nomes


def test_openapi_e_publicado_e_descreve_a_api(mundo: Mundo) -> None:
    http = mundo.navegador()
    r = http.get("/openapi.json")
    assert r.status_code == 200
    documento = r.json()
    assert documento["info"]["title"] == "Gestão de Manutenção de Equipamentos"
    assert "X-CSRF-Token" in documento["info"]["description"]
    assert http.get("/docs").status_code == 200
    assert http.get("/redoc").status_code == 200
    for operacoes in documento["paths"].values():
        for operacao in operacoes.values():
            assert operacao.get("summary"), operacao  # toda operação é documentada
            assert operacao["tags"]


def test_nenhuma_entrada_aceita_identificador_do_ator_ou_campos_sensiveis(mundo: Mundo) -> None:
    documento = mundo.app.openapi()
    esquemas = _esquemas(documento)
    for nome in _corpos_de_requisicao(documento):
        esquema = esquemas[nome]
        assert esquema.get("additionalProperties") is False, f"{nome} aceita campos extras"
        assert not CAMPOS_PROIBIDOS_NA_ENTRADA & set(esquema["properties"]), nome
    for caminho, operacoes in documento["paths"].items():
        for operacao in operacoes.values():
            for parametro in operacao.get("parameters", []):
                assert parametro["name"].lower() not in {"ator_id", "ator", "usuario_logado"}, (
                    caminho
                )


def _referencias(no: Any) -> set[str]:
    """Nomes de esquemas citados (``$ref``) em qualquer ponto de ``no``."""
    achadas: set[str] = set()
    if isinstance(no, dict):
        for chave, valor in no.items():
            if chave == "$ref" and isinstance(valor, str):
                achadas.add(valor.rsplit("/", 1)[1])
            else:
                achadas |= _referencias(valor)
    elif isinstance(no, list):
        for item in no:
            achadas |= _referencias(item)
    return achadas


def _esquemas_de_resposta(documento: dict[str, Any]) -> set[str]:
    esquemas = _esquemas(documento)
    pendentes = set()
    for operacoes in documento["paths"].values():
        for operacao in operacoes.values():
            pendentes |= _referencias(operacao["responses"])
    vistos: set[str] = set()
    while pendentes:
        nome = pendentes.pop()
        if nome not in vistos:
            vistos.add(nome)
            pendentes |= _referencias(esquemas[nome]) - vistos
    return vistos


def test_nenhuma_saida_expoe_hash_token_ou_segredo(mundo: Mundo) -> None:
    documento = mundo.app.openapi()
    esquemas = _esquemas(documento)
    de_resposta = _esquemas_de_resposta(documento)
    assert "UsuarioSaida" in de_resposta
    assert "CredencialEntrada" not in de_resposta  # entradas de senha nunca voltam em resposta
    for nome in de_resposta:
        propriedades = set(esquemas[nome].get("properties", {}))
        assert not CAMPOS_PROIBIDOS_NA_SAIDA & propriedades, f"{nome} expõe campo sensível"


def test_entradas_de_senha_tem_limite_de_tamanho(mundo: Mundo) -> None:
    esquemas = _esquemas(mundo.app.openapi())
    for nome in ("LoginEntrada", "SenhaAlterarEntrada", "CredencialEntrada"):
        for campo, propriedade in esquemas[nome]["properties"].items():
            if "senha" in campo:
                assert propriedade["maxLength"] == 128, (nome, campo)


def test_documentacao_pode_ser_desligada_por_configuracao(mundo: Mundo) -> None:
    from dataclasses import replace

    from fastapi.testclient import TestClient

    from manutencao.api import criar_app

    cfg = replace(mundo.configuracao, documentacao=False)
    app = criar_app(replace(mundo.aplicacao.contexto, configuracao=cfg))
    http = TestClient(app)
    for caminho in ("/docs", "/redoc", "/openapi.json"):
        assert http.get(caminho).status_code == 404


# ------------------------------------------------------------------------------------------ erros
def test_rota_inexistente_e_metodo_nao_permitido_respondem_json(mundo: Mundo) -> None:
    http = mundo.navegador()
    nao = http.get(f"{PREFIXO}/nada")
    assert nao.status_code == 404
    assert nao.json()["codigo"] == "rota_nao_encontrada"
    metodo = http.delete(f"{PREFIXO}/saude")
    assert metodo.status_code == 405
    assert metodo.json()["codigo"] == "metodo_nao_permitido"


def test_erro_interno_e_generico_e_nao_vaza_detalhes(
    mundo: Mundo, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    ana = mundo.entrar(ANA)

    def quebrar(*_: object, **__: object) -> None:
        raise RuntimeError("segredo-interno postgresql://user:senha@host/db")

    monkeypatch.setattr(mundo.aplicacao.contexto.painel, "consultar", quebrar)
    with caplog.at_level("ERROR", logger="manutencao.api"):
        r = ana.get("/painel")
    assert r.status_code == 500
    assert r.json() == {"codigo": "erro_interno", "mensagem": "Erro interno do servidor."}
    assert "segredo-interno" not in r.text
    assert "postgresql://" not in r.text
    assert any(
        "Erro inesperado" in m for m in caplog.messages
    )  # a causa vai para o log, não ao cliente


def test_todo_erro_de_dominio_tem_codigo_e_mensagem(mundo: Mundo) -> None:
    r = mundo.entrar(BRUNO).get("/usuarios")
    assert set(r.json()) == {"codigo", "mensagem"}


def test_corpo_nao_json_e_422(mundo: Mundo) -> None:
    ana = mundo.entrar(ANA)
    r = ana.http.post(
        f"{PREFIXO}/equipamentos",
        content=b"isto nao e json",
        headers={"X-CSRF-Token": ana.csrf, "Content-Type": "application/json"},
    )
    assert r.status_code == 422
    assert r.json()["codigo"] == "entrada_invalida"


def test_detalhes_de_validacao_nomeiam_o_campo(mundo: Mundo) -> None:
    ana = mundo.entrar(ANA)
    r = ana.post("/equipamentos", {"nome": "x"})
    detalhes = r.json()["detalhes"]
    assert detalhes == [{"campo": "modelo", "mensagem": "Field required"}]


# ----------------------------------------------------------------------------------------- saúde
def test_saude_e_publica_e_informa_o_banco(mundo: Mundo) -> None:
    r = mundo.navegador().get(f"{PREFIXO}/saude")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "banco": "ok"}


def test_saude_degradada_quando_o_banco_cai(mundo: Mundo) -> None:
    from dataclasses import replace

    from fastapi.testclient import TestClient

    from manutencao.api import criar_app

    contexto = replace(mundo.aplicacao.contexto, banco_disponivel=lambda: False)
    r = TestClient(criar_app(contexto)).get(f"{PREFIXO}/saude")
    assert r.json() == {"status": "degradado", "banco": "indisponivel"}


# ----------------------------------------------------------------------------------------- painel
def test_painel_reflete_as_ordens_e_a_disponibilidade(mundo: Mundo) -> None:
    ana, bruno = mundo.entrar(ANA), mundo.entrar(BRUNO)
    for falha, crit in (("a", "Alta"), ("b", "Baixa"), ("c", "Alta")):
        bruno.post("/ordens", {"equipamento_id": 1, "falha": falha, "criticidade": crit})
    ana.post("/ordens/1/atribuicao", {"tecnico_id": BRUNO})
    ana.post("/ordens/3/cancelamento", {"motivo": "m"})
    painel = bruno.get("/painel").json()
    assert (painel["total"], painel["em_aberto"], painel["encerradas"]) == (3, 2, 1)
    assert painel["minhas_em_aberto"] == 1
    por_status = {s["status"]: s["quantidade"] for s in painel["por_status"]}
    assert por_status["Aberta"] == 1
    assert por_status["Atribuída"] == 1
    assert por_status["Cancelada"] == 1
    assert sum(por_status.values()) == 3
    criticidades = {c["criticidade"]: c["quantidade"] for c in painel["por_criticidade_em_aberto"]}
    assert criticidades == {"Baixa": 1, "Média": 0, "Alta": 1, "Crítica": 0}
    assert [o["numero"] for o in painel["recentes"]] == [3, 2, 1]
    assert {t["id"] for t in painel["tecnicos"]} == {2, 3}


def test_painel_vazio_e_exige_autenticacao(mundo: Mundo) -> None:
    painel = mundo.entrar(ANA).get("/painel").json()
    assert painel["total"] == 0
    assert painel["recentes"] == []
    assert len(painel["por_status"]) == 8
    assert mundo.navegador().get(f"{PREFIXO}/painel").status_code == 401
