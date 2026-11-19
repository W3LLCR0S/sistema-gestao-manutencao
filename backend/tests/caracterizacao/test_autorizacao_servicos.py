"""Legado e serviços lado a lado nos cenários de autorização.

DLT-12 a DLT-17; CAR-65, 71, 72, 73 e 91 a 93.

Cada teste aplica o **mesmo roteiro** ao legado e aos serviços, com o solicitante sempre explícito
(nunca o alvo, nunca um administrador implícito), e mostra as duas coisas que a regularização da
Operação D exige: o legado **aceitava** a operação e os serviços a **recusam sem alterar o
estado**. Não há ``skip`` nem comparação suprimida: o que difere é exatamente o que cada delta
aprova, e o resto (o estado depois de uma recusa) é conferido igual.

Testes de infraestrutura da caracterização (sem marcador ``cenario``): os cenários CAR-nn que estes
comportamentos caracterizam têm seus testes do legado em ``test_legado_defeitos.py`` e
``test_cadastros.py``.
"""

import pytest

from manutencao.application.erros import NaoEncontradoError
from tests.caracterizacao.cenarios import (
    ANA,
    BRUNO,
    CARGO_GESTOR,
    CARGO_TECNICO,
    CARLA,
    COMPRESSOR,
    PERMISSOES_PADRAO_GESTOR,
    PERMISSOES_PADRAO_TECNICO,
    TORNO,
)
from tests.caracterizacao.fachada import Fachada, FachadaAutorizada, Recusa, Resultado
from tests.caracterizacao.fluxos import (
    aceitar,
    estado_global,
    os_aberta,
    os_atribuida,
    recusada,
)
from tests.caracterizacao.pares import Par

INEXISTENTE = 99


def _sem_permissao_alguma(f: Fachada) -> None:
    f.definir_permissoes_cargo(CARGO_TECNICO, ())
    assert not any(f.usuario_pode(BRUNO, p) for p in PERMISSOES_PADRAO_TECNICO)


# =============================================================================== DLT-12 (CAR-71)


def test_dlt12_o_legado_permite_retirar_o_proprio_acesso_e_os_servicos_recusam(par: Par) -> None:
    # 1. trocar o próprio cargo por um sem gestão
    aceitar(par.legado.alterar_cargo_por(ANA, ANA, CARGO_TECNICO))
    assert not par.legado.usuario_pode(ANA, "gerir_usuarios")
    antes = estado_global(par.servicos)
    resultado = recusada(
        par.servicos.alterar_cargo_por(ANA, ANA, CARGO_TECNICO),
        Recusa.AUTOREMOCAO_DE_ACESSO_DE_GESTAO,
    )
    assert resultado.mensagem == "Você não pode remover o próprio acesso de gestão."
    assert estado_global(par.servicos) == antes
    assert par.servicos.usuario_pode(ANA, "gerir_usuarios")


@pytest.mark.parametrize(
    "permissoes",
    [
        pytest.param((), id="nenhuma"),
        pytest.param(
            tuple(p for p in PERMISSOES_PADRAO_GESTOR if p != "gerir_usuarios"), id="so-sem-gestao"
        ),
    ],
)
def test_dlt12_reduzir_as_permissoes_do_proprio_cargo_o_legado_permite_e_os_servicos_recusam(
    par: Par, permissoes: tuple[str, ...]
) -> None:
    aceitar(par.legado.definir_permissoes_cargo_por(ANA, CARGO_GESTOR, permissoes))
    assert not par.legado.usuario_pode(ANA, "gerir_usuarios")
    antes = estado_global(par.servicos)
    recusada(
        par.servicos.definir_permissoes_cargo_por(ANA, CARGO_GESTOR, permissoes),
        Recusa.AUTOREMOCAO_DE_ACESSO_DE_GESTAO,
    )
    assert estado_global(par.servicos) == antes


def test_dlt12_alteracoes_que_preservam_a_autorizacao_sao_aceitas_nos_dois(par: Par) -> None:
    for f in (par.legado, par.servicos):
        manter = (*PERMISSOES_PADRAO_GESTOR[:2], "gerir_usuarios")
        aceitar(f.definir_permissoes_cargo_por(ANA, CARGO_GESTOR, manter))
        aceitar(f.alterar_cargo_por(ANA, ANA, CARGO_GESTOR))
        assert f.usuario_pode(ANA, "gerir_usuarios")
    assert estado_global(par.legado) == estado_global(par.servicos)


# =============================================================================== DLT-13 (CAR-73)


def test_dlt13_gestao_sem_permissao_o_legado_aceita_e_os_servicos_recusam(par: Par) -> None:
    for f in (par.legado, par.servicos):
        _sem_permissao_alguma(f)
    assert not par.servicos.usuario_pode(BRUNO, "gerir_equipamentos")

    # o legado aceita tudo, sem olhar quem pede
    legado = par.legado
    novo = aceitar(legado.cadastrar_equipamento_por(BRUNO, "Prensa", "P1")).valor
    aceitar(legado.editar_equipamento_por(BRUNO, novo, "Prensa 2", "P2"))
    aceitar(legado.inativar_equipamento_por(BRUNO, novo))
    aceitar(legado.reativar_equipamento_por(BRUNO, novo))
    aceitar(legado.remover_equipamento_por(BRUNO, novo))
    aceitar(legado.cadastrar_usuario_por(BRUNO, "Diego", CARGO_TECNICO))
    aceitar(legado.editar_usuario_por(BRUNO, CARLA, "Carla M."))
    aceitar(legado.alterar_cargo_por(BRUNO, CARLA, CARGO_GESTOR))
    aceitar(legado.definir_permissoes_cargo_por(BRUNO, CARGO_TECNICO, ("ver_os",)))

    # os serviços recusam cada uma por falta de permissão e deixam o estado exatamente igual
    s = par.servicos
    antes = estado_global(s)
    operacoes = (
        s.cadastrar_equipamento_por(BRUNO, "Prensa", "P1"),
        s.editar_equipamento_por(BRUNO, TORNO, "Torno 2", "T2"),
        s.inativar_equipamento_por(BRUNO, TORNO),
        s.reativar_equipamento_por(BRUNO, TORNO),
        s.remover_equipamento_por(BRUNO, COMPRESSOR),
        s.cadastrar_usuario_por(BRUNO, "Diego", CARGO_TECNICO),
        s.editar_usuario_por(BRUNO, CARLA, "Carla M."),
        s.alterar_cargo_por(BRUNO, CARLA, CARGO_GESTOR),
        s.definir_permissoes_cargo_por(BRUNO, CARGO_TECNICO, ("ver_os",)),
    )
    for resultado in operacoes:
        recusada(resultado, Recusa.SEM_PERMISSAO)
    assert estado_global(s) == antes


def test_dlt13_exclusao_de_usuario_sem_permissao_o_legado_aceita_e_os_servicos_recusam(
    par: Par,
) -> None:
    for f in (par.legado, par.servicos):
        diego = f.cadastrar_usuario("Diego", CARGO_TECNICO)
        assert not f.usuario_pode(BRUNO, "gerir_usuarios")
        resultado = f.remover_usuario(diego, BRUNO)
        if f is par.legado:
            aceitar(resultado)
            assert f.usuario(diego) is None
        else:
            recusada(resultado, Recusa.SEM_PERMISSAO)
            assert f.usuario(diego) is not None


def test_dlt13_a_recusa_nao_consome_identificador_e_a_gestao_autorizada_continua_igual(
    par: Par,
) -> None:
    s = par.servicos
    recusada(s.cadastrar_usuario_por(BRUNO, "Diego", CARGO_TECNICO), Recusa.SEM_PERMISSAO)
    recusada(s.cadastrar_equipamento_por(BRUNO, "Prensa", "P1"), Recusa.SEM_PERMISSAO)
    for f in (par.legado, par.servicos):
        assert aceitar(f.cadastrar_usuario_por(ANA, "Diego", CARGO_TECNICO)).valor == 4
        assert aceitar(f.cadastrar_equipamento_por(ANA, "Prensa", "P1")).valor == 4
    assert estado_global(par.legado) == estado_global(par.servicos)


# =============================================================================== DLT-14 (CAR-91)


def _leituras(f: FachadaAutorizada, ator: int, numero: int) -> dict[str, Resultado]:
    return {
        "ver_equipamentos": f.consultar_equipamentos_por(ator),
        "ver_os": f.consultar_os_por(ator, numero),
        "ver_os (lista)": f.listar_os_por(ator),
        "ver_disponibilidade": f.consultar_disponibilidade_por(ator),
        "gerir_usuarios (usuários)": f.consultar_usuarios_por(ator),
        "gerir_usuarios (cargos)": f.listar_cargos_por(ator),
    }


def test_dlt14_o_legado_le_sem_permissao_e_os_servicos_recusam(par: Par) -> None:
    numero = os_aberta(par.legado)  # a OS é preparada antes de retirar as permissões
    assert os_aberta(par.servicos) == numero
    for f in (par.legado, par.servicos):
        _sem_permissao_alguma(f)
    do_legado = _leituras(par.legado, BRUNO, numero)
    assert all(r.aceito for r in do_legado.values())
    dos_servicos = _leituras(par.servicos, BRUNO, numero)
    for nome, resultado in dos_servicos.items():
        recusada(resultado, Recusa.SEM_PERMISSAO)
        assert resultado.valor is None, nome


def test_dlt14_com_as_permissoes_correspondentes_as_leituras_dos_dois_lados_coincidem(
    par: Par,
) -> None:
    numero = os_aberta(par.legado)
    assert os_aberta(par.servicos) == numero
    # Ana (gestora) tem tudo; o técnico padrão só não lê usuários e cargos
    for ator, bloqueadas in (
        (ANA, set()),
        (BRUNO, {"gerir_usuarios (usuários)", "gerir_usuarios (cargos)"}),
    ):
        legado = _leituras(par.legado, ator, numero)
        servicos = _leituras(par.servicos, ator, numero)
        for nome, resultado in servicos.items():
            if nome in bloqueadas:
                recusada(resultado, Recusa.SEM_PERMISSAO)
            else:
                assert resultado.aceito, nome
                if nome != "ver_disponibilidade":  # o valor dos serviços é o DTO de aplicação
                    assert resultado.valor == legado[nome].valor or nome == "ver_os", nome


def test_dlt14_cada_leitura_exige_a_sua_permissao_e_nenhuma_outra(par: Par) -> None:
    numero = os_aberta(par.servicos)
    permissoes = {
        "ver_equipamentos": "ver_equipamentos",
        "ver_os": "ver_os",
        "ver_os (lista)": "ver_os",
        "ver_disponibilidade": "ver_disponibilidade",
        "gerir_usuarios (usuários)": "gerir_usuarios",
        "gerir_usuarios (cargos)": "gerir_usuarios",
    }
    for exigida in set(permissoes.values()):
        par.servicos.definir_permissoes_cargo(CARGO_TECNICO, (exigida,))
        for nome, resultado in _leituras(par.servicos, BRUNO, numero).items():
            if permissoes[nome] == exigida:
                assert resultado.aceito, (exigida, nome)
            else:
                recusada(resultado, Recusa.SEM_PERMISSAO)


# =============================================================================== DLT-15 (CAR-72)


def test_dlt15_alteracao_propria_e_aceita_no_legado_e_nos_servicos(par: Par) -> None:
    for f in (par.legado, par.servicos):
        _sem_permissao_alguma(f)
        aceitar(f.definir_disponibilidade(BRUNO, "Ausente", solicitante=BRUNO))
        bruno = f.usuario(BRUNO)
        assert bruno is not None
        assert bruno.disponibilidade == "Ausente"
    assert estado_global(par.legado) == estado_global(par.servicos)


def test_dlt15_terceiro_por_gestor_autorizado_e_aceito_no_legado_e_nos_servicos(par: Par) -> None:
    for f in (par.legado, par.servicos):
        aceitar(f.definir_disponibilidade(CARLA, "Ausente", solicitante=ANA))
        carla = f.usuario(CARLA)
        assert carla is not None
        assert carla.disponibilidade == "Ausente"
        bruno = f.usuario(BRUNO)
        assert bruno is not None
        assert bruno.disponibilidade == "Disponível"  # só o alvo mudou
    assert estado_global(par.legado) == estado_global(par.servicos)


def test_dlt15_terceiro_sem_autorizacao_o_legado_aceita_e_os_servicos_recusam(par: Par) -> None:
    antes = estado_global(par.servicos)
    for f in (par.legado, par.servicos):
        assert not f.usuario_pode(BRUNO, "gerir_usuarios")
    aceitar(par.legado.definir_disponibilidade(CARLA, "Ausente", solicitante=BRUNO))
    carla_no_legado = par.legado.usuario(CARLA)
    assert carla_no_legado is not None
    assert carla_no_legado.disponibilidade == "Ausente"

    recusada(
        par.servicos.definir_disponibilidade(CARLA, "Ausente", solicitante=BRUNO),
        Recusa.SEM_PERMISSAO,
    )
    assert estado_global(par.servicos) == antes  # nem a Carla, nem o Bruno (o ator) mudaram


def test_dlt15_o_alvo_nao_e_usado_como_ator_implicito(par: Par) -> None:
    """Se o alvo fosse o ator, a alteração de terceiro seria sempre aceita; não é."""
    for ator, alvo in ((BRUNO, CARLA), (CARLA, BRUNO)):
        recusada(
            par.servicos.definir_disponibilidade(alvo, "Ausente", solicitante=ator),
            Recusa.SEM_PERMISSAO,
        )
    nao_encontrado = par.servicos.definir_disponibilidade(INEXISTENTE, "Ausente", solicitante=ANA)
    recusada(nao_encontrado, Recusa.NAO_ENCONTRADO)
    # sem autorização, o alvo inexistente nem chega a ser procurado (DLT-16)
    recusada(
        par.servicos.definir_disponibilidade(INEXISTENTE, "Ausente", solicitante=BRUNO),
        Recusa.SEM_PERMISSAO,
    )


# =============================================================================== DLT-16 (CAR-93)


def test_dlt16_sem_permissao_e_autoexclusao_legado_recusa_pela_regra_e_servicos_por_autorizacao(
    par: Par,
) -> None:
    for f in (par.legado, par.servicos):
        assert not f.usuario_pode(BRUNO, "gerir_usuarios")
    recusada(par.legado.remover_usuario(BRUNO, BRUNO), Recusa.AUTOEXCLUSAO)
    antes = estado_global(par.servicos)
    recusada(par.servicos.remover_usuario(BRUNO, BRUNO), Recusa.SEM_PERMISSAO)
    assert estado_global(par.servicos) == antes


def test_dlt16_sem_permissao_e_historico_legado_recusa_pela_regra_e_servicos_por_autorizacao(
    par: Par,
) -> None:
    for f in (par.legado, par.servicos):
        os_atribuida(f, tecnico=BRUNO)
    recusada(par.legado.remover_usuario(CARLA, BRUNO), Recusa.USUARIO_COM_HISTORICO)
    antes = estado_global(par.servicos)
    for alvo in (CARLA, BRUNO, ANA):
        recusada(par.servicos.remover_usuario(alvo, BRUNO), Recusa.SEM_PERMISSAO)
    assert estado_global(par.servicos) == antes


def test_dlt16_sem_permissao_e_recurso_inexistente_a_autorizacao_vem_primeiro(par: Par) -> None:
    s = par.servicos
    antes = estado_global(s)
    recusada(s.remover_usuario(INEXISTENTE, BRUNO), Recusa.SEM_PERMISSAO)
    recusada(s.remover_equipamento_por(BRUNO, INEXISTENTE), Recusa.SEM_PERMISSAO)
    recusada(s.editar_usuario_por(BRUNO, INEXISTENTE, "x"), Recusa.SEM_PERMISSAO)
    recusada(s.alterar_cargo_por(BRUNO, CARLA, INEXISTENTE), Recusa.SEM_PERMISSAO)
    assert estado_global(s) == antes
    # com permissão, o erro é o do recurso ausente (a precedência não foi invertida)
    recusada(s.remover_usuario(INEXISTENTE, ANA), Recusa.NAO_ENCONTRADO)
    recusada(s.remover_equipamento_por(ANA, INEXISTENTE), Recusa.NAO_ENCONTRADO)


def test_dlt16_com_permissao_a_precedencia_das_regras_de_dominio_e_a_do_legado(par: Par) -> None:
    for f in (par.legado, par.servicos):
        os_atribuida(f, tecnico=BRUNO)
        recusada(f.remover_usuario(ANA, ANA), Recusa.AUTOEXCLUSAO)  # antes do histórico (CAR-64)
        recusada(f.remover_usuario(CARLA, ANA), Recusa.USUARIO_COM_HISTORICO)
    assert estado_global(par.legado) == estado_global(par.servicos)


def test_dlt16_uma_operacao_de_os_sem_permissao_e_recusada_por_autorizacao(par: Par) -> None:
    """OS inexistente não esconde a falta de permissão (e a recusa não gasta número de OS)."""
    s = par.servicos
    antes = estado_global(s)
    recusada(s.aprovar(INEXISTENTE, BRUNO), Recusa.SEM_PERMISSAO)
    recusada(s.atribuir(INEXISTENTE, BRUNO, BRUNO), Recusa.SEM_PERMISSAO)
    recusada(s.cancelar(INEXISTENTE, CARLA, "x"), Recusa.SEM_PERMISSAO)
    recusada(s.aprovar(INEXISTENTE, ANA), Recusa.NAO_ENCONTRADO)
    assert estado_global(s) == antes


# =============================================================================== DLT-17 (CAR-92)


def test_dlt17_ator_inexistente_o_legado_ignora_e_os_servicos_recusam(par: Par) -> None:
    assert par.legado.usuario(INEXISTENTE) is None
    aceitar(par.legado.cadastrar_equipamento_por(INEXISTENTE, "Prensa", "P1"))  # ninguém pergunta

    s = par.servicos
    antes = estado_global(s)
    resultados = (
        s.cadastrar_equipamento_por(INEXISTENTE, "Prensa", "P1"),
        s.cadastrar_usuario_por(INEXISTENTE, "Diego", CARGO_TECNICO),
        s.remover_equipamento_por(INEXISTENTE, COMPRESSOR),
        s.alterar_cargo_por(INEXISTENTE, BRUNO, CARGO_GESTOR),
        s.consultar_equipamentos_por(INEXISTENTE),
        s.consultar_os_por(INEXISTENTE, 1),
        s.listar_os_por(INEXISTENTE),
        s.consultar_disponibilidade_por(INEXISTENTE),
        s.consultar_usuarios_por(INEXISTENTE),
        s.listar_cargos_por(INEXISTENTE),
        s.remover_usuario(BRUNO, INEXISTENTE),
        s.definir_disponibilidade(BRUNO, "Ausente", solicitante=INEXISTENTE),
        s.abrir_os(INEXISTENTE, TORNO, "x", "Baixa"),
        s.aprovar(1, INEXISTENTE),
    )
    for resultado in resultados:
        recusada(resultado, Recusa.NAO_ENCONTRADO)
        assert f"{INEXISTENTE}" in resultado.mensagem
    assert estado_global(s) == antes


def test_dlt17_ator_inexistente_nao_cria_usuario_nem_o_substitui_por_administrador(
    par: Par,
) -> None:
    s = par.servicos
    usuarios = s.usuarios()
    recusada(s.cadastrar_usuario_por(INEXISTENTE, "Intruso", CARGO_GESTOR), Recusa.NAO_ENCONTRADO)
    assert s.usuario(INEXISTENTE) is None
    assert s.usuarios() == usuarios
    # o próximo identificador autorizado continua sendo o 4 (nada foi consumido)
    assert aceitar(s.cadastrar_usuario_por(ANA, "Diego", CARGO_TECNICO)).valor == 4


def test_o_erro_tipado_do_ator_inexistente_e_o_nao_encontrado_da_aplicacao(par: Par) -> None:
    """O adaptador traduz o erro tipado existente; a prova direta está em ``tests/aplicacao``."""
    with pytest.raises(NaoEncontradoError):
        par.servicos._c.servico_usuarios.listar(INEXISTENTE)


# =============================================================================== CAR-65


def test_car65_o_legado_permite_a_tentativa_do_tecnico_e_os_servicos_recusam_por_permissao(
    par: Par,
) -> None:
    """O teste da regra de histórico (CAR-65) passou a usar uma segunda gestora (Eva) como
    solicitante, para exercitar ``USUARIO_COM_HISTORICO`` nos serviços. A tentativa original,
    feita pelo técnico Bruno, é preservada aqui: o legado a aceitava até a regra de histórico; os
    serviços a recusam antes, por falta de permissão (DLT-13 e DLT-16)."""
    for f in (par.legado, par.servicos):
        os_atribuida(f, tecnico=BRUNO)  # aberta por Carla, de Bruno, atribuída por Ana
    for alvo in (CARLA, BRUNO, ANA):
        legado = par.legado.remover_usuario(alvo, BRUNO)
        if alvo == BRUNO:
            recusada(legado, Recusa.AUTOEXCLUSAO)
        else:
            recusada(legado, Recusa.USUARIO_COM_HISTORICO)
    antes = estado_global(par.servicos)
    for alvo in (CARLA, BRUNO, ANA):
        recusada(par.servicos.remover_usuario(alvo, BRUNO), Recusa.SEM_PERMISSAO)
    assert estado_global(par.servicos) == antes


def test_car65_com_uma_segunda_gestora_a_regra_de_historico_e_a_mesma_nos_dois(par: Par) -> None:
    for f in (par.legado, par.servicos):
        os_atribuida(f, tecnico=BRUNO)
        eva = f.cadastrar_usuario("Eva", CARGO_GESTOR)
        for alvo in (CARLA, BRUNO, ANA):
            resultado = recusada(f.remover_usuario(alvo, eva), Recusa.USUARIO_COM_HISTORICO)
            assert resultado.mensagem == "Usuário possui histórico em OS; não pode ser excluído."
    assert estado_global(par.legado) == estado_global(par.servicos)
