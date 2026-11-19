"""A infraestrutura em memória não usa sistema de arquivos, banco, rede nem relógio (D-10).

Análise estática (``ast``): nenhum módulo é importado ou executado.
"""

from tests.arquitetura.analise_imports import coletar_importacoes, listar_fontes
from tests.guardas_ambiente import RAIZ_BACKEND

FONTES_MEMORIA = [
    f
    for f in listar_fontes(RAIZ_BACKEND / "src")
    if f.modulo.startswith("manutencao.infrastructure.memoria")
]

# Qualquer uma destas importações significaria E/S externa ou dependência do ambiente.
PROIBIDOS = {
    "os",
    "io",
    "pathlib",
    "shutil",
    "tempfile",
    "glob",
    "json",
    "pickle",
    "shelve",
    "sqlite3",
    "dbm",
    "csv",
    "socket",
    "http",
    "urllib",
    "ssl",
    "subprocess",
    "random",
    "uuid",
    "time",
    "datetime",
    "sqlalchemy",
    "fastapi",
}


def test_a_varredura_enxerga_os_modulos_em_memoria() -> None:
    modulos = {f.modulo.rsplit(".", 1)[-1] for f in FONTES_MEMORIA}
    assert {"cargos", "equipamentos", "ordens", "usuarios", "sequencia"} <= modulos


def test_modulos_em_memoria_nao_importam_io_banco_aleatoriedade_nem_relogio() -> None:
    achados: list[str] = []
    for fonte in FONTES_MEMORIA:
        texto = fonte.caminho.read_text(encoding="utf-8")
        for importacao in coletar_importacoes(texto, fonte.modulo, fonte.eh_pacote):
            if importacao.modulo.split(".")[0] in PROIBIDOS:
                achados.append(f"{fonte.modulo}: {importacao.modulo}")
    assert achados == []


def test_modulos_em_memoria_nao_abrem_arquivos() -> None:
    for fonte in FONTES_MEMORIA:
        texto = fonte.caminho.read_text(encoding="utf-8")
        assert "open(" not in texto, fonte.modulo
