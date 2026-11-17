"""Análise estática (``ast``) de quais responsabilidades cada cenário exige.

Lê os testes de caracterização **sem importá-los**. Para cada teste com marcador ``cenario``:

* se recebe a fixture ``f``, o teste usa a fachada: as responsabilidades que ele exige são as das
  operações ausentes do domínio puro que ele chama, direta ou **indiretamente** (por funções
  auxiliares do próprio módulo ou de ``fluxos.py``, inclusive as passadas como argumento de
  ``parametrize``);
* se não recebe ``f``, o teste não usa a fachada e só roda contra o legado: ``cli`` exige a
  interface de linha de comando; ``adaptador``, ``caminho_base`` e ``tmp_path`` exigem a
  persistência (instâncias do repositório sobre o arquivo JSON).

O resultado é o conjunto de pares (cenário, responsabilidade) que o registro de
``aplicabilidade.py`` precisa conter, nem mais, nem menos.
"""

import ast
from pathlib import Path

from tests.caracterizacao.aplicabilidade import Responsabilidade

DIRETORIO = Path(__file__).resolve().parent
SEM_CENARIO = {"test_base.py", "test_rastreabilidade.py", "test_aplicabilidade.py"}

# Operação da fachada -> responsabilidade que o domínio puro não tem. É a fonte única; o teste de
# aplicabilidade confere que o adaptador do domínio ausenta exatamente estas operações.
RESPONSABILIDADE_DO_METODO: dict[str, Responsabilidade] = {
    "atualizar_disponibilidades": Responsabilidade.DISPONIBILIDADE_DERIVADA,
    "cadastrar_usuario": Responsabilidade.CADASTRO_E_IDENTIFICADORES,
    "cadastrar_equipamento": Responsabilidade.CADASTRO_E_IDENTIFICADORES,
    "remover_usuario": Responsabilidade.REGRAS_DE_EXCLUSAO,
    "remover_equipamento": Responsabilidade.REGRAS_DE_EXCLUSAO,
    "salvar_e_recarregar": Responsabilidade.PERSISTENCIA,
}


def _cenario(decorador: ast.expr) -> str | None:
    if (
        isinstance(decorador, ast.Call)
        and isinstance(decorador.func, ast.Attribute)
        and decorador.func.attr == "cenario"
        and len(decorador.args) == 1
        and isinstance(decorador.args[0], ast.Constant)
        and isinstance(decorador.args[0].value, str)
    ):
        return decorador.args[0].value
    return None


def _nomes_e_metodos(no: ast.AST) -> tuple[set[str], set[str]]:
    """Nomes lidos (funções referenciadas) e métodos chamados dentro de um nó."""
    nomes: set[str] = set()
    metodos: set[str] = set()
    for filho in ast.walk(no):
        if isinstance(filho, ast.Name) and isinstance(filho.ctx, ast.Load):
            nomes.add(filho.id)
        elif isinstance(filho, ast.Attribute):
            metodos.add(filho.attr)
    return nomes, metodos


def _funcoes_do_modulo(arquivo: Path) -> dict[str, ast.FunctionDef]:
    arvore = ast.parse(arquivo.read_text(encoding="utf-8"))
    return {n.name: n for n in arvore.body if isinstance(n, ast.FunctionDef)}


def _tabela_de_auxiliares() -> dict[str, ast.FunctionDef]:
    """Funções de apoio que os testes podem chamar (``fluxos.py``; as locais entram por arquivo)."""
    return _funcoes_do_modulo(DIRETORIO / "fluxos.py")


def _metodos_usados(
    funcao: ast.FunctionDef, auxiliares: dict[str, ast.FunctionDef], vistos: set[str]
) -> set[str]:
    nomes, metodos = _nomes_e_metodos(funcao)
    for nome in nomes:
        auxiliar = auxiliares.get(nome)
        if auxiliar is not None and nome not in vistos and nome != funcao.name:
            vistos.add(nome)
            metodos |= _metodos_usados(auxiliar, auxiliares, vistos)
    return metodos


def exigencias_por_teste() -> dict[tuple[str, str], tuple[str, set[Responsabilidade]]]:
    """(arquivo, teste) -> (cenário, responsabilidades exigidas) para todo teste de regra."""
    resultado: dict[tuple[str, str], tuple[str, set[Responsabilidade]]] = {}
    fluxos = _tabela_de_auxiliares()
    for arquivo in sorted(DIRETORIO.glob("test_*.py")):
        if arquivo.name in SEM_CENARIO:
            continue
        locais = _funcoes_do_modulo(arquivo)
        auxiliares = {**fluxos, **{n: f for n, f in locais.items() if not n.startswith("test_")}}
        for nome, funcao in locais.items():
            if not nome.startswith("test_"):
                continue
            cenarios = [c for d in funcao.decorator_list if (c := _cenario(d))]
            if len(cenarios) != 1:
                continue
            parametros = {a.arg for a in funcao.args.args}
            exigidas: set[Responsabilidade] = set()
            if "f" in parametros:
                usados = _metodos_usados(funcao, auxiliares, set())
                exigidas = {r for m, r in RESPONSABILIDADE_DO_METODO.items() if m in usados}
            elif "cli" in parametros:
                exigidas = {Responsabilidade.INTERFACE_DE_LINHA_DE_COMANDO}
            elif parametros & {"adaptador", "caminho_base", "tmp_path"}:
                exigidas = {Responsabilidade.PERSISTENCIA}
            else:
                raise AssertionError(f"{arquivo.name}::{nome}: não sei classificar a dependência")
            resultado[(arquivo.name, nome)] = (cenarios[0], exigidas)
    return resultado


def pares_esperados() -> set[tuple[str, Responsabilidade]]:
    """Os pares (cenário, responsabilidade) que o registro de aplicabilidade deve conter."""
    return {(cenario, r) for cenario, exigidas in exigencias_por_teste().values() for r in exigidas}
