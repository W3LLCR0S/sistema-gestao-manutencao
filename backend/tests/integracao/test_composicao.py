"""A raiz de composição liga portas, implementações e serviços (D6, ADR-0005)."""

import dataclasses
from datetime import timedelta

import pytest

from manutencao.application.dto import PecaInformada
from manutencao.application.portas.relogio import Relogio
from manutencao.application.portas.repositorios import (
    CargoRepository,
    EquipamentoRepository,
    OrdemServicoRepository,
    UsuarioRepository,
)
from manutencao.composicao.container import Container, montar
from manutencao.composicao.fabrica import criar_container_em_memoria
from manutencao.domain.enums import Criticidade, StatusOS
from manutencao.infrastructure.memoria import (
    CargosEmMemoria,
    EquipamentosEmMemoria,
    OrdensEmMemoria,
    UsuariosEmMemoria,
)
from manutencao.infrastructure.relogio import RelogioDeSistema
from tests.apoio.ambiente import ANA, BRUNO, CARLA, TORNO
from tests.apoio.relogio import INICIO, RelogioFixo


def test_container_em_memoria_comeca_vazio_por_padrao() -> None:
    container = criar_container_em_memoria()
    assert container.equipamentos.listar() == ()
    assert container.usuarios.listar() == ()
    assert container.cargos.listar() == ()
    assert container.ordens.listar() == ()


def test_container_com_dados_de_exemplo_reproduz_a_base_do_legado() -> None:
    container = criar_container_em_memoria(com_dados_de_exemplo=True)
    assert [(c.id, c.nome) for c in container.cargos.listar()] == [(1, "Gestor"), (2, "Técnico")]
    assert [(u.id, u.nome, u.cargo.id) for u in container.usuarios.listar()] == [
        (1, "Ana Souza", 1),
        (2, "Bruno Lima", 2),
        (3, "Carla Mendes", 2),
    ]
    assert [(e.id, e.nome, e.modelo) for e in container.equipamentos.listar()] == [
        (1, "Torno CNC", "GL 240"),
        (2, "Compressor de Ar", "CSW 40"),
        (3, "Empilhadeira Elétrica", "PT 1650"),
    ]
    assert (
        container.equipamentos.proximo_id(),
        container.usuarios.proximo_id(),
        container.cargos.proximo_id(),
        container.ordens.proximo_numero(),
    ) == (4, 4, 3, 1)


def test_os_atributos_do_container_satisfazem_as_portas() -> None:
    container = criar_container_em_memoria()
    assert isinstance(container.equipamentos, EquipamentoRepository)
    assert isinstance(container.cargos, CargoRepository)
    assert isinstance(container.usuarios, UsuarioRepository)
    assert isinstance(container.ordens, OrdemServicoRepository)
    assert isinstance(container.relogio, Relogio)


def test_o_relogio_padrao_e_o_de_sistema_e_um_relogio_injetado_vale() -> None:
    assert isinstance(criar_container_em_memoria().relogio, RelogioDeSistema)
    fixo = RelogioFixo()
    assert criar_container_em_memoria(relogio=fixo).relogio is fixo


def test_servicos_operam_sobre_os_mesmos_repositorios_do_container() -> None:
    container = criar_container_em_memoria(com_dados_de_exemplo=True)
    novo = container.servico_equipamentos.cadastrar(ANA, "Prensa", "P1")
    assert container.equipamentos.obter(novo.id) is not None  # visível pela porta
    os_ = container.servico_ordens.abrir(CARLA, TORNO, "Torno parado", Criticidade.ALTA)
    assert container.ordens.obter(os_.numero) is not None
    assert container.projecoes.ordens_do_equipamento(TORNO)[0].numero == os_.numero
    assert container.servico_disponibilidade.consultar(ANA)[0].id == BRUNO


def test_fluxo_completo_pelo_container_com_relogio_fixo() -> None:
    relogio = RelogioFixo()
    container = criar_container_em_memoria(relogio=relogio, com_dados_de_exemplo=True)
    ordens, disponibilidade = container.servico_ordens, container.servico_disponibilidade
    numero = ordens.abrir(CARLA, TORNO, "Torno parado", Criticidade.ALTA).numero
    ordens.atribuir(ANA, numero, BRUNO)
    relogio.avancar(hours=1)
    ordens.registrar_diagnostico(BRUNO, numero, "Rolamento gasto", "Falta de graxa")
    ordens.apontar_reparo(BRUNO, numero, 1.5, "Troca", [PecaInformada("Rolamento", 2)])
    disponibilidade.atualizar_disponibilidades()
    assert disponibilidade.consultar(ANA)[0].disponibilidade.value == "Em atendimento"
    ordens.alterar_status(BRUNO, numero, StatusOS.REPARO_FINALIZADO)
    assert ordens.concluir_tecnicamente(BRUNO, numero, "Funcionou", True)
    ordens.aprovar(ANA, numero)
    final = ordens.consultar(ANA, numero)
    assert final.status is StatusOS.CONCLUIDA
    assert final.data_conclusao == INICIO + timedelta(hours=1)


def test_dois_containers_nao_compartilham_estado() -> None:
    a = criar_container_em_memoria(com_dados_de_exemplo=True)
    b = criar_container_em_memoria(com_dados_de_exemplo=True)
    a.servico_equipamentos.cadastrar(ANA, "Prensa", "P1")
    a.servico_ordens.abrir(CARLA, TORNO, "x", Criticidade.BAIXA)
    assert len(b.equipamentos.listar()) == 3
    assert b.ordens.listar() == ()
    assert (b.equipamentos.proximo_id(), b.ordens.proximo_numero()) == (4, 1)
    assert a.equipamentos is not b.equipamentos
    assert a.servico_ordens is not b.servico_ordens


def test_montar_aceita_outras_implementacoes_das_portas() -> None:
    """A mesma ligação serve a qualquer implementação (aqui, instâncias montadas à mão)."""
    cargos = CargosEmMemoria()
    container = montar(
        relogio=RelogioFixo(),
        equipamentos=EquipamentosEmMemoria(),
        cargos=cargos,
        usuarios=UsuariosEmMemoria(cargos),
        ordens=OrdensEmMemoria(),
    )
    assert isinstance(container, Container)
    assert container.servico_equipamentos is not None


def test_container_e_imutavel() -> None:
    container = criar_container_em_memoria()
    with pytest.raises(dataclasses.FrozenInstanceError):
        container.relogio = RelogioFixo()  # type: ignore[misc]
