"""Coerência entre o registro de cenários, os testes e o registro de deltas.

Análise estática (``ast``): lê o código dos testes sem importá-los nem executá-los.
"""

import ast
import re
from pathlib import Path

import pytest

from tests.caracterizacao.cenarios import CENARIOS, CENARIOS_POR_ID, Classe
from tests.caracterizacao.deltas import DELTAS, DELTAS_POR_ID, StatusDelta
from tests.guardas_ambiente import RAIZ_REPOSITORIO

DIRETORIO = Path(__file__).resolve().parent
# Testes de infraestrutura e de meta-verificação não descrevem regras e não têm cenário.
SEM_CENARIO = {
    "test_base.py",
    "test_rastreabilidade.py",
    "test_aplicabilidade.py",
    "test_adaptador_dominio.py",
    "test_adaptador_servicos.py",
}
FORMATO_ID = re.compile(r"^(CAR|NV)-\d{2}$")


def _cenario_do_decorador(decorador: ast.expr) -> str | None:
    """Devolve ``"CAR-01"`` para ``@pytest.mark.cenario("CAR-01")``; senão ``None``."""
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


def _testes_por_arquivo() -> dict[str, dict[str, list[str]]]:
    """arquivo -> {nome do teste -> [ids de cenário]} (testes de nível de módulo)."""
    resultado: dict[str, dict[str, list[str]]] = {}
    for arquivo in sorted(DIRETORIO.glob("test_*.py")):
        arvore = ast.parse(arquivo.read_text(encoding="utf-8"))
        testes: dict[str, list[str]] = {}
        for no in arvore.body:
            if isinstance(no, ast.FunctionDef) and no.name.startswith("test_"):
                ids = [i for d in no.decorator_list if (i := _cenario_do_decorador(d))]
                testes[no.name] = ids
        resultado[arquivo.name] = testes
    return resultado


def _ids_com_teste() -> set[str]:
    return {
        i
        for arquivo, testes in _testes_por_arquivo().items()
        if arquivo not in SEM_CENARIO
        for ids in testes.values()
        for i in ids
    }


# ----------------------------------------------------------------------------------- cenários


def test_todo_teste_de_regra_tem_exatamente_um_cenario_registrado() -> None:
    sem_marcador: list[str] = []
    ambiguos: list[str] = []
    for arquivo, testes in _testes_por_arquivo().items():
        if arquivo in SEM_CENARIO:
            continue
        for nome, ids in testes.items():
            if not ids:
                sem_marcador.append(f"{arquivo}::{nome}")
            elif len(ids) > 1:
                ambiguos.append(f"{arquivo}::{nome}")
    assert not sem_marcador, f"testes sem cenário: {sem_marcador}"
    assert not ambiguos, f"testes com mais de um cenário: {ambiguos}"


def test_testes_de_infraestrutura_nao_usam_cenario() -> None:
    usados = {
        (arquivo, nome)
        for arquivo, testes in _testes_por_arquivo().items()
        if arquivo in SEM_CENARIO
        for nome, ids in testes.items()
        if ids
    }
    assert not usados


def test_todo_marcador_aponta_para_um_cenario_do_registro() -> None:
    desconhecidos = _ids_com_teste() - set(CENARIOS_POR_ID)
    assert not desconhecidos, f"marcadores sem registro: {sorted(desconhecidos)}"


def test_todo_cenario_verificavel_tem_ao_menos_um_teste() -> None:
    sem_teste = {
        c.id for c in CENARIOS if c.classe is not Classe.NAO_VERIFICAVEL
    } - _ids_com_teste()
    assert not sem_teste, f"cenários sem teste: {sorted(sem_teste)}"


def test_cenarios_nao_verificaveis_nao_tem_teste_e_explicam_o_motivo() -> None:
    nao_verificaveis = {c.id for c in CENARIOS if c.classe is Classe.NAO_VERIFICAVEL}
    assert nao_verificaveis, "deve haver requisitos ainda não verificáveis documentados"
    assert not nao_verificaveis & _ids_com_teste()
    for c in CENARIOS:
        assert bool(c.motivo) is (c.classe is Classe.NAO_VERIFICAVEL), c.id


def test_registro_tem_ids_unicos_bem_formados_e_prefixo_coerente() -> None:
    ids = [c.id for c in CENARIOS]
    assert len(ids) == len(set(ids))
    for c in CENARIOS:
        assert FORMATO_ID.match(c.id), c.id
        assert c.id.startswith("NV-") is (c.classe is Classe.NAO_VERIFICAVEL), c.id
        assert c.titulo.strip(), c.id


def test_ids_car_sao_contiguos_de_1_ao_maior() -> None:
    numeros = sorted(int(c.id[4:]) for c in CENARIOS if c.id.startswith("CAR-"))
    assert numeros == list(range(1, len(numeros) + 1))


def test_cenarios_de_defeito_ou_de_mudanca_citam_o_achado_ou_a_decisao() -> None:
    for c in CENARIOS:
        if c.classe in (Classe.MODIFICAR, Classe.DEFEITO_LEGADO, Classe.NAO_VERIFICAVEL):
            assert c.referencias, f"{c.id} deve citar AUD-nn ou D-nn"
        for ref in c.referencias:
            assert re.fullmatch(r"(AUD|D)-\d{2}", ref), f"{c.id}: referência inválida {ref}"


def test_referencias_aud_existem_na_auditoria_e_d_nas_decisoes() -> None:
    docs = RAIZ_REPOSITORIO / "docs"
    auditoria = (docs / "AUDITORIA_ARQUITETURAL.md").read_text(encoding="utf-8")
    decisoes = (docs / "DECISOES_APROVADAS.md").read_text(encoding="utf-8")
    for c in CENARIOS:
        for ref in c.referencias:
            fonte = auditoria if ref.startswith("AUD") else decisoes
            assert ref in fonte, f"{c.id}: {ref} não consta da documentação"


# -------------------------------------------------------------------------------------- deltas


# O estado esperado de CADA delta (Operação D): DLT-07 e DLT-11 (Operação C) e DLT-10 (IDs
# monotônicos, Operação D) estão implementados; os demais são da Operação E. Ao implementar um
# delta, este dicionário muda no mesmo commit que o código, os testes e a evidência.
ESTADO_ESPERADO: dict[str, StatusDelta] = {
    "DLT-01": StatusDelta.NAO_IMPLEMENTADO,
    "DLT-02": StatusDelta.NAO_IMPLEMENTADO,
    "DLT-03": StatusDelta.NAO_IMPLEMENTADO,
    "DLT-04": StatusDelta.NAO_IMPLEMENTADO,
    "DLT-05": StatusDelta.NAO_IMPLEMENTADO,
    "DLT-06": StatusDelta.NAO_IMPLEMENTADO,
    "DLT-07": StatusDelta.IMPLEMENTADO,
    "DLT-08": StatusDelta.NAO_IMPLEMENTADO,
    "DLT-09": StatusDelta.NAO_IMPLEMENTADO,
    "DLT-10": StatusDelta.IMPLEMENTADO,
    "DLT-11": StatusDelta.IMPLEMENTADO,
}
OPERACAO_ESPERADA = {"DLT-07": "C", "DLT-10": "D", "DLT-11": "C"}  # os demais: "E"
DIRETORIO_TESTES = DIRETORIO.parent


def test_todos_os_deltas_estao_registrados_com_ids_unicos() -> None:
    assert DELTAS
    assert len({d.id for d in DELTAS}) == len(DELTAS) == len(DELTAS_POR_ID)


def test_o_estado_esperado_cobre_exatamente_os_deltas_registrados() -> None:
    assert set(ESTADO_ESPERADO) == set(DELTAS_POR_ID)


@pytest.mark.parametrize("delta_id", sorted(ESTADO_ESPERADO))
def test_cada_delta_esta_no_estado_esperado(delta_id: str) -> None:
    assert DELTAS_POR_ID[delta_id].status is ESTADO_ESPERADO[delta_id], delta_id


@pytest.mark.parametrize("delta_id", sorted(ESTADO_ESPERADO))
def test_cada_delta_tem_a_operacao_prevista_esperada(delta_id: str) -> None:
    assert DELTAS_POR_ID[delta_id].operacao_prevista == OPERACAO_ESPERADA.get(delta_id, "E")


def test_dlt_10_ids_monotonicos_esta_implementado_na_operacao_d_com_evidencia() -> None:
    delta = DELTAS_POR_ID["DLT-10"]
    assert (delta.status, delta.operacao_prevista) == (StatusDelta.IMPLEMENTADO, "D")
    assert delta.cenarios == ("CAR-75",)
    prefixos = {e.split("/")[0] for e in delta.evidencia}
    # contrato (toda implementação), aplicação (serviços) e comparação com o legado
    assert {"contrato", "aplicacao", "caracterizacao"} <= prefixos


def _funcoes_de_nivel_de_modulo(caminho_relativo: str) -> set[str]:
    arquivo = DIRETORIO_TESTES / caminho_relativo
    assert arquivo.is_file(), f"evidência aponta arquivo inexistente: {caminho_relativo}"
    arvore = ast.parse(arquivo.read_text(encoding="utf-8"))
    return {n.name for n in arvore.body if isinstance(n, ast.FunctionDef)}


def test_delta_implementado_tem_evidencia_existente_e_nao_implementado_nao_tem() -> None:
    for delta in DELTAS:
        if delta.status is StatusDelta.IMPLEMENTADO:
            assert delta.evidencia, f"{delta.id} implementado sem evidência"
            # Delta de regra de domínio (Operação C) exige teste de domínio; delta de política de
            # repositório (Operação D) exige teste de contrato e de aplicação.
            exigidos = (
                ("dominio/",) if delta.operacao_prevista == "C" else ("contrato/", "aplicacao/")
            )
            for prefixo in exigidos:
                assert any(e.startswith(prefixo) for e in delta.evidencia), (delta.id, prefixo)
            assert any(e.startswith("caracterizacao/") for e in delta.evidencia), (
                f"{delta.id} implementado sem comparação com o legado"
            )
            for evidencia in delta.evidencia:
                arquivo, _, teste = evidencia.partition("::")
                assert teste in _funcoes_de_nivel_de_modulo(arquivo), evidencia
        else:
            assert not delta.evidencia, f"{delta.id} não implementado, mas com evidência"


def test_deltas_cobrem_as_decisoes_e_melhorias_aprovadas() -> None:
    cobertas = {d.decisao.split(" ")[0] for d in DELTAS}
    esperadas = {"D-02", "D-03", "D-04", "D-05", "D-06", "D-11"}
    assert esperadas <= cobertas
    textos = " ".join(d.decisao for d in DELTAS)
    for melhoria in ("Validações obrigatórias", "Usuário ativo/inativo", "IDs monotônicos"):
        assert melhoria in textos


def test_todo_delta_e_verificado_por_cenarios_existentes_e_testados() -> None:
    testados = _ids_com_teste()
    for d in DELTAS:
        assert d.cenarios, d.id
        for cenario in d.cenarios:
            assert cenario in CENARIOS_POR_ID, f"{d.id}: {cenario} não está no registro"
            assert cenario in testados, f"{d.id}: {cenario} não tem teste"


def test_todo_cenario_de_mudanca_aprovada_pertence_a_algum_delta() -> None:
    em_deltas = {c for d in DELTAS for c in d.cenarios}
    a_modificar = {c.id for c in CENARIOS if c.classe is Classe.MODIFICAR}
    assert a_modificar <= em_deltas, f"sem delta: {sorted(a_modificar - em_deltas)}"


def test_decisoes_dos_deltas_constam_do_registro_de_decisoes() -> None:
    decisoes = (RAIZ_REPOSITORIO / "docs" / "DECISOES_APROVADAS.md").read_text(encoding="utf-8")
    for d in DELTAS:
        primeiro = d.decisao.split(" ")[0]
        if re.fullmatch(r"D-\d{2}", primeiro):
            assert f"| {primeiro} |" in decisoes, f"{d.id}: {primeiro} ausente das decisões"
