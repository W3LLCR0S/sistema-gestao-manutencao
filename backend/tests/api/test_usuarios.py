"""Usuários, cargos, permissões e disponibilidade pela API (regras vêm dos serviços)."""

import pytest

from manutencao.domain.matricula import matricula_valida
from tests.apoio.ambiente import ANA, BRUNO, CARLA
from tests.apoio.api import MAT_ANA, MAT_BRUNO, MAT_CARLA, MATRICULAS, PREFIXO, SENHA, Mundo

NOVO = {"nome": "Diego Rocha", "cargo_id": 2, "papel": "Técnico", "email": "d@x.com"}


def _abrir_os_atribuida(mundo: Mundo, tecnico: int) -> None:
    ana = mundo.entrar(ANA)
    numero = ana.post(
        "/ordens", {"equipamento_id": 1, "falha": "Falha qualquer", "criticidade": "Média"}
    ).json()["numero"]
    assert ana.post(f"/ordens/{numero}/atribuicao", {"tecnico_id": tecnico}).status_code == 200


# --------------------------------------------------------------------------------------- consulta
def test_gestor_lista_usuarios_sem_hash_nem_segredos(mundo: Mundo) -> None:
    r = mundo.entrar(ANA).get("/usuarios")
    assert r.status_code == 200
    corpo = r.json()
    assert corpo["total"] == 3
    assert [u["id"] for u in corpo["itens"]] == [1, 2, 3]
    texto = r.text.casefold()
    assert "hash" not in texto
    assert "senha" not in texto
    assert "argon" not in texto
    ana = corpo["itens"][0]
    assert ana["cargo"] == {"id": 1, "nome": "Gestor"}
    assert "gerir_usuarios" in ana["permissoes"]


def test_tecnico_nao_lista_nem_consulta_usuarios(mundo: Mundo) -> None:
    bruno = mundo.entrar(BRUNO)
    for caminho in ("/usuarios", f"/usuarios/{ANA}", "/cargos"):
        r = bruno.get(caminho)
        assert r.status_code == 403, caminho
        assert r.json()["codigo"] == "sem_permissao"


def test_paginacao_de_usuarios(mundo: Mundo) -> None:
    ana = mundo.entrar(ANA)
    p1 = ana.get("/usuarios?limite=2&deslocamento=0").json()
    p2 = ana.get("/usuarios?limite=2&deslocamento=2").json()
    assert [u["id"] for u in p1["itens"]] == [1, 2]
    assert p1["total"] == 3
    assert [u["id"] for u in p2["itens"]] == [3]
    assert (p1["limite"], p1["deslocamento"]) == (2, 0)
    assert ana.get("/usuarios?deslocamento=99").json()["itens"] == []


@pytest.mark.parametrize("consulta", ["limite=0", "limite=201", "deslocamento=-1", "limite=abc"])
def test_paginacao_invalida_e_422(mundo: Mundo, consulta: str) -> None:
    r = mundo.entrar(ANA).get(f"/usuarios?{consulta}")
    assert r.status_code == 422
    assert r.json()["codigo"] == "entrada_invalida"


def test_filtros_de_usuarios(mundo: Mundo) -> None:
    ana = mundo.entrar(ANA)
    assert [u["id"] for u in ana.get("/usuarios?papel=Técnico").json()["itens"]] == [2, 3]
    ana.post(f"/usuarios/{CARLA}/desativar")
    assert [u["id"] for u in ana.get("/usuarios?ativo=false").json()["itens"]] == [3]
    assert [u["id"] for u in ana.get("/usuarios?ativo=true&papel=Técnico").json()["itens"]] == [2]
    assert ana.get("/usuarios?papel=Chefe").status_code == 422


def test_consultar_usuario_e_inexistente(mundo: Mundo) -> None:
    ana = mundo.entrar(ANA)
    assert ana.get(f"/usuarios/{BRUNO}").json()["nome"] == "Bruno Lima"
    r = ana.get("/usuarios/99")
    assert r.status_code == 404
    assert r.json()["codigo"] == "nao_encontrado"


# --------------------------------------------------------------------------------------- cadastro
def test_cadastrar_usuario(mundo: Mundo) -> None:
    r = mundo.entrar(ANA).post("/usuarios", NOVO)
    assert r.status_code == 201
    corpo = r.json()
    assert corpo["id"] == 4
    assert corpo["ativo"] is True
    assert corpo["disponibilidade"] == "Disponível"
    assert corpo["papel"] == "Técnico"
    assert corpo["cargo"]["nome"] == "Técnico"


def test_cadastrar_gera_a_matricula_e_a_devolve_na_confirmacao(mundo: Mundo) -> None:
    r = mundo.entrar(ANA).post("/usuarios", NOVO)
    assert r.status_code == 201
    matricula = r.json()["matricula"]
    assert matricula_valida(matricula)
    assert matricula not in MATRICULAS.values()


def test_matricula_nao_pode_ser_informada_no_cadastro(mundo: Mundo) -> None:
    r = mundo.entrar(ANA).post("/usuarios", {**NOVO, "matricula": "AB123456"})
    assert r.status_code == 422  # campo desconhecido: a matrícula é gerada pelo sistema


def test_cadastrar_com_senha_permite_login_imediato_pela_matricula(mundo: Mundo) -> None:
    ana = mundo.entrar(ANA)
    r = ana.post("/usuarios", {**NOVO, "senha": "senha-do-diego-123"})
    assert r.status_code == 201
    matricula = r.json()["matricula"]
    novo = mundo.navegador()
    ok = novo.post(
        f"{PREFIXO}/auth/login", json={"matricula": matricula, "senha": "senha-do-diego-123"}
    )
    assert ok.status_code == 200
    assert ok.json()["usuario"]["id"] == 4
    assert ok.json()["usuario"]["matricula"] == matricula


def test_cadastrar_com_o_campo_antigo_login_e_recusado_e_senha_fraca_nao_cria_nada(
    mundo: Mundo,
) -> None:
    ana = mundo.entrar(ANA)
    assert ana.post("/usuarios", {**NOVO, "login": "diego"}).status_code == 422
    assert ana.post("/usuarios", {**NOVO, "senha": "curta"}).status_code == 422
    assert ana.get("/usuarios").json()["total"] == 3
    assert ana.post("/usuarios", NOVO).json()["id"] == 4  # nenhum id foi gasto


def test_matriculas_geradas_sao_unicas_entre_varios_cadastros(mundo: Mundo) -> None:
    ana = mundo.entrar(ANA)
    geradas = [
        ana.post("/usuarios", {**NOVO, "nome": f"Pessoa {i}"}).json()["matricula"]
        for i in range(15)
    ]
    todas = [*geradas, *MATRICULAS.values()]
    assert len(set(todas)) == len(todas)
    assert all(matricula_valida(m) for m in geradas)


def test_listagem_e_detalhe_mostram_a_matricula(mundo: Mundo) -> None:
    ana = mundo.entrar(ANA)
    itens = ana.get("/usuarios").json()["itens"]
    assert {u["id"]: u["matricula"] for u in itens} == MATRICULAS
    assert ana.get(f"/usuarios/{BRUNO}").json()["matricula"] == MAT_BRUNO
    assert ana.get("/auth/me").json()["usuario"]["matricula"] == MAT_ANA


def test_gestor_pesquisa_usuarios_por_matricula(mundo: Mundo) -> None:
    ana = mundo.entrar(ANA)
    por_inteira = ana.get("/usuarios", params={"busca": MAT_BRUNO}).json()
    assert [u["id"] for u in por_inteira["itens"]] == [BRUNO]
    por_parte = ana.get("/usuarios", params={"busca": MAT_CARLA[:4].lower()}).json()
    assert [u["id"] for u in por_parte["itens"]] == [CARLA]
    assert ana.get("/usuarios", params={"busca": "ZZ999999"}).json()["total"] == 0
    assert ana.get("/usuarios", params={"busca": "bruno"}).json()["total"] == 1  # nome também


def test_tecnico_nao_consulta_matriculas_de_outros(mundo: Mundo) -> None:
    bruno = mundo.entrar(BRUNO)
    assert bruno.get("/usuarios").status_code == 403
    assert bruno.get(f"/usuarios/{ANA}").status_code == 403
    assert bruno.get("/usuarios", params={"busca": MAT_ANA}).status_code == 403


def test_matricula_e_imutavel_pela_api(mundo: Mundo) -> None:
    ana = mundo.entrar(ANA)
    r = ana.patch(f"/usuarios/{BRUNO}", {"matricula": "AB123456"})
    assert r.status_code == 422
    r = ana.patch(f"/usuarios/{BRUNO}", {"nome": "Bruno Lima Jr."})  # outras edições preservam
    assert r.status_code == 200
    assert r.json()["matricula"] == MAT_BRUNO
    ana.put(f"/usuarios/{BRUNO}/cargo", {"cargo_id": 1})
    ana.post(f"/usuarios/{BRUNO}/desativar")
    ana.post(f"/usuarios/{BRUNO}/reativar")
    assert ana.get(f"/usuarios/{BRUNO}").json()["matricula"] == MAT_BRUNO


@pytest.mark.parametrize(
    ("alteracao", "codigo"),
    [
        ({"nome": "   "}, "campo_obrigatorio"),
        ({"cargo_id": 99}, "nao_encontrado"),
    ],
)
def test_cadastro_recusado_pelo_dominio(
    mundo: Mundo, alteracao: dict[str, object], codigo: str
) -> None:
    r = mundo.entrar(ANA).post("/usuarios", {**NOVO, **alteracao})
    assert r.json()["codigo"] == codigo
    assert r.status_code in (404, 422)


@pytest.mark.parametrize(
    "corpo",
    [
        {},
        {**NOVO, "papel": "Chefe"},
        {**NOVO, "cargo_id": "dois"},
        {**NOVO, "nome": "x" * 201},
        {**NOVO, "ator_id": 1},
        {**NOVO, "ativo": False},
    ],
)
def test_cadastro_valida_a_forma_da_entrada(mundo: Mundo, corpo: dict[str, object]) -> None:
    r = mundo.entrar(ANA).post("/usuarios", corpo)
    assert r.status_code == 422
    assert r.json()["codigo"] == "entrada_invalida"


def test_tecnico_nao_cadastra(mundo: Mundo) -> None:
    assert mundo.entrar(BRUNO).post("/usuarios", NOVO).status_code == 403


def test_atualizar_apenas_os_campos_informados(mundo: Mundo) -> None:
    ana = mundo.entrar(ANA)
    r = ana.patch(f"/usuarios/{BRUNO}", {"escala": "Seg-Sab 06h-14h"})
    assert r.status_code == 200
    assert r.json()["escala"] == "Seg-Sab 06h-14h"
    assert r.json()["nome"] == "Bruno Lima"
    assert ana.patch(f"/usuarios/{BRUNO}", {"nome": ""}).status_code == 422
    assert (
        ana.patch(f"/usuarios/{BRUNO}", {"papel": "Gestor"}).status_code == 422
    )  # campo desconhecido


# ---------------------------------------------------------------------------- cargo, papel, ativo
def test_alterar_cargo_muda_as_permissoes_efetivas(mundo: Mundo) -> None:
    ana, bruno = mundo.entrar(ANA), mundo.entrar(BRUNO)
    assert ana.put(f"/usuarios/{BRUNO}/cargo", {"cargo_id": 1}).status_code == 200
    assert "gerir_usuarios" in bruno.get("/auth/me").json()["usuario"]["permissoes"]
    assert bruno.get("/usuarios").status_code == 200  # a permissão vale na requisição seguinte


def test_ninguem_remove_de_si_o_acesso_de_gestao(mundo: Mundo) -> None:
    ana = mundo.entrar(ANA)
    r = ana.put(f"/usuarios/{ANA}/cargo", {"cargo_id": 2})
    assert r.status_code == 409
    assert r.json()["codigo"] == "autoremocao_de_acesso_de_gestao"
    r = ana.put(f"/usuarios/{ANA}/papel", {"papel": "Técnico"})
    assert r.status_code == 409
    assert r.json()["codigo"] == "autoremocao_de_acesso_de_gestao"
    r = ana.post(f"/usuarios/{ANA}/desativar")
    assert r.status_code == 409
    assert r.json()["codigo"] == "autoremocao_de_acesso_de_gestao"
    r = ana.delete(f"/usuarios/{ANA}")
    assert r.status_code == 409
    assert r.json()["codigo"] == "autoexclusao"
    assert ana.get("/usuarios/1").json()["ativo"] is True


def test_alterar_papel_e_so_do_gestor(mundo: Mundo) -> None:
    ana, bruno = mundo.entrar(ANA), mundo.entrar(BRUNO)
    assert bruno.put(f"/usuarios/{CARLA}/papel", {"papel": "Gestor"}).status_code == 403
    r = ana.put(f"/usuarios/{CARLA}/papel", {"papel": "Gestor"})
    assert r.status_code == 200
    assert r.json()["papel"] == "Gestor"


def test_usuario_com_os_ativa_nao_e_desativado_nem_deixa_de_ser_tecnico(mundo: Mundo) -> None:
    _abrir_os_atribuida(mundo, BRUNO)
    ana = mundo.entrar(ANA)
    r = ana.post(f"/usuarios/{BRUNO}/desativar")
    assert r.status_code == 409
    assert r.json()["codigo"] == "usuario_com_os_ativas"
    r = ana.put(f"/usuarios/{BRUNO}/papel", {"papel": "Gestor"})
    assert r.status_code == 409
    assert r.json()["codigo"] == "usuario_com_os_ativas"
    assert ana.get(f"/usuarios/{BRUNO}").json()["ativo"] is True


def test_desativar_revoga_sessoes_e_impede_novo_login_reativar_restaura(mundo: Mundo) -> None:
    ana, carla = mundo.entrar(ANA), mundo.entrar(CARLA)
    r = ana.post(f"/usuarios/{CARLA}/desativar")
    assert r.status_code == 200
    assert r.json()["ativo"] is False
    assert r.json()["permissoes"] == []  # inativo não tem permissão efetiva
    assert carla.get("/auth/me").status_code == 401
    tentativa = mundo.navegador().post(
        f"{PREFIXO}/auth/login", json={"matricula": MATRICULAS[CARLA], "senha": SENHA}
    )
    assert tentativa.status_code == 401
    assert ana.post(f"/usuarios/{CARLA}/desativar").status_code == 200  # idempotente
    assert ana.post(f"/usuarios/{CARLA}/reativar").json()["ativo"] is True
    assert mundo.entrar(CARLA).get("/auth/me").status_code == 200


def test_usuario_inativo_nao_e_atribuivel(mundo: Mundo) -> None:
    ana = mundo.entrar(ANA)
    numero = ana.post(
        "/ordens", {"equipamento_id": 1, "falha": "Falha", "criticidade": "Baixa"}
    ).json()["numero"]
    ana.post(f"/usuarios/{CARLA}/desativar")
    r = ana.post(f"/ordens/{numero}/atribuicao", {"tecnico_id": CARLA})
    assert r.status_code >= 400
    assert ana.get(f"/ordens/{numero}").json()["tecnico"] is None


def test_excluir_usuario_sem_historico_e_com_historico(mundo: Mundo) -> None:
    ana = mundo.entrar(ANA)
    ana.post(
        "/ordens", {"equipamento_id": 1, "falha": "Falha", "criticidade": "Baixa"}
    )  # Ana tem histórico
    mundo.entrar(BRUNO).post(
        "/ordens", {"equipamento_id": 1, "falha": "Outra", "criticidade": "Baixa"}
    )
    r = ana.delete(f"/usuarios/{BRUNO}")
    assert r.status_code == 409
    assert r.json()["codigo"] == "usuario_com_historico"
    carla = mundo.entrar(CARLA)
    assert ana.delete(f"/usuarios/{CARLA}").status_code == 204
    assert ana.get(f"/usuarios/{CARLA}").status_code == 404
    assert carla.get("/auth/me").status_code == 401
    assert (
        mundo.navegador()
        .post(f"{PREFIXO}/auth/login", json={"matricula": MAT_CARLA, "senha": SENHA})
        .status_code
        == 401
    )


# ---------------------------------------------------------------------------------- disponibilidade
def test_disponibilidade_propria_e_de_terceiros(mundo: Mundo) -> None:
    ana, bruno = mundo.entrar(ANA), mundo.entrar(BRUNO)
    r = bruno.put("/me/disponibilidade", {"disponibilidade": "Ausente"})
    assert r.status_code == 200
    assert r.json()["disponibilidade"] == "Ausente"
    consulta = ana.get("/disponibilidade").json()
    assert {linha["id"]: linha["disponibilidade"] for linha in consulta} == {
        BRUNO: "Ausente",
        CARLA: "Disponível",
    }
    assert (
        ana.put(f"/usuarios/{BRUNO}/disponibilidade", {"disponibilidade": "Disponível"}).status_code
        == 200
    )
    r = bruno.put(f"/usuarios/{CARLA}/disponibilidade", {"disponibilidade": "Ausente"})
    assert r.status_code == 403  # sem gerir_usuarios, só a própria


def test_em_atendimento_e_derivado_nao_manual(mundo: Mundo) -> None:
    r = mundo.entrar(BRUNO).put("/me/disponibilidade", {"disponibilidade": "Em atendimento"})
    assert r.status_code == 422
    assert r.json()["codigo"] == "disponibilidade_manual_invalida"
    assert (
        mundo.entrar(BRUNO).put("/me/disponibilidade", {"disponibilidade": "Folga"}).status_code
        == 422
    )


def test_disponibilidade_derivada_das_os_em_execucao(mundo: Mundo) -> None:
    _abrir_os_atribuida(mundo, BRUNO)
    bruno, ana = mundo.entrar(BRUNO), mundo.entrar(ANA)
    assert bruno.post("/ordens/1/status", {"status": "Em Execução"}).status_code == 200
    linhas = {linha["id"]: linha for linha in ana.get("/disponibilidade").json()}
    assert linhas[BRUNO]["disponibilidade"] == "Em atendimento"
    assert linhas[BRUNO]["carga"] == 1
    assert linhas[CARLA]["disponibilidade"] == "Disponível"
    assert linhas[CARLA]["carga"] == 0
    ordenada = ana.get("/disponibilidade?ordenar_por_carga=true").json()
    assert [linha["id"] for linha in ordenada] == [CARLA, BRUNO]


# --------------------------------------------------------------------------- cargos e permissões
def test_listar_cargos_e_catalogo_de_permissoes(mundo: Mundo) -> None:
    ana, bruno = mundo.entrar(ANA), mundo.entrar(BRUNO)
    cargos = ana.get("/cargos").json()
    assert [c["nome"] for c in cargos] == ["Gestor", "Técnico"]
    catalogo = bruno.get("/permissoes").json()  # qualquer autenticado
    assert len(catalogo) == 13
    assert all(item["descricao"] for item in catalogo)


def test_alterar_permissoes_do_cargo_vale_na_requisicao_seguinte(mundo: Mundo) -> None:
    ana, bruno = mundo.entrar(ANA), mundo.entrar(BRUNO)
    cargo = ana.get("/cargos").json()[1]
    novas = [p for p in cargo["permissoes"] if p != "abrir_os"]
    r = ana.put("/cargos/2/permissoes", {"permissoes": novas})
    assert r.status_code == 200
    assert "abrir_os" not in r.json()["permissoes"]
    r = bruno.post("/ordens", {"equipamento_id": 1, "falha": "x", "criticidade": "Baixa"})
    assert r.status_code == 403
    assert r.json()["codigo"] == "sem_permissao"
    assert "abrir_os" not in bruno.get("/auth/me").json()["usuario"]["permissoes"]


def test_permissao_desconhecida_e_recusada_e_nada_muda(mundo: Mundo) -> None:
    ana = mundo.entrar(ANA)
    antes = ana.get("/cargos").json()
    r = ana.put("/cargos/2/permissoes", {"permissoes": ["ver_os", "voar"]})
    assert r.status_code == 422
    assert r.json()["codigo"] == "entrada_invalida"
    assert ana.get("/cargos").json() == antes


def test_gestor_nao_tira_do_proprio_cargo_o_acesso_de_gestao(mundo: Mundo) -> None:
    ana = mundo.entrar(ANA)
    r = ana.put("/cargos/1/permissoes", {"permissoes": ["ver_os"]})
    assert r.status_code == 409
    assert r.json()["codigo"] == "autoremocao_de_acesso_de_gestao"
    assert "gerir_usuarios" in ana.get("/cargos").json()[0]["permissoes"]


def test_cargo_inexistente(mundo: Mundo) -> None:
    assert mundo.entrar(ANA).put("/cargos/99/permissoes", {"permissoes": []}).status_code == 404
