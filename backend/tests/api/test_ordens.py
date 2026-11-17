"""Ordens de serviço pela API: fluxo completo, permissões, transições e filtros.

O ator vem sempre da sessão. As regras (permissão, posse, transições, D-03/D-06) são do domínio; os
testes verificam que a API as **expõe** com os códigos HTTP certos e não cria atalho por fora.
"""

import pytest

from tests.apoio.ambiente import ANA, BRUNO, CARLA
from tests.apoio.api import Mundo

ABERTURA = {"equipamento_id": 1, "falha": "Vibração excessiva no eixo", "criticidade": "Alta"}


def _abrir(cliente, corpo: dict[str, object] | None = None) -> int:  # type: ignore[no-untyped-def]
    r = cliente.post("/ordens", corpo or ABERTURA)
    assert r.status_code == 201, r.text
    return int(r.json()["numero"])


def _pronta_para_aprovar(mundo: Mundo) -> int:
    """OS atribuída a Bruno, diagnosticada, reparada, finalizada e submetida à aprovação."""
    ana, bruno = mundo.entrar(ANA), mundo.entrar(BRUNO)
    n = _abrir(ana)
    assert ana.post(f"/ordens/{n}/atribuicao", {"tecnico_id": BRUNO}).status_code == 200
    assert (
        bruno.post(f"/ordens/{n}/diagnostico", {"parecer": "p", "causa_raiz": "c"}).status_code
        == 200
    )
    assert (
        bruno.post(f"/ordens/{n}/reparos", {"horas": 1, "intervencao": "trocou"}).status_code == 200
    )
    assert bruno.post(f"/ordens/{n}/status", {"status": "Reparo Finalizado"}).status_code == 200
    r = bruno.post(f"/ordens/{n}/conclusao-tecnica", {"teste": "ok", "passou": True})
    assert r.json()["submetida_a_aprovacao"] is True
    return n


# ------------------------------------------------------------------------------ fluxo completo
def test_fluxo_completo_da_abertura_a_aprovacao(mundo: Mundo) -> None:
    ana, bruno, carla = mundo.entrar(ANA), mundo.entrar(BRUNO), mundo.entrar(CARLA)

    aberta = bruno.post("/ordens", ABERTURA)
    assert aberta.status_code == 201
    os_ = aberta.json()
    assert os_["numero"] == 1
    assert os_["status"] == "Aberta"
    assert os_["tecnico"] is None
    assert os_["aberta_por"] == {"id": BRUNO, "nome": "Bruno Lima"}
    assert os_["equipamento"]["nome"] == "Torno CNC"
    assert os_["encerrada"] is False

    primeira = ana.post("/ordens/1/atribuicao", {"tecnico_id": CARLA}).json()
    assert primeira["tecnico_anterior"] is None
    assert primeira["ordem"]["status"] == "Atribuída"
    reatribuida = ana.post("/ordens/1/atribuicao", {"tecnico_id": BRUNO}).json()
    assert reatribuida["tecnico_anterior"] == {"id": CARLA, "nome": "Carla Mendes"}
    assert reatribuida["ordem"]["tecnico"]["id"] == BRUNO

    # quem não é o técnico da OS não executa (mesmo com a permissão do cargo)
    for rota, corpo in (
        ("diagnostico", {"parecer": "p", "causa_raiz": "c"}),
        ("reparos", {"horas": 1, "intervencao": "x"}),
        ("status", {"status": "Em Execução"}),
    ):
        r = carla.post(f"/ordens/1/{rota}", corpo)
        assert r.status_code == 403 and r.json()["codigo"] == "nao_responsavel", rota

    diag = bruno.post("/ordens/1/diagnostico", {"parecer": "Rolamento", "causa_raiz": "Desgaste"})
    assert diag.status_code == 200
    assert diag.json()["diagnostico"] == "Rolamento"

    reparo = bruno.post(
        "/ordens/1/reparos",
        {
            "horas": 2.5,
            "intervencao": "Troca do rolamento",
            "pecas": [{"descricao": "Rolamento 6205", "quantidade": 2}],
        },
    ).json()
    assert reparo["horas_trabalhadas"] == 2.5
    assert reparo["status"] == "Em Execução"
    assert reparo["intervencoes"] == ["Troca do rolamento"]
    assert reparo["pecas"] == [{"descricao": "Rolamento 6205", "quantidade": 2.0}]

    assert bruno.post("/ordens/1/status", {"status": "Reparo Finalizado"}).json()["status"] == (
        "Reparo Finalizado"
    )
    concl = bruno.post("/ordens/1/conclusao-tecnica", {"teste": "30 min sem ruído", "passou": True})
    assert concl.json()["submetida_a_aprovacao"] is True
    assert concl.json()["ordem"]["status"] == "Aguardando Aprovação"

    aprovada = ana.post("/ordens/1/aprovacao").json()
    assert aprovada["status"] == "Concluída"
    assert aprovada["encerrada"] is True
    assert aprovada["data_conclusao"] is not None
    assert aprovada["teste_funcional"]

    historico = ana.get("/ordens/1/historico").json()
    assert [s["numero"] for s in historico] == list(range(1, len(historico) + 1))
    tipos = [s["tipo"] for s in historico]
    assert tipos[0] == "Abertura"
    assert tipos[-2:] == ["Encerramento", "Mudança de status"]  # encerra e muda para Concluída
    assert {"Atribuição", "Reatribuição", "Diagnóstico", "Reparo", "Conclusão técnica"} <= set(
        tipos
    )
    reparo_hist = next(s for s in historico if s["tipo"] == "Reparo")
    assert reparo_hist["horas"] == 2.5
    assert reparo_hist["responsavel"]["id"] == BRUNO
    assert reparo_hist["pecas"][0]["quantidade"] == 2.0


def test_teste_reprovado_registra_mas_nao_submete(mundo: Mundo) -> None:
    ana, bruno = mundo.entrar(ANA), mundo.entrar(BRUNO)
    n = _abrir(ana)
    ana.post(f"/ordens/{n}/atribuicao", {"tecnico_id": BRUNO})
    bruno.post(f"/ordens/{n}/diagnostico", {"parecer": "p", "causa_raiz": "c"})
    bruno.post(f"/ordens/{n}/reparos", {"horas": 1, "intervencao": "i"})
    bruno.post(f"/ordens/{n}/status", {"status": "Reparo Finalizado"})
    r = bruno.post(f"/ordens/{n}/conclusao-tecnica", {"teste": "vibrou", "passou": False}).json()
    assert r["submetida_a_aprovacao"] is False
    assert r["ordem"]["status"] == "Reparo Finalizado"
    tipos = [s["tipo"] for s in ana.get(f"/ordens/{n}/historico").json()]
    assert "Teste funcional" in tipos  # o registro do teste ficou no histórico


def test_reprovacao_devolve_a_os_ao_tecnico(mundo: Mundo) -> None:
    n = _pronta_para_aprovar(mundo)
    ana = mundo.entrar(ANA)
    r = ana.post(f"/ordens/{n}/reprovacao", {"motivo": "Ainda vibra"})
    assert r.status_code == 200
    assert r.json()["status"] == "Em Execução"
    assert r.json()["encerrada"] is False
    assert ana.post(f"/ordens/{n}/reprovacao", {"motivo": "de novo"}).status_code == 409


# --------------------------------------------------------------------------------- permissões
def test_so_o_gestor_atribui_aprova_reprova_e_cancela(mundo: Mundo) -> None:
    n = _pronta_para_aprovar(mundo)
    bruno = mundo.entrar(BRUNO)
    for r in (
        bruno.post(f"/ordens/{n}/atribuicao", {"tecnico_id": CARLA}),
        bruno.post(f"/ordens/{n}/aprovacao"),
        bruno.post(f"/ordens/{n}/reprovacao", {"motivo": "m"}),
        bruno.post(f"/ordens/{n}/cancelamento", {"motivo": "m"}),
    ):
        assert r.status_code == 403
        assert r.json()["codigo"] == "sem_permissao"


def test_gestor_nao_executa_o_trabalho_tecnico(mundo: Mundo) -> None:
    ana = mundo.entrar(ANA)
    n = _abrir(ana)
    for rota, corpo in (
        ("diagnostico", {"parecer": "p", "causa_raiz": "c"}),
        ("reparos", {"horas": 1, "intervencao": "x"}),
        ("status", {"status": "Em Execução"}),
        ("conclusao-tecnica", {"teste": "t", "passou": True}),
    ):
        assert ana.post(f"/ordens/{n}/{rota}", corpo).status_code == 403, rota


def test_a_permissao_vence_a_existencia_do_recurso(mundo: Mundo) -> None:
    """Sem permissão, a resposta é 403 mesmo para uma OS inexistente (não vaza existência)."""
    bruno = mundo.entrar(BRUNO)
    assert bruno.post("/ordens/99/aprovacao").status_code == 403
    assert bruno.post("/ordens/99/atribuicao", {"tecnico_id": 1}).status_code == 403


def test_consulta_de_os_inexistente_e_404(mundo: Mundo) -> None:
    ana = mundo.entrar(ANA)
    for r in (
        ana.get("/ordens/99"),
        ana.get("/ordens/99/historico"),
        ana.post("/ordens/99/aprovacao"),
    ):
        assert r.status_code == 404
        assert r.json()["codigo"] == "nao_encontrado"


def test_equipamento_inexistente_na_abertura(mundo: Mundo) -> None:
    r = mundo.entrar(BRUNO).post("/ordens", {**ABERTURA, "equipamento_id": 99})
    assert r.status_code == 404


# ----------------------------------------------------------------------- atribuição e ausência
def test_atribuir_tecnico_ausente_exige_confirmacao_explicita(mundo: Mundo) -> None:
    ana = mundo.entrar(ANA)
    mundo.entrar(CARLA).put("/me/disponibilidade", {"disponibilidade": "Ausente"})
    n = _abrir(ana)
    recusada = ana.post(f"/ordens/{n}/atribuicao", {"tecnico_id": CARLA})
    assert recusada.status_code >= 400
    assert recusada.json()["codigo"] == "tecnico_ausente"
    assert ana.get(f"/ordens/{n}").json()["tecnico"] is None
    aceita = ana.post(f"/ordens/{n}/atribuicao", {"tecnico_id": CARLA, "confirmar_ausente": True})
    assert aceita.status_code == 200
    assert aceita.json()["ordem"]["tecnico"]["id"] == CARLA


def test_nao_atribui_a_gestor_nem_a_usuario_inexistente(mundo: Mundo) -> None:
    ana = mundo.entrar(ANA)
    n = _abrir(ana)
    r = ana.post(f"/ordens/{n}/atribuicao", {"tecnico_id": ANA})
    assert r.status_code >= 400
    assert r.json()["codigo"] == "nao_e_tecnico"
    assert ana.post(f"/ordens/{n}/atribuicao", {"tecnico_id": 99}).status_code == 404


# ------------------------------------------------------------------------- transições inválidas
def test_transicoes_invalidas_sao_conflitos(mundo: Mundo) -> None:
    ana, bruno = mundo.entrar(ANA), mundo.entrar(BRUNO)
    n = _abrir(ana)
    ana.post(f"/ordens/{n}/atribuicao", {"tecnico_id": BRUNO})
    r = bruno.post(f"/ordens/{n}/status", {"status": "Concluída"})  # status só o gestor encerra
    assert r.status_code == 422
    assert r.json()["codigo"] == "status_nao_permitido"
    r = bruno.post(f"/ordens/{n}/status", {"status": "Reparo Finalizado"})  # sem intervenção
    assert r.status_code == 422
    assert r.json()["codigo"] == "sem_intervencao"
    r = bruno.post(f"/ordens/{n}/conclusao-tecnica", {"teste": "t", "passou": True})
    assert r.status_code in (409, 422)  # sem diagnóstico
    assert r.json()["codigo"] in ("sem_diagnostico", "estado_invalido")


def test_status_invalido_e_422(mundo: Mundo) -> None:
    ana = mundo.entrar(ANA)
    n = _abrir(ana)
    assert ana.post(f"/ordens/{n}/status", {"status": "Quebrada"}).status_code == 422


def test_os_encerrada_nao_aceita_mais_operacoes(mundo: Mundo) -> None:
    ana, bruno = mundo.entrar(ANA), mundo.entrar(BRUNO)
    n = _abrir(ana)
    r = ana.post(f"/ordens/{n}/cancelamento", {"motivo": "Duplicada"})
    assert r.status_code == 200
    assert r.json()["status"] == "Cancelada"
    assert r.json()["motivo_cancelamento"] == "Duplicada"
    assert r.json()["encerrada"] is True
    esperados = (
        (ana.post(f"/ordens/{n}/cancelamento", {"motivo": "outra vez"}), "os_encerrada"),
        (ana.post(f"/ordens/{n}/atribuicao", {"tecnico_id": BRUNO}), "estado_invalido"),
        (ana.post(f"/ordens/{n}/apontamentos", {"texto": "tarde demais"}), "os_encerrada"),
    )
    for resposta, codigo in esperados:
        assert resposta.status_code == 409
        assert resposta.json()["codigo"] == codigo
    assert bruno.get(f"/ordens/{n}").json()["status"] == "Cancelada"


def test_aprovar_so_aguardando_aprovacao(mundo: Mundo) -> None:
    ana = mundo.entrar(ANA)
    n = _abrir(ana)
    r = ana.post(f"/ordens/{n}/aprovacao")
    assert r.status_code == 409
    assert r.json()["codigo"] == "estado_invalido"


# ------------------------------------------------------------------------------- validação
@pytest.mark.parametrize(
    ("rota", "corpo", "codigo"),
    [
        ("reparos", {"horas": -1, "intervencao": "x"}, "horas_negativas"),
        ("reparos", {"horas": 0, "intervencao": "x"}, "horas_nao_positivas"),
        ("reparos", {"horas": 1, "intervencao": "  "}, "campo_obrigatorio"),
        (
            "reparos",
            {"horas": 1, "intervencao": "x", "pecas": [{"descricao": "p", "quantidade": 0}]},
            "quantidade_invalida",
        ),
        (
            "reparos",
            {"horas": 1, "intervencao": "x", "pecas": [{"descricao": " ", "quantidade": 1}]},
            "campo_obrigatorio",
        ),
        ("diagnostico", {"parecer": "", "causa_raiz": "c"}, "campo_obrigatorio"),
    ],
)
def test_regras_de_entrada_do_dominio(
    mundo: Mundo, rota: str, corpo: dict[str, object], codigo: str
) -> None:
    ana, bruno = mundo.entrar(ANA), mundo.entrar(BRUNO)
    n = _abrir(ana)
    ana.post(f"/ordens/{n}/atribuicao", {"tecnico_id": BRUNO})
    if rota == "reparos":
        bruno.post(f"/ordens/{n}/diagnostico", {"parecer": "p", "causa_raiz": "c"})
    r = bruno.post(f"/ordens/{n}/{rota}", corpo)
    assert r.status_code == 422
    assert r.json()["codigo"] == codigo


@pytest.mark.parametrize(
    "corpo",
    [
        {},
        {**ABERTURA, "criticidade": "Extrema"},
        {**ABERTURA, "equipamento_id": "um"},
        {**ABERTURA, "falha": "x" * 4001},
        {**ABERTURA, "ator_id": 1},
        {**ABERTURA, "aberta_por": 1},
        {**ABERTURA, "status": "Concluída"},
    ],
)
def test_abertura_valida_forma_e_ignora_ator_do_cliente(
    mundo: Mundo, corpo: dict[str, object]
) -> None:
    r = mundo.entrar(BRUNO).post("/ordens", corpo)
    assert r.status_code == 422
    assert r.json()["codigo"] == "entrada_invalida"


def test_falha_vazia_na_abertura(mundo: Mundo) -> None:
    r = mundo.entrar(BRUNO).post("/ordens", {**ABERTURA, "falha": "   "})
    assert r.status_code == 422
    assert r.json()["codigo"] == "campo_obrigatorio"
    assert mundo.entrar(BRUNO).get("/ordens").json()["total"] == 0


def test_quem_abre_e_sempre_o_usuario_da_sessao(mundo: Mundo) -> None:
    assert _abrir(mundo.entrar(CARLA)) == 1
    assert mundo.entrar(ANA).get("/ordens/1").json()["aberta_por"]["id"] == CARLA


def test_pecas_acima_do_limite_sao_recusadas(mundo: Mundo) -> None:
    ana, bruno = mundo.entrar(ANA), mundo.entrar(BRUNO)
    n = _abrir(ana)
    ana.post(f"/ordens/{n}/atribuicao", {"tecnico_id": BRUNO})
    pecas = [{"descricao": f"p{i}", "quantidade": 1} for i in range(51)]
    r = bruno.post(f"/ordens/{n}/reparos", {"horas": 1, "intervencao": "x", "pecas": pecas})
    assert r.status_code == 422
    assert r.json()["codigo"] == "entrada_invalida"


# --------------------------------------------------------------------------------- observações
def test_apontamentos_exigem_vinculo_com_a_os(mundo: Mundo) -> None:
    ana, bruno, carla = mundo.entrar(ANA), mundo.entrar(BRUNO), mundo.entrar(CARLA)
    n = _abrir(bruno)
    ana.post(f"/ordens/{n}/atribuicao", {"tecnico_id": BRUNO})
    for autor in (ana, bruno):  # gestor, e técnico atribuído que também abriu
        r = autor.post(f"/ordens/{n}/apontamentos", {"texto": "Observação"})
        assert r.status_code == 200
    r = carla.post(f"/ordens/{n}/apontamentos", {"texto": "Intrusa"})
    assert r.status_code == 403
    assert r.json()["codigo"] == "sem_vinculo_com_a_os"
    assert ana.post(f"/ordens/{n}/apontamentos", {"texto": " "}).status_code == 422
    tipos = [s["tipo"] for s in ana.get(f"/ordens/{n}/historico").json()]
    assert tipos.count("Apontamento") == 2


# ------------------------------------------------------------------------- listagem e filtros
def _popular(mundo: Mundo) -> None:
    ana, bruno, carla = mundo.entrar(ANA), mundo.entrar(BRUNO), mundo.entrar(CARLA)
    _abrir(ana, {"equipamento_id": 1, "falha": "f1", "criticidade": "Alta"})  # 1 Aberta
    _abrir(bruno, {"equipamento_id": 2, "falha": "f2", "criticidade": "Baixa"})  # 2
    _abrir(carla, {"equipamento_id": 2, "falha": "f3", "criticidade": "Alta"})  # 3
    _abrir(ana, {"equipamento_id": 3, "falha": "f4", "criticidade": "Crítica"})  # 4
    ana.post("/ordens/2/atribuicao", {"tecnico_id": BRUNO})
    ana.post("/ordens/3/atribuicao", {"tecnico_id": CARLA})
    ana.post("/ordens/4/cancelamento", {"motivo": "m"})


def _numeros(r) -> list[int]:  # type: ignore[no-untyped-def]
    assert r.status_code == 200, r.text
    return [o["numero"] for o in r.json()["itens"]]


def test_listagem_padrao_traz_as_mais_recentes_primeiro(mundo: Mundo) -> None:
    _popular(mundo)
    ana = mundo.entrar(ANA)
    assert _numeros(ana.get("/ordens")) == [4, 3, 2, 1]
    assert _numeros(ana.get("/ordens?mais_antigas_primeiro=true")) == [1, 2, 3, 4]
    assert ana.get("/ordens").json()["total"] == 4


def test_filtros_de_ordens(mundo: Mundo) -> None:
    _popular(mundo)
    ana = mundo.entrar(ANA)
    assert _numeros(ana.get("/ordens?status=Aberta")) == [1]
    assert _numeros(ana.get("/ordens?status=Atribuída")) == [3, 2]
    assert _numeros(ana.get("/ordens?criticidade=Alta")) == [3, 1]
    assert _numeros(ana.get("/ordens?equipamento_id=2")) == [3, 2]
    assert _numeros(ana.get(f"/ordens?tecnico_id={BRUNO}")) == [2]
    assert _numeros(ana.get("/ordens?encerrada=true")) == [4]
    assert _numeros(ana.get("/ordens?encerrada=false")) == [3, 2, 1]
    assert _numeros(ana.get("/ordens?encerrada=false&criticidade=Alta&equipamento_id=2")) == [3]
    assert _numeros(ana.get("/ordens?status=Concluída")) == []


@pytest.mark.parametrize(
    "consulta",
    ["status=Quebrada", "criticidade=Enorme", "equipamento_id=x", "encerrada=talvez", "limite=0"],
)
def test_filtro_invalido_e_422(mundo: Mundo, consulta: str) -> None:
    r = mundo.entrar(ANA).get(f"/ordens?{consulta}")
    assert r.status_code == 422
    assert r.json()["codigo"] == "entrada_invalida"


def test_paginacao_de_ordens(mundo: Mundo) -> None:
    _popular(mundo)
    ana = mundo.entrar(ANA)
    assert _numeros(ana.get("/ordens?limite=2")) == [4, 3]
    assert _numeros(ana.get("/ordens?limite=2&deslocamento=2")) == [2, 1]
    assert _numeros(ana.get("/ordens?limite=2&deslocamento=4")) == []
    assert ana.get("/ordens?limite=2&deslocamento=2").json()["total"] == 4


def test_tecnico_com_ver_os_lista_todas(mundo: Mundo) -> None:
    _popular(mundo)
    assert _numeros(mundo.entrar(CARLA).get("/ordens")) == [4, 3, 2, 1]


def test_numeros_de_os_sao_sequenciais_e_nao_reaproveitados(mundo: Mundo) -> None:
    ana = mundo.entrar(ANA)
    assert _abrir(ana) == 1
    ana.post("/ordens", {**ABERTURA, "falha": " "})  # recusada: não gasta número
    assert _abrir(ana) == 2
