"""Matrícula ``AA999999``: formato, geração segura, unicidade, colisões e imutabilidade."""

import re
import secrets

import pytest

from manutencao.domain.cargo import Cargo
from manutencao.domain.enums import Papel
from manutencao.domain.erros import CodigoErro, PermissaoNegadaError, ViolacaoDeRegraError
from manutencao.domain.matricula import (
    exigir_matricula_valida,
    gerar_matricula_unica,
    matricula_valida,
    sortear_matricula,
)
from manutencao.domain.permissoes import Permissoes
from manutencao.domain.usuario import Usuario

VALIDAS = ["KM482731", "RT095624", "VX716309", "AA000000", "ZZ999999"]
INVALIDAS = [
    "",
    "km482731",  # minúsculas
    "Km482731",
    "KM48273",  # 7 caracteres
    "KM4827311",  # 9 caracteres
    "K1482731",  # dígito onde vai letra
    "KMA82731",  # letra onde vai dígito
    "KM 82731",
    " KM482731",
    "KM482731 ",
    "KM482731\n",  # fullmatch: quebra de linha final não passa
    "ÁÉ482731",  # letras fora de A-Z
    "KM48273٣",  # dígito não ASCII
    "482731KM",
    "KM-82731",
]


@pytest.mark.parametrize("valor", VALIDAS)
def test_formato_valido(valor: str) -> None:
    assert matricula_valida(valor)
    assert exigir_matricula_valida(valor) == valor


@pytest.mark.parametrize("valor", INVALIDAS)
def test_formato_invalido(valor: str) -> None:
    assert not matricula_valida(valor)
    with pytest.raises(ViolacaoDeRegraError) as erro:
        exigir_matricula_valida(valor)
    assert erro.value.codigo is CodigoErro.MATRICULA_INVALIDA


@pytest.mark.parametrize("valor", [None, 482731, b"KM482731", ["KM482731"]])
def test_so_str_e_matricula(valor: object) -> None:
    assert not matricula_valida(valor)


def test_sorteio_gera_sempre_o_formato_aa999999() -> None:
    gerados = {sortear_matricula() for _ in range(500)}
    assert all(re.fullmatch(r"[A-Z]{2}[0-9]{6}", m) for m in gerados)
    assert all(matricula_valida(m) for m in gerados)
    assert len(gerados) > 490  # espaço de 676 milhões: repetições em 500 sorteios são raríssimas


def test_sorteio_usa_a_fonte_criptografica_do_sistema(monkeypatch: pytest.MonkeyPatch) -> None:
    chamadas: list[str] = []
    real = secrets.choice

    def espiao(alfabeto: str) -> str:
        chamadas.append(alfabeto)
        return real(alfabeto)

    monkeypatch.setattr(secrets, "choice", espiao)
    assert matricula_valida(sortear_matricula())
    assert len(chamadas) == 8  # 2 letras + 6 dígitos, todos por secrets.choice
    assert chamadas[:2] == ["ABCDEFGHIJKLMNOPQRSTUVWXYZ"] * 2
    assert chamadas[2:] == ["0123456789"] * 6


def test_sorteio_deterministico_injetado_monta_letras_e_digitos_na_ordem() -> None:
    fila = iter("KM482731")
    assert sortear_matricula(lambda _alfabeto: next(fila)) == "KM482731"


def test_gerar_devolve_a_primeira_livre() -> None:
    assert matricula_valida(gerar_matricula_unica(lambda _m: False))


def test_colisao_sorteia_de_novo_ate_achar_uma_livre() -> None:
    ocupadas = {"KM482731"}
    consultas: list[str] = []

    def existe(m: str) -> bool:
        consultas.append(m)
        return m in ocupadas

    escolhas = iter("KM482731" + "KM482731" + "RT095624")  # 1ª e 2ª colidem; a 3ª é livre
    assert gerar_matricula_unica(existe, sorteio=lambda _a: next(escolhas)) == "RT095624"
    assert consultas == ["KM482731", "KM482731", "RT095624"]


def test_esgotadas_as_tentativas_a_geracao_falha_com_erro_claro() -> None:
    with pytest.raises(ViolacaoDeRegraError) as erro:
        gerar_matricula_unica(lambda _m: True, tentativas=7)
    assert erro.value.codigo is CodigoErro.MATRICULA_INDISPONIVEL


def test_geracao_consulta_a_unicidade_a_cada_candidata() -> None:
    contagem = 0

    def existe(_m: str) -> bool:
        nonlocal contagem
        contagem += 1
        return contagem < 5  # as quatro primeiras colidem

    gerar_matricula_unica(existe)
    assert contagem == 5


# ----------------------------------------------------------------------------- imutabilidade
def _usuario(matricula: str | None = None) -> Usuario:
    return Usuario(
        1, "Ana", Cargo(1, "Gestor", Permissoes.padrao_gestor()), papel=Papel.GESTOR,
        matricula=matricula,
    )  # fmt: skip


def test_usuario_novo_nao_tem_matricula_ate_ser_cadastrado() -> None:
    assert _usuario().matricula is None


def test_usuario_com_matricula_a_expoe_somente_para_leitura() -> None:
    u = _usuario("KM482731")
    assert u.matricula == "KM482731"
    with pytest.raises(AttributeError):
        u.matricula = "RT095624"  # type: ignore[misc]


def test_matricula_invalida_nao_entra_no_usuario() -> None:
    with pytest.raises(ViolacaoDeRegraError):
        _usuario("km482731")
    u = _usuario()
    with pytest.raises(ViolacaoDeRegraError):
        u.atribuir_matricula("invalida")
    assert u.matricula is None


def test_matricula_e_atribuida_uma_unica_vez() -> None:
    u = _usuario()
    u.atribuir_matricula("KM482731")
    u.atribuir_matricula("KM482731")  # repetir o mesmo valor é inofensivo
    with pytest.raises(PermissaoNegadaError):
        u.atribuir_matricula("RT095624")
    assert u.matricula == "KM482731"


def test_igualdade_de_usuarios_continua_por_id() -> None:
    assert _usuario("KM482731") == _usuario("RT095624")
