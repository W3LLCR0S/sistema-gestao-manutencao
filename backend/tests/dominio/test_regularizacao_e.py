"""Regularização da Operação E no domínio (REG-E-05 e REG-E-06).

* REG-E-05 / DLT-22: o texto da observação e a descrição da peça são obrigatórios (texto não vazio
  depois de remover os espaços das extremidades), como os demais campos do DLT-08.
* REG-E-06 / DLT-23: a disponibilidade **manual** só aceita ``Disponível`` e ``Ausente``;
  ``Em atendimento`` é exclusivamente derivado das OS.
* REG-E-01 / DLT-18: gestor administrativamente apto (papel Gestor, ativo e com ``gerir_usuarios``).

Toda recusa é provada **sem mutação**.
"""

from collections.abc import Callable

import pytest

from manutencao.domain.cargo import Cargo
from manutencao.domain.disponibilidade import (
    DISPONIBILIDADES_MANUAIS,
    derivar_disponibilidade,
    exigir_disponibilidade_manual,
)
from manutencao.domain.enums import Disponibilidade, Papel, StatusOS, TipoServico
from manutencao.domain.erros import (
    CodigoErro,
    ConflitoDeEstadoError,
    DominioError,
    PermissaoNegadaError,
    ViolacaoDeRegraError,
)
from manutencao.domain.ordem_servico import OrdemServico
from manutencao.domain.peca_material import PecaMaterial
from manutencao.domain.permissoes import Permissao, Permissoes
from manutencao.domain.usuario import Usuario
from tests.dominio.fabrica import Mundo, instantaneo

VAZIOS = ["", " ", "   ", "\t", "\n", " \t\n "]


# =========================================================================================
# DLT-22 — observação obrigatória
# =========================================================================================


@pytest.mark.parametrize("texto", VAZIOS)
@pytest.mark.parametrize("status", [StatusOS.ATRIBUIDA, StatusOS.EM_EXECUCAO])
def test_dlt22_observacao_vazia_ou_so_com_espacos_e_recusada_sem_alterar_a_os(
    texto: str, status: StatusOS
) -> None:
    m = Mundo()
    os_ = m.em_status(status)
    antes = instantaneo(os_)
    for autor in (m.ana, m.bruno, m.carla):  # gestor, responsável e quem abriu
        with pytest.raises(ViolacaoDeRegraError) as capturado:
            os_.adicionar_apontamento(autor, texto, quando=m.quando())
        assert capturado.value.codigo is CodigoErro.CAMPO_OBRIGATORIO
    assert instantaneo(os_) == antes


def test_dlt22_observacao_com_texto_e_aceita_e_guardada_exatamente_como_informada() -> None:
    m = Mundo()
    os_ = m.atribuida()
    os_.adicionar_apontamento(m.ana, "  Verificar o eixo  ", quando=m.quando())
    ultimo = os_.servicos[-1]
    assert (ultimo.tipo, ultimo.descricao) == (TipoServico.APONTAMENTO, "  Verificar o eixo  ")


def test_dlt22_precedencia_permissao_vinculo_estado_e_depois_o_conteudo() -> None:
    m = Mundo()
    ativa = m.atribuida()
    encerrada = m.concluida()
    diego = Usuario(4, "Diego", m.tecnico, papel=Papel.TECNICO)
    sem_permissao = Usuario(5, "Eva", Cargo(9, "Nada", Permissoes()), papel=Papel.GESTOR)

    def recusa(
        os_: OrdemServico, usuario: Usuario, erro: type[DominioError], codigo: CodigoErro
    ) -> None:
        antes = instantaneo(os_)
        with pytest.raises(erro) as capturado:
            os_.adicionar_apontamento(usuario, "   ", quando=m.quando())
        assert capturado.value.codigo is codigo
        assert instantaneo(os_) == antes

    recusa(ativa, sem_permissao, PermissaoNegadaError, CodigoErro.SEM_PERMISSAO)
    recusa(ativa, diego, PermissaoNegadaError, CodigoErro.SEM_VINCULO_COM_A_OS)
    recusa(encerrada, m.ana, ConflitoDeEstadoError, CodigoErro.OS_ENCERRADA)
    recusa(ativa, m.ana, ViolacaoDeRegraError, CodigoErro.CAMPO_OBRIGATORIO)


def test_dlt22_o_instante_invalido_nao_mascara_a_recusa_do_conteudo() -> None:
    """O conteúdo é verificado antes do instante, como as demais validações do DLT-08."""
    m = Mundo()
    os_ = m.atribuida()
    with pytest.raises(ViolacaoDeRegraError) as capturado:
        os_.adicionar_apontamento(m.ana, " ", quando=m.quando().replace(tzinfo=None))
    assert capturado.value.codigo is CodigoErro.CAMPO_OBRIGATORIO


# =========================================================================================
# DLT-22 — descrição de peça obrigatória
# =========================================================================================


@pytest.mark.parametrize("descricao", VAZIOS)
def test_dlt22_peca_com_descricao_vazia_ou_so_com_espacos_e_recusada(descricao: str) -> None:
    with pytest.raises(ViolacaoDeRegraError) as capturado:
        PecaMaterial(descricao, 1)
    assert capturado.value.codigo is CodigoErro.CAMPO_OBRIGATORIO
    assert "descrição da peça" in str(capturado.value)


def test_dlt22_peca_valida_guarda_a_descricao_como_informada() -> None:
    peca = PecaMaterial(" Rolamento 6204 ", 2)
    assert (peca.descricao, peca.quantidade) == (" Rolamento 6204 ", 2)
    assert str(peca) == "2x  Rolamento 6204 "


def test_dlt22_a_quantidade_e_verificada_antes_da_descricao() -> None:
    """Ordem herdada: a quantidade não positiva continua sendo a primeira recusa da peça."""
    for quantidade in (0, -1):
        with pytest.raises(ViolacaoDeRegraError) as capturado:
            PecaMaterial("", quantidade)
        assert capturado.value.codigo is CodigoErro.QUANTIDADE_INVALIDA
    with pytest.raises(ViolacaoDeRegraError) as descricao:
        PecaMaterial(" ", 1)
    assert descricao.value.codigo is CodigoErro.CAMPO_OBRIGATORIO


def test_dlt22_peca_invalida_nao_inicia_a_execucao_da_os() -> None:
    """A peça é construída antes da operação: uma peça inválida nunca chega à OS."""
    m = Mundo()
    os_ = m.atribuida()
    antes = instantaneo(os_)
    with pytest.raises(ViolacaoDeRegraError):
        os_.apontar_reparo(
            m.bruno,
            1.0,
            "Troca",
            [PecaMaterial("Rolamento", 1), PecaMaterial("", 1)],
            quando=m.quando(),
        )
    assert instantaneo(os_) == antes
    assert os_.status is StatusOS.ATRIBUIDA


def test_dlt22_os_campos_do_delta_anterior_continuam_validados() -> None:
    m = Mundo()
    os_ = m.atribuida()
    chamadas: tuple[Callable[[], object], ...] = (
        lambda: os_.registrar_diagnostico(m.bruno, " ", "causa", quando=m.quando()),
        lambda: os_.registrar_diagnostico(m.bruno, "parecer", "", quando=m.quando()),
        lambda: os_.apontar_reparo(m.bruno, 1.0, "  ", [], quando=m.quando()),
        lambda: os_.cancelar(m.ana, "  ", quando=m.quando()),
    )
    for chamada in chamadas:
        with pytest.raises(DominioError) as capturado:
            chamada()
        assert capturado.value.codigo is CodigoErro.CAMPO_OBRIGATORIO


# =========================================================================================
# DLT-23 — disponibilidade manual
# =========================================================================================


def test_dlt23_so_disponivel_e_ausente_sao_valores_manuais() -> None:
    assert set(DISPONIBILIDADES_MANUAIS) == {Disponibilidade.DISPONIVEL, Disponibilidade.AUSENTE}
    for valor in DISPONIBILIDADES_MANUAIS:
        exigir_disponibilidade_manual(valor)


def test_dlt23_em_atendimento_e_recusado_como_valor_manual() -> None:
    with pytest.raises(ViolacaoDeRegraError) as capturado:
        exigir_disponibilidade_manual(Disponibilidade.EM_ATENDIMENTO)
    assert capturado.value.codigo is CodigoErro.DISPONIBILIDADE_MANUAL_INVALIDA
    assert "derivado" in str(capturado.value)


@pytest.mark.parametrize("valor", ["Ocupado", "", "em atendimento"])
def test_dlt23_um_valor_desconhecido_tambem_e_recusado(valor: str) -> None:
    with pytest.raises(ViolacaoDeRegraError):
        exigir_disponibilidade_manual(valor)  # type: ignore[arg-type]


def test_dlt23_o_usuario_grava_disponivel_e_ausente_e_recusa_em_atendimento_sem_mutacao() -> None:
    bruno = Mundo().bruno

    def valor() -> Disponibilidade:
        return bruno.disponibilidade

    bruno.definir_disponibilidade_manual(Disponibilidade.AUSENTE)
    assert valor() is Disponibilidade.AUSENTE
    with pytest.raises(ViolacaoDeRegraError) as capturado:
        bruno.definir_disponibilidade_manual(Disponibilidade.EM_ATENDIMENTO)
    assert capturado.value.codigo is CodigoErro.DISPONIBILIDADE_MANUAL_INVALIDA
    assert valor() is Disponibilidade.AUSENTE  # o valor anterior ficou
    bruno.definir_disponibilidade_manual(Disponibilidade.DISPONIVEL)
    assert valor() is Disponibilidade.DISPONIVEL


def test_dlt23_em_atendimento_continua_sendo_derivado_e_a_ausencia_prevalece() -> None:
    assert (
        derivar_disponibilidade(Disponibilidade.DISPONIVEL, ha_os_em_execucao=True)
        is Disponibilidade.EM_ATENDIMENTO
    )
    assert (
        derivar_disponibilidade(Disponibilidade.DISPONIVEL, ha_os_em_execucao=False)
        is Disponibilidade.DISPONIVEL
    )
    assert (
        derivar_disponibilidade(Disponibilidade.AUSENTE, ha_os_em_execucao=True)
        is Disponibilidade.AUSENTE
    )


# =========================================================================================
# DLT-18 — gestor administrativamente apto
# =========================================================================================


def test_dlt18_o_gestor_apto_exige_papel_gestor_ativo_e_gerir_usuarios() -> None:
    m = Mundo()

    def apto() -> bool:
        return m.ana.e_gestor_administrativo

    assert apto()
    m.ana.desativar()
    assert not apto()  # inativo
    m.ana.reativar()
    assert apto()
    m.gestor.permissoes.definir(
        [p for p in m.gestor.permissoes.ativas() if p is not Permissao.GERIR_USUARIOS]
    )
    assert not apto()  # sem gerir_usuarios
    assert m.ana.e_gestor  # continua Gestor pelo papel


def test_dlt18_o_tecnico_com_gerir_usuarios_nao_e_gestor_administrativo() -> None:
    m = Mundo()
    m.tecnico.permissoes.definir((*m.tecnico.permissoes.ativas(), Permissao.GERIR_USUARIOS))
    assert m.bruno.pode(Permissao.GERIR_USUARIOS)
    assert not m.bruno.e_gestor_administrativo
