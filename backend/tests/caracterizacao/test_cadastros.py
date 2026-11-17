"""Cadastros: usuários, cargos, permissões e equipamentos (inativação, exclusão, vínculos)."""

from collections.abc import Callable

import pytest

from tests.caracterizacao.cenarios import (
    ANA,
    BRUNO,
    CARGO_GESTOR,
    CARGO_TECNICO,
    CARLA,
    COMPRESSOR,
    DISPONIVEL,
    EMPILHADEIRA,
    PERMISSOES_PADRAO_TECNICO,
    TORNO,
)
from tests.caracterizacao.fachada import Fachada, Recusa
from tests.caracterizacao.fluxos import (
    aceitar,
    estado_global,
    os_aberta,
    os_atribuida,
    os_cancelada,
    os_concluida,
    os_snap,
    recusada,
)

# --------------------------------------------------------------------------------- usuários


@pytest.mark.cenario("CAR-61")
def test_cadastrar_usuario_recebe_proximo_id_e_disponibilidade_inicial(f: Fachada) -> None:
    novo = f.cadastrar_usuario("Diego Alves", CARGO_TECNICO, "diego@empresa.com", "Seg-Sex 08h-17h")
    assert novo == 4
    snap = f.usuario(novo)
    assert snap is not None
    assert (snap.nome, snap.cargo, snap.cargo_id) == ("Diego Alves", "Técnico", CARGO_TECNICO)
    assert (snap.email, snap.escala) == ("diego@empresa.com", "Seg-Sex 08h-17h")
    assert (snap.disponibilidade, snap.carga) == (DISPONIVEL, 0)
    assert [u.id for u in f.usuarios()] == [ANA, BRUNO, CARLA, 4]


@pytest.mark.cenario("CAR-61")
def test_email_e_escala_sao_opcionais_no_cadastro(f: Fachada) -> None:
    novo = f.cadastrar_usuario("Eva", CARGO_GESTOR)
    snap = f.usuario(novo)
    assert snap is not None
    assert (snap.email, snap.escala) == ("", "")


@pytest.mark.cenario("CAR-62")
def test_novo_tecnico_aparece_na_lista_de_tecnicos_e_recebe_os(f: Fachada) -> None:
    novo = f.cadastrar_usuario("Diego", CARGO_TECNICO)
    assert f.tecnicos() == (BRUNO, CARLA, novo)
    numero = os_aberta(f)
    aceitar(f.atribuir(numero, novo, ANA))
    assert os_snap(f, numero).tecnico_id == novo


@pytest.mark.cenario("CAR-62")
def test_novo_gestor_nao_e_tecnico_nem_recebe_os(f: Fachada) -> None:
    novo = f.cadastrar_usuario("Eva", CARGO_GESTOR)
    assert novo not in f.tecnicos()
    numero = os_aberta(f)
    recusada(f.atribuir(numero, novo, ANA), Recusa.NAO_E_TECNICO)


@pytest.mark.cenario("CAR-63")
def test_editar_usuario_altera_apenas_os_campos_informados(f: Fachada) -> None:
    f.editar_usuario(BRUNO, nome="Bruno L. Lima", escala="Seg-Qui 06h-14h")
    snap = f.usuario(BRUNO)
    assert snap is not None
    assert (snap.nome, snap.escala, snap.email, snap.cargo_id) == (
        "Bruno L. Lima",
        "Seg-Qui 06h-14h",
        "bruno@empresa.com",
        CARGO_TECNICO,
    )


@pytest.mark.cenario("CAR-63")
def test_alterar_o_cargo_move_o_usuario_entre_tecnicos_e_gestores(f: Fachada) -> None:
    f.editar_usuario(CARLA, cargo=CARGO_GESTOR)
    assert f.tecnicos() == (BRUNO,)
    f.editar_usuario(CARLA, cargo=CARGO_TECNICO)
    assert f.tecnicos() == (BRUNO, CARLA)


@pytest.mark.cenario("CAR-63")
def test_renomear_usuario_nao_reescreve_registros_historicos_de_texto(f: Fachada) -> None:
    """O histórico guarda o texto da descrição; o autor é uma referência (por isso muda)."""
    numero = os_atribuida(f, tecnico=BRUNO)
    f.editar_usuario(BRUNO, nome="Bruno Renomeado")
    os_ = os_snap(f, numero)
    assert os_.historico[1].descricao == "Atribuída a Bruno Lima"  # texto fixo na época
    assert os_.tecnico_id == BRUNO  # a referência segue o usuário


@pytest.mark.cenario("CAR-64")
def test_excluir_usuario_sem_historico_o_remove(f: Fachada) -> None:
    novo = f.cadastrar_usuario("Diego", CARGO_TECNICO)
    aceitar(f.remover_usuario(novo, ANA))
    assert f.usuario(novo) is None
    assert [u.id for u in f.usuarios()] == [ANA, BRUNO, CARLA]


@pytest.mark.cenario("CAR-64")
def test_gestor_nao_pode_excluir_o_proprio_usuario(f: Fachada) -> None:
    antes = estado_global(f)
    resultado = recusada(f.remover_usuario(ANA, ANA), Recusa.AUTOEXCLUSAO)
    assert resultado.mensagem == "Você não pode excluir o próprio usuário."
    assert estado_global(f) == antes


@pytest.mark.cenario("CAR-64")
def test_autoexclusao_e_verificada_antes_do_historico(f: Fachada) -> None:
    os_atribuida(f)  # Ana (atribuição) e Carla (abertura) e Bruno (técnico) têm histórico
    recusada(f.remover_usuario(ANA, ANA), Recusa.AUTOEXCLUSAO)


@pytest.mark.cenario("CAR-65")
@pytest.mark.parametrize(
    "usuario",
    [
        pytest.param(CARLA, id="abriu-a-os"),
        pytest.param(BRUNO, id="tecnico-atribuido"),
        pytest.param(ANA, id="responsavel-de-um-registro-de-atribuicao"),
    ],
)
def test_usuario_com_historico_em_os_nao_pode_ser_excluido(f: Fachada, usuario: int) -> None:
    os_atribuida(f, tecnico=BRUNO)  # aberta por Carla, de Bruno, atribuída por Ana
    solicitante = BRUNO if usuario == ANA else ANA  # ninguém pode excluir a si mesmo
    antes = estado_global(f)
    resultado = recusada(f.remover_usuario(usuario, solicitante), Recusa.USUARIO_COM_HISTORICO)
    assert resultado.mensagem == "Usuário possui histórico em OS; não pode ser excluído."
    assert estado_global(f) == antes


@pytest.mark.cenario("CAR-65")
def test_autor_de_apenas_uma_observacao_tambem_tem_historico(f: Fachada) -> None:
    numero = os_aberta(f, solicitante=ANA)
    novo = f.cadastrar_usuario("Diego", CARGO_TECNICO)
    aceitar(f.adicionar_observacao(numero, novo, "passou aqui"))
    recusada(f.remover_usuario(novo, ANA), Recusa.USUARIO_COM_HISTORICO)


@pytest.mark.cenario("CAR-65")
@pytest.mark.parametrize("construir", [os_concluida, os_cancelada])
def test_historico_em_os_encerrada_continua_impedindo_a_exclusao(
    f: Fachada, construir: Callable[[Fachada], int]
) -> None:
    construir(f)
    recusada(f.remover_usuario(CARLA, ANA), Recusa.USUARIO_COM_HISTORICO)


# ------------------------------------------------------------------------------ equipamentos


@pytest.mark.cenario("CAR-66")
def test_cadastrar_equipamento_recebe_proximo_id_e_nasce_ativo(f: Fachada) -> None:
    novo = f.cadastrar_equipamento("Prensa Hidráulica", "PH 100")
    assert novo == 4
    snap = f.equipamento(novo)
    assert snap is not None
    assert (snap.nome, snap.modelo, snap.ativo) == ("Prensa Hidráulica", "PH 100", True)
    assert [e.id for e in f.equipamentos()] == [TORNO, COMPRESSOR, EMPILHADEIRA, 4]


@pytest.mark.cenario("CAR-66")
def test_editar_equipamento_altera_nome_e_modelo(f: Fachada) -> None:
    f.editar_equipamento(TORNO, nome="Torno CNC 2", modelo="GL 300")
    snap = f.equipamento(TORNO)
    assert snap is not None
    assert (snap.nome, snap.modelo, snap.ativo) == ("Torno CNC 2", "GL 300", True)


@pytest.mark.cenario("CAR-67")
def test_inativar_e_reativar_equipamento_alternam_a_situacao(f: Fachada) -> None:
    f.inativar_equipamento(TORNO)
    inativo = f.equipamento(TORNO)
    assert inativo is not None
    assert inativo.ativo is False
    f.inativar_equipamento(TORNO)  # repetir é inofensivo
    assert f.equipamento(TORNO) == inativo
    f.reativar_equipamento(TORNO)
    reativado = f.equipamento(TORNO)
    assert reativado is not None
    assert reativado.ativo is True


@pytest.mark.cenario("CAR-67")
def test_inativar_equipamento_nao_afeta_as_os_ja_abertas(f: Fachada) -> None:
    numero = os_atribuida(f)
    f.inativar_equipamento(TORNO)
    aceitar(f.apontar_reparo(numero, BRUNO, 1.0, "continua o reparo"))  # a OS segue o seu curso
    assert os_snap(f, numero).status == "Em Execução"
    recusada(f.abrir_os(CARLA, TORNO, "nova", "Baixa"), Recusa.EQUIPAMENTO_INATIVO)


@pytest.mark.cenario("CAR-68")
def test_excluir_equipamento_sem_os_o_remove(f: Fachada) -> None:
    aceitar(f.remover_equipamento(EMPILHADEIRA))
    assert f.equipamento(EMPILHADEIRA) is None
    assert [e.id for e in f.equipamentos()] == [TORNO, COMPRESSOR]


@pytest.mark.cenario("CAR-68")
def test_excluir_equipamento_inativo_sem_os_tambem_e_permitido(f: Fachada) -> None:
    f.inativar_equipamento(EMPILHADEIRA)
    aceitar(f.remover_equipamento(EMPILHADEIRA))
    assert f.equipamento(EMPILHADEIRA) is None


@pytest.mark.cenario("CAR-69")
@pytest.mark.parametrize("construir", [os_aberta, os_concluida, os_cancelada])
def test_equipamento_com_os_vinculada_nao_pode_ser_excluido(
    f: Fachada, construir: Callable[[Fachada], int]
) -> None:
    construir(f)  # todas usam o TORNO
    antes = estado_global(f)
    resultado = recusada(f.remover_equipamento(TORNO), Recusa.EQUIPAMENTO_COM_OS)
    assert "use Inativar para preservar o histórico" in resultado.mensagem
    assert estado_global(f) == antes


@pytest.mark.cenario("CAR-69")
def test_equipamento_inativado_com_os_continua_com_o_historico_e_nao_e_excluivel(
    f: Fachada,
) -> None:
    numero = os_concluida(f)
    f.inativar_equipamento(TORNO)
    recusada(f.remover_equipamento(TORNO), Recusa.EQUIPAMENTO_COM_OS)
    assert f.ordens_do_equipamento(TORNO) == (numero,)
    assert os_snap(f, numero).equipamento_id == TORNO


# ----------------------------------------------------------------------------------- cargos


@pytest.mark.cenario("CAR-70")
def test_ha_dois_cargos_fixos_na_base_inicial(f: Fachada) -> None:
    assert [(c.id, c.nome) for c in f.cargos()] == [
        (CARGO_GESTOR, "Gestor"),
        (CARGO_TECNICO, "Técnico"),
    ]


@pytest.mark.cenario("CAR-70")
def test_permissoes_do_cargo_sobrevivem_a_gravacao_e_recarga(f: Fachada) -> None:
    f.definir_permissoes_cargo(CARGO_TECNICO, (*PERMISSOES_PADRAO_TECNICO, "atribuir_os"))
    novo = f.cadastrar_usuario("Diego", CARGO_TECNICO, "d@e.com", "Seg")
    equipamento = f.cadastrar_equipamento("Prensa", "P1")
    f.inativar_equipamento(equipamento)
    antes = estado_global(f)
    f.salvar_e_recarregar()
    assert estado_global(f) == antes
    assert f.usuario_pode(novo, "atribuir_os")
