"""Só a infraestrutura lê a hora do sistema (D-11, ADR-0007).

O domínio e a aplicação recebem o instante: nenhum deles chama ``now``/``utcnow``/``today`` nem
importa ``time`` ou ``zoneinfo``. A composição também não: ela só injeta ``Relogio``.
"""

import ast

import pytest

from tests.arquitetura.analise_imports import ArquivoFonte, listar_fontes
from tests.guardas_ambiente import RAIZ_BACKEND

CAMADAS_SEM_RELOGIO = ("domain", "application", "composicao", "api")
FONTES = [f for f in listar_fontes(RAIZ_BACKEND / "src") if f.camada in CAMADAS_SEM_RELOGIO]
LEITURAS_DE_HORA = {"now", "utcnow", "today", "time", "monotonic", "perf_counter", "fromtimestamp"}
MODULOS_DE_TEMPO = {"time", "zoneinfo"}


def _leituras(fonte: ArquivoFonte) -> list[str]:
    achados: list[str] = []
    for no in ast.walk(ast.parse(fonte.caminho.read_text(encoding="utf-8"))):
        if (
            isinstance(no, ast.Call)
            and isinstance(no.func, ast.Attribute)
            and no.func.attr in LEITURAS_DE_HORA
        ):
            achados.append(f"{fonte.modulo}:{no.lineno} chama .{no.func.attr}()")
        if isinstance(no, ast.Import):
            achados += [
                f"{fonte.modulo}: import {a.name}" for a in no.names if a.name in MODULOS_DE_TEMPO
            ]
        if isinstance(no, ast.ImportFrom) and no.module in MODULOS_DE_TEMPO:
            achados.append(f"{fonte.modulo}: from {no.module} import ...")
    return achados


def test_a_varredura_enxerga_dominio_e_aplicacao() -> None:
    assert {"domain", "application"} <= {f.camada for f in FONTES}


@pytest.mark.parametrize("fonte", FONTES, ids=lambda f: f.modulo)
def test_camada_nao_le_a_hora_do_sistema(fonte: ArquivoFonte) -> None:
    assert _leituras(fonte) == []


def test_o_detector_acusa_a_leitura_da_hora(tmp_path_factory: pytest.TempPathFactory) -> None:
    pasta = tmp_path_factory.mktemp("fonte")
    arquivo = pasta / "ruim.py"
    arquivo.write_text(
        "from datetime import UTC, datetime\n"
        "import time\n"
        "def f():\n"
        "    return datetime.now(UTC), time.time()\n",
        encoding="utf-8",
    )
    achados = _leituras(ArquivoFonte(arquivo, "manutencao.application.ruim", False, "application"))
    assert any("now" in a for a in achados)
    assert any("import time" in a for a in achados)
