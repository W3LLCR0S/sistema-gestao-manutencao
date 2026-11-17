"""Permissões, responsável técnico e gestor (autorização no domínio da OS)."""

from collections.abc import Callable

import pytest

from tests.caracterizacao.cenarios import (
    ANA,
    BRUNO,
    CARGO_GESTOR,
    CARGO_TECNICO,
    CARLA,
    PERMISSOES_DO_SISTEMA,
    PERMISSOES_PADRAO_GESTOR,
    PERMISSOES_PADRAO_TECNICO,
    STATUS_EM_EXECUCAO,
    STATUS_REPARO_FINALIZADO,
)
from tests.caracterizacao.fachada import Fachada, Peca, Recusa, Resultado
from tests.caracterizacao.fluxos import (
    aceitar,
    estado_global,
    os_aberta,
    os_aguardando_aprovacao,
    os_atribuida,
    os_em_execucao,
    os_reparo_finalizado,
    recusada,
)


@pytest.mark.cenario("CAR-55")
def test_perfis_padrao_tem_exatamente_as_permissoes_documentadas(f: Fachada) -> None:
    cargos = {c.nome: c.permissoes for c in f.cargos()}
    assert cargos["Gestor"] == PERMISSOES_PADRAO_GESTOR
    assert cargos["Técnico"] == PERMISSOES_PADRAO_TECNICO
    assert set(cargos["Gestor"]) & set(cargos["Técnico"]) == set(PERMISSOES_DO_SISTEMA[:5])


@pytest.mark.cenario("CAR-55")
@pytest.mark.parametrize("permissao", PERMISSOES_DO_SISTEMA)
def test_matriz_de_permissoes_por_usuario(f: Fachada, permissao: str) -> None:
    assert f.usuario_pode(ANA, permissao) is (permissao in PERMISSOES_PADRAO_GESTOR)
    assert f.usuario_pode(BRUNO, permissao) is (permissao in PERMISSOES_PADRAO_TECNICO)
    assert f.usuario_pode(CARLA, permissao) is (permissao in PERMISSOES_PADRAO_TECNICO)


@pytest.mark.cenario("CAR-55")
def test_permissao_exigida_e_negada_com_a_descricao_do_acesso(f: Fachada) -> None:
    assert f.exigir_permissao(BRUNO, "diagnosticar").aceito
    resultado = recusada(f.exigir_permissao(BRUNO, "gerir_usuarios"), Recusa.SEM_PERMISSAO)
    assert resultado.mensagem == "Sem permissão: Gerenciar usuários, cargos e permissões."


@pytest.mark.cenario("CAR-56")
def test_alterar_permissoes_do_cargo_vale_para_todos_os_usuarios_do_cargo(f: Fachada) -> None:
    novo = f.cadastrar_usuario("Diego", CARGO_TECNICO)
    assert f.usuario_pode(BRUNO, "diagnosticar")
    assert f.usuario_pode(novo, "diagnosticar")
    f.definir_permissoes_cargo(
        CARGO_TECNICO, tuple(p for p in PERMISSOES_PADRAO_TECNICO if p != "diagnosticar")
    )
    assert not f.usuario_pode(BRUNO, "diagnosticar")
    assert not f.usuario_pode(CARLA, "diagnosticar")
    assert not f.usuario_pode(novo, "diagnosticar")
    assert f.usuario_pode(ANA, "ver_os")  # outro cargo não é afetado


@pytest.mark.cenario("CAR-56")
def test_trocar_o_cargo_do_usuario_troca_as_permissoes(f: Fachada) -> None:
    f.editar_usuario(CARLA, cargo=CARGO_GESTOR)
    assert f.usuario_pode(CARLA, "atribuir_os")
    assert not f.usuario_pode(CARLA, "diagnosticar")


@pytest.mark.cenario("CAR-56")
def test_definir_permissoes_liga_so_as_informadas_e_desliga_as_demais(f: Fachada) -> None:
    f.definir_permissoes_cargo(CARGO_TECNICO, ("ver_os", "abrir_os"))
    cargo = next(c for c in f.cargos() if c.id == CARGO_TECNICO)
    assert cargo.permissoes == ("ver_os", "abrir_os")
    f.definir_permissoes_cargo(CARGO_TECNICO, ())
    cargo = next(c for c in f.cargos() if c.id == CARGO_TECNICO)
    assert cargo.permissoes == ()


@pytest.mark.cenario("CAR-57")
def test_operacoes_tecnicas_exigem_ser_o_responsavel_mesmo_para_quem_tem_a_permissao(
    f: Fachada,
) -> None:
    numero = os_em_execucao(f, tecnico=BRUNO)
    antes = estado_global(f)
    tentativas: list[Resultado] = [
        f.registrar_diagnostico(numero, CARLA, "p", "c"),
        f.apontar_reparo(numero, CARLA, 1.0, "i"),
        f.alterar_status(numero, CARLA, STATUS_REPARO_FINALIZADO),
    ]
    assert all(t.recusa is Recusa.NAO_RESPONSAVEL for t in tentativas)
    assert estado_global(f) == antes


@pytest.mark.cenario("CAR-57")
def test_conclusao_tecnica_exige_ser_o_responsavel(f: Fachada) -> None:
    numero = os_reparo_finalizado(f, tecnico=BRUNO)
    recusada(f.concluir_tecnicamente(numero, CARLA, "ok", True), Recusa.NAO_RESPONSAVEL)


@pytest.mark.cenario("CAR-57")
def test_reatribuicao_transfere_a_responsabilidade_tecnica(f: Fachada) -> None:
    numero = os_em_execucao(f, tecnico=BRUNO)
    aceitar(f.atribuir(numero, CARLA, ANA))
    recusada(f.apontar_reparo(numero, BRUNO, 1.0, "i"), Recusa.NAO_RESPONSAVEL)
    aceitar(f.apontar_reparo(numero, CARLA, 1.0, "i"))


@pytest.mark.cenario("CAR-58")
def test_gestor_com_permissoes_tecnicas_continua_sem_ser_o_responsavel(f: Fachada) -> None:
    """Gestor não opera a OS de um técnico: faltaria ser o responsável (AUD-20 trata o papel)."""
    numero = os_em_execucao(f, tecnico=BRUNO)
    f.definir_permissoes_cargo(
        CARGO_GESTOR, (*PERMISSOES_PADRAO_GESTOR, *PERMISSOES_PADRAO_TECNICO)
    )
    recusada(f.registrar_diagnostico(numero, ANA, "p", "c"), Recusa.NAO_RESPONSAVEL)
    recusada(f.apontar_reparo(numero, ANA, 1.0, "i"), Recusa.NAO_RESPONSAVEL)


@pytest.mark.cenario("CAR-58")
def test_gestor_nao_opera_o_lado_tecnico_sem_as_permissoes_tecnicas(f: Fachada) -> None:
    numero = os_atribuida(f, tecnico=BRUNO)
    recusada(f.registrar_diagnostico(numero, ANA, "p", "c"), Recusa.SEM_PERMISSAO)
    recusada(f.apontar_reparo(numero, ANA, 1.0, "i"), Recusa.SEM_PERMISSAO)
    recusada(f.alterar_status(numero, ANA, STATUS_EM_EXECUCAO), Recusa.SEM_PERMISSAO)
    recusada(f.concluir_tecnicamente(numero, ANA, "t", True), Recusa.SEM_PERMISSAO)


@pytest.mark.cenario("CAR-58")
def test_tecnico_nao_opera_o_lado_gestor(f: Fachada) -> None:
    numero = os_aguardando_aprovacao(f)
    outra = os_aberta(f)
    recusada(f.aprovar(numero, BRUNO), Recusa.SEM_PERMISSAO)
    recusada(f.reprovar(numero, BRUNO, "m"), Recusa.SEM_PERMISSAO)
    recusada(f.cancelar(outra, BRUNO, "m"), Recusa.SEM_PERMISSAO)
    recusada(f.atribuir(outra, CARLA, BRUNO), Recusa.SEM_PERMISSAO)


@pytest.mark.cenario("CAR-59")
@pytest.mark.parametrize(
    ("permissao", "operacao"),
    [
        ("diagnosticar", lambda f, n: f.registrar_diagnostico(n, BRUNO, "p", "c")),
        ("apontar_reparo", lambda f, n: f.apontar_reparo(n, BRUNO, 1.0, "i", (Peca("x", 1),))),
        ("atualizar_status", lambda f, n: f.alterar_status(n, BRUNO, STATUS_REPARO_FINALIZADO)),
        ("registrar_apontamento", lambda f, n: f.adicionar_observacao(n, BRUNO, "nota")),
        ("concluir_os", lambda f, n: f.concluir_tecnicamente(n, BRUNO, "ok", True)),
    ],
)
def test_cada_operacao_tecnica_depende_da_sua_propria_permissao(
    f: Fachada, permissao: str, operacao: Callable[[Fachada, int], Resultado]
) -> None:
    numero = os_em_execucao(f)
    # com todas as permissões padrão, a operação seria aceita (ou recusada por outra regra)...
    f.definir_permissoes_cargo(
        CARGO_TECNICO, tuple(p for p in PERMISSOES_PADRAO_TECNICO if p != permissao)
    )
    # ... mas sem exatamente esta permissão a causa da recusa é a permissão
    antes = estado_global(f)
    recusada(operacao(f, numero), Recusa.SEM_PERMISSAO)
    assert estado_global(f) == antes


@pytest.mark.cenario("CAR-60")
def test_usuario_sem_nenhuma_permissao_nao_opera_nada(f: Fachada) -> None:
    f.definir_permissoes_cargo(CARGO_TECNICO, ())
    assert all(not f.usuario_pode(BRUNO, p) for p in PERMISSOES_DO_SISTEMA)
    assert f.tecnicos() == ()  # sem apontar_reparo ninguém é técnico (AUD-20)
    recusada(f.abrir_os(BRUNO, 1, "x", "Baixa"), Recusa.SEM_PERMISSAO)
