"""C5: instantes do domínio em UTC (D-11, DLT-07).

O domínio recebe o instante de quem o chama, exige fuso e guarda sempre em UTC. A conversão para
``America/Sao_Paulo`` é apresentação (Fase 04) e não existe aqui.
"""

import ast
from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta, timezone, tzinfo
from pathlib import Path

import pytest

from manutencao.domain.enums import Criticidade, StatusOS, TipoServico
from manutencao.domain.erros import (
    CodigoErro,
    DominioError,
    ViolacaoDeRegraError,
)
from manutencao.domain.ordem_servico import OrdemServico
from manutencao.domain.peca_material import PecaMaterial
from manutencao.domain.servico import Servico
from manutencao.domain.tempo import garantir_utc
from tests.dominio.fabrica import Mundo, instantaneo, sem_acesso

BRASILIA = timezone(timedelta(hours=-3))  # fuso fixo: sem tzdata, sem depender do sistema
INDIA = timezone(timedelta(hours=5, minutes=30))
UTC_MAIS_3 = timezone(timedelta(hours=3))

NO_UTC = datetime(2026, 3, 10, 9, 0, 30, 123456, tzinfo=UTC)
NO_BRASIL = datetime(2026, 3, 10, 6, 0, 30, 123456, tzinfo=BRASILIA)  # o mesmo instante
NA_INDIA = datetime(2026, 3, 10, 14, 30, 30, 123456, tzinfo=INDIA)  # o mesmo instante
INGENUO = datetime(2026, 3, 10, 9, 0)


class _FusoSemDeslocamento(tzinfo):
    """Um ``tzinfo`` que não sabe o deslocamento: pela definição do Python, o datetime é ingênuo."""

    def utcoffset(self, dt: datetime | None) -> timedelta | None:
        return None

    def dst(self, dt: datetime | None) -> timedelta | None:
        return None

    def tzname(self, dt: datetime | None) -> str | None:
        return None


def em_utc(instante: datetime) -> bool:
    return instante.tzinfo is UTC and instante.utcoffset() == timedelta(0)


# =========================================================================== garantir_utc


def test_instante_em_utc_volta_igual() -> None:
    resultado = garantir_utc(NO_UTC)
    assert resultado == NO_UTC
    assert em_utc(resultado)
    assert (resultado.hour, resultado.minute, resultado.microsecond) == (9, 0, 123456)


@pytest.mark.parametrize("instante", [NO_BRASIL, NA_INDIA], ids=["brasilia", "india"])
def test_outros_fusos_sao_normalizados_para_utc_preservando_o_momento(instante: datetime) -> None:
    resultado = garantir_utc(instante)
    assert em_utc(resultado)
    assert (resultado.year, resultado.month, resultado.day) == (2026, 3, 10)
    assert (resultado.hour, resultado.minute, resultado.second) == (9, 0, 30)
    assert resultado.microsecond == 123456
    assert resultado == instante  # mesmo momento


def test_a_normalizacao_atravessa_a_virada_do_dia() -> None:
    tarde = datetime(2026, 12, 31, 22, 0, tzinfo=BRASILIA)
    resultado = garantir_utc(tarde)
    assert (resultado.year, resultado.month, resultado.day, resultado.hour) == (2027, 1, 1, 1)
    cedo = datetime(2026, 1, 1, 1, 0, tzinfo=UTC_MAIS_3)
    assert garantir_utc(cedo).day == 31  # 31/12 do ano anterior em UTC
    assert garantir_utc(cedo).year == 2025


def test_garantir_utc_e_idempotente() -> None:
    uma_vez = garantir_utc(NO_BRASIL)
    assert garantir_utc(uma_vez) == uma_vez
    assert em_utc(garantir_utc(uma_vez))


def test_datetime_ingenuo_e_rejeitado() -> None:
    with pytest.raises(ViolacaoDeRegraError) as capturado:
        garantir_utc(INGENUO)
    assert capturado.value.codigo is CodigoErro.INSTANTE_INVALIDO
    assert "fuso" in capturado.value.mensagem


def test_tzinfo_sem_deslocamento_conta_como_ingenuo() -> None:
    estranho = datetime(2026, 3, 10, 9, 0, tzinfo=_FusoSemDeslocamento())
    with pytest.raises(ViolacaoDeRegraError) as capturado:
        garantir_utc(estranho)
    assert capturado.value.codigo is CodigoErro.INSTANTE_INVALIDO


@pytest.mark.parametrize(
    "valor",
    [None, "2026-03-10T09:00:00+00:00", 1_773_133_200, 1.5, date(2026, 3, 10), b"2026"],
    ids=["none", "texto", "int", "float", "date", "bytes"],
)
def test_so_datetime_e_aceito(valor: object) -> None:
    with pytest.raises(ViolacaoDeRegraError) as capturado:
        garantir_utc(valor)
    assert capturado.value.codigo is CodigoErro.INSTANTE_INVALIDO
    assert "datetime" in capturado.value.mensagem


# =========================================================================== Servico


def test_servico_guarda_a_data_em_utc() -> None:
    servico = Servico(1, TipoServico.ABERTURA, "x", None, NO_BRASIL)
    assert em_utc(servico.data)
    assert servico.data.hour == 9
    assert servico.data == NO_BRASIL


def test_servico_com_data_ingenua_e_recusado() -> None:
    with pytest.raises(ViolacaoDeRegraError) as capturado:
        Servico(1, TipoServico.ABERTURA, "x", None, INGENUO)
    assert capturado.value.codigo is CodigoErro.INSTANTE_INVALIDO


# =========================================================================== OrdemServico
# Cada caso: (como preparar a OS, como chamar a operação com um instante).

Preparar = Callable[[Mundo], OrdemServico]
Chamar = Callable[[Mundo, OrdemServico, datetime], object]

CASOS: dict[str, tuple[Preparar, Chamar]] = {
    "apontamento": (
        lambda m: m.aberta(),
        lambda m, o, q: o.adicionar_apontamento(m.ana, "nota", quando=q),
    ),
    "atribuir": (
        lambda m: m.aberta(),
        lambda m, o, q: o.atribuir(m.bruno, m.ana, quando=q),
    ),
    "reatribuir": (
        lambda m: m.atribuida(),
        lambda m, o, q: o.atribuir(m.carla, m.ana, quando=q),
    ),
    "diagnostico": (
        lambda m: m.atribuida(),
        lambda m, o, q: o.registrar_diagnostico(m.bruno, "p", "c", quando=q),
    ),
    "reparo (inicia a execucao)": (
        lambda m: m.atribuida(),
        lambda m, o, q: o.apontar_reparo(m.bruno, 1, "i", [PecaMaterial("p", 1)], quando=q),
    ),
    "reparo (em execucao)": (
        lambda m: m.em_execucao(),
        lambda m, o, q: o.apontar_reparo(m.bruno, 1, "i", [], quando=q),
    ),
    "alterar status": (
        lambda m: m.em_execucao(),
        lambda m, o, q: o.alterar_status(m.bruno, StatusOS.AGUARDANDO_PECA, quando=q),
    ),
    "concluir (aprovado)": (
        lambda m: m.reparo_finalizado(),
        lambda m, o, q: o.concluir_tecnicamente(m.bruno, "ok", True, quando=q),
    ),
    "concluir (reprovado)": (
        lambda m: m.reparo_finalizado(),
        lambda m, o, q: o.concluir_tecnicamente(m.bruno, "falhou", False, quando=q),
    ),
    "aprovar": (
        lambda m: m.aguardando_aprovacao(),
        lambda m, o, q: o.aprovar(m.ana, quando=q),
    ),
    "reprovar": (
        lambda m: m.aguardando_aprovacao(),
        lambda m, o, q: o.reprovar(m.ana, "r", quando=q),
    ),
    "cancelar": (
        lambda m: m.em_execucao(),
        lambda m, o, q: o.cancelar(m.ana, "c", quando=q),
    ),
}


@pytest.mark.parametrize(
    "instante", [NO_UTC, NO_BRASIL, NA_INDIA], ids=["utc", "brasilia", "india"]
)
@pytest.mark.parametrize("nome", CASOS)
def test_toda_operacao_guarda_em_utc_os_registros_que_cria(nome: str, instante: datetime) -> None:
    preparar, chamar = CASOS[nome]
    m = Mundo()
    os_ = preparar(m)
    antes = len(os_.servicos)
    chamar(m, os_, instante)
    novos = os_.servicos[antes:]
    assert novos, "a operação deve ter registrado algo no histórico"
    for registro in novos:
        assert em_utc(registro.data)
        assert registro.data == NO_UTC
        assert (registro.data.hour, registro.data.microsecond) == (9, 123456)


@pytest.mark.parametrize("nome", CASOS)
def test_instante_ingenuo_e_recusado_sem_alterar_nada(nome: str) -> None:
    preparar, chamar = CASOS[nome]
    m = Mundo()
    os_ = preparar(m)
    antes = instantaneo(os_)
    with pytest.raises(ViolacaoDeRegraError) as capturado:
        chamar(m, os_, INGENUO)
    assert capturado.value.codigo is CodigoErro.INSTANTE_INVALIDO
    assert instantaneo(os_) == antes  # nem status, nem histórico, nem campos


@pytest.mark.parametrize("nome", CASOS)
def test_instante_que_nao_e_datetime_tambem_e_recusado_sem_alterar_nada(nome: str) -> None:
    preparar, chamar = CASOS[nome]
    m = Mundo()
    os_ = preparar(m)
    antes = instantaneo(os_)
    with pytest.raises(ViolacaoDeRegraError) as capturado:
        chamar(m, os_, "2026-03-10T09:00:00+00:00")  # type: ignore[arg-type]
    assert capturado.value.codigo is CodigoErro.INSTANTE_INVALIDO
    assert instantaneo(os_) == antes


def test_data_de_conclusao_e_normalizada_na_aprovacao_e_no_cancelamento() -> None:
    m = Mundo()
    aprovada = m.aguardando_aprovacao()
    aprovada.aprovar(m.ana, quando=NO_BRASIL)
    cancelada = m.em_execucao()
    cancelada.cancelar(m.ana, "c", quando=NA_INDIA)
    for os_ in (aprovada, cancelada):
        assert os_.data_conclusao is not None
        assert em_utc(os_.data_conclusao)
        assert os_.data_conclusao == NO_UTC


def test_abertura_normaliza_a_data_de_abertura_e_recusa_instante_ingenuo() -> None:
    m = Mundo()
    os_ = OrdemServico.abrir(1, m.torno, "f", Criticidade.BAIXA, m.carla, quando=NO_BRASIL)
    assert em_utc(os_.data_abertura)
    assert os_.data_abertura == NO_UTC
    assert em_utc(os_.servicos[0].data)
    with pytest.raises(ViolacaoDeRegraError) as capturado:
        OrdemServico.abrir(2, m.torno, "f", Criticidade.BAIXA, m.carla, quando=INGENUO)
    assert capturado.value.codigo is CodigoErro.INSTANTE_INVALIDO


def test_o_construtor_tambem_exige_instante_com_fuso() -> None:
    m = Mundo()
    with pytest.raises(ViolacaoDeRegraError):
        OrdemServico(1, m.torno, "f", Criticidade.BAIXA, m.carla, INGENUO)
    os_ = OrdemServico(1, m.torno, "f", Criticidade.BAIXA, m.carla, NO_BRASIL)
    assert em_utc(os_.data_abertura)


# --------------------------------------------------------------- precedência das verificações


def _com_os(preparar: Preparar, chamar: Chamar) -> Callable[[Mundo], object]:
    """Prepara a OS e chama a operação com um instante ingênuo."""
    return lambda m: chamar(m, preparar(m), INGENUO)


def _abrir_sem_permissao(m: Mundo) -> object:
    return OrdemServico.abrir(1, m.torno, "f", Criticidade.BAIXA, sem_acesso(), quando=INGENUO)


def _abrir_equipamento_inativo(m: Mundo) -> object:
    m.torno.inativar()
    return OrdemServico.abrir(1, m.torno, "f", Criticidade.BAIXA, m.carla, quando=INGENUO)


# Cada caso viola uma regra funcional E traz instante ingênuo: a regra funcional é a recusa
# observada, exatamente como no legado (que não tinha a verificação do instante).
PRECEDENCIA: dict[str, tuple[Callable[[Mundo], object], CodigoErro]] = {
    "abrir sem permissão": (_abrir_sem_permissao, CodigoErro.SEM_PERMISSAO),
    "abrir equipamento inativo": (_abrir_equipamento_inativo, CodigoErro.EQUIPAMENTO_INATIVO),
    "apontamento sem permissão": (
        _com_os(
            lambda m: m.aberta(),
            lambda m, o, q: o.adicionar_apontamento(sem_acesso(), "n", quando=q),
        ),
        CodigoErro.SEM_PERMISSAO,
    ),
    "atribuir a quem não é técnico": (
        _com_os(lambda m: m.aberta(), lambda m, o, q: o.atribuir(m.ana, m.ana, quando=q)),
        CodigoErro.NAO_E_TECNICO,
    ),
    "atribuir em OS encerrada": (
        _com_os(lambda m: m.concluida(), lambda m, o, q: o.atribuir(m.carla, m.ana, quando=q)),
        CodigoErro.ESTADO_INVALIDO,
    ),
    "diagnosticar sem ser responsável": (
        _com_os(
            lambda m: m.atribuida(),
            lambda m, o, q: o.registrar_diagnostico(m.carla, "p", "c", quando=q),
        ),
        CodigoErro.NAO_RESPONSAVEL,
    ),
    "diagnosticar em estado inválido": (
        _com_os(
            lambda m: m.reparo_finalizado(),
            lambda m, o, q: o.registrar_diagnostico(m.bruno, "p", "c", quando=q),
        ),
        CodigoErro.ESTADO_INVALIDO,
    ),
    "reparo com horas negativas": (
        _com_os(
            lambda m: m.atribuida(),
            lambda m, o, q: o.apontar_reparo(m.bruno, -1, "i", [], quando=q),
        ),
        CodigoErro.HORAS_NEGATIVAS,
    ),
    "status não permitido": (
        _com_os(
            lambda m: m.em_execucao(),
            lambda m, o, q: o.alterar_status(m.bruno, StatusOS.CONCLUIDA, quando=q),
        ),
        CodigoErro.STATUS_NAO_PERMITIDO,
    ),
    "finalizar sem intervenção": (
        _com_os(
            lambda m: m.atribuida(),
            lambda m, o, q: o.alterar_status(m.bruno, StatusOS.REPARO_FINALIZADO, quando=q),
        ),
        CodigoErro.SEM_INTERVENCAO,
    ),
    "concluir sem diagnóstico": (
        _com_os(
            lambda m: m.reparo_finalizado(com_diagnostico=False),
            lambda m, o, q: o.concluir_tecnicamente(m.bruno, "t", True, quando=q),
        ),
        CodigoErro.SEM_DIAGNOSTICO,
    ),
    "aprovar fora de Aguardando Aprovação": (
        _com_os(lambda m: m.aberta(), lambda m, o, q: o.aprovar(m.ana, quando=q)),
        CodigoErro.ESTADO_INVALIDO,
    ),
    "reprovar sem permissão": (
        _com_os(
            lambda m: m.aguardando_aprovacao(),
            lambda m, o, q: o.reprovar(m.bruno, "r", quando=q),
        ),
        CodigoErro.SEM_PERMISSAO,
    ),
    "cancelar OS encerrada": (
        _com_os(lambda m: m.concluida(), lambda m, o, q: o.cancelar(m.ana, "c", quando=q)),
        CodigoErro.OS_ENCERRADA,
    ),
}


@pytest.mark.parametrize("nome", PRECEDENCIA)
def test_a_recusa_funcional_vence_o_instante_ingenuo(nome: str) -> None:
    """D-11 não muda a precedência do legado: o instante é a última verificação."""
    chamada, codigo = PRECEDENCIA[nome]
    with pytest.raises(DominioError) as capturado:
        chamada(Mundo())
    assert capturado.value.codigo is codigo
    assert capturado.value.codigo is not CodigoErro.INSTANTE_INVALIDO


# --------------------------------------------------------------------------------- histórico


def test_historico_do_ciclo_completo_com_fusos_diferentes_fica_em_utc_e_ordenado() -> None:
    m = Mundo()
    fusos = [BRASILIA, UTC, INDIA, UTC_MAIS_3]
    base = datetime(2026, 3, 10, 9, 0, tzinfo=UTC)
    passo = {"n": 0}

    def quando() -> datetime:
        """Cada operação num fuso diferente, sempre um minuto depois da anterior."""
        passo["n"] += 1
        instante = base + timedelta(minutes=passo["n"])
        return instante.astimezone(fusos[passo["n"] % len(fusos)])

    os_ = OrdemServico.abrir(1, m.torno, "Torno parado", Criticidade.ALTA, m.carla, quando=quando())
    os_.atribuir(m.bruno, m.ana, quando=quando())
    os_.registrar_diagnostico(m.bruno, "p", "c", quando=quando())
    os_.apontar_reparo(m.bruno, 1, "i", [], quando=quando())
    os_.alterar_status(m.bruno, StatusOS.REPARO_FINALIZADO, quando=quando())
    os_.concluir_tecnicamente(m.bruno, "ok", True, quando=quando())
    os_.aprovar(m.ana, quando=quando())
    datas = [s.data for s in os_.servicos]
    assert len(datas) == 11
    assert all(em_utc(d) for d in datas)
    assert datas == sorted(datas)
    assert datas[0] == os_.data_abertura
    assert os_.data_conclusao == datas[-1]
    assert datas[0].minute == 1  # 09:01 UTC, mesmo tendo entrado em outro fuso


# ------------------------------------------------------------- o domínio não lê o relógio

RAIZ_DOMINIO = Path(__file__).resolve().parents[2] / "src" / "manutencao" / "domain"
LEITURAS_DE_RELOGIO = {
    "now",
    "utcnow",
    "today",
    "time",
    "time_ns",
    "monotonic",
    "perf_counter",
    "localtime",
    "gmtime",
    "ctime",
}
MODULOS_PROIBIDOS = {"time", "zoneinfo", "pytz", "dateutil", "tzdata", "freezegun"}


def achados_de_relogio(codigo: str) -> list[str]:
    """Chamadas que leem o relógio e imports de módulos de relógio/fuso, por análise estática."""
    achados: list[str] = []
    for no in ast.walk(ast.parse(codigo)):
        if (
            isinstance(no, ast.Call)
            and isinstance(no.func, ast.Attribute)
            and no.func.attr in LEITURAS_DE_RELOGIO
        ):
            achados.append(f"chamada .{no.func.attr}() na linha {no.lineno}")
        if isinstance(no, ast.Import):
            modulos = [alias.name for alias in no.names]
        elif isinstance(no, ast.ImportFrom) and no.module:
            modulos = [no.module]
        else:
            continue
        achados.extend(
            f"import {m} na linha {no.lineno}"
            for m in modulos
            if m.split(".")[0] in MODULOS_PROIBIDOS
        )
    return achados


def test_o_verificador_estatico_detecta_leituras_do_relogio() -> None:
    ruim = (
        "from datetime import datetime, date\n"
        "import time\n"
        "a = datetime.now()\n"
        "b = datetime.utcnow()\n"
        "c = date.today()\n"
        "d = datetime.today()\n"
        "e = time.time()\n"
        "from zoneinfo import ZoneInfo\n"
    )
    assert len(achados_de_relogio(ruim)) == 7
    assert achados_de_relogio("from datetime import datetime\nx = datetime(2026, 1, 1)\n") == []


@pytest.mark.parametrize("arquivo", sorted(RAIZ_DOMINIO.glob("*.py")), ids=lambda p: p.name)
def test_nenhum_modulo_do_dominio_consulta_o_relogio_nem_converte_fusos(arquivo: Path) -> None:
    assert achados_de_relogio(arquivo.read_text(encoding="utf-8")) == []


def test_o_dominio_foi_inspecionado() -> None:
    nomes = {p.name for p in RAIZ_DOMINIO.glob("*.py")}
    assert {"ordem_servico.py", "servico.py", "tempo.py", "usuario.py"} <= nomes
