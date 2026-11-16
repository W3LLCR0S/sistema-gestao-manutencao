"""Impressão digital do código legado: os testes de caracterização não podem alterá-lo.

Só lê arquivos de código e documentação do legado (``main.py``, ``models/``, ``persistencia/``,
``ui/``, ``app/``, ``README.md``, ``DOCUMENTACAO.md``). Nunca toca ``dados/``.
"""

import hashlib
from pathlib import Path

from tests.guardas_ambiente import RAIZ_REPOSITORIO

PASTAS_LEGADAS = ("models", "persistencia", "ui", "app")
ARQUIVOS_LEGADOS = ("main.py", "README.md", "DOCUMENTACAO.md")


def arquivos_legados() -> list[Path]:
    arquivos = [RAIZ_REPOSITORIO / nome for nome in ARQUIVOS_LEGADOS]
    for pasta in PASTAS_LEGADAS:
        arquivos.extend(p for p in sorted((RAIZ_REPOSITORIO / pasta).rglob("*")) if _e_fonte(p))
    return arquivos


def _e_fonte(caminho: Path) -> bool:
    return caminho.is_file() and "__pycache__" not in caminho.parts and caminho.suffix != ".pyc"


def impressao_digital_do_legado() -> dict[str, str]:
    """Caminho relativo -> SHA-256 do conteúdo, para cada arquivo legado."""
    return {
        arquivo.relative_to(RAIZ_REPOSITORIO).as_posix(): hashlib.sha256(
            arquivo.read_bytes()
        ).hexdigest()
        for arquivo in arquivos_legados()
    }


def pycs_do_legado() -> set[str]:
    """Todos os ``.pyc`` existentes nas pastas legadas (para detectar bytecode novo)."""
    encontrados: set[str] = set()
    for pasta in PASTAS_LEGADAS:
        encontrados.update(
            p.relative_to(RAIZ_REPOSITORIO).as_posix()
            for p in (RAIZ_REPOSITORIO / pasta).rglob("*.pyc")
        )
    return encontrados
