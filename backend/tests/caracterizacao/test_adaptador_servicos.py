"""Os serviços de aplicação lado a lado com o legado (Operação D7) e o registro de aplicabilidade.

Os testes de cenário rodam cada comportamento contra um adaptador de cada vez. Estes aqui rodam o
**mesmo** roteiro no legado e nos serviços e exigem resultados e estados idênticos (inclusive o
texto das mensagens e a ordem do histórico), com as únicas diferenças aprovadas:

* DLT-07: datas em UTC com fuso (a comparação as normaliza para o texto do legado);
* DLT-10: identificadores monotônicos (o legado reaproveita o maior id após exclusão);
* DLT-11: permissões tipadas (nome inválido é erro; no legado, negação silenciosa);
* os defeitos do legado que a autorização central fecha (``NAO_REPRODUZIDOS_PELOS_SERVICOS``).

São testes de infraestrutura da caracterização (sem marcador ``cenario``).
"""

import ast
import sys
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from manutencao.application.erros import RegraDeAplicacaoError
from tests.caracterizacao.adaptador_legado import AdaptadorLegado
from tests.caracterizacao.adaptador_servicos import AdaptadorServicos
from tests.caracterizacao.analise_aplicabilidade import pares_esperados
from tests.caracterizacao.aplicabilidade import (
    NAO_REPRODUZIDOS_PELOS_SERVICOS,
    REGISTRO,
    REGISTRO_SERVICOS,
    REGISTRO_SERVICOS_POR_PAR,
    RESPONSABILIDADES_AUSENTES_DOS_SERVICOS,
    Motivo,
    Responsabilidade,
    decidir_servicos,
)
from tests.caracterizacao.cenarios import (
    ANA,
    BRUNO,
    CARGO_GESTOR,
    CARGO_TECNICO,
    CARLA,
    CENARIOS_POR_ID,
    PERMISSOES_DO_SISTEMA,
    TORNO,
    Classe,
)
from tests.caracterizacao.deltas import DELTAS_POR_ID, StatusDelta
from tests.caracterizacao.fachada import Fachada, Recusa, RelogioFixo
from tests.caracterizacao.fluxos import (
    os_aberta,
    os_aguardando_aprovacao,
    os_atribuida,
    os_em_execucao,
)
from tests.caracterizacao.test_adaptador_dominio import CONSTRUTORES, OPERACOES, estado, observavel
from tests.guardas_ambiente import RAIZ_BACKEND

DIRETORIO_TESTES = RAIZ_BACKEND / "tests"
ARQUIVO_ADAPTADOR = DIRETORIO_TESTES / "caracterizacao" / "adaptador_servicos.py"


@dataclass
class Par:
    """O mesmo roteiro, nos dois adaptadores, com o mesmo relógio fixo."""

    legado: AdaptadorLegado
    servicos: AdaptadorServicos
    relogio: RelogioFixo


@pytest.fixture
def par(caminho_base: Path, relogio: RelogioFixo) -> Iterator[Par]:
    legado = AdaptadorLegado(caminho_base, relogio)
    try:
        yield Par(legado, AdaptadorServicos(relogio), relogio)
    finally:
        legado.fechar()


# --------------------------------------------------------------------------- o registro


def test_o_registro_dos_servicos_e_o_subconjunto_do_domino_que_ainda_e_inaplicavel() -> None:
    assert set(REGISTRO_SERVICOS) < set(REGISTRO)
    assert {
        i.responsabilidade for i in REGISTRO_SERVICOS
    } == RESPONSABILIDADES_AUSENTES_DOS_SERVICOS
    assert len(REGISTRO_SERVICOS) == len(REGISTRO_SERVICOS_POR_PAR)
    # Cadastro, exclusão e disponibilidade deixaram de ser inaplicáveis: os serviços as executam.
    assert {
        Responsabilidade.PERSISTENCIA,
        Responsabilidade.INTERFACE_DE_LINHA_DE_COMANDO,
    } == RESPONSABILIDADES_AUSENTES_DOS_SERVICOS


def test_o_registro_dos_servicos_e_exatamente_o_que_os_testes_exigem() -> None:
    """Nem linha a mais, nem skip sem justificativa: só persistência e CLI, fora os substituídos."""
    registrados = {(i.cenario, i.responsabilidade) for i in REGISTRO_SERVICOS}
    esperados = {
        (cenario, r)
        for cenario, r in pares_esperados()
        if r in RESPONSABILIDADES_AUSENTES_DOS_SERVICOS
        and cenario not in NAO_REPRODUZIDOS_PELOS_SERVICOS
    }
    assert registrados - esperados == set()
    assert esperados - registrados == set()


def test_decidir_servicos_so_justifica_o_que_esta_no_registro() -> None:
    linha = REGISTRO_SERVICOS[0]
    assert decidir_servicos((linha.cenario,), linha.responsabilidade) is linha
    # cadastro e disponibilidade já não justificam skip nos serviços
    assert decidir_servicos(("CAR-61",), Responsabilidade.CADASTRO_E_IDENTIFICADORES) is None
    assert decidir_servicos(("CAR-41",), Responsabilidade.DISPONIBILIDADE_DERIVADA) is None
    assert decidir_servicos((), Responsabilidade.PERSISTENCIA) is None


def test_os_cenarios_de_cadastro_exclusao_e_disponibilidade_agora_rodam_nos_servicos() -> None:
    """O objetivo da D7: reduzir os cenários inaplicáveis da Operação C."""
    dependiam = {
        cenario
        for cenario, r in pares_esperados()
        if r
        in {
            Responsabilidade.CADASTRO_E_IDENTIFICADORES,
            Responsabilidade.REGRAS_DE_EXCLUSAO,
            Responsabilidade.DISPONIBILIDADE_DERIVADA,
        }
    }
    ainda_pulados = {i.cenario for i in REGISTRO_SERVICOS}
    passam_a_rodar = dependiam - ainda_pulados - set(NAO_REPRODUZIDOS_PELOS_SERVICOS)
    assert len(passam_a_rodar) == 24, sorted(passam_a_rodar)
    assert len(REGISTRO_SERVICOS) < len(REGISTRO)


# --------------------------------------------------------------------- não reproduzidos


def _funcoes_de_teste(arquivo: Path) -> set[str]:
    arvore = ast.parse(arquivo.read_text(encoding="utf-8"))
    return {n.name for n in arvore.body if isinstance(n, ast.FunctionDef)}


def test_cada_cenario_nao_reproduzido_tem_motivo_valido_e_evidencia_existente() -> None:
    assert set(NAO_REPRODUZIDOS_PELOS_SERVICOS) == {"CAR-71", "CAR-73", "CAR-74", "CAR-75"}
    registrados = {i.cenario for i in REGISTRO_SERVICOS}
    for cenario, item in NAO_REPRODUZIDOS_PELOS_SERVICOS.items():
        assert item.cenario == cenario
        assert cenario in CENARIOS_POR_ID
        assert CENARIOS_POR_ID[cenario].classe is not Classe.NAO_VERIFICAVEL
        assert cenario not in registrados, (
            f"{cenario}: não reproduzido e inaplicável ao mesmo tempo"
        )
        assert len(item.justificativa) >= 80, cenario
        if item.motivo is Motivo.DELTA_IMPLEMENTADO:
            delta = DELTAS_POR_ID[item.referencia]
            assert delta.status is StatusDelta.IMPLEMENTADO, f"{item.referencia} não implementado"
            assert cenario in delta.cenarios
        else:
            assert CENARIOS_POR_ID[cenario].classe is Classe.DEFEITO_LEGADO, cenario
            assert item.referencia.startswith("AUD-")
        assert item.evidencias, cenario
        for evidencia in item.evidencias:
            arquivo, _, teste = evidencia.partition("::")
            assert teste in _funcoes_de_teste(DIRETORIO_TESTES / arquivo), evidencia


def test_os_defeitos_corrigidos_sao_so_de_classe_defeito_do_legado() -> None:
    corrigidos = {
        c
        for c, i in NAO_REPRODUZIDOS_PELOS_SERVICOS.items()
        if i.motivo is Motivo.DEFEITO_CORRIGIDO
    }
    assert corrigidos == {"CAR-71", "CAR-73"}
    assert all(CENARIOS_POR_ID[c].classe is Classe.DEFEITO_LEGADO for c in corrigidos)


# ------------------------------------------------------------------------- o adaptador


def _metodos_ausentes() -> dict[str, Responsabilidade]:
    arvore = ast.parse(ARQUIVO_ADAPTADOR.read_text(encoding="utf-8"))
    classe = next(
        n for n in arvore.body if isinstance(n, ast.ClassDef) and n.name == "AdaptadorServicos"
    )
    ausentes: dict[str, Responsabilidade] = {}
    for metodo in classe.body:
        if not isinstance(metodo, ast.FunctionDef):
            continue
        for chamada in ast.walk(metodo):
            if (
                isinstance(chamada, ast.Call)
                and isinstance(chamada.func, ast.Attribute)
                and chamada.func.attr == "_ausente"
            ):
                argumento = chamada.args[0]
                assert isinstance(argumento, ast.Attribute)
                ausentes[metodo.name] = Responsabilidade[argumento.attr]
    return ausentes


def test_o_adaptador_dos_servicos_so_ausenta_a_persistencia() -> None:
    assert _metodos_ausentes() == {"salvar_e_recarregar": Responsabilidade.PERSISTENCIA}


def test_o_adaptador_cobre_toda_a_fachada() -> None:
    faltando = [
        nome
        for nome in vars(Fachada)
        if not nome.startswith("_") and not hasattr(AdaptadorServicos, nome)
    ]
    assert faltando == []


def test_sem_gancho_o_adaptador_falha_em_vez_de_fingir_a_persistencia() -> None:
    with pytest.raises(NotImplementedError, match="persistencia"):
        AdaptadorServicos().salvar_e_recarregar()


PERMITIDOS = {
    "tests.caracterizacao.aplicabilidade",
    "tests.caracterizacao.fachada",
    "tests.caracterizacao.traducao",
}


def _importados() -> set[str]:
    modulos: set[str] = set()
    for no in ast.walk(ast.parse(ARQUIVO_ADAPTADOR.read_text(encoding="utf-8"))):
        if isinstance(no, ast.Import):
            modulos |= {alias.name for alias in no.names}
        elif isinstance(no, ast.ImportFrom) and no.module:
            modulos.add(no.module)
    return modulos


def test_o_adaptador_so_conhece_aplicacao_dominio_e_a_composicao() -> None:
    for modulo in _importados():
        permitido = (
            modulo.split(".")[0] in sys.stdlib_module_names
            or modulo.startswith(("manutencao.application", "manutencao.domain"))
            or modulo == "manutencao.composicao.fabrica"
            or modulo in PERMITIDOS
        )
        assert permitido, f"importação não permitida no adaptador dos serviços: {modulo}"


def test_o_adaptador_nao_importa_o_legado_a_infraestrutura_nem_a_api() -> None:
    proibidos = {"models", "persistencia", "ui", "app", "sqlalchemy", "fastapi", "pydantic"}
    modulos = _importados()
    assert {m.split(".")[0] for m in modulos} & proibidos == set()
    assert not any(m.startswith(("manutencao.infrastructure", "manutencao.api")) for m in modulos)


# ------------------------------------------------------------------------ base inicial


def test_a_base_inicial_dos_servicos_e_a_do_legado(par: Par) -> None:
    assert estado(par.legado) == estado(par.servicos)
    assert len(par.servicos.usuarios()) == 3
    assert len(par.servicos.equipamentos()) == 3
    assert par.servicos.todas_as_os() == ()


# ------------------------------------------------------- roteiros em todos os estados


@pytest.mark.parametrize("construtor", CONSTRUTORES)
def test_toda_operacao_em_cada_estado_tem_o_mesmo_resultado_e_o_mesmo_estado(
    construtor: str, caminho_base: Path, relogio: RelogioFixo
) -> None:
    comparadas = 0
    for nome, operacao in OPERACOES.items():
        legado = AdaptadorLegado(caminho_base.with_name(f"{comparadas}.json"), relogio)
        servicos = AdaptadorServicos(relogio)
        try:
            numero_legado = CONSTRUTORES[construtor](legado)
            numero_servicos = CONSTRUTORES[construtor](servicos)
            assert numero_legado == numero_servicos
            assert estado(legado) == estado(servicos), f"{construtor}: estados diferem antes"
            relogio.avancar(minutes=7)  # a operação acontece em outro instante
            do_legado = operacao(legado, numero_legado)
            do_servicos = operacao(servicos, numero_servicos)
            assert observavel(do_legado) == observavel(do_servicos), f"{construtor} / {nome}"
            assert estado(legado) == estado(servicos), f"{construtor} / {nome}: estados diferem"
            # a rotina de disponibilidade também produz o mesmo resultado nos dois
            legado.atualizar_disponibilidades()
            servicos.atualizar_disponibilidades()
            assert estado(legado) == estado(servicos), f"{construtor} / {nome}: após a rotina"
            comparadas += 1
        finally:
            legado.fechar()
    assert comparadas == len(OPERACOES)


# ------------------------------------------------------------- cadastros e exclusões


def _roteiro_de_cadastros(f: Fachada) -> list[tuple[object, ...]]:
    """Cadastros, edições, inativações e exclusões; devolve o que cada passo observou."""
    vistos: list[tuple[object, ...]] = []
    diego = f.cadastrar_usuario("Diego", CARGO_TECNICO, "d@e.com", "Seg")
    eva = f.cadastrar_usuario("Eva", CARGO_GESTOR)
    prensa = f.cadastrar_equipamento("Prensa", "P1")
    f.editar_usuario(diego, nome="Diego S.", escala="Ter")
    f.editar_usuario(eva, cargo=CARGO_TECNICO)
    f.editar_equipamento(prensa, nome="Prensa 2", modelo="P2")
    f.inativar_equipamento(prensa)
    f.reativar_equipamento(prensa)
    numero = os_atribuida(f, tecnico=BRUNO)
    f.atualizar_disponibilidades()
    iris = f.cadastrar_usuario("Iris", CARGO_GESTOR)  # outra gestora, com permissão para excluir
    vistos.append(observavel(f.remover_usuario(ANA, iris)))  # Ana tem histórico
    vistos.append(observavel(f.remover_usuario(BRUNO, ANA)))  # Bruno tem histórico
    vistos.append(observavel(f.remover_usuario(ANA, ANA)))  # autoexclusão
    vistos.append(observavel(f.remover_equipamento(TORNO)))  # com OS
    vistos.append(observavel(f.remover_equipamento(prensa)))  # sem OS
    vistos.append(observavel(f.remover_usuario(diego, ANA)))  # sem histórico
    vistos.append((numero, f.tecnicos(), f.ordens_do_equipamento(TORNO)))
    return vistos


def test_cadastros_edicoes_e_exclusoes_dao_o_mesmo_resultado_e_o_mesmo_estado(par: Par) -> None:
    do_legado = _roteiro_de_cadastros(par.legado)
    do_servicos = _roteiro_de_cadastros(par.servicos)
    assert do_legado == do_servicos
    assert estado(par.legado) == estado(par.servicos)
    assert par.servicos.usuario(4) is None  # Diego foi excluído
    assert par.servicos.equipamento(4) is None  # a prensa foi excluída


# ------------------------------------------------------------------ DLT-10


def test_dlt10_unica_diferenca_de_ids_o_legado_reaproveita_e_os_servicos_nao(par: Par) -> None:
    for f in (par.legado, par.servicos):
        diego = f.cadastrar_usuario("Diego", CARGO_TECNICO)
        assert diego == 4
        assert f.remover_usuario(diego, ANA).aceito
        prensa = f.cadastrar_equipamento("Prensa", "P1")
        assert f.remover_equipamento(prensa).aceito
    assert par.legado.cadastrar_usuario("Outro", CARGO_TECNICO) == 4  # reaproveitado (AUD-05)
    assert par.servicos.cadastrar_usuario("Outro", CARGO_TECNICO) == 5  # monotônico
    assert par.legado.cadastrar_equipamento("Nova", "N") == 4
    assert par.servicos.cadastrar_equipamento("Nova", "N") == 5


def test_dlt10_excluir_um_id_do_meio_nao_o_reaproveita_nem_no_legado(par: Par) -> None:
    for f in (par.legado, par.servicos):
        assert f.remover_equipamento(2).aceito
        assert f.cadastrar_equipamento("Nova", "N1") == 4
        assert [e.id for e in f.equipamentos()] == [1, 3, 4]


def test_a_numeracao_das_os_e_sequencial_e_recusa_nao_consome_numero_nos_dois(par: Par) -> None:
    for f in (par.legado, par.servicos):
        assert os_aberta(f) == 1
        f.inativar_equipamento(2)
        recusada = f.abrir_os(CARLA, 2, "x", "Baixa")
        assert (recusada.aceito, recusada.recusa) == (False, Recusa.EQUIPAMENTO_INATIVO)
        assert os_aberta(f) == 2


# ------------------------------------------------------------------- disponibilidade


def test_disponibilidade_antes_e_depois_da_rotina_e_igual_ao_legado(par: Par) -> None:
    for f in (par.legado, par.servicos):
        numero = os_em_execucao(f, tecnico=BRUNO)
        assert f.usuario(BRUNO).disponibilidade == "Disponível"  # type: ignore[union-attr]
        f.atualizar_disponibilidades()
        assert f.usuario(BRUNO).disponibilidade == "Em atendimento"  # type: ignore[union-attr]
        f.definir_disponibilidade(BRUNO, "Ausente")
        f.atualizar_disponibilidades()
        assert f.usuario(BRUNO).disponibilidade == "Ausente"  # type: ignore[union-attr]
        assert f.usuario(BRUNO).carga == 1  # type: ignore[union-attr]
        assert f.cancelar(numero, ANA, "x").aceito
    assert estado(par.legado) == estado(par.servicos)


# --------------------------------------------------------------------------- DLT-07


def test_os_instantes_dos_servicos_sao_utc_com_fuso_e_o_texto_bate_com_o_legado(par: Par) -> None:
    par.relogio.definir(datetime(2026, 3, 10, 23, 55))
    inicio = par.relogio.agora()
    numero = os_aguardando_aprovacao(par.legado)
    par.relogio.definir(inicio)
    assert os_aguardando_aprovacao(par.servicos) == numero
    assert estado(par.legado) == estado(par.servicos)
    entidade = par.servicos._c.ordens.obter(numero)  # a entidade por trás do snapshot
    assert entidade is not None
    instantes = [entidade.data_abertura, *(s.data for s in entidade.servicos)]
    assert all(i.tzinfo is UTC and i.utcoffset() == timedelta(0) for i in instantes)
    assert entidade.data_abertura == datetime(2026, 3, 10, 23, 55, tzinfo=UTC)


# --------------------------------------------------------------------------- DLT-11


@pytest.mark.parametrize("permissao", PERMISSOES_DO_SISTEMA)
@pytest.mark.parametrize("usuario", [ANA, BRUNO, CARLA])
def test_permissoes_validas_se_comportam_como_no_legado(
    par: Par, usuario: int, permissao: str
) -> None:
    assert par.legado.usuario_pode(usuario, permissao) == par.servicos.usuario_pode(
        usuario, permissao
    )
    do_legado = par.legado.exigir_permissao(usuario, permissao)
    do_servicos = par.servicos.exigir_permissao(usuario, permissao)
    assert observavel(do_legado) == observavel(do_servicos)


# ---------------------------------------------- defeitos corrigidos: o comportamento novo


def test_exclusao_por_quem_nao_gere_usuarios_e_aceita_no_legado_e_recusada_nos_servicos(
    par: Par,
) -> None:
    """CAR-73 / AUD-02: o técnico exclui um usuário no legado (repositório sem permissão)."""
    for f in (par.legado, par.servicos):
        diego = f.cadastrar_usuario("Diego", CARGO_TECNICO)
        assert not f.usuario_pode(BRUNO, "gerir_usuarios")
        resultado = f.remover_usuario(diego, BRUNO)
        if f is par.legado:
            assert resultado.aceito
        else:
            assert (resultado.aceito, resultado.recusa) == (False, Recusa.SEM_PERMISSAO)
            assert f.usuario(diego) is not None  # nada foi excluído


def test_remover_o_proprio_acesso_de_gestao_e_possivel_no_dominio_e_recusado_nos_servicos(
    par: Par,
) -> None:
    """CAR-71 / AUD-09: a proteção que só a tela aplicava agora é do caso de uso."""
    par.legado.editar_usuario(ANA, cargo=CARGO_TECNICO)  # o legado aceita
    assert not par.legado.usuario_pode(ANA, "gerir_usuarios")
    with pytest.raises(RegraDeAplicacaoError, match="próprio acesso de gestão"):
        par.servicos.editar_usuario(ANA, cargo=CARGO_TECNICO)
    assert par.servicos.usuario_pode(ANA, "gerir_usuarios")  # nada mudou
