"""Execução da CLI legada numa **cópia temporária isolada** da árvore necessária (Operação B).

A CLI original nunca é executada diretamente: ela calcula o caminho dos dados a partir da própria
localização (``persistencia/repositorio.py::ARQUIVO_PADRAO``). Executando a cópia, esse caminho cai
dentro do diretório temporário e o ``dados/`` real não é tocado. Garantias:

* só ``main.py``, ``models/``, ``persistencia/`` e ``ui/`` são copiados (nunca ``dados/``);
* subprocesso com ``-I -B``, entradas controladas, saída capturada e *timeout*;
* um lançador bloqueia conexões de rede antes de rodar a CLI (a CLI não usa rede).
"""

import hashlib
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from tests.guardas_ambiente import DIRETORIO_DADOS, RAIZ_REPOSITORIO, caminho_em_dados

ITENS_COPIADOS = ("main.py", "models", "persistencia", "ui")
TIMEOUT_SEGUNDOS = 30

LANCADOR = """\
import runpy
import socket
import sys


def _bloqueado(*args, **kwargs):
    raise RuntimeError("rede bloqueada na caracterizacao da CLI")


socket.socket.connect = _bloqueado
socket.socket.connect_ex = _bloqueado
socket.getaddrinfo = _bloqueado

raiz = sys.argv[1]
sys.path.insert(0, raiz)
sys.argv = [raiz + "/main.py"]
runpy.run_path(raiz + "/main.py", run_name="__main__")
"""


@dataclass(frozen=True)
class Execucao:
    codigo: int
    saida: str
    erro: str


class CliIsolada:
    """Uma cópia da CLI legada num diretório temporário, com seus próprios ``dados/``."""

    def __init__(self, base: Path) -> None:
        self.base = base
        self.raiz = base / "copia"
        self.lancador = base / "lancador.py"  # fora da cópia: não faz parte do legado
        assert not caminho_em_dados(self.raiz)
        self._copiar()
        self.lancador.write_text(LANCADOR, encoding="utf-8")

    def _copiar(self) -> None:
        self.raiz.mkdir()
        for item in ITENS_COPIADOS:
            origem = RAIZ_REPOSITORIO / item
            destino = self.raiz / item
            if origem.is_dir():
                shutil.copytree(
                    origem, destino, ignore=shutil.ignore_patterns("__pycache__", "*.pyc")
                )
            else:
                shutil.copy2(origem, destino)
        assert not (self.raiz / "dados").exists(), "a cópia não pode conter dados/"

    # ------------------------------------------------------------------------------ verificações
    def copia_e_fiel_ao_original(self) -> bool:
        """Cada arquivo copiado tem o mesmo conteúdo do original (a cópia é a CLI da Entrega 1)."""
        for copiado in self.raiz.rglob("*"):
            if copiado.is_file():
                original = RAIZ_REPOSITORIO / copiado.relative_to(self.raiz)
                if _sha(copiado) != _sha(original):
                    return False
        return True

    @property
    def arquivo_de_dados(self) -> Path:
        return self.raiz / "dados" / "dados.json"

    def dados(self) -> dict[str, Any]:
        resultado: dict[str, Any] = json.loads(self.arquivo_de_dados.read_text(encoding="utf-8"))
        return resultado

    # ---------------------------------------------------------------------------------- execução
    def executar(self, entradas: list[str]) -> Execucao:
        """Roda ``main.py`` da cópia, alimentando o ``stdin`` com as linhas informadas."""
        ambiente = {k: v for k, v in os.environ.items() if not k.upper().startswith("PYTHON")}
        processo = subprocess.run(
            [sys.executable, "-I", "-B", "-X", "utf8", str(self.lancador), str(self.raiz)],
            input="".join(f"{linha}\n" for linha in entradas),
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=TIMEOUT_SEGUNDOS,
            cwd=self.base,
            env=ambiente,
            check=False,
        )
        # a execução não pode ter escrito no ``dados/`` real (o instantâneo da sessão confere)
        assert DIRETORIO_DADOS not in self.raiz.parents
        return Execucao(processo.returncode, processo.stdout, processo.stderr)


def _sha(caminho: Path) -> str:
    return hashlib.sha256(caminho.read_bytes()).hexdigest()
