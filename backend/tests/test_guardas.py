"""Guardas do ambiente de testes: rede, dados reais, estrutura mínima e privacidade.

Cada teste exercita a proteção real (instalada por ``conftest.py``); se a proteção for removida,
o teste correspondente falha.
"""

import importlib
import os
import socket
import sys
from pathlib import Path

import pytest

from tests.guardas_ambiente import (
    DIRETORIO_DADOS,
    AcessoADadosReaisError,
    RedeBloqueadaError,
    caminho_em_dados,
    destino_permitido,
)

CAMADAS = ("domain", "application", "infrastructure", "api", "composicao")


# ------------------------------------------------------------------- 3. sem rede externa


def test_conexao_externa_por_nome_e_bloqueada() -> None:
    with pytest.raises(RedeBloqueadaError):
        socket.create_connection(("example.com", 80), timeout=1)


def test_conexao_externa_por_ip_e_bloqueada() -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s, pytest.raises(RedeBloqueadaError):
        s.connect(("203.0.113.10", 80))  # TEST-NET-3: nunca é alcançado, a guarda age antes


def test_conexao_externa_connect_ex_e_bloqueada() -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s, pytest.raises(RedeBloqueadaError):
        s.connect_ex(("203.0.113.10", 80))


def test_envio_udp_externo_e_bloqueado() -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s, pytest.raises(RedeBloqueadaError):
        s.sendto(b"x", ("203.0.113.10", 53))


def test_resolucao_de_nome_externo_e_bloqueada() -> None:
    with pytest.raises(RedeBloqueadaError):
        socket.getaddrinfo("example.com", 80)


@pytest.mark.parametrize(
    ("endereco", "esperado"),
    [
        (("127.0.0.1", 8000), True),
        (("localhost", 8000), True),
        (("::1", 8000, 0, 0), True),
        ("/tmp/socket.sock", True),
        (("example.com", 80), False),
        (("203.0.113.10", 80), False),
        (("0.0.0.0", 80), False),
        ((), False),
        (None, False),
    ],
)
def test_destino_permitido_somente_local(endereco: object, esperado: bool) -> None:
    assert destino_permitido(endereco) is esperado


# ------------------------------------------------------------- 4. dados reais protegidos


def test_diretorio_dados_e_o_da_raiz_do_repositorio(raiz_repositorio: Path) -> None:
    assert raiz_repositorio / "dados" == DIRETORIO_DADOS
    assert (raiz_repositorio / "main.py").is_file()  # a raiz calculada é de fato a do legado


@pytest.mark.parametrize("nome", ["dados.json", "inexistente.json", "sub/arquivo.txt"])
def test_abrir_arquivo_em_dados_e_bloqueado(nome: str) -> None:
    alvo = DIRETORIO_DADOS / nome
    with pytest.raises(AcessoADadosReaisError):
        open(alvo, encoding="utf-8")  # noqa: PTH123, SIM115 - o ponto do teste é o open()
    with pytest.raises(AcessoADadosReaisError):
        alvo.read_text(encoding="utf-8")
    with pytest.raises(AcessoADadosReaisError):
        alvo.open("rb")
    with pytest.raises(AcessoADadosReaisError):
        os.open(alvo, os.O_RDONLY)


def test_caminho_relativo_para_dados_tambem_e_bloqueado(
    monkeypatch: pytest.MonkeyPatch, raiz_repositorio: Path
) -> None:
    monkeypatch.chdir(raiz_repositorio)
    with pytest.raises(AcessoADadosReaisError):
        open("dados/dados.json", encoding="utf-8")  # noqa: PTH123, SIM115


def test_caminho_com_ponto_ponto_nao_escapa_da_guarda(raiz_repositorio: Path) -> None:
    disfarcado = raiz_repositorio / "backend" / ".." / "dados" / "dados.json"
    assert caminho_em_dados(disfarcado)
    with pytest.raises(AcessoADadosReaisError):
        disfarcado.read_text(encoding="utf-8")


def test_arquivos_fora_de_dados_continuam_acessiveis(tmp_path: Path) -> None:
    arquivo = tmp_path / "ok.txt"
    arquivo.write_text("conteúdo", encoding="utf-8")
    assert arquivo.read_text(encoding="utf-8") == "conteúdo"
    assert not caminho_em_dados(arquivo)
    assert not caminho_em_dados(DIRETORIO_DADOS.parent / "dados_extra" / "x.txt")


def test_gitignore_protege_dados_ambiente_e_planejamento(raiz_repositorio: Path) -> None:
    linhas = {
        linha.strip()
        for linha in (raiz_repositorio / ".gitignore").read_text(encoding="utf-8").splitlines()
    }
    for regra in ("dados/*", "!dados/.gitkeep", ".venv/", ".env", "/planejamento/"):
        assert regra in linhas, f".gitignore sem a regra '{regra}'"


# --------------------------------------------------- 5. estrutura mínima importável


def test_versao_do_python_e_3_11() -> None:
    assert sys.version_info[:2] == (3, 11)


def test_pacote_importa_do_diretorio_src_do_backend(raiz_backend: Path) -> None:
    manutencao = importlib.import_module("manutencao")
    assert manutencao.__file__ is not None
    assert (
        Path(manutencao.__file__).resolve() == raiz_backend / "src" / "manutencao" / "__init__.py"
    )


@pytest.mark.parametrize("camada", CAMADAS)
def test_camadas_sao_importaveis(camada: str) -> None:
    modulo = importlib.import_module(f"manutencao.{camada}")
    assert modulo.__name__ == f"manutencao.{camada}"


def test_pacote_declara_tipagem_pep_561(raiz_backend: Path) -> None:
    assert (raiz_backend / "src" / "manutencao" / "py.typed").is_file()


def test_estrutura_de_testes_existe(raiz_backend: Path) -> None:
    for diretorio in (
        "caracterizacao",
        "dominio",
        "aplicacao",
        "integracao",
        "contrato",
        "arquitetura",
    ):
        assert (raiz_backend / "tests" / diretorio / "__init__.py").is_file()


def test_marcadores_do_pyproject_estao_registrados(pytestconfig: pytest.Config) -> None:
    registrados = {linha.split(":", 1)[0].strip() for linha in pytestconfig.getini("markers")}
    esperados = {"caracterizacao", "dominio", "aplicacao", "integracao", "contrato", "arquitetura"}
    assert esperados <= registrados


def test_marcador_e_aplicado_pelo_diretorio(request: pytest.FixtureRequest) -> None:
    """Este arquivo está na raiz de tests/: não recebe marcador de camada."""
    nomes = {m.name for m in request.node.iter_markers()}
    assert not nomes & {"caracterizacao", "dominio", "aplicacao", "integracao", "contrato"}
