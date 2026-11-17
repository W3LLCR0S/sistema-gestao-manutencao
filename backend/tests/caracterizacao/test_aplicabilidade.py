"""Consistência do registro de aplicabilidade dos cenários ao domínio puro (Operação C6).

Garante que o registro (``aplicabilidade.py``) diz a verdade: cada linha é uma dependência real,
nenhuma dependência real ficou de fora, todo ``skip`` vem do registro e o adaptador do domínio não
importa infraestrutura. Testes de infraestrutura da caracterização (sem marcador ``cenario``).
"""

import ast
import sys
from collections import Counter
from collections.abc import Callable
from pathlib import Path

import pytest

from tests.caracterizacao.adaptador_dominio import AdaptadorDominio
from tests.caracterizacao.analise_aplicabilidade import (
    RESPONSABILIDADE_DO_METODO,
    exigencias_por_teste,
    pares_esperados,
)
from tests.caracterizacao.aplicabilidade import (
    REGISTRO,
    REGISTRO_POR_PAR,
    SUBSTITUIDOS_POR_DELTA,
    Camada,
    Responsabilidade,
    decidir,
)
from tests.caracterizacao.cenarios import CENARIOS_POR_ID, Classe
from tests.caracterizacao.deltas import DELTAS_POR_ID, StatusDelta
from tests.caracterizacao.fachada import Fachada
from tests.caracterizacao.numeracao import nova_numeracao
from tests.guardas_ambiente import RAIZ_BACKEND

DIRETORIO_TESTES = RAIZ_BACKEND / "tests"
ARQUIVO_ADAPTADOR = DIRETORIO_TESTES / "caracterizacao" / "adaptador_dominio.py"


# ------------------------------------------------------------------------------ o registro


def test_toda_linha_cita_um_cenario_car_existente_e_verificavel() -> None:
    for linha in REGISTRO:
        assert linha.cenario in CENARIOS_POR_ID, linha.cenario
        assert linha.cenario.startswith("CAR-"), f"{linha.cenario}: NV-nn não tem teste"
        assert CENARIOS_POR_ID[linha.cenario].classe is not Classe.NAO_VERIFICAVEL


def test_pares_cenario_responsabilidade_sao_unicos() -> None:
    pares = Counter((linha.cenario, linha.responsabilidade) for linha in REGISTRO)
    assert [p for p, n in pares.items() if n > 1] == []
    assert len(REGISTRO_POR_PAR) == len(REGISTRO)


def test_toda_linha_informa_responsabilidade_camada_e_justificativa() -> None:
    for linha in REGISTRO:
        assert isinstance(linha.responsabilidade, Responsabilidade), linha.cenario
        assert isinstance(linha.camada, Camada), linha.cenario
        assert len(linha.justificativa.strip()) >= 80, f"{linha.cenario}: justificativa curta"
        assert linha.cenario in linha.motivo
        assert linha.responsabilidade.value in linha.motivo
        assert linha.camada.value in linha.motivo


def test_cada_responsabilidade_tem_uma_unica_camada_futura() -> None:
    camadas: dict[Responsabilidade, set[Camada]] = {}
    for linha in REGISTRO:
        camadas.setdefault(linha.responsabilidade, set()).add(linha.camada)
    assert all(len(c) == 1 for c in camadas.values()), camadas
    assert set(camadas) == set(Responsabilidade), "responsabilidade catalogada e nunca usada"


def test_o_registro_e_exatamente_o_que_os_testes_exigem() -> None:
    """Nem uma linha a mais (registro velho), nem uma a menos (skip sem justificativa)."""
    registrados = {(i.cenario, i.responsabilidade) for i in REGISTRO}
    esperados = pares_esperados()
    assert registrados - esperados == set(), "linhas sem teste que dependa da responsabilidade"
    assert esperados - registrados == set(), "dependências reais sem linha no registro"


def test_a_analise_estatica_viu_todos_os_testes_de_regra() -> None:
    # 173 funções de teste de regra na Operação B (uma por marcador ``cenario``).
    assert len(exigencias_por_teste()) == 173


def test_cenarios_inteiramente_aplicaveis_nao_estao_no_registro() -> None:
    exigencias = exigencias_por_teste()
    por_cenario: dict[str, list[bool]] = {}
    for cenario, exigidas in exigencias.values():
        por_cenario.setdefault(cenario, []).append(bool(exigidas))
    registrados = {i.cenario for i in REGISTRO}
    aplicaveis = {c for c, lista in por_cenario.items() if not any(lista)}
    assert aplicaveis & registrados == set()
    assert len(aplicaveis) >= 40, "o domínio puro deve responder à maior parte dos cenários"


# --------------------------------------------------------------- o adaptador do domínio


def _metodos_ausentes_do_adaptador() -> dict[str, Responsabilidade]:
    """Métodos do adaptador cujo corpo é só ``self._ausente(Responsabilidade.X)``."""
    arvore = ast.parse(ARQUIVO_ADAPTADOR.read_text(encoding="utf-8"))
    classe = next(
        n for n in arvore.body if isinstance(n, ast.ClassDef) and n.name == "AdaptadorDominio"
    )
    ausentes: dict[str, Responsabilidade] = {}
    for metodo in classe.body:
        if not isinstance(metodo, ast.FunctionDef):
            continue
        chamadas = [
            n
            for n in ast.walk(metodo)
            if isinstance(n, ast.Call)
            and isinstance(n.func, ast.Attribute)
            and n.func.attr == "_ausente"
        ]
        for chamada in chamadas:
            argumento = chamada.args[0]
            assert isinstance(argumento, ast.Attribute)
            ausentes[metodo.name] = Responsabilidade[argumento.attr]
    return ausentes


def test_o_adaptador_ausenta_exatamente_as_operacoes_catalogadas() -> None:
    assert _metodos_ausentes_do_adaptador() == RESPONSABILIDADE_DO_METODO


CHAMADAS_DE_TESTE: dict[str, Callable[[AdaptadorDominio], object]] = {
    "atualizar_disponibilidades": lambda a: a.atualizar_disponibilidades(),
    "cadastrar_usuario": lambda a: a.cadastrar_usuario("Diego", 2),
    "cadastrar_equipamento": lambda a: a.cadastrar_equipamento("Prensa", "P1"),
    "remover_usuario": lambda a: a.remover_usuario(3, 1),
    "remover_equipamento": lambda a: a.remover_equipamento(3),
    "salvar_e_recarregar": lambda a: a.salvar_e_recarregar(),
}


@pytest.mark.parametrize("metodo", RESPONSABILIDADE_DO_METODO)
def test_operacao_ausente_avisa_a_responsabilidade_certa_e_nao_altera_a_base(metodo: str) -> None:
    pedidas: list[Responsabilidade] = []

    def registrar(responsabilidade: Responsabilidade) -> None:
        pedidas.append(responsabilidade)
        raise LookupError("interrompe a chamada, como o skip faz")

    adaptador = AdaptadorDominio(diante_da_ausencia=registrar, numeracao=nova_numeracao())  # type: ignore[arg-type]
    antes = (adaptador.usuarios(), adaptador.equipamentos(), adaptador.todas_as_os())
    with pytest.raises(LookupError):
        CHAMADAS_DE_TESTE[metodo](adaptador)
    assert pedidas == [RESPONSABILIDADE_DO_METODO[metodo]]
    assert (adaptador.usuarios(), adaptador.equipamentos(), adaptador.todas_as_os()) == antes


def test_sem_gancho_o_adaptador_falha_em_vez_de_fingir_a_operacao() -> None:
    with pytest.raises(NotImplementedError, match="persistencia"):
        AdaptadorDominio(numeracao=nova_numeracao()).salvar_e_recarregar()


def test_o_adaptador_cobre_toda_a_fachada() -> None:
    faltando = [
        nome
        for nome in vars(Fachada)
        if not nome.startswith("_") and not hasattr(AdaptadorDominio, nome)
    ]
    assert faltando == []


# ---------------------------------------------------------------- a decisão de pular ou falhar


def test_decidir_so_justifica_o_que_esta_no_registro() -> None:
    linha = REGISTRO[0]
    assert decidir((linha.cenario,), linha.responsabilidade) is linha
    assert decidir(("CAR-01",), Responsabilidade.PERSISTENCIA) is None  # cenário aplicável
    assert decidir((linha.cenario,), Responsabilidade.INTERFACE_DE_LINHA_DE_COMANDO) is None
    assert decidir((), Responsabilidade.PERSISTENCIA) is None


# -------------------------------------------------------------- nenhum skip/xfail fora do registro


def _usos_de_skip_ou_xfail(arquivo: Path) -> list[str]:
    achados: list[str] = []
    for no in ast.walk(ast.parse(arquivo.read_text(encoding="utf-8"))):
        if isinstance(no, ast.Attribute) and no.attr in {
            "skip",
            "skipif",
            "xfail",
            "importorskip",
        }:
            achados.append(f"{no.attr} na linha {no.lineno}")
    return achados


def test_nenhum_teste_usa_skip_ou_xfail_fora_do_gancho_do_registro() -> None:
    """O único ``pytest.skip`` é o do conftest da caracterização, e só pelo registro."""
    permitido = DIRETORIO_TESTES / "caracterizacao" / "conftest.py"
    proibidos: dict[str, list[str]] = {}
    for arquivo in sorted(DIRETORIO_TESTES.rglob("*.py")):
        if arquivo in {permitido, Path(__file__).resolve()}:
            continue
        achados = _usos_de_skip_ou_xfail(arquivo)
        if achados:
            proibidos[str(arquivo.relative_to(DIRETORIO_TESTES))] = achados
    assert proibidos == {}
    assert len(_usos_de_skip_ou_xfail(permitido)) == 1


# ------------------------------------------------------------- o adaptador não toca infraestrutura

PERMITIDOS_NO_ADAPTADOR = {
    "tests.caracterizacao.aplicabilidade",
    "tests.caracterizacao.fachada",
    "tests.caracterizacao.traducao",
}


def _importados(arquivo: Path) -> set[str]:
    modulos: set[str] = set()
    for no in ast.walk(ast.parse(arquivo.read_text(encoding="utf-8"))):
        if isinstance(no, ast.Import):
            modulos |= {alias.name for alias in no.names}
        elif isinstance(no, ast.ImportFrom) and no.module:
            modulos.add(no.module)
    return modulos


def test_adaptador_do_dominio_so_importa_o_dominio_a_biblioteca_padrao_e_a_fachada() -> None:
    for modulo in _importados(ARQUIVO_ADAPTADOR):
        raiz = modulo.split(".")[0]
        permitido = (
            raiz in sys.stdlib_module_names
            or modulo.startswith("manutencao.domain")
            or modulo in PERMITIDOS_NO_ADAPTADOR
        )
        assert permitido, f"importação não permitida no adaptador do domínio: {modulo}"


def test_a_traducao_compartilhada_so_importa_o_dominio_a_biblioteca_padrao_e_a_fachada() -> None:
    arquivo = DIRETORIO_TESTES / "caracterizacao" / "traducao.py"
    for modulo in _importados(arquivo):
        permitido = (
            modulo.split(".")[0] in sys.stdlib_module_names
            or modulo.startswith("manutencao.domain")
            or modulo == "tests.caracterizacao.fachada"
        )
        assert permitido, f"importação não permitida na tradução: {modulo}"


def test_adaptador_do_dominio_nao_importa_o_legado_nem_outras_camadas() -> None:
    proibidos = {"models", "persistencia", "ui", "app", "sqlalchemy", "fastapi", "pydantic"}
    modulos = _importados(ARQUIVO_ADAPTADOR)
    assert {m.split(".")[0] for m in modulos} & proibidos == set()
    assert not any(
        m.startswith(("manutencao.application", "manutencao.infrastructure", "manutencao.api"))
        for m in modulos
    )


# --------------------------------------------------------------- substituídos por delta


def _funcoes_de_teste(arquivo: Path) -> set[str]:
    arvore = ast.parse(arquivo.read_text(encoding="utf-8"))
    return {n.name for n in arvore.body if isinstance(n, ast.FunctionDef)}


def test_cenarios_substituidos_apontam_delta_implementado_e_testes_novos_existentes() -> None:
    assert SUBSTITUIDOS_POR_DELTA, "o registro deve explicar o CAR-74 (DLT-11)"
    registrados = {i.cenario for i in REGISTRO}
    for cenario, (delta_id, evidencias) in SUBSTITUIDOS_POR_DELTA.items():
        assert cenario in CENARIOS_POR_ID, cenario
        assert CENARIOS_POR_ID[cenario].classe is not Classe.NAO_VERIFICAVEL
        assert cenario not in registrados, f"{cenario}: substituído e inaplicável ao mesmo tempo"
        delta = DELTAS_POR_ID[delta_id]
        assert delta.status is StatusDelta.IMPLEMENTADO, f"{delta_id} ainda não implementado"
        assert cenario in delta.cenarios, f"{delta_id} não lista {cenario}"
        assert evidencias, cenario
        for teste in evidencias:
            assert teste in _funcoes_de_teste(DIRETORIO_TESTES / "dominio" / "test_permissoes.py")
        # os testes novos também constam como evidência do delta
        for teste in evidencias:
            assert any(e.endswith(f"::{teste}") for e in delta.evidencia), teste
