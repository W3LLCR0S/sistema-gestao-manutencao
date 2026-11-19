"""C3: entidades menores (Equipamento, PecaMaterial, Cargo, Usuario, Servico)."""

import dataclasses
from datetime import UTC, datetime

import pytest

from manutencao.domain.cargo import Cargo
from manutencao.domain.enums import Disponibilidade, Papel, TipoServico
from manutencao.domain.equipamento import Equipamento
from manutencao.domain.erros import (
    CodigoErro,
    PermissaoNegadaError,
    ViolacaoDeRegraError,
)
from manutencao.domain.peca_material import PecaMaterial
from manutencao.domain.permissoes import Permissao, Permissoes
from manutencao.domain.servico import Servico
from manutencao.domain.usuario import Usuario

# ------------------------------------------------------------------------------ Equipamento


def test_equipamento_novo_nasce_ativo() -> None:
    torno = Equipamento(1, "Torno CNC", "GL 240")
    assert (torno.id, torno.nome, torno.modelo, torno.ativo) == (1, "Torno CNC", "GL 240", True)
    assert torno.situacao == "Ativo"
    assert str(torno) == "Torno CNC (GL 240)"


def test_equipamento_inativar_e_reativar() -> None:
    torno = Equipamento(1, "Torno", "GL")
    torno.inativar()
    assert (torno.ativo, torno.situacao) == (False, "Inativo")
    torno.reativar()
    assert (torno.ativo, torno.situacao) == (True, "Ativo")


def test_equipamento_pode_nascer_inativo() -> None:
    assert Equipamento(1, "Torno", "GL", ativo=False).ativo is False


def test_equipamento_e_igual_por_identificador() -> None:
    assert Equipamento(1, "Torno", "GL") == Equipamento(1, "Outro nome", "Outro modelo")
    assert Equipamento(1, "Torno", "GL") != Equipamento(2, "Torno", "GL")
    assert len({Equipamento(1, "A", "x"), Equipamento(1, "B", "y")}) == 1


def test_equipamento_nao_e_igual_a_outro_tipo() -> None:
    assert Equipamento(1, "Torno", "GL") != 1


# ------------------------------------------------------------------------------ PecaMaterial


def test_peca_aceita_quantidade_positiva_inclusive_fracionada() -> None:
    assert PecaMaterial("Rolamento", 2).quantidade == 2
    assert PecaMaterial("Óleo (L)", 0.5).quantidade == 0.5


@pytest.mark.parametrize("quantidade", [0, -1, -0.5])
def test_peca_recusa_quantidade_nao_positiva(quantidade: float) -> None:
    with pytest.raises(ViolacaoDeRegraError) as erro:
        PecaMaterial("Rolamento", quantidade)
    assert erro.value.codigo is CodigoErro.QUANTIDADE_INVALIDA
    assert str(erro.value) == "A quantidade deve ser maior que zero."


def test_peca_e_imutavel_e_comparada_por_valor() -> None:
    peca = PecaMaterial("Rolamento", 2)
    with pytest.raises(dataclasses.FrozenInstanceError):
        peca.quantidade = 3  # type: ignore[misc]
    assert peca == PecaMaterial("Rolamento", 2)
    assert peca != PecaMaterial("Rolamento", 3)


@pytest.mark.parametrize(
    ("quantidade", "texto"), [(2, "2x Rolamento"), (1.5, "1.5x Rolamento"), (10.0, "10x Rolamento")]
)
def test_peca_como_texto(quantidade: float, texto: str) -> None:
    assert str(PecaMaterial("Rolamento", quantidade)) == texto


# ------------------------------------------------------------------------- Cargo e Usuario


def _cargo(id: int = 2, permissoes: Permissoes | None = None) -> Cargo:
    return Cargo(id, "Técnico", permissoes or Permissoes.padrao_tecnico())


def test_cargo_guarda_nome_e_permissoes() -> None:
    cargo = _cargo()
    assert (cargo.id, cargo.nome, str(cargo)) == (2, "Técnico", "Técnico")
    assert cargo.permissoes.tem(Permissao.DIAGNOSTICAR)


def test_cargo_e_igual_por_identificador() -> None:
    assert _cargo(1) == Cargo(1, "Outro", Permissoes())
    assert _cargo(1) != _cargo(2)
    assert _cargo(1) != "Técnico"


def test_usuario_nasce_disponivel_com_dados_cadastrais_vazios() -> None:
    usuario = Usuario(2, "Bruno Lima", _cargo(), papel=Papel.TECNICO)
    assert usuario.disponibilidade is Disponibilidade.DISPONIVEL
    assert (usuario.email, usuario.escala) == ("", "")
    assert str(usuario) == "Bruno Lima"


def test_usuario_e_igual_por_identificador() -> None:
    assert Usuario(1, "Ana", _cargo(), papel=Papel.TECNICO) == Usuario(
        1, "Outro nome", _cargo(9), papel=Papel.TECNICO
    )
    assert Usuario(1, "Ana", _cargo(), papel=Papel.TECNICO) != Usuario(
        2, "Ana", _cargo(), papel=Papel.TECNICO
    )
    assert (
        len(
            {
                Usuario(1, "A", _cargo(), papel=Papel.TECNICO),
                Usuario(1, "B", _cargo(), papel=Papel.TECNICO),
            }
        )
        == 1
    )


def test_permissoes_do_usuario_vem_do_cargo_e_acompanham_suas_mudancas() -> None:
    cargo = _cargo()
    bruno, carla = (
        Usuario(2, "Bruno", cargo, papel=Papel.TECNICO),
        Usuario(3, "Carla", cargo, papel=Papel.TECNICO),
    )
    assert bruno.pode(Permissao.APONTAR_REPARO)
    assert carla.pode(Permissao.APONTAR_REPARO)
    cargo.permissoes.definir([Permissao.VER_OS])
    assert not bruno.pode(Permissao.APONTAR_REPARO)
    assert not carla.pode(Permissao.APONTAR_REPARO)
    assert bruno.pode(Permissao.VER_OS)


def test_mudar_de_cargo_muda_as_permissoes() -> None:
    gestor = Cargo(1, "Gestor", Permissoes.padrao_gestor())
    usuario = Usuario(2, "Bruno", _cargo(), papel=Papel.TECNICO)
    assert not usuario.pode(Permissao.APROVAR_OS)
    usuario.cargo = gestor
    assert usuario.pode(Permissao.APROVAR_OS)


def test_exigir_nao_faz_nada_quando_tem_a_permissao() -> None:
    Usuario(2, "Bruno", _cargo(), papel=Papel.TECNICO).exigir(Permissao.DIAGNOSTICAR)


@pytest.mark.parametrize(
    ("permissao", "descricao"),
    [
        (Permissao.APROVAR_OS, "Aprovar, cancelar e encerrar OS"),
        (Permissao.GERIR_USUARIOS, "Gerenciar usuários, cargos e permissões"),
    ],
)
def test_exigir_recusa_com_a_descricao_da_permissao(permissao: Permissao, descricao: str) -> None:
    with pytest.raises(PermissaoNegadaError) as erro:
        Usuario(2, "Bruno", _cargo(), papel=Papel.TECNICO).exigir(permissao)
    assert erro.value.codigo is CodigoErro.SEM_PERMISSAO
    assert str(erro.value) == f"Sem permissão: {descricao}."


def test_pode_e_exigir_recusam_texto_em_vez_de_negar_em_silencio() -> None:
    bruno = Usuario(2, "Bruno", _cargo(), papel=Papel.TECNICO)
    for operacao in (bruno.pode, bruno.exigir):
        with pytest.raises(ViolacaoDeRegraError) as erro:
            operacao("aprovar_oss")  # type: ignore[arg-type]
        assert erro.value.codigo is CodigoErro.PERMISSAO_INVALIDA


def test_e_tecnico_depende_so_do_papel_e_nao_de_apontar_reparo() -> None:
    """D-02 (DLT-01): no legado retirar ``apontar_reparo`` destituía o técnico (AUD-20)."""
    cargo = _cargo()
    bruno = Usuario(2, "Bruno", cargo, papel=Papel.TECNICO)
    antes = bruno.e_tecnico
    cargo.permissoes.definir([p for p in Permissao if p is not Permissao.APONTAR_REPARO])
    depois = bruno.e_tecnico
    assert (antes, depois) == (True, True)
    assert not bruno.pode(Permissao.APONTAR_REPARO)  # continua técnico, mas sem a permissão


def test_gestor_nao_vira_tecnico_ao_receber_apontar_reparo() -> None:
    """D-02 (DLT-01): no legado conceder ``apontar_reparo`` ao gestor o tornava técnico (AUD-20)."""
    gestor = Usuario(1, "Ana", Cargo(1, "Gestor", Permissoes.padrao_gestor()), papel=Papel.GESTOR)
    antes = gestor.e_tecnico
    gestor.cargo.permissoes.definir([Permissao.APONTAR_REPARO])
    depois = gestor.e_tecnico
    assert (antes, depois) == (False, False)
    assert gestor.pode(Permissao.APONTAR_REPARO)  # a permissão vale, o papel não muda


def test_disponibilidade_e_um_valor_armazenado_alteravel() -> None:
    usuario = Usuario(2, "Bruno", _cargo(), papel=Papel.TECNICO)
    usuario.disponibilidade = Disponibilidade.AUSENTE
    assert usuario.disponibilidade is Disponibilidade.AUSENTE


# ------------------------------------------------------------------------------- Servico

AGORA = datetime(2026, 3, 10, 9, 0, tzinfo=UTC)


def test_servico_guarda_os_campos_e_tem_valores_padrao() -> None:
    autor = Usuario(2, "Bruno", _cargo(), papel=Papel.TECNICO)
    servico = Servico(1, TipoServico.ABERTURA, "[Alta] Torno parado", autor, AGORA)
    assert (servico.numero, servico.tipo, servico.responsavel, servico.data) == (
        1,
        TipoServico.ABERTURA,
        autor,
        AGORA,
    )
    assert (servico.horas, servico.pecas) == (0.0, ())


def test_servico_aceita_pecas_e_responsavel_ausente() -> None:
    pecas = (PecaMaterial("Rolamento", 2),)
    servico = Servico(2, TipoServico.REPARO, "Troca", None, AGORA, horas=1.5, pecas=pecas)
    assert (servico.responsavel, servico.horas, servico.pecas) == (None, 1.5, pecas)


def test_servico_e_imutavel() -> None:
    servico = Servico(1, TipoServico.APONTAMENTO, "x", None, AGORA)
    with pytest.raises(dataclasses.FrozenInstanceError):
        servico.descricao = "y"  # type: ignore[misc]
