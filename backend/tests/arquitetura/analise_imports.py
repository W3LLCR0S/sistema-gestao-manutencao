"""Análise estática de importações para os testes de arquitetura.

Usa apenas ``ast``: **nenhum módulo analisado é importado ou executado**, nem do pacote novo nem
do legado. Regras de referência: ADR-0002 (camadas), ADR-0006 (teste de arquitetura) e
ADR-0008 (isolamento do legado).
"""

import ast
import sys
from dataclasses import dataclass
from pathlib import Path

PACOTE = "manutencao"
CAMADAS = ("domain", "application", "infrastructure", "api", "composicao")

# Módulos do código legado da Entrega 1 (raiz do repositório). O pacote novo não os importa.
MODULOS_LEGADOS = frozenset({"models", "ui", "persistencia", "app", "main"})

# Biblioteca padrão que o domínio e a aplicação não devem usar: serialização, persistência, rede.
STDLIB_PROIBIDA_NO_NUCLEO = frozenset(
    {
        "json",
        "pickle",
        "shelve",
        "marshal",
        "sqlite3",
        "dbm",
        "socket",
        "http",
        "urllib",
        "ssl",
        "smtplib",
    }
)


@dataclass(frozen=True)
class Importacao:
    """Um módulo importado (nome absoluto) e a linha onde aparece."""

    modulo: str
    linha: int


@dataclass(frozen=True)
class Regra:
    """O que uma camada pode importar."""

    internas: frozenset[str]  # camadas de ``manutencao`` permitidas (inclui a própria)
    terceiros: bool  # pode importar bibliotecas de terceiros?
    stdlib_proibida: frozenset[str] = frozenset()


REGRAS: dict[str, Regra] = {
    # ADR-0002: domain só usa a biblioteca padrão e não importa nenhuma outra camada.
    "domain": Regra(
        frozenset({"domain"}), terceiros=False, stdlib_proibida=STDLIB_PROIBIDA_NO_NUCLEO
    ),
    # application depende só de domain; sem frameworks nem infraestrutura.
    "application": Regra(
        frozenset({"domain", "application"}),
        terceiros=False,
        stdlib_proibida=STDLIB_PROIBIDA_NO_NUCLEO,
    ),
    # infrastructure implementa as portas; não importa api nem composicao.
    "infrastructure": Regra(frozenset({"domain", "application", "infrastructure"}), terceiros=True),
    # api não importa infrastructure (ADR-0002/0005) nem a raiz de composição.
    "api": Regra(frozenset({"domain", "application", "api"}), terceiros=True),
    # composicao é a camada mais externa: conhece todas.
    "composicao": Regra(frozenset(CAMADAS), terceiros=True),
}


# --------------------------------------------------------------------------- coleta de imports


def _resolver_relativo(modulo_atual: str, eh_pacote: bool, nivel: int, modulo: str | None) -> str:
    pacote = modulo_atual.split(".") if eh_pacote else modulo_atual.split(".")[:-1]
    base = pacote[: len(pacote) - (nivel - 1)] if nivel > 1 else pacote
    if modulo:
        base = [*base, *modulo.split(".")]
    return ".".join(base)


def coletar_importacoes(fonte: str, modulo_atual: str, eh_pacote: bool = False) -> list[Importacao]:
    """Lista todas as importações de ``fonte`` (inclusive dentro de funções e ``TYPE_CHECKING``).

    Para ``from X import a`` registra ``X`` e também ``X.a``, pois ``a`` pode ser um submódulo
    (``from manutencao import infrastructure``). Importações relativas são resolvidas para o
    nome absoluto. Chamadas literais a ``importlib.import_module("x")`` e ``__import__("x")``
    também contam.
    """
    resultado: list[Importacao] = []
    for no in ast.walk(ast.parse(fonte)):
        if isinstance(no, ast.Import):
            resultado.extend(Importacao(alias.name, no.lineno) for alias in no.names)
        elif isinstance(no, ast.ImportFrom):
            if no.level:
                base = _resolver_relativo(modulo_atual, eh_pacote, no.level, no.module)
            else:
                base = no.module or ""
            if base:
                resultado.append(Importacao(base, no.lineno))
            for alias in no.names:
                if alias.name != "*" and base:
                    resultado.append(Importacao(f"{base}.{alias.name}", no.lineno))
        elif isinstance(no, ast.Call) and no.args:
            funcao = no.func
            nome = funcao.attr if isinstance(funcao, ast.Attribute) else getattr(funcao, "id", "")
            primeiro = no.args[0]
            if (
                nome in {"import_module", "__import__"}
                and isinstance(primeiro, ast.Constant)
                and isinstance(primeiro.value, str)
            ):
                resultado.append(Importacao(primeiro.value, no.lineno))
    return resultado


def topo(modulo: str) -> str:
    return modulo.split(".", 1)[0]


# ------------------------------------------------------------------------------- verificações


def violacoes_de_legado(importacoes: list[Importacao]) -> list[str]:
    """Importações dos módulos legados (``models``, ``ui``, ``persistencia``, ``app``, ``main``)."""
    return [
        f"linha {i.linha}: importa o legado '{i.modulo}'"
        for i in importacoes
        if topo(i.modulo) in MODULOS_LEGADOS
    ]


def violacoes_de_camada(camada: str, importacoes: list[Importacao]) -> list[str]:
    """Violações da regra de dependência da ``camada`` (inclui o legado)."""
    regra = REGRAS[camada]
    problemas = violacoes_de_legado(importacoes)
    for i in importacoes:
        raiz = topo(i.modulo)
        if raiz in MODULOS_LEGADOS:
            continue  # já reportado acima
        if raiz == PACOTE:
            partes = i.modulo.split(".")
            if len(partes) > 1 and partes[1] in CAMADAS and partes[1] not in regra.internas:
                problemas.append(f"linha {i.linha}: '{camada}' não pode importar '{i.modulo}'")
        elif raiz in sys.stdlib_module_names:
            if raiz in regra.stdlib_proibida:
                problemas.append(
                    f"linha {i.linha}: '{camada}' não pode usar '{i.modulo}' (serialização/rede)"
                )
        elif not regra.terceiros:
            problemas.append(
                f"linha {i.linha}: '{camada}' só usa a biblioteca padrão, importa '{i.modulo}'"
            )
    return problemas


# ------------------------------------------------------------------------ varredura de arquivos


@dataclass(frozen=True)
class ArquivoFonte:
    caminho: Path
    modulo: str
    eh_pacote: bool
    camada: str | None  # None para o ``__init__`` raiz de ``manutencao``


def listar_fontes(diretorio_src: Path) -> list[ArquivoFonte]:
    """Todos os ``.py`` de ``src/manutencao`` com nome de módulo e camada."""
    raiz = diretorio_src / PACOTE
    fontes: list[ArquivoFonte] = []
    for caminho in sorted(raiz.rglob("*.py")):
        partes = caminho.relative_to(diretorio_src).with_suffix("").parts
        eh_pacote = partes[-1] == "__init__"
        modulo = ".".join(partes[:-1] if eh_pacote else partes)
        camada = partes[1] if len(partes) > 2 or (len(partes) == 2 and not eh_pacote) else None
        if camada is not None and camada not in CAMADAS:
            camada = None  # módulo solto na raiz do pacote
        fontes.append(ArquivoFonte(caminho, modulo, eh_pacote, camada))
    return fontes


def listar_arquivos_python(diretorio: Path, relativo_a: Path) -> list[ArquivoFonte]:
    """Todos os ``.py`` de ``diretorio`` com nome de módulo relativo a ``relativo_a``."""
    fontes: list[ArquivoFonte] = []
    for caminho in sorted(diretorio.rglob("*.py")):
        partes = caminho.relative_to(relativo_a).with_suffix("").parts
        eh_pacote = partes[-1] == "__init__"
        fontes.append(
            ArquivoFonte(caminho, ".".join(partes[:-1] if eh_pacote else partes), eh_pacote, None)
        )
    return fontes
