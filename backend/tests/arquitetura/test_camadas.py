"""Regras de dependência entre camadas (ADR-0002, ADR-0005, ADR-0006).

Setas apontam para dentro: ``api`` -> ``application`` -> ``domain``; ``infrastructure`` implementa
as portas de ``application``; ``composicao`` é a camada mais externa e conhece todas.

Parte dos testes aplica o analisador a trechos de código sintéticos, para provar que ele
**detecta** violações; sem isso, uma varredura sobre pacotes ainda vazios passaria sempre.
"""

from pathlib import Path

import pytest

from tests.arquitetura.analise_imports import (
    CAMADAS,
    PACOTE,
    ArquivoFonte,
    coletar_importacoes,
    listar_fontes,
    violacoes_de_camada,
)
from tests.guardas_ambiente import RAIZ_BACKEND

DIRETORIO_SRC = RAIZ_BACKEND / "src"
FONTES = listar_fontes(DIRETORIO_SRC)


def _violacoes(camada: str, fonte: str, modulo: str | None = None) -> list[str]:
    modulo = modulo or f"{PACOTE}.{camada}.exemplo"
    return violacoes_de_camada(camada, coletar_importacoes(fonte, modulo))


# ------------------------------------------------------------------------ o analisador detecta

VIOLACOES_ESPERADAS = [
    # domain não importa outras camadas, nem frameworks, nem serialização
    ("domain", "from manutencao.application import portas"),
    ("domain", "import manutencao.infrastructure.repositorios"),
    ("domain", "from manutencao import api"),
    ("domain", "from manutencao.composicao import montar"),
    ("domain", "import sqlalchemy"),
    ("domain", "from pydantic import BaseModel"),
    ("domain", "import fastapi"),
    ("domain", "import json"),
    ("domain", "from pickle import dumps"),
    (
        "domain",
        "from ..application import servicos",
    ),  # relativo: resolve para manutencao.application
    ("domain", "def f():\n    import manutencao.api"),  # importação dentro de função
    # application depende só de domain
    ("application", "from manutencao.infrastructure import memoria"),
    ("application", "import manutencao.api.rotas"),
    ("application", "from manutencao import composicao"),
    ("application", "import sqlalchemy.orm"),
    ("application", "from fastapi import Depends"),
    ("application", "import json"),
    # infrastructure não importa api nem composicao
    ("infrastructure", "from manutencao.api import rotas"),
    ("infrastructure", "import manutencao.composicao"),
    # api não importa infrastructure nem composicao
    ("api", "from manutencao.infrastructure import memoria"),
    ("api", "from manutencao import infrastructure"),
    ("api", "from ..infrastructure.memoria import RepositorioEmMemoria"),
    ("api", "from manutencao.composicao import montar"),
    # qualquer camada: legado e importação dinâmica
    ("composicao", "import models"),
    ("composicao", "from persistencia.repositorio import Repositorio"),
    ("domain", "import importlib\nimportlib.import_module('manutencao.api')"),
    ("domain", "__import__('manutencao.infrastructure')"),
]


@pytest.mark.parametrize(("camada", "fonte"), VIOLACOES_ESPERADAS)
def test_analisador_detecta_violacao(camada: str, fonte: str) -> None:
    assert _violacoes(camada, fonte), f"Violação não detectada em '{camada}': {fonte!r}"


IMPORTACOES_PERMITIDAS = [
    ("domain", "from dataclasses import dataclass\nfrom datetime import datetime\nimport enum"),
    ("domain", "from manutencao.domain.excecoes import RegraNegocioError"),
    ("domain", "from . import excecoes"),
    ("application", "from manutencao.domain.ordem_servico import OrdemServico"),
    ("application", "from typing import Protocol\nfrom manutencao.application import portas"),
    ("infrastructure", "from manutencao.application.portas import RepositorioDeOrdens"),
    ("infrastructure", "from manutencao.domain import usuario\nimport sqlalchemy"),
    ("api", "from manutencao.application.servicos import ServicoDeOrdens\nimport fastapi"),
    ("api", "from manutencao.domain.enums import StatusOS\nfrom pydantic import BaseModel"),
    (
        "composicao",
        "from manutencao.api import app\nfrom manutencao.application import servicos\n"
        "from manutencao.infrastructure import memoria\nfrom manutencao.domain import usuario",
    ),
]


@pytest.mark.parametrize(("camada", "fonte"), IMPORTACOES_PERMITIDAS)
def test_analisador_aceita_importacoes_permitidas(camada: str, fonte: str) -> None:
    assert _violacoes(camada, fonte) == []


def test_importacao_relativa_e_resolvida_para_o_nome_absoluto() -> None:
    importacoes = coletar_importacoes(
        "from ..infrastructure import memoria", "manutencao.api.rotas", eh_pacote=False
    )
    assert "manutencao.infrastructure" in {i.modulo for i in importacoes}
    importacoes = coletar_importacoes("from . import rotas", "manutencao.api", eh_pacote=True)
    assert "manutencao.api.rotas" in {i.modulo for i in importacoes}


# ------------------------------------------------------------------------- o pacote real


def test_pacote_tem_exatamente_as_cinco_camadas() -> None:
    subpacotes = {
        p.name for p in (DIRETORIO_SRC / PACOTE).iterdir() if p.is_dir() and p.name != "__pycache__"
    }
    assert subpacotes == set(CAMADAS)
    for camada in CAMADAS:
        assert (DIRETORIO_SRC / PACOTE / camada / "__init__.py").is_file()


def test_varredura_enxerga_todas_as_camadas() -> None:
    """Garante que a varredura real não passa por falta de arquivos analisados."""
    assert {f.camada for f in FONTES if f.camada} == set(CAMADAS)


def test_nao_ha_modulos_fora_das_camadas() -> None:
    soltos = [f.modulo for f in FONTES if f.camada is None and f.modulo != PACOTE]
    assert soltos == [], f"Módulos fora das camadas definidas: {soltos}"


@pytest.mark.parametrize("fonte", [f for f in FONTES if f.camada], ids=lambda f: f.modulo)
def test_camada_respeita_a_regra_de_dependencia(fonte: ArquivoFonte) -> None:
    assert fonte.camada is not None
    texto = Path(fonte.caminho).read_text(encoding="utf-8")
    importacoes = coletar_importacoes(texto, fonte.modulo, fonte.eh_pacote)
    assert violacoes_de_camada(fonte.camada, importacoes) == []


def test_raiz_do_pacote_nao_importa_camadas_nem_legado() -> None:
    raiz = next(f for f in FONTES if f.modulo == PACOTE)
    importacoes = coletar_importacoes(raiz.caminho.read_text(encoding="utf-8"), PACOTE, True)
    internas = [i.modulo for i in importacoes if i.modulo.split(".")[0] == PACOTE]
    assert internas == []
    assert violacoes_de_camada("api", importacoes) == []
