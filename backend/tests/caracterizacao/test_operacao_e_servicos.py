"""Legado e serviços lado a lado nas regras de negócio da Operação E (DLT-01 a DLT-06, 08 e 09).

Cada teste aplica o **mesmo roteiro** ao legado e aos serviços e mostra as três coisas que a
implementação de um delta exige: o legado **aceitava** (ou calculava de outro modo) o que a decisão
aprovada muda; os serviços **recusam ou calculam o novo** sem alterar o estado numa recusa; e
**o que não muda é idêntico** nos dois (resultado, mensagem e estado). Nenhum ``skip`` e nenhuma
comparação suprimida: a tabela das diferenças por estado e operação está em ``divergencias.py``.

Testes de infraestrutura da caracterização (sem marcador ``cenario``): os cenários CAR-nn que estes
comportamentos caracterizam têm seus testes do legado em ``test_atribuicao.py``,
``test_observacao.py``, ``test_disponibilidade.py``, ``test_tecnico.py``, ``test_permissoes.py``,
``test_cadastros.py`` e ``test_legado_defeitos.py``.
"""

from dataclasses import replace

from tests.caracterizacao.adaptador_servicos import AdaptadorServicos
from tests.caracterizacao.cenarios import (
    ALTA,
    ANA,
    AUSENTE,
    BAIXA,
    BRUNO,
    CARGO_GESTOR,
    CARGO_TECNICO,
    CARLA,
    DISPONIVEL,
    EM_ATENDIMENTO,
    PERMISSOES_PADRAO_GESTOR,
    PERMISSOES_PADRAO_TECNICO,
    STATUS_AGUARDANDO_PECA,
    STATUS_ATRIBUIDA,
    STATUS_REPARO_FINALIZADO,
    TORNO,
)
from tests.caracterizacao.fachada import Fachada, Peca, Recusa
from tests.caracterizacao.fluxos import (
    aceitar,
    estado_global,
    os_aberta,
    os_atribuida,
    os_cancelada,
    os_concluida,
    os_em_execucao,
    os_snap,
    recusada,
)
from tests.caracterizacao.pares import Par


def _disp(f: Fachada, usuario: int) -> str:
    snap = f.usuario(usuario)
    assert snap is not None
    return snap.disponibilidade


def _servicos(par: Par) -> AdaptadorServicos:
    return par.servicos


# =========================================================================================
# DLT-01 — papéis Gestor e Técnico (D-02)
# =========================================================================================


def test_dlt01_retirar_apontar_reparo_tira_o_tecnico_da_lista_no_legado_e_nao_nos_servicos(
    par: Par,
) -> None:
    permissoes = tuple(p for p in PERMISSOES_PADRAO_TECNICO if p != "apontar_reparo")
    for f in (par.legado, par.servicos):
        f.definir_permissoes_cargo(CARGO_TECNICO, permissoes)
    assert par.legado.tecnicos() == ()  # AUD-20: a identidade de técnico era a permissão
    assert par.servicos.tecnicos() == (BRUNO, CARLA)
    numero_legado = os_aberta(par.legado, solicitante=ANA)
    numero_servicos = os_aberta(par.servicos, solicitante=ANA)
    recusada(par.legado.atribuir(numero_legado, BRUNO, ANA), Recusa.NAO_E_TECNICO)
    aceitar(par.servicos.atribuir(numero_servicos, BRUNO, ANA))  # continua atribuível
    # ...mas é negado ao apontar: a permissão continua valendo (no legado o técnico nem recebe a OS)
    recusada(
        par.servicos.apontar_reparo(numero_servicos, BRUNO, 1.0, "Troca"), Recusa.SEM_PERMISSAO
    )


def test_dlt01_conceder_apontar_reparo_ao_gestor_o_torna_atribuivel_no_legado_e_nao_nos_servicos(
    par: Par,
) -> None:
    permissoes = (*PERMISSOES_PADRAO_GESTOR, "apontar_reparo")
    for f in (par.legado, par.servicos):
        f.definir_permissoes_cargo(CARGO_GESTOR, permissoes)
    assert ANA in par.legado.tecnicos()  # AUD-20
    assert ANA not in par.servicos.tecnicos()
    numero_legado = os_aberta(par.legado, solicitante=ANA)
    numero_servicos = os_aberta(par.servicos, solicitante=ANA)
    aceitar(par.legado.atribuir(numero_legado, ANA, ANA))
    recusada(par.servicos.atribuir(numero_servicos, ANA, ANA), Recusa.NAO_E_TECNICO)
    assert os_snap(par.servicos, numero_servicos).tecnico_id is None  # nada mudou


def test_dlt01_mudar_o_cargo_move_o_usuario_no_legado_e_so_as_permissoes_nos_servicos(
    par: Par,
) -> None:
    for f in (par.legado, par.servicos):
        f.editar_usuario(CARLA, cargo=CARGO_GESTOR)
    assert par.legado.tecnicos() == (BRUNO,)
    assert par.servicos.tecnicos() == (BRUNO, CARLA)  # o papel não acompanha o cargo
    assert par.legado.usuario(CARLA) == par.servicos.usuario(CARLA)  # o cargo mudou nos dois
    assert par.servicos.usuario_pode(CARLA, "aprovar_os")  # e as permissões vieram do novo cargo


def test_dlt01_o_que_nao_depende_do_papel_e_igual_nos_dois(par: Par) -> None:
    assert par.legado.tecnicos() == par.servicos.tecnicos() == (BRUNO, CARLA)
    for f in (par.legado, par.servicos):
        numero = os_atribuida(f)
        recusada(f.atribuir(numero, ANA, ANA), Recusa.NAO_E_TECNICO)  # gestor não é técnico
        recusada(f.atribuir(numero, BRUNO, ANA), Recusa.JA_ATRIBUIDA)
        aceitar(f.atribuir(numero, CARLA, ANA))
    assert estado_global(par.legado) == estado_global(par.servicos)


# =========================================================================================
# DLT-02 — atribuição a técnico ausente (D-03)
# =========================================================================================


def test_dlt02_atribuir_a_tecnico_ausente_o_legado_aceita_e_os_servicos_recusam(par: Par) -> None:
    for f in (par.legado, par.servicos):
        aceitar(f.definir_disponibilidade(BRUNO, AUSENTE, solicitante=BRUNO))
    numero_legado = os_aberta(par.legado)
    numero_servicos = os_aberta(par.servicos)
    aceitar(par.legado.atribuir(numero_legado, BRUNO, ANA))
    assert os_snap(par.legado, numero_legado).historico[1].descricao == "Atribuída a Bruno Lima"
    antes = estado_global(par.servicos)
    resultado = recusada(par.servicos.atribuir(numero_servicos, BRUNO, ANA), Recusa.TECNICO_AUSENTE)
    assert "ausente" in resultado.mensagem
    assert estado_global(par.servicos) == antes
    assert os_snap(par.servicos, numero_servicos).status == "Aberta"


def test_dlt02_com_confirmacao_os_servicos_aceitam_e_registram_a_ausencia_no_historico(
    par: Par,
) -> None:
    for f in (par.legado, par.servicos):
        aceitar(f.definir_disponibilidade(BRUNO, AUSENTE, solicitante=BRUNO))
    numero_legado = os_aberta(par.legado)
    numero_servicos = os_aberta(par.servicos)
    aceitar(par.legado.atribuir(numero_legado, BRUNO, ANA))
    _servicos(par)._c.servico_ordens.atribuir(ANA, numero_servicos, BRUNO, confirmar_ausente=True)
    do_legado = os_snap(par.legado, numero_legado)
    dos_servicos = os_snap(par.servicos, numero_servicos)
    assert "técnico ausente" in dos_servicos.historico[1].descricao
    # a única diferença é o texto do registro de atribuição
    normalizado = replace(
        dos_servicos,
        historico=(
            dos_servicos.historico[0],
            replace(dos_servicos.historico[1], descricao=do_legado.historico[1].descricao),
            *dos_servicos.historico[2:],
        ),
    )
    assert normalizado == do_legado
    assert _disp(par.servicos, BRUNO) == AUSENTE  # a ausência segue registrada


def test_dlt02_tecnico_presente_e_igual_nos_dois(par: Par) -> None:
    for f in (par.legado, par.servicos):
        numero = os_aberta(f)
        aceitar(f.atribuir(numero, BRUNO, ANA))
    assert estado_global(par.legado) == estado_global(par.servicos)


# =========================================================================================
# DLT-03 e DLT-04 — observações (D-04)
# =========================================================================================


def test_dlt03_observacao_em_os_encerrada_o_legado_aceita_e_os_servicos_recusam(par: Par) -> None:
    for construir in (os_concluida, lambda f: os_cancelada(f, atribuida=True)):
        numero_legado = construir(par.legado)
        numero_servicos = construir(par.servicos)
        aceitar(par.legado.adicionar_observacao(numero_legado, CARLA, "Comentário tardio"))
        antes = estado_global(par.servicos)
        recusada(
            par.servicos.adicionar_observacao(numero_servicos, CARLA, "Comentário tardio"),
            Recusa.OS_ENCERRADA,
        )
        assert estado_global(par.servicos) == antes


def test_dlt04_observacao_de_terceiro_o_legado_aceita_e_os_servicos_recusam(par: Par) -> None:
    for f in (par.legado, par.servicos):
        numero = os_atribuida(f, tecnico=BRUNO)  # aberta por Carla, de Bruno
        f.cadastrar_usuario("Diego", CARGO_TECNICO)  # sem relação com a OS (id 4)
        if f is par.legado:
            aceitar(f.adicionar_observacao(numero, 4, "Passando por aqui"))
        else:
            antes = estado_global(f)
            recusada(
                f.adicionar_observacao(numero, 4, "Passando por aqui"), Recusa.SEM_VINCULO_COM_A_OS
            )
            assert estado_global(f) == antes


def test_dlt04_gestor_responsavel_e_autor_da_abertura_observam_igual_nos_dois(par: Par) -> None:
    for f in (par.legado, par.servicos):
        numero = os_atribuida(f, tecnico=BRUNO)
        for autor in (ANA, BRUNO, CARLA):
            aceitar(f.adicionar_observacao(numero, autor, f"nota {autor}"))
    assert estado_global(par.legado) == estado_global(par.servicos)


# =========================================================================================
# DLT-05 — disponibilidade derivada (D-05)
# =========================================================================================


def test_dlt05_o_legado_so_atualiza_apos_a_rotina_e_os_servicos_derivam_na_hora(
    par: Par,
) -> None:
    for f in (par.legado, par.servicos):
        numero = os_em_execucao(f, tecnico=BRUNO)
    # cenário 3: Em Execução
    assert _disp(par.legado, BRUNO) == DISPONIVEL  # desatualizado até a rotina (AUD-13)
    assert _disp(par.servicos, BRUNO) == EM_ATENDIMENTO
    # cenário 7: ausência removida
    for f in (par.legado, par.servicos):
        aceitar(f.definir_disponibilidade(BRUNO, AUSENTE, solicitante=BRUNO))
        f.atualizar_disponibilidades()
    assert (_disp(par.legado, BRUNO), _disp(par.servicos, BRUNO)) == (AUSENTE, AUSENTE)  # nº 6
    for f in (par.legado, par.servicos):
        aceitar(f.definir_disponibilidade(BRUNO, DISPONIVEL, solicitante=BRUNO))
    assert _disp(par.legado, BRUNO) == DISPONIVEL  # o legado só recalcula depois
    assert _disp(par.servicos, BRUNO) == EM_ATENDIMENTO
    # cenário 8: Em Execução -> Aguardando Peça
    for f in (par.legado, par.servicos):
        aceitar(f.alterar_status(numero, BRUNO, STATUS_AGUARDANDO_PECA))
    assert _disp(par.servicos, BRUNO) == DISPONIVEL  # "Aguardando Peça" não é atendimento
    # cenário 9: reatribuição, com a OS de volta em execução
    for f in (par.legado, par.servicos):
        aceitar(f.alterar_status(numero, BRUNO, "Em Execução"))
        aceitar(f.atribuir(numero, CARLA, ANA))
    assert (_disp(par.servicos, BRUNO), _disp(par.servicos, CARLA)) == (
        DISPONIVEL,
        EM_ATENDIMENTO,
    )
    assert (_disp(par.legado, BRUNO), _disp(par.legado, CARLA)) == (DISPONIVEL, DISPONIVEL)


def test_dlt05_depois_da_rotina_do_legado_os_dois_mostram_o_mesmo_valor(par: Par) -> None:
    for f in (par.legado, par.servicos):
        os_em_execucao(f, tecnico=BRUNO)
        os_atribuida(f, tecnico=CARLA)
        f.atualizar_disponibilidades()
    # o valor manual "Em atendimento" só o legado aceita (REG-E-06, DLT-23): os serviços o recusam
    aceitar(par.legado.definir_disponibilidade(ANA, EM_ATENDIMENTO, solicitante=ANA))
    recusada(
        par.servicos.definir_disponibilidade(ANA, EM_ATENDIMENTO, solicitante=ANA),
        Recusa.DISPONIBILIDADE_MANUAL_INVALIDA,
    )
    for tecnico in (BRUNO, CARLA):
        assert _disp(par.legado, tecnico) == _disp(par.servicos, tecnico)
    assert [_disp(par.servicos, u) for u in (BRUNO, CARLA)] == [EM_ATENDIMENTO, DISPONIVEL]
    # a única diferença é a do valor manual de quem não é técnico: o legado o guarda (a rotina só
    # recalcula técnicos, CAR-52); os serviços mostram sempre o derivado das OS
    assert (_disp(par.legado, ANA), _disp(par.servicos, ANA)) == (EM_ATENDIMENTO, DISPONIVEL)


# =========================================================================================
# DLT-06 — diagnóstico obrigatório (D-06)
# =========================================================================================


def test_dlt06_finalizar_sem_diagnostico_o_legado_aceita_e_os_servicos_recusam(par: Par) -> None:
    for f in (par.legado, par.servicos):
        numero = os_atribuida(f)
        aceitar(f.apontar_reparo(numero, BRUNO, 1.0, "Troca"))
    aceitar(par.legado.alterar_status(1, BRUNO, STATUS_REPARO_FINALIZADO))
    assert os_snap(par.legado, 1).diagnostico == ""  # AUD-21: finalizado sem diagnóstico
    antes = estado_global(par.servicos)
    resultado = recusada(
        par.servicos.alterar_status(1, BRUNO, STATUS_REPARO_FINALIZADO), Recusa.SEM_DIAGNOSTICO
    )
    assert "diagnóstico" in resultado.mensagem
    assert estado_global(par.servicos) == antes
    assert os_snap(par.servicos, 1).status == "Em Execução"


def test_dlt06_com_diagnostico_o_resultado_e_o_estado_sao_iguais_nos_dois(par: Par) -> None:
    for f in (par.legado, par.servicos):
        numero = os_atribuida(f)
        aceitar(f.registrar_diagnostico(numero, BRUNO, "Rolamento gasto", "Falta de graxa"))
        aceitar(f.apontar_reparo(numero, BRUNO, 1.0, "Troca"))
        aceitar(f.alterar_status(numero, BRUNO, STATUS_REPARO_FINALIZADO))
        aceitar(f.concluir_tecnicamente(numero, BRUNO, "Funcionou", True))
        aceitar(f.aprovar(numero, ANA))
    assert estado_global(par.legado) == estado_global(par.servicos)


def test_dlt06_a_falta_de_intervencao_continua_com_a_mesma_recusa_nos_dois(par: Par) -> None:
    for f in (par.legado, par.servicos):
        numero = os_atribuida(f)
        recusada(f.alterar_status(numero, BRUNO, STATUS_REPARO_FINALIZADO), Recusa.SEM_INTERVENCAO)
    assert estado_global(par.legado) == estado_global(par.servicos)
    assert os_snap(par.servicos, 1).status == STATUS_ATRIBUIDA


# =========================================================================================
# DLT-08 — campos obrigatórios e horas maiores que zero
# =========================================================================================


def test_dlt08_textos_vazios_e_zero_hora_o_legado_aceita_e_os_servicos_recusam(par: Par) -> None:
    for f in (par.legado, par.servicos):
        numero = os_atribuida(f)
        antes = estado_global(f)
        resultados = (
            f.abrir_os(CARLA, TORNO, "   ", BAIXA),
            f.registrar_diagnostico(numero, BRUNO, "", "causa"),
            f.apontar_reparo(numero, BRUNO, 0.0, "Troca", (Peca("Rolamento", 1),)),
            f.apontar_reparo(numero, BRUNO, 1.0, "", ()),
            f.cancelar(numero, ANA, ""),
        )
        if f is par.servicos:
            assert [r.recusa for r in resultados] == [
                Recusa.CAMPO_OBRIGATORIO,
                Recusa.CAMPO_OBRIGATORIO,
                Recusa.HORAS_NAO_POSITIVAS,
                Recusa.CAMPO_OBRIGATORIO,
                Recusa.CAMPO_OBRIGATORIO,
            ]
            assert estado_global(f) == antes  # nenhuma recusa alterou nada
        else:
            assert all(r.aceito for r in resultados)  # o legado aceitava todas


def test_dlt08_com_valores_validos_o_resultado_e_o_estado_sao_iguais_nos_dois(par: Par) -> None:
    for f in (par.legado, par.servicos):
        numero = aceitar(f.abrir_os(CARLA, TORNO, "Falha real", ALTA)).valor
        aceitar(f.atribuir(numero, BRUNO, ANA))
        aceitar(f.registrar_diagnostico(numero, BRUNO, "Parecer", "Causa"))
        aceitar(f.apontar_reparo(numero, BRUNO, 0.25, "Troca", (Peca("Rolamento", 2),)))
        aceitar(f.cancelar(numero, ANA, "Sem solução"))
    assert estado_global(par.legado) == estado_global(par.servicos)


def test_dlt08_horas_negativas_e_quantidade_de_peca_continuam_iguais_nos_dois(par: Par) -> None:
    for f in (par.legado, par.servicos):
        numero = os_atribuida(f)
        horas = recusada(f.apontar_reparo(numero, BRUNO, -1.0, "i"), Recusa.HORAS_NEGATIVAS)
        peca = recusada(
            f.apontar_reparo(numero, BRUNO, 1.0, "i", (Peca("x", 0),)), Recusa.QUANTIDADE_INVALIDA
        )
        assert horas.mensagem == "Horas trabalhadas não podem ser negativas."
        assert peca.mensagem == "A quantidade deve ser maior que zero."
    assert estado_global(par.legado) == estado_global(par.servicos)


# =========================================================================================
# DLT-09 — usuário ativo ou inativo
# =========================================================================================


def test_dlt09_o_legado_nao_tem_o_conceito_de_ativo_e_so_exclui_quem_nao_tem_historico(
    par: Par,
) -> None:
    os_atribuida(par.legado, tecnico=BRUNO)
    snap = par.legado.usuario(BRUNO)
    assert snap is not None
    assert not hasattr(snap, "ativo")  # não há como desativar: só excluir
    recusada(par.legado.remover_usuario(BRUNO, ANA), Recusa.USUARIO_COM_HISTORICO)
    diego = par.legado.cadastrar_usuario("Diego", CARGO_TECNICO)
    aceitar(par.legado.remover_usuario(diego, ANA))  # sem histórico, é excluído (e some)
    assert par.legado.usuario(diego) is None


def test_dlt09_nos_servicos_o_usuario_com_historico_e_desativado_sem_perder_a_referencia(
    par: Par,
) -> None:
    os_cancelada(par.servicos, atribuida=True, tecnico=BRUNO)  # histórico, sem OS ativa (REG-E-04)
    servicos = _servicos(par)._c
    recusada(
        par.servicos.remover_usuario(BRUNO, ANA), Recusa.USUARIO_COM_HISTORICO
    )  # igual ao legado
    servicos.servico_usuarios.desativar(ANA, BRUNO)
    bruno = servicos.usuarios.obter(BRUNO)
    assert bruno is not None
    assert bruno.ativo is False
    assert par.servicos.usuario(BRUNO) is not None  # a referência histórica continua
    assert os_snap(par.servicos, 1).tecnico_id == BRUNO  # sem reatribuição automática
    assert par.servicos.tecnicos() == (CARLA,)  # mas já não é atribuível
    numero = os_aberta(par.servicos)
    antes = estado_global(par.servicos)
    resultado = par.servicos.atribuir(numero, BRUNO, ANA)
    assert (resultado.aceito, resultado.recusa) == (False, Recusa.USUARIO_INATIVO)
    assert estado_global(par.servicos) == antes
    resultado = par.servicos.abrir_os(BRUNO, TORNO, "x", BAIXA)  # inativo não opera
    assert (resultado.aceito, resultado.recusa) == (False, Recusa.USUARIO_INATIVO)


def test_dlt09_sem_desativacao_as_os_sao_iguais_nos_dois(par: Par) -> None:
    """Usuários ativos (todos, no legado): o histórico das OS é o mesmo nos dois."""
    for f in (par.legado, par.servicos):
        numero = os_atribuida(f, tecnico=BRUNO)
        aceitar(f.apontar_reparo(numero, BRUNO, 1.0, "Troca"))
    assert par.legado.todas_as_os() == par.servicos.todas_as_os()
