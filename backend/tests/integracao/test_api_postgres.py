"""API sobre o PostgreSQL real: persistência após reinício, comandos administrativos e segredos.

"Reinício" é descartar ``Banco``, aplicação e FastAPI e montar tudo de novo sobre o mesmo banco:
nada
do que o teste verifica pode vir da memória do processo. Os comandos administrativos rodam em
**processos separados**.
"""

import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

from manutencao.api import criar_app
from manutencao.composicao import acesso
from manutencao.composicao.aplicacao import Aplicacao, criar_aplicacao_postgres
from manutencao.infrastructure.postgres import Banco, migracoes
from tests.apoio.ambiente import ANA
from tests.apoio.api import HASHER_RAPIDO, PREFIXO, SENHA, semear_com_acesso
from tests.apoio.postgres import banco_temporario
from tests.apoio.relogio import RelogioFixo

COOKIE = "manutencao_sessao"


@dataclass
class Instancia:
    banco: Banco
    aplicacao: Aplicacao
    http: TestClient

    def encerrar(self) -> None:
        self.http.close()
        self.banco.encerrar()


def _subir(url: URL, relogio: RelogioFixo) -> Instancia:
    banco = Banco(url)
    aplicacao = criar_aplicacao_postgres(banco, relogio=relogio, hasher=HASHER_RAPIDO)
    return Instancia(banco, aplicacao, TestClient(criar_app(aplicacao.contexto)))


@pytest.fixture
def banco_de_demonstracao(url_do_banco_de_teste: URL, banco_limpo: Banco) -> URL:
    aplicacao = criar_aplicacao_postgres(banco_limpo, hasher=HASHER_RAPIDO)
    semear_com_acesso(aplicacao)
    return url_do_banco_de_teste


def _login(http: TestClient, login: str = "ana") -> str:
    r = http.post(f"{PREFIXO}/auth/login", json={"login": login, "senha": SENHA})
    assert r.status_code == 200, r.text
    return str(r.json()["csrf_token"])


# ----------------------------------------------------------------- persistência após o reinício
def test_dados_e_sessao_sobrevivem_ao_reinicio_da_aplicacao(banco_de_demonstracao: URL) -> None:
    relogio = RelogioFixo()
    primeira = _subir(banco_de_demonstracao, relogio)
    csrf = _login(primeira.http)
    criado = primeira.http.post(
        f"{PREFIXO}/equipamentos",
        json={"nome": "Prensa Hidráulica", "modelo": "PH-200"},
        headers={"X-CSRF-Token": csrf},
    )
    assert criado.status_code == 201
    equipamento_id = criado.json()["id"]
    os_criada = primeira.http.post(
        f"{PREFIXO}/ordens",
        json={
            "equipamento_id": equipamento_id,
            "falha": "Vazamento de óleo",
            "criticidade": "Alta",
        },
        headers={"X-CSRF-Token": csrf},
    )
    assert os_criada.status_code == 201
    cookie = primeira.http.cookies[COOKIE]
    primeira.encerrar()

    segunda = _subir(banco_de_demonstracao, relogio)  # processo "novo": nada em memória
    try:
        navegador = segunda.http
        navegador.cookies.set(COOKIE, cookie)  # o cookie do navegador continua valendo
        assert navegador.get(f"{PREFIXO}/auth/me").status_code == 200
        lista = navegador.get(f"{PREFIXO}/equipamentos").json()
        assert any(e["id"] == equipamento_id for e in lista["itens"])
        ordem = navegador.get(f"{PREFIXO}/ordens/{os_criada.json()['numero']}").json()
        assert ordem["falha"] == "Vazamento de óleo"
        assert ordem["status"] == "Aberta"
        historico = navegador.get(f"{PREFIXO}/ordens/{ordem['numero']}/historico").json()
        assert [s["tipo"] for s in historico] == ["Abertura"]
    finally:
        segunda.encerrar()


def test_logout_persiste_apos_reinicio(banco_de_demonstracao: URL) -> None:
    relogio = RelogioFixo()
    primeira = _subir(banco_de_demonstracao, relogio)
    csrf = _login(primeira.http)
    cookie = primeira.http.cookies[COOKIE]
    primeira.http.post(f"{PREFIXO}/auth/logout", headers={"X-CSRF-Token": csrf})
    primeira.encerrar()
    segunda = _subir(banco_de_demonstracao, relogio)
    try:
        segunda.http.cookies.set(COOKIE, cookie)
        assert segunda.http.get(f"{PREFIXO}/auth/me").status_code == 401
    finally:
        segunda.encerrar()


def test_sessao_expira_pelo_relogio_mesmo_apos_reinicio(banco_de_demonstracao: URL) -> None:
    relogio = RelogioFixo()
    primeira = _subir(banco_de_demonstracao, relogio)
    _login(primeira.http)
    cookie = primeira.http.cookies[COOKIE]
    primeira.encerrar()
    relogio.avancar(hours=9)
    segunda = _subir(banco_de_demonstracao, relogio)
    try:
        segunda.http.cookies.set(COOKIE, cookie)
        assert segunda.http.get(f"{PREFIXO}/auth/me").status_code == 401
    finally:
        segunda.encerrar()


# ---------------------------------------------------------------------- segredos no banco
def test_o_banco_guarda_so_hash_de_senha_e_hash_de_token(banco_de_demonstracao: URL) -> None:
    instancia = _subir(banco_de_demonstracao, RelogioFixo())
    try:
        _login(instancia.http)
        token = instancia.http.cookies[COOKIE]
    finally:
        instancia.encerrar()
    engine = create_engine(banco_de_demonstracao)
    try:
        with engine.connect() as conexao:
            hashes = conexao.execute(text("SELECT senha_hash FROM credenciais")).scalars().all()
            ids = conexao.execute(text("SELECT id_hash FROM sessoes")).scalars().all()
            tudo = " ".join(
                str(v)
                for tabela in ("credenciais", "sessoes", "usuarios")
                for linha in conexao.execute(text(f"SELECT * FROM {tabela}")).all()
                for v in linha
            )
    finally:
        engine.dispose()
    assert hashes
    assert all(h.startswith("$argon2id$") for h in hashes)
    assert token not in ids
    assert len(ids) == 1
    assert len(ids[0]) == 64
    assert SENHA not in tudo
    assert token not in tudo


def test_excluir_usuario_apaga_credencial_e_sessoes_no_banco(banco_de_demonstracao: URL) -> None:
    instancia = _subir(banco_de_demonstracao, RelogioFixo())
    try:
        ana = _login(instancia.http)
        carla = TestClient(criar_app(instancia.aplicacao.contexto))
        _login(carla, "carla")
        r = instancia.http.delete(f"{PREFIXO}/usuarios/3", headers={"X-CSRF-Token": ana})
        assert r.status_code == 204
        assert carla.get(f"{PREFIXO}/auth/me").status_code == 401
        assert instancia.aplicacao.credenciais.obter_por_usuario(3) is None
        carla.close()
    finally:
        instancia.encerrar()
    engine = create_engine(banco_de_demonstracao)
    try:
        with engine.connect() as conexao:
            assert (
                conexao.execute(text("SELECT count(*) FROM sessoes WHERE usuario_id = 3")).scalar()
                == 0
            )
    finally:
        engine.dispose()


def test_login_unico_e_garantido_pelo_banco(banco_de_demonstracao: URL) -> None:
    engine = create_engine(banco_de_demonstracao)
    try:
        with pytest.raises(Exception, match="uq_credenciais_login"), engine.begin() as conexao:
            conexao.execute(text("UPDATE credenciais SET login = 'ana' WHERE usuario_id = 2"))
    finally:
        engine.dispose()


# ------------------------------------------------------------------------- comandos de acesso
def _executar(
    url: URL, raiz: Path, *argumentos: str, entrada: str = ""
) -> subprocess.CompletedProcess[str]:
    ambiente = {
        **os.environ,
        "MANUTENCAO_DATABASE_URL": url.render_as_string(hide_password=False),
        "MANUTENCAO_ENV_FILE": "",
        "PYTHONPATH": str(raiz / "src"),
        "PYTHONIOENCODING": "utf-8",
    }
    return subprocess.run(
        [sys.executable, "-m", "manutencao.composicao.banco", *argumentos],
        cwd=raiz,
        env=ambiente,
        input=entrada,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
        timeout=180,
    )


def test_criar_gestor_inicial_e_definir_acesso_em_processos_separados(
    url_do_servidor_de_teste: URL, raiz_backend: Path
) -> None:
    senha = "uma-senha-so-de-teste-9"
    with banco_temporario(url_do_servidor_de_teste) as url:
        sem_esquema = _executar(url, raiz_backend, "criar-gestor", "--nome", "X", "--login", "xxx")
        assert sem_esquema.returncode == 2
        assert "migrar" in sem_esquema.stderr

        assert _executar(url, raiz_backend, "migrar").returncode == 0
        criado = _executar(
            url,
            raiz_backend,
            "criar-gestor",
            "--nome",
            "Marina Costa",
            "--login",
            "Marina",
            "--senha-stdin",
            entrada=senha + "\n",
        )
        assert criado.returncode == 0, criado.stderr
        assert "login 'marina'" in criado.stdout
        assert senha not in criado.stdout + criado.stderr  # nunca ecoa a senha

        # outro processo (a aplicação) autentica com o que foi gravado
        banco = Banco(url)
        try:
            aplicacao = criar_aplicacao_postgres(banco, hasher=HASHER_RAPIDO)
            # o hash do comando usa os parâmetros padrão; a verificação os lê do próprio hash
            iniciada = aplicacao.autenticacao.login("marina", senha)
            assert iniciada.usuario.papel.value == "Gestor"
            assert iniciada.usuario.nome == "Marina Costa"
            assert {c.nome for c in aplicacao.container.cargos.listar()} == {"Gestor", "Técnico"}
        finally:
            banco.encerrar()

        de_novo = _executar(
            url, raiz_backend, "criar-gestor", "--nome", "Outro", "--login", "outro",
            "--senha-stdin", entrada=senha + "\n",
        )  # fmt: skip
        assert de_novo.returncode == 3
        assert "Já existe um Gestor" in de_novo.stderr

        redefinido = _executar(
            url, raiz_backend, "definir-acesso", "--usuario-id", "1", "--login", "marina",
            "--senha-stdin", entrada="outra-senha-so-de-teste-9\n",
        )  # fmt: skip
        assert redefinido.returncode == 0, redefinido.stderr
        banco = Banco(url)
        try:
            aplicacao = criar_aplicacao_postgres(banco, hasher=HASHER_RAPIDO)
            assert aplicacao.autenticacao.login("marina", "outra-senha-so-de-teste-9")
        finally:
            banco.encerrar()


def test_comando_recusa_senha_fraca_e_login_invalido(
    url_do_servidor_de_teste: URL, raiz_backend: Path
) -> None:
    with banco_temporario(url_do_servidor_de_teste) as url:
        _executar(url, raiz_backend, "migrar")
        fraca = _executar(
            url, raiz_backend, "criar-gestor", "--nome", "M", "--login", "marina",
            "--senha-stdin", entrada="curta\n",
        )  # fmt: skip
        assert fraca.returncode == 3
        assert "pelo menos" in fraca.stderr
        ruim = _executar(
            url, raiz_backend, "criar-gestor", "--nome", "M", "--login", "a b",
            "--senha-stdin", entrada="uma-senha-so-de-teste-9\n",
        )  # fmt: skip
        assert ruim.returncode == 3
        estado = _executar(url, raiz_backend, "estado")
        assert "usuários: 0" in estado.stdout  # nada ficou pela metade


def test_semear_com_acesso_cria_logins_da_demonstracao(
    url_do_servidor_de_teste: URL, raiz_backend: Path
) -> None:
    senha = "senha-da-demonstracao-9"
    with banco_temporario(url_do_servidor_de_teste) as url:
        _executar(url, raiz_backend, "migrar")
        semeado = _executar(
            url, raiz_backend, "semear", "--com-acesso", "--senha-stdin", entrada=senha + "\n"
        )
        assert semeado.returncode == 0, semeado.stderr
        assert "ana, bruno, carla" in semeado.stdout
        assert senha not in semeado.stdout + semeado.stderr
        banco = Banco(url)
        try:
            aplicacao = criar_aplicacao_postgres(banco, hasher=HASHER_RAPIDO)
            for login in ("ana", "bruno", "carla"):
                assert aplicacao.autenticacao.login(login, senha)
        finally:
            banco.encerrar()


def test_versao_do_esquema_e_a_mais_recente(banco_limpo: Banco, url_do_banco_de_teste: URL) -> None:
    assert migracoes.revisao_atual(url_do_banco_de_teste) == migracoes.revisao_mais_recente()


def test_gestor_inicial_em_memoria_cria_cargos_e_recusa_um_segundo() -> None:
    from manutencao.composicao.aplicacao import criar_aplicacao_em_memoria

    app = criar_aplicacao_em_memoria(hasher=HASHER_RAPIDO)
    usuario = acesso.criar_gestor_inicial(
        app.container,
        app.credenciais,
        app.autenticacao,
        app.unidade,
        nome="Gestora",
        login="gestora",
        senha=SENHA,
    )
    assert usuario.id == ANA
    assert usuario.e_gestor_administrativo
    with pytest.raises(acesso.GestorJaExisteError):
        acesso.criar_gestor_inicial(
            app.container,
            app.credenciais,
            app.autenticacao,
            app.unidade,
            nome="B",
            login="b.b.b",
            senha=SENHA,
        )
