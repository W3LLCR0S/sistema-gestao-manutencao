"""DLT-10: identificadores monotônicos, em todos os repositórios (AUD-05).

Diferença **aprovada** em relação ao legado: ali o próximo id era ``max(ids) + 1``, então excluir
o maior id fazia o cadastro seguinte reutilizá-lo (CAR-75). Aqui a sequência pertence ao
repositório e nunca recua. Os testes valem para toda implementação das portas.
"""

from collections.abc import Callable
from dataclasses import dataclass

import pytest

from manutencao.application.erros import IdentificadorJaEmitidoError
from manutencao.domain.cargo import Cargo
from manutencao.domain.enums import Papel
from manutencao.domain.equipamento import Equipamento
from manutencao.domain.ordem_servico import OrdemServico
from manutencao.domain.permissoes import Permissoes
from manutencao.domain.usuario import Usuario
from tests.contrato.implementacoes import Repositorios
from tests.dominio.fabrica import Mundo


@dataclass(frozen=True)
class Tipo:
    """Um repositório visto de forma uniforme: como criar, adicionar, salvar e remover."""

    nome: str
    proximo: Callable[[Repositorios], int]
    adicionar: Callable[[Repositorios, int], None]
    salvar: Callable[[Repositorios, int], None]
    existe: Callable[[Repositorios, int], bool]
    remover: Callable[[Repositorios, int], None] | None


def _cargos(repos: Repositorios) -> None:
    if repos.cargos.obter(1) is None:
        repos.cargos.adicionar(Cargo(1, "Técnico", Permissoes.padrao_tecnico()))


def _adicionar_usuario(repos: Repositorios, id: int) -> None:
    _cargos(repos)
    cargo = repos.cargos.obter(1)
    assert cargo is not None
    repos.usuarios.adicionar(Usuario(id, f"U{id}", cargo, papel=Papel.TECNICO))


def _salvar_usuario(repos: Repositorios, id: int) -> None:
    usuario = repos.usuarios.obter(id)
    assert usuario is not None
    usuario.nome = f"{usuario.nome}!"
    repos.usuarios.salvar(usuario)


def _salvar_equipamento(repos: Repositorios, id: int) -> None:
    equipamento = repos.equipamentos.obter(id)
    assert equipamento is not None
    equipamento.nome = f"{equipamento.nome}!"
    repos.equipamentos.salvar(equipamento)


def _salvar_ordem(repos: Repositorios, numero: int) -> None:
    ordem = repos.ordens.obter(numero)
    assert ordem is not None
    repos.ordens.salvar(ordem)


def _os(numero: int) -> OrdemServico:
    return Mundo().aberta(numero)


def _salvar_cargo(repos: Repositorios, id: int) -> None:
    cargo = repos.cargos.obter(id)
    assert cargo is not None
    cargo.nome = f"{cargo.nome}!"
    repos.cargos.salvar(cargo)


TIPOS = [
    Tipo(
        "equipamento",
        lambda r: r.equipamentos.proximo_id(),
        lambda r, i: r.equipamentos.adicionar(Equipamento(i, f"E{i}", "M")),
        _salvar_equipamento,
        lambda r, i: r.equipamentos.obter(i) is not None,
        lambda r, i: r.equipamentos.remover(i),
    ),
    Tipo(
        "usuario",
        lambda r: r.usuarios.proximo_id(),
        _adicionar_usuario,
        _salvar_usuario,
        lambda r, i: r.usuarios.obter(i) is not None,
        lambda r, i: r.usuarios.remover(i),
    ),
    Tipo(
        "ordem",
        lambda r: r.ordens.proximo_numero(),
        lambda r, i: r.ordens.adicionar(_os(i)),
        _salvar_ordem,
        lambda r, i: r.ordens.obter(i) is not None,
        None,  # a OS nunca é excluída
    ),
    Tipo(
        "cargo",
        lambda r: r.cargos.proximo_id(),
        lambda r, i: r.cargos.adicionar(Cargo(i, f"C{i}", Permissoes())),
        _salvar_cargo,
        lambda r, i: r.cargos.obter(i) is not None,
        None,  # os cargos são fixos
    ),
]
COM_EXCLUSAO = [t for t in TIPOS if t.remover is not None]
IDS = [t.nome for t in TIPOS]
IDS_COM_EXCLUSAO = [t.nome for t in COM_EXCLUSAO]


def _remover(tipo: Tipo, repos: Repositorios, id: int) -> None:
    assert tipo.remover is not None
    tipo.remover(repos, id)


@pytest.mark.parametrize("tipo", TIPOS, ids=IDS)
def test_ids_comecam_em_1_e_crescem_um_a_um(repos: Repositorios, tipo: Tipo) -> None:
    emitidos = []
    for _ in range(4):
        id = tipo.proximo(repos)
        tipo.adicionar(repos, id)
        emitidos.append(id)
    assert emitidos == [1, 2, 3, 4]


@pytest.mark.parametrize("tipo", TIPOS, ids=IDS)
def test_consultar_o_proximo_id_nao_o_consome(repos: Repositorios, tipo: Tipo) -> None:
    assert [tipo.proximo(repos) for _ in range(3)] == [1, 1, 1]
    tipo.adicionar(repos, 1)
    assert [tipo.proximo(repos) for _ in range(3)] == [2, 2, 2]


@pytest.mark.parametrize("tipo", COM_EXCLUSAO, ids=IDS_COM_EXCLUSAO)
def test_excluir_o_maior_id_nao_o_reaproveita(repos: Repositorios, tipo: Tipo) -> None:
    """O contrário do CAR-75 do legado (``max()+1``): o id do excluído não volta."""
    for id in (1, 2, 3):
        tipo.adicionar(repos, id)
    _remover(tipo, repos, 3)
    assert tipo.proximo(repos) == 4
    tipo.adicionar(repos, tipo.proximo(repos))
    assert tipo.existe(repos, 4)
    assert not tipo.existe(repos, 3)


@pytest.mark.parametrize("tipo", COM_EXCLUSAO, ids=IDS_COM_EXCLUSAO)
def test_excluir_tudo_nao_reinicia_a_sequencia(repos: Repositorios, tipo: Tipo) -> None:
    for id in (1, 2):
        tipo.adicionar(repos, id)
    for id in (1, 2):
        _remover(tipo, repos, id)
    assert tipo.proximo(repos) == 3


@pytest.mark.parametrize("tipo", COM_EXCLUSAO, ids=IDS_COM_EXCLUSAO)
def test_excluir_um_id_do_meio_deixa_lacuna_e_nao_renumera(repos: Repositorios, tipo: Tipo) -> None:
    for id in (1, 2, 3):
        tipo.adicionar(repos, id)
    _remover(tipo, repos, 2)
    assert tipo.existe(repos, 1)
    assert not tipo.existe(repos, 2)
    assert tipo.existe(repos, 3)  # o 3 continua sendo o 3
    assert tipo.proximo(repos) == 4


@pytest.mark.parametrize("tipo", COM_EXCLUSAO, ids=IDS_COM_EXCLUSAO)
def test_adicionar_id_de_objeto_excluido_e_recusado(repos: Repositorios, tipo: Tipo) -> None:
    for id in (1, 2):
        tipo.adicionar(repos, id)
    _remover(tipo, repos, 2)
    with pytest.raises(IdentificadorJaEmitidoError):
        tipo.adicionar(repos, 2)
    assert not tipo.existe(repos, 2)


@pytest.mark.parametrize("tipo", TIPOS, ids=IDS)
def test_adicionar_id_em_uso_e_recusado_sem_colisao(repos: Repositorios, tipo: Tipo) -> None:
    for id in (1, 2):
        tipo.adicionar(repos, id)
    with pytest.raises(IdentificadorJaEmitidoError):
        tipo.adicionar(repos, 2)
    with pytest.raises(IdentificadorJaEmitidoError):
        tipo.adicionar(repos, 1)
    assert tipo.proximo(repos) == 3


@pytest.mark.parametrize("tipo", TIPOS, ids=IDS)
def test_adicionar_aceita_salto_e_a_sequencia_segue_dele(repos: Repositorios, tipo: Tipo) -> None:
    tipo.adicionar(repos, 1)
    tipo.adicionar(repos, 10)
    assert tipo.proximo(repos) == 11
    with pytest.raises(IdentificadorJaEmitidoError):
        tipo.adicionar(repos, 5)  # menor que o último emitido: recusado


@pytest.mark.parametrize("tipo", TIPOS, ids=IDS)
def test_adicionar_recusado_nao_consome_nem_altera_a_sequencia(
    repos: Repositorios, tipo: Tipo
) -> None:
    tipo.adicionar(repos, 1)
    with pytest.raises(IdentificadorJaEmitidoError):
        tipo.adicionar(repos, 1)
    assert tipo.proximo(repos) == 2


@pytest.mark.parametrize("tipo", TIPOS, ids=IDS)
def test_id_e_estavel_depois_de_atualizacoes(repos: Repositorios, tipo: Tipo) -> None:
    for id in (1, 2, 3):
        tipo.adicionar(repos, id)
    for _ in range(3):
        for id in (1, 2, 3):
            tipo.salvar(repos, id)
    assert all(tipo.existe(repos, id) for id in (1, 2, 3))
    assert tipo.proximo(repos) == 4


@pytest.mark.parametrize("tipo", TIPOS, ids=IDS)
def test_id_nao_positivo_e_recusado(repos: Repositorios, tipo: Tipo) -> None:
    with pytest.raises(ValueError, match="positivo"):
        tipo.adicionar(repos, 0)
    assert tipo.proximo(repos) == 1


def test_sequencias_sao_independentes_por_tipo(repos: Repositorios) -> None:
    for tipo in COM_EXCLUSAO:
        for id in (1, 2, 3):
            tipo.adicionar(repos, id)
    _remover(COM_EXCLUSAO[0], repos, 3)  # só os equipamentos perdem o 3
    assert repos.equipamentos.proximo_id() == 4
    assert repos.usuarios.proximo_id() == 4
    assert repos.ordens.proximo_numero() == 1  # nenhuma OS foi adicionada
    assert repos.cargos.proximo_id() == 2  # só o cargo criado como apoio dos usuários
