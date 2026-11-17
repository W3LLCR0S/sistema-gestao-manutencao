"""Contrato de ``OrdemServicoRepository``: escrita, consultas, filtros, ausência e cópia."""

from datetime import UTC, datetime

import pytest

from manutencao.application.erros import NaoEncontradoError
from manutencao.application.portas.repositorios import FiltroDeOrdens
from manutencao.domain.enums import Criticidade, StatusOS
from manutencao.domain.ordem_servico import OrdemServico
from tests.contrato.implementacoes import Repositorios
from tests.dominio.fabrica import Mundo

QUANDO = datetime(2026, 3, 11, 8, 0, tzinfo=UTC)


def test_repositorio_novo_esta_vazio_e_o_primeiro_numero_e_1(repos: Repositorios) -> None:
    assert repos.ordens.listar() == ()
    assert repos.ordens.contar() == 0
    assert repos.ordens.proximo_numero() == 1


def test_adicionar_e_obter_por_numero_preserva_o_agregado(repos: Repositorios) -> None:
    mundo = Mundo()
    os_ = mundo.concluida()
    repos.ordens.adicionar(os_)
    achada = repos.ordens.obter(os_.numero)
    assert achada is not None
    assert achada == os_  # igualdade por número
    assert achada.status is StatusOS.CONCLUIDA
    assert achada.servicos == os_.servicos  # o histórico inteiro, na mesma ordem
    assert achada.pecas_utilizadas == os_.pecas_utilizadas
    assert achada.data_conclusao == os_.data_conclusao
    assert repos.ordens.obter(99) is None


def test_adicionar_guarda_copia_do_que_recebeu(repos: Repositorios) -> None:
    mundo = Mundo()
    os_ = mundo.aberta()
    repos.ordens.adicionar(os_)
    os_.atribuir(mundo.bruno, mundo.ana, quando=QUANDO)  # alterada depois de adicionada
    guardada = repos.ordens.obter(1)
    assert guardada is not None
    assert guardada.status is StatusOS.ABERTA
    assert guardada.tecnico_atribuido is None


def test_obter_devolve_copia_e_so_salvar_altera(repos: Repositorios) -> None:
    mundo = Mundo()
    repos.ordens.adicionar(mundo.aberta())
    editada = repos.ordens.obter(1)
    assert editada is not None
    editada.atribuir(mundo.bruno, mundo.ana, quando=QUANDO)
    intacta = repos.ordens.obter(1)
    assert intacta is not None
    assert (intacta.status, len(intacta.servicos)) == (StatusOS.ABERTA, 1)
    repos.ordens.salvar(editada)
    salva = repos.ordens.obter(1)
    assert salva is not None
    assert salva.status is StatusOS.ATRIBUIDA
    assert salva.tecnico_atribuido == mundo.bruno
    assert [s.numero for s in salva.servicos] == [1, 2, 3]


def test_obter_duas_vezes_devolve_objetos_distintos_e_iguais(repos: Repositorios) -> None:
    repos.ordens.adicionar(Mundo().aberta())
    primeira, segunda = repos.ordens.obter(1), repos.ordens.obter(1)
    assert primeira is not None
    assert segunda is not None
    assert primeira is not segunda
    assert primeira == segunda


def test_salvar_inexistente_levanta_nao_encontrado_e_nao_cria(repos: Repositorios) -> None:
    with pytest.raises(NaoEncontradoError):
        repos.ordens.salvar(Mundo().aberta(7))
    assert repos.ordens.obter(7) is None
    assert repos.ordens.contar() == 0


def test_listar_em_ordem_de_numero_com_copias_independentes(repos: Repositorios) -> None:
    mundo = Mundo()
    for numero in (1, 2, 5):
        repos.ordens.adicionar(mundo.aberta(numero))
    assert [o.numero for o in repos.ordens.listar()] == [1, 2, 5]
    repos.ordens.listar()[0].cancelar(mundo.ana, "x", quando=QUANDO)
    assert repos.ordens.listar()[0].status is StatusOS.ABERTA


def _popular(repos: Repositorios) -> Mundo:
    """OS 1 aberta, 2 atribuída (Bruno), 3 concluída (Bruno), 4 cancelada; todas no torno."""
    mundo = Mundo()
    repos.ordens.adicionar(mundo.aberta(1))
    atribuida = mundo.aberta(2)
    atribuida.atribuir(mundo.bruno, mundo.ana, quando=QUANDO)
    repos.ordens.adicionar(atribuida)
    repos.ordens.adicionar(_concluida(mundo, 3))
    cancelada = mundo.aberta(4)
    cancelada.cancelar(mundo.ana, "Indevida", quando=QUANDO)
    repos.ordens.adicionar(cancelada)
    return mundo


def _concluida(mundo: Mundo, numero: int) -> OrdemServico:
    """Uma OS concluída pelo caminho normal, com o número pedido (Bruno é o técnico)."""
    os_ = mundo.aberta(numero)
    os_.atribuir(mundo.bruno, mundo.ana, quando=QUANDO)
    os_.registrar_diagnostico(mundo.bruno, "Rolamento", "Graxa", quando=QUANDO)
    os_.apontar_reparo(mundo.bruno, 1.0, "Troca", [], quando=QUANDO)
    os_.alterar_status(mundo.bruno, StatusOS.REPARO_FINALIZADO, quando=QUANDO)
    os_.concluir_tecnicamente(mundo.bruno, "ok", True, quando=QUANDO)
    os_.aprovar(mundo.ana, quando=QUANDO)
    assert os_.status is StatusOS.CONCLUIDA
    return os_


def _numeros(repos: Repositorios, filtro: FiltroDeOrdens | None = None) -> list[int]:
    return [o.numero for o in repos.ordens.listar(filtro)]


def test_filtros_da_listagem_reproduzem_os_do_legado(repos: Repositorios) -> None:
    _popular(repos)
    assert _numeros(repos) == [1, 2, 3, 4]
    assert _numeros(repos, FiltroDeOrdens(encerrada=False)) == [1, 2]  # em aberto
    assert _numeros(repos, FiltroDeOrdens(encerrada=True)) == [3, 4]  # concluídas e canceladas
    assert _numeros(repos, FiltroDeOrdens(status=StatusOS.ATRIBUIDA)) == [2]
    assert _numeros(repos, FiltroDeOrdens(equipamento_id=1)) == [1, 2, 3, 4]
    assert _numeros(repos, FiltroDeOrdens(equipamento_id=2)) == []
    assert _numeros(repos, FiltroDeOrdens(tecnico_id=2)) == [2, 3]
    assert _numeros(repos, FiltroDeOrdens(tecnico_id=3)) == []
    assert _numeros(repos, FiltroDeOrdens(criticidade=Criticidade.ALTA)) == [1, 2, 3, 4]
    assert _numeros(repos, FiltroDeOrdens(criticidade=Criticidade.BAIXA)) == []


def test_filtros_combinados_e_contagem(repos: Repositorios) -> None:
    _popular(repos)
    carga_do_bruno = FiltroDeOrdens(tecnico_id=2, encerrada=False)
    assert _numeros(repos, carga_do_bruno) == [2]
    assert repos.ordens.contar(carga_do_bruno) == 1
    assert repos.ordens.contar() == 4
    assert repos.ordens.contar(FiltroDeOrdens(encerrada=True)) == 2


def test_participacao_do_usuario_cobre_abertura_atribuicao_e_historico(repos: Repositorios) -> None:
    mundo = Mundo()
    assert not repos.ordens.usuario_tem_participacao(mundo.carla.id)
    repos.ordens.adicionar(mundo.aberta())  # aberta pela Carla; o registro de abertura é dela
    assert repos.ordens.usuario_tem_participacao(mundo.carla.id)
    assert not repos.ordens.usuario_tem_participacao(mundo.bruno.id)
    os_ = repos.ordens.obter(1)
    assert os_ is not None
    os_.atribuir(mundo.bruno, mundo.ana, quando=QUANDO)  # Bruno técnico; Ana no histórico
    repos.ordens.salvar(os_)
    assert repos.ordens.usuario_tem_participacao(mundo.bruno.id)
    assert repos.ordens.usuario_tem_participacao(mundo.ana.id)
    assert not repos.ordens.usuario_tem_participacao(99)


def test_participacao_vale_para_quem_so_registrou_no_historico(repos: Repositorios) -> None:
    mundo = Mundo()
    repos.ordens.adicionar(mundo.aberta())
    os_ = repos.ordens.obter(1)
    assert os_ is not None
    os_.adicionar_apontamento(mundo.ana, "Nota do gestor", quando=QUANDO)
    repos.ordens.salvar(os_)
    assert repos.ordens.usuario_tem_participacao(mundo.ana.id)
