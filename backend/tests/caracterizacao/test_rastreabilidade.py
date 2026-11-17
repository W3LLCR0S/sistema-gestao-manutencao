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
    "test_autorizacao_servicos.py",
    "test_operacao_e_servicos.py",
    "test_regularizacao_e_servicos.py",
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


# O estado esperado de CADA delta: DLT-07 e DLT-11 (Operação C), DLT-10 (IDs monotônicos, Operação
# D), DLT-12 a DLT-17 (autorização nos serviços, regularização da Operação D) e DLT-01 a DLT-06,
# DLT-08 e DLT-09 (regras de negócio, Operação E) estão implementados. Ao implementar um delta, este
# dicionário muda no mesmo commit que o código, os testes e a evidência.
ESTADO_ESPERADO: dict[str, StatusDelta] = {
    "DLT-01": StatusDelta.IMPLEMENTADO,
    "DLT-02": StatusDelta.IMPLEMENTADO,
    "DLT-03": StatusDelta.IMPLEMENTADO,
    "DLT-04": StatusDelta.IMPLEMENTADO,
    "DLT-05": StatusDelta.IMPLEMENTADO,
    "DLT-06": StatusDelta.IMPLEMENTADO,
    "DLT-07": StatusDelta.IMPLEMENTADO,
    "DLT-08": StatusDelta.IMPLEMENTADO,
    "DLT-09": StatusDelta.IMPLEMENTADO,
    "DLT-10": StatusDelta.IMPLEMENTADO,
    "DLT-11": StatusDelta.IMPLEMENTADO,
    "DLT-12": StatusDelta.IMPLEMENTADO,
    "DLT-13": StatusDelta.IMPLEMENTADO,
    "DLT-14": StatusDelta.IMPLEMENTADO,
    "DLT-15": StatusDelta.IMPLEMENTADO,
    "DLT-16": StatusDelta.IMPLEMENTADO,
    "DLT-17": StatusDelta.IMPLEMENTADO,
}
DELTAS_DA_REGULARIZACAO_D = tuple(f"DLT-{n}" for n in range(12, 18))
DELTAS_DA_OPERACAO_E = tuple(f"DLT-0{n}" for n in (1, 2, 3, 4, 5, 6, 8, 9))
OPERACAO_ESPERADA = {
    "DLT-07": "C",
    "DLT-10": "D",
    "DLT-11": "C",
    **dict.fromkeys(DELTAS_DA_REGULARIZACAO_D, "D"),
}  # os demais: "E"
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
            # Delta de regra de domínio (Operação C) exige teste de domínio; de política de
            # repositório (DLT-10) exige contrato e aplicação; de autorização nos serviços
            # (DLT-12 a DLT-17) exige teste de aplicação.
            if delta.operacao_prevista == "C":
                exigidos: tuple[str, ...] = ("dominio/",)
            elif delta.id in DELTAS_DA_REGULARIZACAO_D:
                exigidos = ("aplicacao/",)
            elif delta.id in DELTAS_DA_OPERACAO_E:
                # regra de negócio: o domínio, os serviços e a comparação com o legado
                exigidos = ("dominio/", "aplicacao/")
            else:
                exigidos = ("contrato/", "aplicacao/")
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


# ------------------------------------------------- DLT-12 a DLT-17 (regularização da Operação D)


@pytest.mark.parametrize("delta_id", DELTAS_DA_REGULARIZACAO_D)
def test_delta_da_regularizacao_registra_todos_os_campos_exigidos(delta_id: str) -> None:
    """Os dez itens da aprovação: id, legado, aprovado, justificativa, camada, evidência, testes
    do legado e do novo comportamento, estado e data/referência da aprovação."""
    delta = DELTAS_POR_ID[delta_id]
    assert delta.id == delta_id
    assert len(delta.legado) > 40, "comportamento do legado"
    assert len(delta.aprovado) > 40, "comportamento aprovado"
    assert len(delta.justificativa) > 40, "justificativa"
    assert delta.camada == "application", "camada responsável"
    assert delta.status is StatusDelta.IMPLEMENTADO, "estado"
    assert delta.evidencia, "evidência / testes do comportamento novo"
    assert delta.testes_legado, "testes do comportamento legado"
    assert "2026-11-17" in delta.aprovacao, "data da aprovação"
    assert "DECISOES_APROVADAS" in delta.aprovacao, "referência da aprovação"
    assert delta.operacao_prevista == "D"


@pytest.mark.parametrize("delta_id", DELTAS_DA_REGULARIZACAO_D)
def test_delta_da_regularizacao_tem_teste_do_legado_existente_e_de_cenario_do_delta(
    delta_id: str,
) -> None:
    for referencia in DELTAS_POR_ID[delta_id].testes_legado:
        arquivo, _, teste = referencia.partition("::")
        assert teste in _funcoes_de_nivel_de_modulo(arquivo), referencia
        # o comportamento antigo está num teste de cenário (com marcador) do próprio delta
        assert arquivo.startswith("caracterizacao/test_"), referencia
        ids = _testes_por_arquivo()[arquivo.removeprefix("caracterizacao/")][teste]
        assert len(ids) == 1, referencia
        assert ids[0] in DELTAS_POR_ID[delta_id].cenarios, (referencia, ids)


@pytest.mark.parametrize("delta_id", DELTAS_DA_REGULARIZACAO_D)
def test_delta_da_regularizacao_tem_testes_novos_na_aplicacao_e_na_comparacao_com_o_legado(
    delta_id: str,
) -> None:
    evidencia = DELTAS_POR_ID[delta_id].evidencia
    assert any(e.startswith("aplicacao/test_autorizacao.py::") for e in evidencia)
    assert any(e.startswith("caracterizacao/test_autorizacao_servicos.py::") for e in evidencia)
    prefixo = "test_" + delta_id.lower().replace("-", "")
    assert all(e.partition("::")[2].startswith(prefixo) for e in evidencia), delta_id


def test_os_deltas_nao_foram_renumerados_e_a_operacao_e_implementou_os_que_faltavam() -> None:
    ids = [d.id for d in DELTAS]
    assert ids == [f"DLT-{n:02d}" for n in range(1, 18)]
    # a Operação E implementou DLT-01 a DLT-06, 08 e 09; nenhum delta ficou pendente
    pendentes = {i for i, e in ESTADO_ESPERADO.items() if e is StatusDelta.NAO_IMPLEMENTADO}
    assert pendentes == set()
    for delta_id in ("DLT-07", "DLT-10", "DLT-11", *DELTAS_DA_REGULARIZACAO_D):
        assert DELTAS_POR_ID[delta_id].status is StatusDelta.IMPLEMENTADO
    # o DLT-07 é da Operação C e o DLT-09 nunca foi "reservado" a outra operação
    assert "DLT-07" not in DELTAS_DA_OPERACAO_E


def test_as_decisoes_dlt_12_a_17_constam_de_decisoes_aprovadas_e_do_adr_0006() -> None:
    docs = RAIZ_REPOSITORIO / "docs"
    decisoes = (docs / "DECISOES_APROVADAS.md").read_text(encoding="utf-8")
    adr = (docs / "adr" / "0006-estrategia-de-testes.md").read_text(encoding="utf-8")
    for delta_id in DELTAS_DA_REGULARIZACAO_D:
        assert f"| {delta_id} |" in decisoes, f"{delta_id} ausente de DECISOES_APROVADAS.md"
        assert delta_id in adr, f"{delta_id} ausente do ADR-0006"
    # as decisões D-01 a D-15 continuam todas lá, sem renumeração
    for numero in range(1, 16):
        assert f"| D-{numero:02d} |" in decisoes, f"D-{numero:02d}"


def test_nenhum_cenario_e_dispensado_por_marcador_generico_de_defeito() -> None:
    """Só se exclui um cenário dos serviços por delta (``test_adaptador_servicos.py``); a
    categoria ``DEFEITO_CORRIGIDO`` não existe em nenhum registro."""
    for arquivo in DIRETORIO.glob("*.py"):
        if arquivo.name in {"test_rastreabilidade.py", "test_adaptador_servicos.py"}:
            continue  # estes dois citam o nome só para proibi-lo
        assert "DEFEITO_CORRIGIDO" not in arquivo.read_text(encoding="utf-8"), arquivo.name


# ------------------------------------------------------------ DLT-01 a DLT-09 (Operação E)


@pytest.mark.parametrize("delta_id", DELTAS_DA_OPERACAO_E)
def test_delta_da_operacao_e_registra_todos_os_campos_exigidos(delta_id: str) -> None:
    """Como os da regularização da Operação D: legado, aprovado, justificativa, camada,
    evidência, teste do legado, estado e a data e a referência da aprovação."""
    delta = DELTAS_POR_ID[delta_id]
    assert delta.status is StatusDelta.IMPLEMENTADO
    assert delta.operacao_prevista == "E"
    assert len(delta.legado) > 40, "comportamento do legado"
    assert len(delta.aprovado) > 40, "comportamento aprovado"
    assert len(delta.justificativa) > 40, "justificativa"
    assert delta.camada in {"domain", "application"}, "camada responsável"
    assert delta.evidencia, "evidência / testes do comportamento novo"
    assert delta.testes_legado, "testes do comportamento legado"
    assert "2026-11-15" in delta.aprovacao
    assert "2026-11-17" in delta.aprovacao
    assert "DECISOES_APROVADAS" in delta.aprovacao
    # evidência separada por camada: domínio, serviços e comparação com o legado
    prefixos = {e.split("/")[0] for e in delta.evidencia}
    assert {"dominio", "aplicacao", "caracterizacao"} <= prefixos, delta_id


@pytest.mark.parametrize("delta_id", DELTAS_DA_OPERACAO_E)
def test_delta_da_operacao_e_tem_o_teste_do_legado_existente_e_de_cenario_do_delta(
    delta_id: str,
) -> None:
    for referencia in DELTAS_POR_ID[delta_id].testes_legado:
        arquivo, _, teste = referencia.partition("::")
        assert teste in _funcoes_de_nivel_de_modulo(arquivo), referencia
        assert arquivo.startswith("caracterizacao/test_"), referencia
        ids = _testes_por_arquivo()[arquivo.removeprefix("caracterizacao/")][teste]
        assert len(ids) == 1, referencia
        assert ids[0] in DELTAS_POR_ID[delta_id].cenarios, (referencia, ids)


def test_as_decisoes_dlt_01_a_09_constam_das_decisoes_aprovadas() -> None:
    decisoes = (RAIZ_REPOSITORIO / "docs" / "DECISOES_APROVADAS.md").read_text(encoding="utf-8")
    for delta_id in DELTAS_DA_OPERACAO_E:
        assert f"| {delta_id} |" in decisoes, f"{delta_id} ausente de DECISOES_APROVADAS.md"
