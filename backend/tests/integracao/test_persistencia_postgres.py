"""Persistência real: sobrevive ao reinício, preserva histórico e identificadores, é transacional.

"Reinício" aqui é descartar o ``Banco`` (engine e pool) e todo o contêiner e montar outros do zero
sobre o mesmo PostgreSQL: nada do que o teste verifica pode vir de memória do processo.
"""

import threading
from collections.abc import Callable, Iterator

import pytest
from sqlalchemy.engine import URL

from manutencao.application.erros import (
    IdentificadorJaEmitidoError,
    NaoEncontradoError,
    RegraDeAplicacaoError,
)
from manutencao.application.portas.repositorios import FiltroDeOrdens
from manutencao.composicao.container import Container
from manutencao.composicao.demonstracao import (
    BancoNaoVazioError,
    ResumoDaDemonstracao,
    semear_demonstracao,
)
from manutencao.composicao.fabrica import criar_container_em_memoria, criar_container_postgres
from manutencao.domain.cargo import Cargo
from manutencao.domain.enums import Criticidade, Disponibilidade, Papel, StatusOS, TipoServico
from manutencao.domain.equipamento import Equipamento
from manutencao.domain.ordem_servico import OrdemServico
from manutencao.domain.permissoes import Permissao, Permissoes
from manutencao.domain.servico import Servico
from manutencao.domain.usuario import Usuario
from manutencao.infrastructure.postgres import Banco
from tests.apoio.relogio import RelogioFixo

Reiniciar = Callable[[], Container]


@pytest.fixture
def reiniciar(banco_limpo: Banco, url_do_banco_de_teste: URL) -> Iterator[Reiniciar]:
    """Devolve um contêiner **novo** sobre o mesmo banco a cada chamada (simula o reinício)."""
    abertos: list[Banco] = []

    def novo() -> Container:
        banco = Banco(url_do_banco_de_teste)
        abertos.append(banco)
        return criar_container_postgres(banco, relogio=RelogioFixo())

    yield novo
    for banco in abertos:
        banco.encerrar()


def _retrato(ordem: OrdemServico) -> dict[str, object]:
    """Tudo o que se observa de uma OS, em valores comparáveis."""
    tecnico = ordem.tecnico_atribuido
    return {
        "numero": ordem.numero,
        "equipamento": (ordem.equipamento.id, ordem.equipamento.nome, ordem.equipamento.ativo),
        "falha": ordem.falha,
        "criticidade": ordem.criticidade,
        "aberta_por": (ordem.aberta_por.id, ordem.aberta_por.nome),
        "data_abertura": ordem.data_abertura,
        "status": ordem.status,
        "tecnico": None if tecnico is None else (tecnico.id, tecnico.nome),
        "diagnostico": (ordem.diagnostico, ordem.causa_raiz),
        "horas": ordem.horas_trabalhadas,
        "intervencoes": ordem.intervencoes_realizadas,
        "pecas": tuple((p.descricao, p.quantidade) for p in ordem.pecas_utilizadas),
        "teste": ordem.teste_funcional,
        "motivo_cancelamento": ordem.motivo_cancelamento,
        "data_conclusao": ordem.data_conclusao,
        "historico": tuple(
            (
                s.numero,
                s.tipo,
                s.descricao,
                None if s.responsavel is None else s.responsavel.id,
                s.data,
                s.horas,
                tuple((p.descricao, p.quantidade) for p in s.pecas),
            )
            for s in ordem.servicos
        ),
    }


def _retratos(c: Container) -> list[dict[str, object]]:
    return [_retrato(o) for o in c.ordens.listar()]


def _cadastros(c: Container) -> dict[str, object]:
    return {
        "cargos": [(x.id, x.nome, x.permissoes.ativas()) for x in c.cargos.listar()],
        "usuarios": [
            (u.id, u.nome, u.cargo.id, u.email, u.escala, u.disponibilidade, u.papel, u.ativo)
            for u in c.usuarios.listar()
        ],
        "equipamentos": [(e.id, e.nome, e.modelo, e.ativo) for e in c.equipamentos.listar()],
    }


# ------------------------------------------------------------------------ sobrevive ao reinício
def test_a_demonstracao_sobrevive_ao_reinicio_com_historico_e_relacionamentos(
    reiniciar: Reiniciar,
) -> None:
    antes = reiniciar()
    resumo = semear_demonstracao(antes)
    assert resumo == ResumoDaDemonstracao(cargos=2, usuarios=3, equipamentos=3, ordens=5)
    cadastros, retratos = _cadastros(antes), _retratos(antes)

    depois = reiniciar()  # contêiner e conexões novos: nada vem da memória do processo
    assert _cadastros(depois) == cadastros
    assert _retratos(depois) == retratos
    assert len(retratos) == 5
    # histórico, peças e horas preservados na OS concluída (a 4ª) e na em execução (a 3ª)
    concluida = depois.ordens.obter(4)
    assert concluida is not None
    assert concluida.status is StatusOS.CONCLUIDA
    assert [s.tipo for s in concluida.servicos][:2] == [
        TipoServico.ABERTURA,
        TipoServico.ATRIBUICAO,
    ]
    assert concluida.horas_trabalhadas == 1.5
    assert [(p.descricao, p.quantidade) for p in concluida.pecas_utilizadas] == [
        ("Rolamento 6205", 2),
        ("Graxa (kg)", 0.2),
    ]
    assert concluida.data_conclusao is not None
    em_execucao = depois.ordens.obter(3)
    assert em_execucao is not None
    assert em_execucao.status is StatusOS.EM_EXECUCAO
    assert em_execucao.tecnico_atribuido is not None
    assert em_execucao.tecnico_atribuido.nome == "Carla Mendes"


def test_filtros_e_participacao_valem_depois_do_reinicio(reiniciar: Reiniciar) -> None:
    semear_demonstracao(reiniciar())
    c = reiniciar()
    assert c.ordens.contar(FiltroDeOrdens(encerrada=True)) == 2  # concluída e cancelada
    assert c.ordens.contar(FiltroDeOrdens(encerrada=False)) == 3
    assert [o.numero for o in c.ordens.listar(FiltroDeOrdens(tecnico_id=2))] == [2, 4]
    assert c.ordens.usuario_tem_participacao(1)  # Ana abriu e aprovou
    assert not c.ordens.usuario_tem_participacao(99)


def test_a_operacao_continua_de_onde_parou_apos_o_reinicio(reiniciar: Reiniciar) -> None:
    antes = reiniciar()
    semear_demonstracao(antes)
    depois = reiniciar()
    # a OS 3 (em execução) é finalizada e aprovada por um contêiner que nunca a viu em memória
    depois.servico_ordens.alterar_status(3, 3, StatusOS.REPARO_FINALIZADO)
    depois.servico_ordens.concluir_tecnicamente(3, 3, "Carga estável por 1 h", True)
    depois.servico_ordens.aprovar(1, 3)
    de_novo = reiniciar()
    ordem = de_novo.ordens.obter(3)
    assert ordem is not None
    assert ordem.status is StatusOS.CONCLUIDA
    assert ordem.servicos[-1].tipo is TipoServico.MUDANCA_STATUS
    assert len(ordem.servicos) > 6


def test_a_semente_so_roda_em_banco_vazio(reiniciar: Reiniciar) -> None:
    c = reiniciar()
    semear_demonstracao(c)
    with pytest.raises(BancoNaoVazioError):
        semear_demonstracao(reiniciar())
    assert reiniciar().ordens.contar() == 5  # nada foi duplicado


# ------------------------------------------------------------------------------ identificadores
def test_identificadores_nao_sao_reutilizados_nem_apos_exclusao_e_reinicio(
    reiniciar: Reiniciar,
) -> None:
    c = reiniciar()
    semear_demonstracao(c)
    assert c.equipamentos.proximo_id() == 4
    with pytest.raises(RegraDeAplicacaoError):  # o equipamento 3 tem OS: a regra vale com o banco
        c.servico_equipamentos.excluir(1, 3)
    prensa = c.servico_equipamentos.cadastrar(1, "Prensa", "P1")  # id 4, sem OS
    c.servico_equipamentos.excluir(1, prensa.id)
    novo = reiniciar()
    assert novo.equipamentos.obter(4) is None
    assert novo.equipamentos.proximo_id() == 5  # a sequência não recuou para 4
    assert novo.servico_equipamentos.cadastrar(1, "Serra", "S1").id == 5
    assert [e.id for e in reiniciar().equipamentos.listar()] == [1, 2, 3, 5]


def test_proximos_numeros_de_os_continuam_apos_o_reinicio(reiniciar: Reiniciar) -> None:
    semear_demonstracao(reiniciar())
    c = reiniciar()
    assert c.ordens.proximo_numero() == 6
    nova = c.servico_ordens.abrir(1, 1, "Falha nova", Criticidade.BAIXA)
    assert nova.numero == 6
    assert reiniciar().ordens.proximo_numero() == 7


def test_id_ja_emitido_e_recusado_mesmo_depois_de_excluir(reiniciar: Reiniciar) -> None:
    c = reiniciar()
    c.equipamentos.adicionar(Equipamento(5, "A", "m"))
    c.equipamentos.remover(5)
    with pytest.raises(IdentificadorJaEmitidoError):
        reiniciar().equipamentos.adicionar(Equipamento(5, "B", "m"))


def test_emissoes_concorrentes_do_mesmo_id_so_deixam_uma_vencer(
    banco_limpo: Banco,
) -> None:
    """Quatro fluxos tentam emitir o mesmo identificador: exatamente um consegue."""
    c = criar_container_postgres(banco_limpo)
    resultados: list[str] = []
    trava = threading.Lock()
    largada = threading.Barrier(4)

    def tentar(indice: int) -> None:
        largada.wait()
        try:
            c.equipamentos.adicionar(Equipamento(7, f"E{indice}", "m"))
            situacao = "ok"
        except IdentificadorJaEmitidoError:
            situacao = "recusado"
        with trava:
            resultados.append(situacao)

    fios = [threading.Thread(target=tentar, args=(i,)) for i in range(4)]
    for fio in fios:
        fio.start()
    for fio in fios:
        fio.join()
    assert sorted(resultados) == ["ok", "recusado", "recusado", "recusado"]
    assert len(c.equipamentos.listar()) == 1


# ------------------------------------------------------------------------------ transações
def test_falha_ao_gravar_o_historico_desfaz_a_os_inteira_e_a_sequencia(
    reiniciar: Reiniciar,
) -> None:
    c = reiniciar()
    semear_demonstracao(c)
    ordem = c.ordens.obter(1)
    assert ordem is not None
    # Um registro com horas negativas viola o CHECK do banco **depois** de a OS ter sido gravada.
    invalida = OrdemServico.restaurar(
        numero=6,
        equipamento=ordem.equipamento,
        falha="x",
        criticidade=Criticidade.BAIXA,
        aberta_por=ordem.aberta_por,
        data_abertura=ordem.data_abertura,
        status=StatusOS.ABERTA,
        tecnico_atribuido=None,
        diagnostico="",
        causa_raiz="",
        teste_funcional="",
        motivo_cancelamento="",
        data_conclusao=None,
        servicos=[
            Servico(1, TipoServico.ABERTURA, "x", ordem.aberta_por, ordem.data_abertura, horas=-1)
        ],
    )
    with pytest.raises(Exception, match="horas_nao_negativas"):
        c.ordens.adicionar(invalida)
    novo = reiniciar()
    assert novo.ordens.obter(6) is None  # nada ficou pela metade
    assert novo.ordens.proximo_numero() == 6  # e o número não foi gasto


def test_transacao_externa_junta_varios_repositorios_e_desfaz_tudo_se_falhar(
    banco_limpo: Banco,
) -> None:
    c = criar_container_postgres(banco_limpo)

    def gravar_e_falhar() -> None:
        with banco_limpo.transacao():
            c.equipamentos.adicionar(Equipamento(1, "Torno", "m"))
            c.cargos.adicionar(Cargo(1, "Gestor", Permissoes.padrao_gestor()))
            raise RuntimeError("falhou no meio")

    with pytest.raises(RuntimeError, match="falhou"):
        gravar_e_falhar()
    assert c.equipamentos.listar() == ()
    assert c.cargos.listar() == ()
    assert c.equipamentos.proximo_id() == 1  # sequências também voltaram

    with banco_limpo.transacao():
        c.equipamentos.adicionar(Equipamento(1, "Torno", "m"))
        c.cargos.adicionar(Cargo(1, "Gestor", Permissoes.padrao_gestor()))
    assert len(c.equipamentos.listar()) == 1
    assert len(c.cargos.listar()) == 1


def test_operacao_recusada_nao_deixa_rastro(reiniciar: Reiniciar) -> None:
    c = reiniciar()
    semear_demonstracao(c)
    antes = _retratos(c)
    with pytest.raises(NaoEncontradoError):
        c.servico_ordens.atribuir(1, 1, 99)  # técnico inexistente
    with pytest.raises(Exception, match="Campo obrigatório"):
        c.servico_ordens.abrir(1, 1, "   ", Criticidade.BAIXA)  # falha em branco (DLT-08)
    assert _retratos(reiniciar()) == antes
    assert reiniciar().ordens.proximo_numero() == 6


# ------------------------------------------------------------------------- cadastros e regras
def test_cargo_usuario_e_equipamento_persistem_todos_os_campos(reiniciar: Reiniciar) -> None:
    c = reiniciar()
    cargo = Cargo(1, "Supervisor", Permissoes([Permissao.VER_OS, Permissao.APROVAR_OS]))
    c.cargos.adicionar(cargo)
    c.usuarios.adicionar(
        Usuario(
            1,
            "Dora Ávila",
            cargo,
            "dora@x.com",
            "Seg-Sex",
            Disponibilidade.AUSENTE,
            papel=Papel.GESTOR,
            ativo=False,
        )
    )
    c.equipamentos.adicionar(Equipamento(1, "Fresa ção", "ÇÃO-1", ativo=False))
    novo = reiniciar()
    usuario = novo.usuarios.obter(1)
    assert usuario is not None
    assert (usuario.nome, usuario.email, usuario.escala) == ("Dora Ávila", "dora@x.com", "Seg-Sex")
    assert (usuario.disponibilidade, usuario.papel, usuario.ativo) == (
        Disponibilidade.AUSENTE,
        Papel.GESTOR,
        False,
    )
    assert usuario.cargo.permissoes.ativas() == (Permissao.VER_OS, Permissao.APROVAR_OS)
    equipamento = novo.equipamentos.obter(1)
    assert equipamento is not None
    assert (equipamento.nome, equipamento.modelo, equipamento.ativo) == (
        "Fresa ção",
        "ÇÃO-1",
        False,
    )


def test_alterar_permissoes_do_cargo_vale_para_todos_os_usuarios_na_leitura_seguinte(
    reiniciar: Reiniciar,
) -> None:
    c = reiniciar()
    semear_demonstracao(c)
    cargo = c.cargos.obter(2)
    assert cargo is not None
    cargo.permissoes.definir([Permissao.VER_OS])
    c.cargos.salvar(cargo)
    for usuario_id in (2, 3):
        usuario = reiniciar().usuarios.obter(usuario_id)
        assert usuario is not None
        assert usuario.cargo.permissoes.ativas() == (Permissao.VER_OS,)


def test_disponibilidade_ativo_e_papel_persistem_pelos_servicos(reiniciar: Reiniciar) -> None:
    c = reiniciar()
    semear_demonstracao(c)
    c.servico_disponibilidade.alterar_minha_disponibilidade(2, Disponibilidade.AUSENTE)
    novo = reiniciar()
    bruno = novo.usuarios.obter(2)
    assert bruno is not None
    assert bruno.disponibilidade is Disponibilidade.AUSENTE
    consulta = novo.servico_disponibilidade.consultar(1)
    efetivas = {d.id: d.disponibilidade for d in consulta}
    assert efetivas[2] is Disponibilidade.AUSENTE
    assert efetivas[3] is Disponibilidade.EM_ATENDIMENTO  # derivada da OS 3 em execução


# ------------------------------------------------------------------------ paridade com a memória
def test_o_postgres_e_a_memoria_produzem_exatamente_o_mesmo_estado(reiniciar: Reiniciar) -> None:
    """Mesmos serviços, mesmas regras: a persistência não altera nenhum comportamento."""
    memoria = criar_container_em_memoria(relogio=RelogioFixo())
    postgres = reiniciar()
    semear_demonstracao(memoria)
    semear_demonstracao(postgres)
    assert _cadastros(postgres) == _cadastros(memoria)
    assert _retratos(postgres) == _retratos(memoria)
    # e as mesmas recusas
    for c in (memoria, postgres):
        with pytest.raises(Exception) as erro:  # noqa: PT011
            c.servico_ordens.aprovar(2, 3)  # técnico não aprova
        assert type(erro.value).__name__ == "PermissaoNegadaError"
