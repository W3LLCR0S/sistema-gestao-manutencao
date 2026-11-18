"""Contrato da matrícula em ``UsuarioRepository``: unicidade, busca, geração e imutabilidade.

Roda contra todas as implementações (memória e PostgreSQL): a unicidade vale nas duas e, no
PostgreSQL, também vem da restrição ``UNIQUE`` do banco.
"""

import pytest

from manutencao.application.erros import CodigoErroAplicacao, RegraDeAplicacaoError
from manutencao.domain.cargo import Cargo
from manutencao.domain.enums import Papel
from manutencao.domain.matricula import matricula_valida
from manutencao.domain.permissoes import Permissoes
from manutencao.domain.usuario import Usuario
from tests.contrato.implementacoes import Repositorios


def _cargo(repos: Repositorios) -> Cargo:
    cargo = Cargo(1, "Técnico", Permissoes.padrao_tecnico())
    repos.cargos.adicionar(cargo)
    return cargo


def _usuario(cargo: Cargo, id: int, matricula: str | None = None) -> Usuario:
    return Usuario(id, f"Usuário {id}", cargo, papel=Papel.TECNICO, matricula=matricula)


def test_matricula_informada_e_gravada_e_buscada(repos: Repositorios) -> None:
    cargo = _cargo(repos)
    repos.usuarios.adicionar(_usuario(cargo, 1, "KM482731"))
    assert repos.usuarios.matricula_existe("KM482731")
    assert not repos.usuarios.matricula_existe("RT095624")
    achado = repos.usuarios.obter_por_matricula("KM482731")
    assert achado is not None
    assert (achado.id, achado.matricula) == (1, "KM482731")
    assert repos.usuarios.obter_por_matricula("RT095624") is None
    assert repos.usuarios.obter(1).matricula == "KM482731"  # type: ignore[union-attr]
    assert [u.matricula for u in repos.usuarios.listar()] == ["KM482731"]


def test_busca_por_matricula_e_exata_e_diferencia_maiusculas(repos: Repositorios) -> None:
    cargo = _cargo(repos)
    repos.usuarios.adicionar(_usuario(cargo, 1, "KM482731"))
    for parcial in ("km482731", "KM4827", "KM482731 ", "", "%"):
        assert repos.usuarios.obter_por_matricula(parcial) is None
        assert not repos.usuarios.matricula_existe(parcial)


def test_matricula_repetida_e_recusada_e_nao_consome_o_identificador(repos: Repositorios) -> None:
    cargo = _cargo(repos)
    repos.usuarios.adicionar(_usuario(cargo, 1, "KM482731"))
    proximo = repos.usuarios.proximo_id()
    with pytest.raises(RegraDeAplicacaoError) as erro:
        repos.usuarios.adicionar(_usuario(cargo, proximo, "KM482731"))
    assert erro.value.codigo is CodigoErroAplicacao.MATRICULA_EM_USO
    assert len(repos.usuarios.listar()) == 1
    assert repos.usuarios.proximo_id() == proximo  # a recusa não gasta o id
    repos.usuarios.adicionar(_usuario(cargo, proximo, "RT095624"))
    assert len(repos.usuarios.listar()) == 2


def test_sem_matricula_o_repositorio_gera_uma_valida_e_livre(repos: Repositorios) -> None:
    cargo = _cargo(repos)
    novos = [_usuario(cargo, i) for i in range(1, 21)]
    for u in novos:
        repos.usuarios.adicionar(u)
    geradas = [u.matricula for u in repos.usuarios.listar()]
    assert all(matricula_valida(m) for m in geradas)
    assert len(set(geradas)) == 20
    assert [u.matricula for u in novos] == geradas  # o objeto recebido também a recebe


def test_salvar_nunca_altera_a_matricula(repos: Repositorios) -> None:
    cargo = _cargo(repos)
    repos.usuarios.adicionar(_usuario(cargo, 1, "KM482731"))
    usuario = repos.usuarios.obter(1)
    assert usuario is not None
    usuario.nome = "Outro nome"
    repos.usuarios.salvar(usuario)
    salvo = repos.usuarios.obter(1)
    assert salvo is not None
    assert (salvo.nome, salvo.matricula) == ("Outro nome", "KM482731")


def test_a_matricula_de_um_usuario_excluido_deixa_de_existir(repos: Repositorios) -> None:
    cargo = _cargo(repos)
    repos.usuarios.adicionar(_usuario(cargo, 1, "KM482731"))
    repos.usuarios.remover(1)
    assert not repos.usuarios.matricula_existe("KM482731")
    assert repos.usuarios.obter_por_matricula("KM482731") is None
