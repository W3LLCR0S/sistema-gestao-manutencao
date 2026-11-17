"""Autenticação da API (D-01): login, sessão, expiração, logout, CSRF, origem e tentativas."""

import pytest

from manutencao.application.servicos.autenticacao import hash_do_token
from tests.apoio.ambiente import ANA, BRUNO
from tests.apoio.api import LOGINS, PREFIXO, SENHA, Mundo

LOGIN = f"{PREFIXO}/auth/login"
COOKIE = "manutencao_sessao"


def _login(mundo: Mundo, login: str, senha: str):  # type: ignore[no-untyped-def]
    http = mundo.navegador()
    return http, http.post(LOGIN, json={"login": login, "senha": senha})


# ------------------------------------------------------------------------------------------ login
def test_login_valido_abre_sessao_com_cookie_seguro_e_devolve_o_usuario(mundo: Mundo) -> None:
    http, r = _login(mundo, "ana", SENHA)
    assert r.status_code == 200
    corpo = r.json()
    assert corpo["usuario"]["id"] == ANA
    assert corpo["usuario"]["login"] == "ana"
    assert corpo["usuario"]["papel"] == "Gestor"
    assert corpo["csrf_token"]
    cookie = r.headers["set-cookie"]
    assert cookie.startswith(f"{COOKIE}=")
    assert "HttpOnly" in cookie
    assert "SameSite=lax" in cookie
    assert "Path=/" in cookie
    assert "Secure" not in cookie  # HTTP local: o atributo só vale quando configurado
    assert http.get(f"{PREFIXO}/auth/me").status_code == 200


def test_login_e_insensivel_a_maiusculas_e_a_espacos(mundo: Mundo) -> None:
    _, r = _login(mundo, "  ANA ", SENHA)
    assert r.status_code == 200


def test_resposta_do_login_nao_traz_hash_nem_o_token_da_sessao(mundo: Mundo) -> None:
    http, r = _login(mundo, "ana", SENHA)
    texto = r.text.casefold()
    assert "argon2" not in texto
    assert "hash" not in texto
    token = http.cookies.get(COOKIE)
    assert token
    assert token not in r.text


def test_senha_incorreta_usuario_inexistente_e_inativo_recebem_a_mesma_recusa(
    mundo: Mundo,
) -> None:
    mundo.aplicacao.container.servico_usuarios.desativar(ANA, 3)  # Carla inativa
    respostas = [
        _login(mundo, "ana", "senha-errada-123")[1],
        _login(mundo, "ninguem", SENHA)[1],
        _login(mundo, "carla", SENHA)[1],  # senha certa, usuário inativo
    ]
    for r in respostas:
        assert r.status_code == 401
        assert r.json() == {"codigo": "credenciais_invalidas", "mensagem": "Credenciais inválidas."}
        assert "Max-Age=0" in r.headers["set-cookie"]  # nenhum cookie de sessão é emitido


def test_login_recusado_nao_cria_sessao(mundo: Mundo) -> None:
    http, r = _login(mundo, "ana", "errada-errada-1")
    assert r.status_code == 401
    assert http.get(f"{PREFIXO}/auth/me").status_code == 401


@pytest.mark.parametrize(
    "corpo",
    [
        {},
        {"login": "ana"},
        {"senha": SENHA},
        {"login": "ana", "senha": SENHA, "ator_id": 1},
        {"login": 1, "senha": SENHA},
        {"login": "a" * 101, "senha": SENHA},
        {"login": "ana", "senha": "x" * 129},
    ],
)
def test_login_valida_a_forma_da_entrada(mundo: Mundo, corpo: dict[str, object]) -> None:
    r = mundo.navegador().post(LOGIN, json=corpo)
    assert r.status_code == 422
    assert r.json()["codigo"] == "entrada_invalida"


def test_erro_de_validacao_nao_devolve_o_valor_enviado(mundo: Mundo) -> None:
    segredo = "uma-senha-que-nao-pode-vazar-" + "x" * 200  # excede o limite de 128
    r = mundo.navegador().post(LOGIN, json={"login": "ana", "senha": segredo})
    assert r.status_code == 422
    assert segredo not in r.text
    assert "uma-senha-que-nao-pode-vazar" not in r.text


def test_o_token_nao_e_gravado_em_texto_so_o_hash(mundo: Mundo) -> None:
    http, _ = _login(mundo, "ana", SENHA)
    token = http.cookies[COOKIE]
    sessoes = mundo.aplicacao.sessoes
    assert sessoes.obter(token) is None  # o texto do cookie não é a chave guardada
    guardada = sessoes.obter(hash_do_token(token))
    assert guardada is not None
    assert token not in repr(guardada)


def test_cookie_ganha_secure_quando_configurado_para_https(mundo: Mundo) -> None:
    from dataclasses import replace

    from fastapi.testclient import TestClient

    from manutencao.api import criar_app

    contexto = replace(
        mundo.aplicacao.contexto, configuracao=replace(mundo.configuracao, cookie_seguro=True)
    )
    http = TestClient(criar_app(contexto), base_url="https://testserver")
    r = http.post(LOGIN, json={"login": "ana", "senha": SENHA})
    assert r.status_code == 200
    assert "Secure" in r.headers["set-cookie"]


# --------------------------------------------------------------------------------- sessão e acesso
def test_sem_sessao_toda_rota_protegida_responde_401(mundo: Mundo) -> None:
    http = mundo.navegador()
    for caminho in ("/auth/me", "/usuarios", "/equipamentos", "/ordens", "/painel", "/cargos"):
        r = http.get(PREFIXO + caminho)
        assert r.status_code == 401, caminho
        assert r.json()["codigo"] == "nao_autenticado"


def test_cookie_forjado_e_recusado(mundo: Mundo) -> None:
    http = mundo.navegador()
    http.cookies.set(COOKIE, "token-inventado-pelo-cliente")
    assert http.get(f"{PREFIXO}/auth/me").status_code == 401


def test_cabecalho_de_identidade_enviado_pelo_cliente_e_ignorado(mundo: Mundo) -> None:
    bruno = mundo.entrar(BRUNO)
    r = bruno.get("/auth/me", headers={"X-Usuario-Id": str(ANA), "X-Ator-Id": str(ANA)})
    assert r.json()["usuario"]["id"] == BRUNO


def test_me_devolve_permissoes_efetivas_e_csrf(mundo: Mundo) -> None:
    bruno = mundo.entrar(BRUNO)
    corpo = bruno.get("/auth/me").json()
    assert corpo["usuario"]["papel"] == "Técnico"
    assert "diagnosticar" in corpo["usuario"]["permissoes"]
    assert "gerir_usuarios" not in corpo["usuario"]["permissoes"]
    assert corpo["csrf_token"] == bruno.csrf


def test_verificacao_de_sessao_e_de_permissoes(mundo: Mundo) -> None:
    ana, bruno = mundo.entrar(ANA), mundo.entrar(BRUNO)
    sessao = ana.get("/auth/sessao").json()
    assert sessao["autenticado"] is True
    assert sessao["usuario_id"] == ANA
    assert ana.get("/auth/permissoes/gerir_usuarios").json() == {
        "permissao": "gerir_usuarios",
        "concedida": True,
    }
    assert bruno.get("/auth/permissoes/gerir_usuarios").json()["concedida"] is False
    assert bruno.get("/auth/permissoes/voar").status_code == 422


def test_sessao_expirada_e_recusada_e_removida(mundo: Mundo) -> None:
    ana = mundo.entrar(ANA)
    assert ana.get("/auth/me").status_code == 200
    mundo.relogio.avancar(hours=7, minutes=59)
    assert ana.get("/auth/me").status_code == 200
    mundo.relogio.avancar(minutes=2)  # passou das 8 horas
    r = ana.get("/auth/me")
    assert r.status_code == 401
    assert r.json()["codigo"] == "nao_autenticado"
    token_hash = hash_do_token(ana.http.cookies.get(COOKIE) or "")
    assert mundo.aplicacao.sessoes.obter(token_hash) is None


def test_expiracao_e_absoluta_nao_se_renova_com_o_uso(mundo: Mundo) -> None:
    ana = mundo.entrar(ANA)
    for _ in range(4):
        mundo.relogio.avancar(hours=2)
        ana.get("/auth/me")
    assert ana.get("/auth/me").status_code == 401  # 8 h desde o login, apesar do uso


# ------------------------------------------------------------------------------------------ logout
def test_logout_revoga_a_sessao_no_servidor_e_limpa_o_cookie(mundo: Mundo) -> None:
    ana = mundo.entrar(ANA)
    token = ana.http.cookies[COOKIE]
    r = ana.post("/auth/logout")
    assert r.status_code == 204
    assert "Max-Age=0" in r.headers["set-cookie"] or "expires=" in r.headers["set-cookie"].lower()
    # Reapresentar o cookie antigo (roubado) não funciona: a revogação é do servidor.
    ladrao = mundo.navegador()
    ladrao.cookies.set(COOKIE, token)
    assert ladrao.get(f"{PREFIXO}/auth/me").status_code == 401


def test_logout_sem_sessao_e_idempotente(mundo: Mundo) -> None:
    assert mundo.navegador().post(f"{PREFIXO}/auth/logout").status_code == 204


def test_logout_com_sessao_valida_exige_csrf(mundo: Mundo) -> None:
    ana = mundo.entrar(ANA)
    r = ana.http.post(f"{PREFIXO}/auth/logout")  # sem o cabeçalho
    assert r.status_code == 403
    assert r.json()["codigo"] == "csrf_invalido"
    assert ana.get("/auth/me").status_code == 200  # nada foi encerrado


def test_sessoes_sao_independentes_logout_de_uma_nao_derruba_a_outra(mundo: Mundo) -> None:
    a, b = mundo.entrar(ANA), mundo.entrar(ANA)
    a.post("/auth/logout")
    assert b.get("/auth/me").status_code == 200


# ------------------------------------------------------------------------------------------- CSRF
@pytest.mark.parametrize(
    ("metodo", "caminho"),
    [
        ("post", "/equipamentos"),
        ("put", "/equipamentos/1"),
        ("patch", "/usuarios/2"),
        ("delete", "/equipamentos/1"),
    ],
)
def test_operacoes_que_modificam_dados_exigem_o_token_csrf(
    mundo: Mundo, metodo: str, caminho: str
) -> None:
    ana = mundo.entrar(ANA)
    chamar = getattr(ana.http, metodo)
    sem = chamar(PREFIXO + caminho)  # sem cabeçalho
    assert sem.status_code == 403
    assert sem.json()["codigo"] == "csrf_invalido"
    errado = chamar(PREFIXO + caminho, headers={"X-CSRF-Token": "outro"})
    assert errado.status_code == 403
    assert errado.json()["codigo"] == "csrf_invalido"


def test_csrf_de_outra_sessao_nao_vale(mundo: Mundo) -> None:
    a, b = mundo.entrar(ANA), mundo.entrar(ANA)
    r = a.http.post(
        f"{PREFIXO}/equipamentos",
        json={"nome": "X", "modelo": "Y"},
        headers={"X-CSRF-Token": b.csrf},
    )
    assert r.status_code == 403


def test_csrf_correto_permite_a_operacao(mundo: Mundo) -> None:
    ana = mundo.entrar(ANA)
    assert ana.post("/equipamentos", json={"nome": "Prensa", "modelo": "P-1"}).status_code == 201


def test_leituras_nao_exigem_csrf(mundo: Mundo) -> None:
    ana = mundo.entrar(ANA)
    assert ana.http.get(f"{PREFIXO}/equipamentos").status_code == 200


def test_sem_sessao_o_post_protegido_e_401_e_nao_403(mundo: Mundo) -> None:
    r = mundo.navegador().post(f"{PREFIXO}/equipamentos", json={"nome": "X", "modelo": "Y"})
    assert r.status_code == 401


def test_origem_estranha_e_recusada_nas_escritas_mesmo_com_cookie_e_csrf(mundo: Mundo) -> None:
    ana = mundo.entrar(ANA)
    r = ana.post(
        "/equipamentos",
        json={"nome": "X", "modelo": "Y"},
        headers={"Origin": "http://site-malicioso.example"},
    )
    assert r.status_code == 403
    assert r.json()["codigo"] == "origem_nao_permitida"
    # a mesma origem do servidor é aceita
    ok = ana.post(
        "/equipamentos",
        json={"nome": "X", "modelo": "Y"},
        headers={"Origin": "http://testserver"},
    )
    assert ok.status_code == 201


def test_origem_configurada_e_aceita(mundo: Mundo) -> None:
    from dataclasses import replace

    from fastapi.testclient import TestClient

    from manutencao.api import criar_app

    cfg = replace(mundo.configuracao, origens_permitidas=("http://192.168.0.10:5173",))
    app = criar_app(replace(mundo.aplicacao.contexto, configuracao=cfg))
    http = TestClient(app)
    r = http.post(
        LOGIN,
        json={"login": "ana", "senha": SENHA},
        headers={"Origin": "http://192.168.0.10:5173"},
    )
    assert r.status_code == 200
    # CORS com credenciais, só para a origem configurada (nunca '*')
    assert r.headers["access-control-allow-origin"] == "http://192.168.0.10:5173"
    assert r.headers["access-control-allow-credentials"] == "true"
    estranha = http.options(
        f"{PREFIXO}/auth/me",
        headers={"Origin": "http://outro.example", "Access-Control-Request-Method": "GET"},
    )
    assert "access-control-allow-origin" not in estranha.headers


def test_sem_origens_configuradas_nao_ha_cors(mundo: Mundo) -> None:
    r = mundo.navegador().get(f"{PREFIXO}/saude", headers={"Origin": "http://qualquer.example"})
    assert "access-control-allow-origin" not in r.headers


def test_respostas_nao_sao_armazenaveis_em_cache(mundo: Mundo) -> None:
    ana = mundo.entrar(ANA)
    r = ana.get("/auth/me")
    assert r.headers["cache-control"] == "no-store"
    assert r.headers["x-content-type-options"] == "nosniff"


# ---------------------------------------------------------------------- limite de tentativas
def test_apos_cinco_falhas_o_login_e_bloqueado_com_429_e_retry_after(mundo: Mundo) -> None:
    http = mundo.navegador()
    for _ in range(5):
        assert (
            http.post(LOGIN, json={"login": "ana", "senha": "errada-errada-1"}).status_code == 401
        )
    r = http.post(LOGIN, json={"login": "ana", "senha": SENHA})  # até a senha certa é barrada
    assert r.status_code == 429
    assert r.json()["codigo"] == "muitas_tentativas"
    assert int(r.headers["retry-after"]) > 0
    mundo.relogio.avancar(minutes=16)
    assert http.post(LOGIN, json={"login": "ana", "senha": SENHA}).status_code == 200


def test_login_bem_sucedido_zera_as_falhas(mundo: Mundo) -> None:
    http = mundo.navegador()
    for _ in range(4):
        http.post(LOGIN, json={"login": "ana", "senha": "errada-errada-1"})
    assert http.post(LOGIN, json={"login": "ana", "senha": SENHA}).status_code == 200
    for _ in range(4):
        assert (
            http.post(LOGIN, json={"login": "ana", "senha": "errada-errada-1"}).status_code == 401
        )


def test_o_limite_vale_por_login_e_nao_bloqueia_outras_contas(mundo: Mundo) -> None:
    http = mundo.navegador()
    for _ in range(5):
        http.post(LOGIN, json={"login": "ana", "senha": "errada-errada-1"})
    assert http.post(LOGIN, json={"login": "bruno", "senha": SENHA}).status_code == 200


# ----------------------------------------------------------------------------- senha e credencial
def test_alterar_propria_senha_revoga_as_outras_sessoes_e_mantem_a_atual(mundo: Mundo) -> None:
    atual, outra = mundo.entrar(BRUNO), mundo.entrar(BRUNO)
    nova = "uma-senha-nova-bem-longa"
    r = atual.post("/auth/alterar-senha", json={"senha_atual": SENHA, "nova_senha": nova})
    assert r.status_code == 204
    assert atual.get("/auth/me").status_code == 200
    assert outra.get("/auth/me").status_code == 401
    assert _login(mundo, LOGINS[BRUNO], SENHA)[1].status_code == 401
    assert _login(mundo, LOGINS[BRUNO], nova)[1].status_code == 200


def test_alterar_senha_exige_a_senha_atual_correta_e_uma_nova_valida(mundo: Mundo) -> None:
    bruno = mundo.entrar(BRUNO)
    errada = bruno.post("/auth/alterar-senha", json={"senha_atual": "x" * 12, "nova_senha": SENHA})
    assert errada.status_code == 422
    assert errada.json()["codigo"] == "senha_atual_incorreta"
    assert bruno.get("/auth/me").status_code == 200  # o erro de digitação não derruba a sessão
    curta = bruno.post("/auth/alterar-senha", json={"senha_atual": SENHA, "nova_senha": "curta"})
    assert curta.status_code == 422
    assert curta.json()["codigo"] == "entrada_invalida"


def test_gestor_redefine_o_acesso_e_as_sessoes_do_usuario_caem(mundo: Mundo) -> None:
    ana, bruno = mundo.entrar(ANA), mundo.entrar(BRUNO)
    r = ana.put(
        f"/usuarios/{BRUNO}/credencial",
        json={"login": "bruno.lima", "senha": "outra-senha-longa-1"},
    )
    assert r.status_code == 204
    assert bruno.get("/auth/me").status_code == 401
    assert _login(mundo, "bruno", SENHA)[1].status_code == 401
    assert _login(mundo, "bruno.lima", "outra-senha-longa-1")[1].status_code == 200


def test_tecnico_nao_redefine_credencial_de_ninguem(mundo: Mundo) -> None:
    bruno = mundo.entrar(BRUNO)
    r = bruno.put(
        f"/usuarios/{ANA}/credencial", json={"login": "x.y.z", "senha": "uma-senha-longa-1"}
    )
    assert r.status_code == 403
    assert _login(mundo, "ana", SENHA)[1].status_code == 200  # nada mudou


def test_login_ja_em_uso_e_conflito(mundo: Mundo) -> None:
    ana = mundo.entrar(ANA)
    r = ana.put(
        f"/usuarios/{BRUNO}/credencial", json={"login": "Ana", "senha": "uma-senha-longa-1"}
    )
    assert r.status_code == 409
    assert r.json()["codigo"] == "login_em_uso"


@pytest.mark.parametrize(
    ("login", "senha"),
    [("ab", "uma-senha-longa-1"), ("com espaco", "uma-senha-longa-1"), ("novo.login", "curta")],
)
def test_politica_de_login_e_senha(mundo: Mundo, login: str, senha: str) -> None:
    ana = mundo.entrar(ANA)
    r = ana.put(f"/usuarios/{BRUNO}/credencial", json={"login": login, "senha": senha})
    assert r.status_code == 422


def test_senha_igual_ao_login_e_recusada(mundo: Mundo) -> None:
    ana = mundo.entrar(ANA)
    r = ana.put(
        f"/usuarios/{BRUNO}/credencial", json={"login": "bruno.lima", "senha": "bruno.lima"}
    )
    assert r.status_code == 422
