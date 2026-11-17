"""C1: enumerações e hierarquia de erros do domínio."""

from enum import StrEnum

import pytest

from manutencao.domain.enums import Criticidade, Disponibilidade, StatusOS, TipoServico
from manutencao.domain.erros import (
    CodigoErro,
    ConflitoDeEstadoError,
    DominioError,
    PermissaoNegadaError,
    ViolacaoDeRegraError,
)

# Valores textuais do legado (models/enums.py): fazem parte do comportamento observado.
VALORES_LEGADO: dict[type[StrEnum], list[str]] = {
    StatusOS: [
        "Aberta",
        "Atribuída",
        "Em Execução",
        "Aguardando Peça",
        "Reparo Finalizado",
        "Aguardando Aprovação",
        "Concluída",
        "Cancelada",
    ],
    Criticidade: ["Baixa", "Média", "Alta", "Crítica"],
    Disponibilidade: ["Disponível", "Em atendimento", "Ausente"],
    TipoServico: [
        "Abertura",
        "Atribuição",
        "Reatribuição",
        "Diagnóstico",
        "Reparo",
        "Mudança de status",
        "Apontamento",
        "Teste funcional",
        "Conclusão técnica",
        "Encerramento",
        "Reprovação",
        "Cancelamento",
    ],
}


@pytest.mark.parametrize("enum", list(VALORES_LEGADO), ids=lambda e: e.__name__)
def test_enum_tem_os_valores_e_a_ordem_do_legado(enum: type[StrEnum]) -> None:
    assert [m.value for m in enum] == VALORES_LEGADO[enum]


@pytest.mark.parametrize("enum", list(VALORES_LEGADO), ids=lambda e: e.__name__)
def test_str_e_format_do_enum_sao_o_valor_textual(enum: type[StrEnum]) -> None:
    for membro in enum:
        assert str(membro) == membro.value
        assert f"{membro}" == membro.value


def test_valor_textual_converte_em_membro_e_desconhecido_e_recusado() -> None:
    assert StatusOS("Em Execução") is StatusOS.EM_EXECUCAO
    with pytest.raises(ValueError, match="Inexistente"):
        StatusOS("Inexistente")


def test_hierarquia_de_erros() -> None:
    for classe in (PermissaoNegadaError, ConflitoDeEstadoError, ViolacaoDeRegraError):
        assert issubclass(classe, DominioError)
        assert issubclass(classe, Exception)
    assert not issubclass(PermissaoNegadaError, ConflitoDeEstadoError)
    assert not issubclass(ConflitoDeEstadoError, ViolacaoDeRegraError)


def test_erro_carrega_codigo_e_mensagem() -> None:
    erro = ConflitoDeEstadoError(CodigoErro.OS_ENCERRADA, "A OS já está encerrada.")
    assert erro.codigo is CodigoErro.OS_ENCERRADA
    assert erro.mensagem == str(erro) == "A OS já está encerrada."


def test_codigos_de_erro_sao_unicos_e_estaveis() -> None:
    valores = [c.value for c in CodigoErro]
    assert len(valores) == len(set(valores))
    assert all(v == v.lower() and " " not in v for v in valores)
