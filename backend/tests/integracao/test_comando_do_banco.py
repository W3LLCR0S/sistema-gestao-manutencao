"""O comando ``python -m manutencao.composicao.banco`` em **processos separados**.

Cada comando é um processo novo: o que o segundo vê foi, necessariamente, gravado no PostgreSQL pelo
primeiro. É a prova de "os dados sobrevivem ao reinício da aplicação" sem nenhum estado em comum.
"""

import os
import subprocess
import sys
from pathlib import Path

from sqlalchemy.engine import URL

from tests.apoio.postgres import banco_temporario


def _executar(url: URL, raiz_backend: Path, *argumentos: str) -> subprocess.CompletedProcess[str]:
    ambiente = {
        **os.environ,
        "MANUTENCAO_DATABASE_URL": url.render_as_string(hide_password=False),
        "PYTHONPATH": str(raiz_backend / "src"),
        "PYTHONIOENCODING": "utf-8",
    }
    return subprocess.run(
        [sys.executable, "-m", "manutencao.composicao.banco", *argumentos],
        cwd=raiz_backend,
        env=ambiente,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
        timeout=120,
    )


def test_migrar_semear_e_consultar_em_processos_diferentes(
    url_do_servidor_de_teste: URL, raiz_backend: Path
) -> None:
    with banco_temporario(url_do_servidor_de_teste) as url:
        sem_esquema = _executar(url, raiz_backend, "semear")
        assert sem_esquema.returncode == 2  # recusa semear sem migrar
        assert "migrar" in sem_esquema.stderr

        migrado = _executar(url, raiz_backend, "migrar")
        assert migrado.returncode == 0, migrado.stderr
        assert "0003" in migrado.stdout

        semeado = _executar(url, raiz_backend, "semear")
        assert semeado.returncode == 0, semeado.stderr
        assert "3 usuários" in semeado.stdout
        assert "5 OS" in semeado.stdout

        estado = _executar(url, raiz_backend, "estado")  # outro processo: lê o que ficou no banco
        assert estado.returncode == 0, estado.stderr
        assert "usuários: 3" in estado.stdout
        assert "OS: 5" in estado.stdout

        de_novo = _executar(url, raiz_backend, "semear")
        assert de_novo.returncode == 3  # banco já tem dados: nada é duplicado
        assert "OS: 5" in _executar(url, raiz_backend, "estado").stdout


def test_o_comando_nao_vaza_a_senha_e_exige_confirmacao_para_reverter(
    url_do_servidor_de_teste: URL, raiz_backend: Path
) -> None:
    with banco_temporario(url_do_servidor_de_teste) as url:
        com_senha = url.set(password="senha-que-nao-pode-vazar")
        _executar(url, raiz_backend, "migrar")
        estado = _executar(com_senha, raiz_backend, "estado")
        assert "senha-que-nao-pode-vazar" not in estado.stdout + estado.stderr
        recusado = _executar(url, raiz_backend, "reverter", "base")
        assert recusado.returncode == 2
        assert "--confirmo" in recusado.stderr
        assert _executar(url, raiz_backend, "estado").returncode == 0  # nada foi desfeito


def test_sem_configuracao_o_comando_explica_o_que_falta(raiz_backend: Path) -> None:
    ambiente = {k: v for k, v in os.environ.items() if not k.startswith("MANUTENCAO_")}
    ambiente["PYTHONPATH"] = str(raiz_backend / "src")
    ambiente["PYTHONIOENCODING"] = "utf-8"
    ambiente["MANUTENCAO_ENV_FILE"] = ""  # hermético: ignora um backend/.env do desenvolvedor
    resultado = subprocess.run(
        [sys.executable, "-m", "manutencao.composicao.banco", "estado"],
        cwd=raiz_backend,
        env=ambiente,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
        timeout=60,
    )
    assert resultado.returncode == 1
    assert "MANUTENCAO_DATABASE_URL" in resultado.stderr
