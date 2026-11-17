"""Comparação direta do domínio puro com o legado (Operação C6).

Os testes de cenário rodam cada comportamento contra um adaptador de cada vez. Estes aqui rodam o
**mesmo** roteiro nos dois, lado a lado, e exigem resultados e estados idênticos (inclusive o texto
das mensagens e a ordem do histórico), com duas exceções que são deltas aprovados e implementados:

* DLT-07: o domínio guarda instantes UTC com fuso; a comparação normaliza as datas para o texto do
  legado explicitamente (ver ``adaptador_dominio._texto_legado``);
* DLT-11: permissões tipadas; um nome inválido é erro no domínio e negação silenciosa no legado.

São testes de infraestrutura da caracterização (sem marcador ``cenario``).
"""

from collections.abc import Callable, Iterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from manutencao.domain.erros import CodigoErro, ViolacaoDeRegraError
from tests.caracterizacao.adaptador_dominio import AdaptadorDominio
from tests.caracterizacao.adaptador_legado import AdaptadorLegado
from tests.caracterizacao.cenarios import (
    ANA,
    BRUNO,
    CARGO_TECNICO,
    CARLA,
    PERMISSOES_DO_SISTEMA,
    STATUS_ABERTA,
    STATUS_AGUARDANDO_APROVACAO,
    STATUS_AGUARDANDO_PECA,
    STATUS_ATRIBUIDA,
    STATUS_CANCELADA,
    STATUS_CONCLUIDA,
    STATUS_EM_EXECUCAO,
    STATUS_REPARO_FINALIZADO,
)
from tests.caracterizacao.fachada import Fachada, Peca, Recusa, RelogioFixo, Resultado
from tests.caracterizacao.fluxos import (
    os_aberta,
    os_aguardando_aprovacao,
    os_aguardando_peca,
    os_atribuida,
    os_cancelada,
    os_concluida,
    os_em_execucao,
    os_reparo_finalizado,
)


@dataclass
class Par:
    """O mesmo roteiro, nos dois adaptadores, com o mesmo relógio fixo."""

    legado: AdaptadorLegado
    dominio: AdaptadorDominio
    relogio: RelogioFixo

    def ambos(self, roteiro: Callable[[Fachada], object]) -> tuple[object, object]:
        return roteiro(self.legado), roteiro(self.dominio)


@pytest.fixture
def par(caminho_base: Path, relogio: RelogioFixo) -> Iterator[Par]:
    legado = AdaptadorLegado(caminho_base, relogio)
    try:
        yield Par(legado, AdaptadorDominio(relogio), relogio)
    finally:
        legado.fechar()


def estado(f: Fachada) -> tuple[object, ...]:
    """Tudo o que a fachada observa (snapshots, com as datas já em texto normalizado)."""
    return (f.todas_as_os(), f.usuarios(), f.equipamentos(), f.cargos(), f.tecnicos())


def observavel(r: Resultado) -> tuple[object, ...]:
    return (r.aceito, r.recusa, r.mensagem, r.valor)


# ------------------------------------------------------------------------------- base inicial


def test_a_base_inicial_do_dominio_e_a_do_legado(par: Par) -> None:
    assert estado(par.legado) == estado(par.dominio)
    assert len(par.dominio.usuarios()) == 3
    assert len(par.dominio.equipamentos()) == 3
    assert par.dominio.todas_as_os() == ()


# ----------------------------------------------------------------- roteiros em todos os estados

CONSTRUTORES: dict[str, Callable[[Fachada], int]] = {
    "aberta": os_aberta,
    "atribuida": os_atribuida,
    "em_execucao": os_em_execucao,
    "aguardando_peca": os_aguardando_peca,
    "reparo_finalizado": os_reparo_finalizado,
    "reparo_finalizado_sem_diagnostico": lambda f: os_reparo_finalizado(f, com_diagnostico=False),
    "aguardando_aprovacao": os_aguardando_aprovacao,
    "concluida": os_concluida,
    "cancelada": os_cancelada,
    "cancelada_atribuida": lambda f: os_cancelada(f, atribuida=True),
}

STATUS = (
    STATUS_ABERTA,
    STATUS_ATRIBUIDA,
    STATUS_EM_EXECUCAO,
    STATUS_AGUARDANDO_PECA,
    STATUS_REPARO_FINALIZADO,
    STATUS_AGUARDANDO_APROVACAO,
    STATUS_CONCLUIDA,
    STATUS_CANCELADA,
)
BOA = (Peca("Correia", 1),)
INVALIDA = (Peca("Correia", 0),)

Operacao = Callable[[Fachada, int], Resultado]
OPERACOES: dict[str, Operacao] = {
    **{
        f"atribuir {t} por {g}": lambda f, n, t=t, g=g: f.atribuir(n, t, g)  # type: ignore[misc]
        for t in (BRUNO, CARLA, ANA)
        for g in (ANA, BRUNO)
    },
    **{
        f"diagnosticar por {u}": lambda f, n, u=u: f.registrar_diagnostico(n, u, "p", "c")  # type: ignore[misc]
        for u in (BRUNO, CARLA, ANA)
    },
    "reparo ok": lambda f, n: f.apontar_reparo(n, BRUNO, 2.0, "Ajuste", BOA),
    "reparo sem peças": lambda f, n: f.apontar_reparo(n, BRUNO, 1.0, "Ajuste"),
    "reparo horas negativas": lambda f, n: f.apontar_reparo(n, BRUNO, -1, "Ajuste", BOA),
    "reparo zero hora": lambda f, n: f.apontar_reparo(n, BRUNO, 0, "Ajuste", BOA),
    "reparo peça inválida": lambda f, n: f.apontar_reparo(n, BRUNO, 1, "Ajuste", INVALIDA),
    "reparo de outro técnico": lambda f, n: f.apontar_reparo(n, CARLA, 1, "Ajuste", BOA),
    "reparo do gestor": lambda f, n: f.apontar_reparo(n, ANA, 1, "Ajuste", BOA),
    **{
        f"status {s}": lambda f, n, s=s: f.alterar_status(n, BRUNO, s)  # type: ignore[misc]
        for s in STATUS
    },
    "status pelo gestor": lambda f, n: f.alterar_status(n, ANA, STATUS_EM_EXECUCAO),
    "concluir aprovado": lambda f, n: f.concluir_tecnicamente(n, BRUNO, "ok", True),
    "concluir reprovado": lambda f, n: f.concluir_tecnicamente(n, BRUNO, "falhou", False),
    "concluir por outro técnico": lambda f, n: f.concluir_tecnicamente(n, CARLA, "ok", True),
    "concluir pelo gestor": lambda f, n: f.concluir_tecnicamente(n, ANA, "ok", True),
    "aprovar": lambda f, n: f.aprovar(n, ANA),
    "aprovar sem permissão": lambda f, n: f.aprovar(n, BRUNO),
    "reprovar": lambda f, n: f.reprovar(n, ANA, "Ainda vibra"),
    "reprovar sem permissão": lambda f, n: f.reprovar(n, BRUNO, "x"),
    "cancelar": lambda f, n: f.cancelar(n, ANA, "Sem solução"),
    "cancelar sem permissão": lambda f, n: f.cancelar(n, BRUNO, "x"),
    **{
        f"observação de {u}": lambda f, n, u=u: f.adicionar_observacao(n, u, "nota")  # type: ignore[misc]
        for u in (ANA, BRUNO, CARLA)
    },
}


@pytest.mark.parametrize("construtor", CONSTRUTORES)
def test_toda_operacao_em_cada_estado_tem_o_mesmo_resultado_e_o_mesmo_estado(
    construtor: str, caminho_base: Path, relogio: RelogioFixo
) -> None:
    comparadas = 0
    for nome, operacao in OPERACOES.items():
        legado = AdaptadorLegado(caminho_base.with_name(f"{comparadas}.json"), relogio)
        dominio = AdaptadorDominio(relogio)
        try:
            numero_legado = CONSTRUTORES[construtor](legado)
            numero_dominio = CONSTRUTORES[construtor](dominio)
            assert numero_legado == numero_dominio
            assert estado(legado) == estado(dominio), f"{construtor}: estados diferem antes"
            relogio.avancar(minutes=7)  # a operação acontece em outro instante
            do_legado = operacao(legado, numero_legado)
            do_dominio = operacao(dominio, numero_dominio)
            assert observavel(do_legado) == observavel(do_dominio), f"{construtor} / {nome}"
            assert estado(legado) == estado(dominio), f"{construtor} / {nome}: estados diferem"
            comparadas += 1
        finally:
            legado.fechar()
    assert comparadas == len(OPERACOES)


def test_nao_ser_tecnico_vence_ja_atribuida_igual_ao_legado(par: Par) -> None:
    """Só aparece quando o técnico perde a permissão depois de atribuído (AUD-20)."""
    permissoes = tuple(p for p in PERMISSOES_DO_SISTEMA[:9] if p != "apontar_reparo")
    resultados: list[tuple[object, ...]] = []
    for adaptador in (par.legado, par.dominio):
        numero = os_atribuida(adaptador)
        adaptador.definir_permissoes_cargo(CARGO_TECNICO, permissoes)
        resultados.append(observavel(adaptador.atribuir(numero, BRUNO, ANA)))
    assert resultados[0] == resultados[1]
    assert resultados[0][1] is Recusa.NAO_E_TECNICO
    assert estado(par.legado) == estado(par.dominio)


# ------------------------------------------------------------------------------------- DLT-07


def test_datas_do_dominio_normalizadas_batem_com_as_do_legado(par: Par) -> None:
    """Um ciclo completo que atravessa a meia-noite: cada registro em seu instante, nos dois."""
    par.relogio.definir(datetime(2026, 3, 10, 23, 55))

    def ciclo(f: Fachada) -> int:
        numero = os_aberta(f)
        passos: tuple[Callable[[], Resultado], ...] = (
            lambda: f.atribuir(numero, BRUNO, ANA),
            lambda: f.registrar_diagnostico(numero, BRUNO, "p", "c"),
            lambda: f.apontar_reparo(numero, BRUNO, 1.5, "i", BOA),
            lambda: f.alterar_status(numero, BRUNO, STATUS_REPARO_FINALIZADO),
            lambda: f.concluir_tecnicamente(numero, BRUNO, "ok", True),
            lambda: f.aprovar(numero, ANA),
        )
        for passo in passos:
            par.relogio.avancar(minutes=3)
            assert passo().aceito
        return numero

    # O relógio é compartilhado: o mesmo roteiro, repetido, parte de instantes diferentes; por isso
    # cada adaptador roda o ciclo com o relógio recolocado no mesmo ponto de partida.
    inicio = par.relogio.agora()
    numero = ciclo(par.legado)
    par.relogio.definir(inicio)
    assert ciclo(par.dominio) == numero
    assert estado(par.legado) == estado(par.dominio)

    datas = [s.data for s in par.dominio.os(numero).historico]  # type: ignore[union-attr]
    assert datas == sorted(datas, key=lambda d: datetime.strptime(d, "%d/%m/%Y %H:%M"))
    assert datas[0].startswith("10/03/2026 23:")
    assert datas[-1].startswith("11/03/2026 00:")


def test_o_dominio_guarda_instantes_com_fuso_em_utc_e_o_legado_so_texto(par: Par) -> None:
    par.relogio.definir(datetime(2026, 3, 10, 9, 30))
    numero = os_aguardando_aprovacao(par.dominio)
    par.relogio.avancar(hours=2)
    assert par.dominio.aprovar(numero, ANA).aceito
    entidade = par.dominio.entidade(numero)
    instantes = [
        entidade.data_abertura,
        entidade.data_conclusao,
        *(s.data for s in entidade.servicos),
    ]
    assert all(i is not None and i.tzinfo is UTC for i in instantes)
    assert entidade.data_abertura == datetime(2026, 3, 10, 9, 30, tzinfo=UTC)
    assert entidade.data_conclusao == datetime(2026, 3, 10, 11, 30, tzinfo=UTC)
    # O legado só tem o texto, sem fuso (mesmo ponto de partida do relógio).
    par.relogio.definir(datetime(2026, 3, 10, 9, 30))
    numero_legado = os_aguardando_aprovacao(par.legado)
    snapshot = par.legado.os(numero_legado)
    assert snapshot is not None
    assert snapshot.data_abertura == "10/03/2026 09:30"
    assert not hasattr(snapshot.data_abertura, "tzinfo")


def test_o_relogio_ingenuo_do_teste_e_lido_como_utc_sem_conversao_de_fuso(par: Par) -> None:
    par.relogio.definir(datetime(2026, 7, 1, 0, 5))  # verão: nada de fuso local entra na conta
    numero = os_aberta(par.dominio)
    assert par.dominio.entidade(numero).data_abertura == datetime(2026, 7, 1, 0, 5, tzinfo=UTC)
    assert par.dominio.entidade(numero).data_abertura.utcoffset() == timedelta(0)
    assert par.dominio.os(numero).data_abertura == "01/07/2026 00:05"  # type: ignore[union-attr]


# ------------------------------------------------------------------------------------- DLT-11


@pytest.mark.parametrize("permissao", PERMISSOES_DO_SISTEMA)
@pytest.mark.parametrize("usuario", [ANA, BRUNO, CARLA])
def test_permissoes_validas_se_comportam_como_no_legado(
    par: Par, usuario: int, permissao: str
) -> None:
    assert par.legado.usuario_pode(usuario, permissao) == par.dominio.usuario_pode(
        usuario, permissao
    )
    do_legado = par.legado.exigir_permissao(usuario, permissao)
    do_dominio = par.dominio.exigir_permissao(usuario, permissao)
    assert observavel(do_legado) == observavel(do_dominio)


def test_permissoes_tipadas_so_divergem_do_legado_nos_nomes_invalidos(par: Par) -> None:
    # Legado: erro de digitação vira negação silenciosa (com o nome cru na mensagem).
    assert par.legado.usuario_pode(ANA, "aprovar_oss") is False
    do_legado = par.legado.exigir_permissao(ANA, "aprovar_oss")
    assert (do_legado.aceito, do_legado.recusa) == (False, Recusa.SEM_PERMISSAO)
    assert do_legado.mensagem == "Sem permissão: aprovar_oss."
    # Domínio: erro detectável (código estável), nunca confundido com uma permissão negada.
    with pytest.raises(ViolacaoDeRegraError) as capturado:
        par.dominio.usuario_pode(ANA, "aprovar_oss")
    assert capturado.value.codigo is CodigoErro.PERMISSAO_INVALIDA
    do_dominio = par.dominio.exigir_permissao(ANA, "aprovar_oss")
    assert (do_dominio.aceito, do_dominio.recusa) == (False, Recusa.DESCONHECIDA)
    assert do_dominio.mensagem == "Permissão desconhecida: 'aprovar_oss'."

    # Ao definir as permissões de um cargo: o legado ignora o nome desconhecido e aplica o resto;
    # o domínio recusa tudo e não altera o cargo.
    par.legado.definir_permissoes_cargo(CARGO_TECNICO, ("ver_os", "voar"))
    antes = par.dominio.cargos()
    with pytest.raises(ViolacaoDeRegraError):
        par.dominio.definir_permissoes_cargo(CARGO_TECNICO, ("ver_os", "voar"))
    assert par.dominio.cargos() == antes
    # Só com nomes válidos, os dois aplicam o mesmo resultado.
    par.legado.definir_permissoes_cargo(CARGO_TECNICO, ("ver_os", "abrir_os"))
    par.dominio.definir_permissoes_cargo(CARGO_TECNICO, ("ver_os", "abrir_os"))
    assert par.legado.cargos() == par.dominio.cargos()
    assert par.legado.tecnicos() == par.dominio.tecnicos() == ()
