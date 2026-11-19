"""O pacote novo não importa o código legado da Entrega 1 (ADR-0008, D-10).

A relação com o legado é comparar comportamentos por testes de caracterização, não compartilhar
código. Estes testes **não importam nem executam** nenhum módulo legado: a análise é estática
(``ast``) e a checagem em tempo de execução roda em um subprocesso com um bloqueador de
importação, que falha antes de qualquer código legado ser carregado.
"""

import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from tests.arquitetura.analise_imports import (
    MODULOS_LEGADOS,
    ArquivoFonte,
    coletar_importacoes,
    listar_arquivos_python,
    listar_fontes,
    violacoes_de_legado,
)
from tests.guardas_ambiente import RAIZ_BACKEND

DIRETORIO_SRC = RAIZ_BACKEND / "src"
DIRETORIO_TESTES = RAIZ_BACKEND / "tests"
FONTES = listar_fontes(DIRETORIO_SRC)

# Script do subprocesso: bloqueia o legado e importa os módulos informados.
_SCRIPT_BLOQUEIO = textwrap.dedent(
    """
    import importlib
    import sys

    src, legado, *modulos = sys.argv[1:]
    legado = set(legado.split(","))
    sys.path.insert(0, src)


    class Bloqueador:
        def find_spec(self, nome, caminho=None, alvo=None):
            if nome.split(".")[0] in legado:
                raise ImportError("importação do legado bloqueada: " + nome)
            return None


    sys.meta_path.insert(0, Bloqueador())
    for modulo in modulos:
        importlib.import_module(modulo)
    carregados = sorted(m for m in sys.modules if m.split(".")[0] in legado)
    if carregados:
        raise SystemExit("legado carregado: " + ", ".join(carregados))
    """
)


def _importar_sob_bloqueio(src: Path, modulos: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "-I",
            "-c",
            _SCRIPT_BLOQUEIO,
            str(src),
            ",".join(sorted(MODULOS_LEGADOS)),
            *modulos,
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )


# ------------------------------------------------------------------ o analisador detecta o legado


@pytest.mark.parametrize(
    "fonte",
    [
        "import models",
        "import models.ordem_servico",
        "from models import OrdemServico",
        "from ui.aplicacao import Aplicacao",
        "from persistencia import Repositorio",
        "import persistencia.repositorio as r",
        "from app.contexto import Contexto",
        "import main",
        "def f():\n    from models.usuario import Usuario",
        "import importlib\nimportlib.import_module('persistencia.repositorio')",
        "__import__('ui.tela_base')",
    ],
)
def test_analisador_detecta_importacao_do_legado(fonte: str) -> None:
    assert violacoes_de_legado(coletar_importacoes(fonte, "manutencao.domain.x"))


@pytest.mark.parametrize(
    "fonte",
    [
        "from manutencao.domain import usuario",
        "import json\nfrom pathlib import Path",
        "from application_extras import x",  # nome parecido, mas não é o módulo legado 'app'
        "import models_extra",
    ],
)
def test_analisador_nao_acusa_falso_positivo(fonte: str) -> None:
    assert violacoes_de_legado(coletar_importacoes(fonte, "manutencao.domain.x")) == []


# ---------------------------------------------------------------------------- o pacote real


def test_ha_arquivos_para_analisar() -> None:
    assert len(FONTES) >= 6  # raiz + 5 camadas


@pytest.mark.parametrize("fonte", FONTES, ids=lambda f: f.modulo)
def test_pacote_novo_nao_importa_o_legado(fonte: ArquivoFonte) -> None:
    texto = fonte.caminho.read_text(encoding="utf-8")
    assert violacoes_de_legado(coletar_importacoes(texto, fonte.modulo, fonte.eh_pacote)) == []


def test_pacote_novo_importa_sem_carregar_o_legado() -> None:
    modulos = [f.modulo for f in FONTES]
    resultado = _importar_sob_bloqueio(DIRETORIO_SRC, modulos)
    assert resultado.returncode == 0, resultado.stderr or resultado.stdout


def test_bloqueador_de_runtime_detecta_importacao_do_legado(tmp_path: Path) -> None:
    """Prova que a checagem em subprocesso falha de fato quando o legado é importado."""
    pacote = tmp_path / "pacote_ruim"
    pacote.mkdir()
    (pacote / "__init__.py").write_text("import models\n", encoding="utf-8")
    resultado = _importar_sob_bloqueio(tmp_path, ["pacote_ruim"])
    assert resultado.returncode != 0
    assert "bloqueada" in resultado.stderr


# ----------------------------------------------------------------------- os testes também


def test_testes_fora_da_caracterizacao_nao_importam_o_legado() -> None:
    """Somente ``tests/caracterizacao`` pode tocar o legado (Operação B, via fachada)."""
    permitidos = DIRETORIO_TESTES / "caracterizacao"
    problemas: dict[str, list[str]] = {}
    for fonte in listar_arquivos_python(DIRETORIO_TESTES, RAIZ_BACKEND):
        if permitidos in fonte.caminho.parents:
            continue
        achados = violacoes_de_legado(
            coletar_importacoes(
                fonte.caminho.read_text(encoding="utf-8"), fonte.modulo, fonte.eh_pacote
            )
        )
        if achados:
            problemas[fonte.modulo] = achados
    assert problemas == {}
