"""Repositórios em memória: isolamento entre instâncias, determinismo e ausência de E/S."""

from pathlib import Path

import pytest

from manutencao.domain.cargo import Cargo
from manutencao.domain.equipamento import Equipamento
from manutencao.domain.permissoes import Permissao, Permissoes
from manutencao.domain.usuario import Usuario
from manutencao.infrastructure.memoria import (
    CargosEmMemoria,
    EquipamentosEmMemoria,
    OrdensEmMemoria,
    UsuariosEmMemoria,
)
from tests.dominio.fabrica import Mundo


def _popular(
    equipamentos: EquipamentosEmMemoria,
    cargos: CargosEmMemoria,
    usuarios: UsuariosEmMemoria,
    ordens: OrdensEmMemoria,
) -> None:
    mundo = Mundo()
    cargos.adicionar(Cargo(1, "Gestor", Permissoes.padrao_gestor()))
    cargos.adicionar(Cargo(2, "Técnico", Permissoes.padrao_tecnico()))
    usuarios.adicionar(Usuario(1, "Ana", mundo.gestor))
    equipamentos.adicionar(Equipamento(1, "Torno CNC", "GL 240"))
    ordens.adicionar(mundo.aberta())


def test_duas_instancias_nao_compartilham_estado_nem_sequencia() -> None:
    a = (EquipamentosEmMemoria(), CargosEmMemoria(), OrdensEmMemoria())
    b = (EquipamentosEmMemoria(), CargosEmMemoria(), OrdensEmMemoria())
    a_usuarios = UsuariosEmMemoria(a[1])
    b_usuarios = UsuariosEmMemoria(b[1])
    _popular(a[0], a[1], a_usuarios, a[2])

    assert b[0].listar() == ()
    assert b[1].listar() == ()
    assert b_usuarios.listar() == ()
    assert b[2].listar() == ()
    assert (b[0].proximo_id(), b[1].proximo_id(), b_usuarios.proximo_id()) == (1, 1, 1)
    assert b[2].proximo_numero() == 1  # a sequência da outra instância não vazou


def test_usuarios_resolvem_o_cargo_da_propria_instancia() -> None:
    cargos_a, cargos_b = CargosEmMemoria(), CargosEmMemoria()
    for cargos in (cargos_a, cargos_b):
        cargos.adicionar(Cargo(1, "Técnico", Permissoes.padrao_tecnico()))
    usuarios_a, usuarios_b = UsuariosEmMemoria(cargos_a), UsuariosEmMemoria(cargos_b)
    cargo = cargos_a.obter(1)
    assert cargo is not None
    usuarios_a.adicionar(Usuario(1, "Bruno", cargo))
    usuarios_b.adicionar(Usuario(1, "Bruno", cargo))

    cargo.permissoes.definir([Permissao.VER_OS])
    cargos_a.salvar(cargo)  # muda só a instância A

    a, b = usuarios_a.obter(1), usuarios_b.obter(1)
    assert a is not None
    assert b is not None
    assert a.cargo.permissoes.ativas() == (Permissao.VER_OS,)
    assert b.cargo.permissoes.ativas() == Permissoes.padrao_tecnico().ativas()


def test_nenhum_repositorio_cria_arquivo_nem_toca_o_diretorio_corrente(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    cargos = CargosEmMemoria()
    _popular(EquipamentosEmMemoria(), cargos, UsuariosEmMemoria(cargos), OrdensEmMemoria())
    assert list(tmp_path.iterdir()) == []
    assert Path.cwd() == tmp_path.resolve()


def _roteiro() -> tuple[object, ...]:
    equipamentos = EquipamentosEmMemoria()
    for id in (1, 2, 3):
        equipamentos.adicionar(Equipamento(id, f"E{id}", "M"))
    equipamentos.remover(3)
    return (
        equipamentos.proximo_id(),
        [(e.id, e.nome, e.ativo) for e in equipamentos.listar()],
    )


def test_comportamento_e_deterministico_entre_execucoes() -> None:
    assert _roteiro() == _roteiro() == (4, [(1, "E1", True), (2, "E2", True)])
