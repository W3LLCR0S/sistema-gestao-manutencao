"""C1 / DLT-11: permissões tipadas, com as mesmas permissões efetivas do legado."""

import pytest

from manutencao.domain.erros import CodigoErro, ViolacaoDeRegraError
from manutencao.domain.permissoes import Permissao, Permissoes

# Nomes, ordem e descrições de models/permissoes.py (DESCRICOES): preservados sem alteração.
NOMES_DO_LEGADO = (
    "ver_equipamentos",
    "ver_os",
    "abrir_os",
    "ver_disponibilidade",
    "registrar_apontamento",
    "diagnosticar",
    "apontar_reparo",
    "atualizar_status",
    "concluir_os",
    "gerir_equipamentos",
    "gerir_usuarios",
    "atribuir_os",
    "aprovar_os",
)
DESCRICOES_DO_LEGADO = (
    "Visualizar equipamentos",
    "Consultar ordens de serviço",
    "Abrir chamados (OS)",
    "Consultar disponibilidade dos técnicos",
    "Incluir apontamentos no histórico",
    "Registrar diagnóstico",
    "Registrar horas, intervenções e peças",
    "Atualizar status operacional da OS",
    "Conclusão técnica da OS",
    "Cadastrar/editar/inativar/excluir equipamentos",
    "Gerenciar usuários, cargos e permissões",
    "Atribuir/reatribuir OS a técnicos",
    "Aprovar, cancelar e encerrar OS",
)


def test_nomes_e_ordem_do_sistema_sao_os_do_legado() -> None:
    assert tuple(p.value for p in Permissao) == NOMES_DO_LEGADO


def test_descricoes_sao_as_do_legado() -> None:
    assert tuple(p.descricao for p in Permissao) == DESCRICOES_DO_LEGADO


def test_perfil_padrao_do_tecnico_e_o_do_legado() -> None:
    esperado = NOMES_DO_LEGADO[:9]
    assert tuple(p.value for p in Permissoes.padrao_tecnico().ativas()) == esperado


def test_perfil_padrao_do_gestor_e_o_do_legado() -> None:
    esperado = (*NOMES_DO_LEGADO[:5], *NOMES_DO_LEGADO[9:])
    assert tuple(p.value for p in Permissoes.padrao_gestor().ativas()) == esperado


def test_permissoes_novas_nao_tem_nenhum_acesso() -> None:
    vazias = Permissoes()
    assert vazias.ativas() == ()
    assert not any(vazias.tem(p) for p in Permissao)


def test_tem_responde_para_cada_permissao_liberada() -> None:
    permissoes = Permissoes([Permissao.VER_OS, Permissao.APROVAR_OS])
    assert permissoes.tem(Permissao.VER_OS)
    assert permissoes.tem(Permissao.APROVAR_OS)
    assert not permissoes.tem(Permissao.DIAGNOSTICAR)


def test_ativas_segue_a_ordem_do_sistema_e_nao_a_da_entrada() -> None:
    permissoes = Permissoes([Permissao.APROVAR_OS, Permissao.VER_OS, Permissao.ABRIR_OS])
    assert permissoes.ativas() == (Permissao.VER_OS, Permissao.ABRIR_OS, Permissao.APROVAR_OS)


def test_definir_liga_so_as_informadas_e_desliga_as_demais() -> None:
    permissoes = Permissoes.padrao_gestor()
    permissoes.definir([Permissao.VER_OS])
    assert permissoes.ativas() == (Permissao.VER_OS,)


def test_definir_vazio_desliga_tudo() -> None:
    permissoes = Permissoes.padrao_tecnico()
    permissoes.definir([])
    assert permissoes.ativas() == ()


def test_duplicatas_nao_alteram_o_resultado() -> None:
    permissoes = Permissoes([Permissao.VER_OS, Permissao.VER_OS])
    assert permissoes.ativas() == (Permissao.VER_OS,)


def test_padroes_sao_independentes_entre_instancias() -> None:
    a, b = Permissoes.padrao_tecnico(), Permissoes.padrao_tecnico()
    a.definir([])
    assert b.ativas() != ()


# ------------------------------------------------------------ DLT-11: nome inválido é erro


def test_de_nome_converte_nome_valido() -> None:
    assert Permissao.de_nome("aprovar_os") is Permissao.APROVAR_OS


@pytest.mark.parametrize("nome", ["aprovar_oss", "voar", "", "APROVAR_OS", " aprovar_os"])
def test_de_nome_recusa_nome_invalido_com_erro_detectavel(nome: str) -> None:
    with pytest.raises(ViolacaoDeRegraError) as erro:
        Permissao.de_nome(nome)
    assert erro.value.codigo is CodigoErro.PERMISSAO_INVALIDA
    assert nome in erro.value.mensagem


@pytest.mark.parametrize("texto", ["aprovar_os", "aprovar_oss"])
def test_tem_recusa_texto_solto_mesmo_quando_o_nome_existe(texto: str) -> None:
    permissoes = Permissoes.padrao_gestor()
    with pytest.raises(ViolacaoDeRegraError) as erro:
        permissoes.tem(texto)  # type: ignore[arg-type]
    assert erro.value.codigo is CodigoErro.PERMISSAO_INVALIDA


def test_definir_recusa_texto_e_nao_altera_o_conjunto() -> None:
    permissoes = Permissoes.padrao_tecnico()
    antes = permissoes.ativas()
    with pytest.raises(ViolacaoDeRegraError):
        permissoes.definir([Permissao.VER_OS, "voar"])  # type: ignore[list-item]
    assert permissoes.ativas() == antes  # tudo ou nada: nenhuma troca parcial


def test_construtor_recusa_texto() -> None:
    with pytest.raises(ViolacaoDeRegraError):
        Permissoes(["ver_os"])  # type: ignore[list-item]
