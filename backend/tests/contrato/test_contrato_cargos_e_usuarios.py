"""Contrato de ``CargoRepository`` e ``UsuarioRepository``: escrita, ausência, cópia e relação."""

import pytest

from manutencao.application.erros import NaoEncontradoError
from manutencao.domain.cargo import Cargo
from manutencao.domain.enums import Disponibilidade
from manutencao.domain.permissoes import Permissao, Permissoes
from manutencao.domain.usuario import Usuario
from tests.contrato.implementacoes import Repositorios


def _cargos(repos: Repositorios) -> None:
    repos.cargos.adicionar(Cargo(1, "Gestor", Permissoes.padrao_gestor()))
    repos.cargos.adicionar(Cargo(2, "Técnico", Permissoes.padrao_tecnico()))


def _usuario(repos: Repositorios, id: int = 1, cargo: int = 2) -> Usuario:
    achado = repos.cargos.obter(cargo)
    assert achado is not None
    return Usuario(id, f"Usuário {id}", achado, f"u{id}@empresa.com", "Seg-Sex 08h-17h")


# ------------------------------------------------------------------------------------- cargos


def test_cargos_guardam_e_devolvem_as_permissoes(repos: Repositorios) -> None:
    _cargos(repos)
    tecnico = repos.cargos.obter(2)
    assert tecnico is not None
    assert tecnico.permissoes.ativas() == Permissoes.padrao_tecnico().ativas()
    assert [c.nome for c in repos.cargos.listar()] == ["Gestor", "Técnico"]
    assert repos.cargos.obter(9) is None


def test_cargo_devolvido_e_copia_e_so_salvar_altera_permissoes(repos: Repositorios) -> None:
    _cargos(repos)
    editado = repos.cargos.obter(2)
    assert editado is not None
    editado.permissoes.definir([Permissao.VER_OS])
    intacto = repos.cargos.obter(2)
    assert intacto is not None
    assert intacto.permissoes.ativas() == Permissoes.padrao_tecnico().ativas()
    repos.cargos.salvar(editado)
    salvo = repos.cargos.obter(2)
    assert salvo is not None
    assert salvo.permissoes.ativas() == (Permissao.VER_OS,)


def test_cargo_adicionado_guarda_copia_das_permissoes(repos: Repositorios) -> None:
    permissoes = Permissoes([Permissao.VER_OS])
    repos.cargos.adicionar(Cargo(1, "Leitor", permissoes))
    permissoes.definir([])
    cargo = repos.cargos.obter(1)
    assert cargo is not None
    assert cargo.permissoes.ativas() == (Permissao.VER_OS,)


def test_salvar_cargo_inexistente_levanta_nao_encontrado(repos: Repositorios) -> None:
    with pytest.raises(NaoEncontradoError):
        repos.cargos.salvar(Cargo(3, "Fantasma", Permissoes()))


# ----------------------------------------------------------------------------------- usuários


def test_usuario_adicionado_e_obtido_com_o_cargo(repos: Repositorios) -> None:
    _cargos(repos)
    repos.usuarios.adicionar(_usuario(repos))
    achado = repos.usuarios.obter(1)
    assert achado is not None
    assert (achado.nome, achado.email, achado.escala) == (
        "Usuário 1",
        "u1@empresa.com",
        "Seg-Sex 08h-17h",
    )
    assert achado.cargo.id == 2
    assert achado.e_tecnico
    assert achado.disponibilidade is Disponibilidade.DISPONIVEL
    assert repos.usuarios.obter(9) is None


def test_usuarios_listados_por_id_crescente(repos: Repositorios) -> None:
    _cargos(repos)
    for id in (1, 2, 4):
        repos.usuarios.adicionar(_usuario(repos, id))
    assert [u.id for u in repos.usuarios.listar()] == [1, 2, 4]


def test_usuario_obtido_e_copia_e_so_salvar_altera(repos: Repositorios) -> None:
    _cargos(repos)
    repos.usuarios.adicionar(_usuario(repos))
    editado = repos.usuarios.obter(1)
    assert editado is not None
    editado.nome = "Novo nome"
    editado.disponibilidade = Disponibilidade.AUSENTE
    intacto = repos.usuarios.obter(1)
    assert intacto is not None
    assert (intacto.nome, intacto.disponibilidade) == ("Usuário 1", Disponibilidade.DISPONIVEL)
    repos.usuarios.salvar(editado)
    salvo = repos.usuarios.obter(1)
    assert salvo is not None
    assert (salvo.nome, salvo.disponibilidade) == ("Novo nome", Disponibilidade.AUSENTE)


def test_usuario_adicionado_guarda_copia_do_que_recebeu(repos: Repositorios) -> None:
    _cargos(repos)
    original = _usuario(repos)
    repos.usuarios.adicionar(original)
    original.nome = "Alterado depois de adicionar"
    guardado = repos.usuarios.obter(1)
    assert guardado is not None
    assert guardado.nome == "Usuário 1"


def test_mudar_o_cargo_do_usuario_e_salvar(repos: Repositorios) -> None:
    _cargos(repos)
    repos.usuarios.adicionar(_usuario(repos))
    usuario = repos.usuarios.obter(1)
    gestor = repos.cargos.obter(1)
    assert usuario is not None
    assert gestor is not None
    usuario.cargo = gestor
    repos.usuarios.salvar(usuario)
    salvo = repos.usuarios.obter(1)
    assert salvo is not None
    assert (salvo.cargo.id, salvo.e_tecnico) == (1, False)


def test_permissoes_do_cargo_valem_para_todos_os_usuarios_na_leitura_seguinte(
    repos: Repositorios,
) -> None:
    _cargos(repos)
    repos.usuarios.adicionar(_usuario(repos, 1))
    repos.usuarios.adicionar(_usuario(repos, 2))
    cargo = repos.cargos.obter(2)
    assert cargo is not None
    cargo.permissoes.definir([Permissao.VER_OS])
    repos.cargos.salvar(cargo)
    for usuario in repos.usuarios.listar():
        assert usuario.pode(Permissao.VER_OS)
        assert not usuario.pode(Permissao.APONTAR_REPARO)


def test_adicionar_ou_salvar_com_cargo_inexistente_levanta_nao_encontrado(
    repos: Repositorios,
) -> None:
    _cargos(repos)
    sem_cargo = Usuario(1, "Órfão", Cargo(9, "Inexistente", Permissoes()))
    with pytest.raises(NaoEncontradoError):
        repos.usuarios.adicionar(sem_cargo)
    assert repos.usuarios.listar() == ()
    repos.usuarios.adicionar(_usuario(repos))
    with pytest.raises(NaoEncontradoError):
        repos.usuarios.salvar(Usuario(1, "Órfão", Cargo(9, "Inexistente", Permissoes())))
    achado = repos.usuarios.obter(1)
    assert achado is not None
    assert achado.cargo.id == 2  # a recusa não alterou o armazenado


def test_salvar_e_remover_usuario_inexistente_levantam_nao_encontrado(repos: Repositorios) -> None:
    _cargos(repos)
    with pytest.raises(NaoEncontradoError):
        repos.usuarios.salvar(_usuario(repos, 5))
    with pytest.raises(NaoEncontradoError):
        repos.usuarios.remover(5)
    assert repos.usuarios.listar() == ()


def test_remover_exclui_so_o_indicado(repos: Repositorios) -> None:
    _cargos(repos)
    for id in (1, 2, 3):
        repos.usuarios.adicionar(_usuario(repos, id))
    repos.usuarios.remover(2)
    assert repos.usuarios.obter(2) is None
    assert [u.id for u in repos.usuarios.listar()] == [1, 3]
