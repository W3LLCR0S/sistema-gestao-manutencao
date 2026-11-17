"""Apoio comum aos serviços: carregar o ator e tratar a ausência de um objeto."""

from typing import TypeVar

from manutencao.application.erros import NaoEncontradoError
from manutencao.application.portas.repositorios import UsuarioRepository
from manutencao.domain.usuario import Usuario

T = TypeVar("T")


def exigir_encontrado(entidade: str, identificador: int, achado: T | None) -> T:
    """Devolve ``achado`` ou levanta ``NaoEncontradoError`` (o repositório devolve ``None``)."""
    if achado is None:
        raise NaoEncontradoError(entidade, identificador)
    return achado


def carregar_ator(usuarios: UsuarioRepository, ator_id: int) -> Usuario:
    """O usuário que executa o caso de uso, com o cargo e as permissões **atuais**.

    Cada caso de uso carrega o ator de novo: uma permissão alterada vale na chamada seguinte.
    Quem é o ator (autenticação) é da borda; aqui só se confia no identificador recebido.
    """
    return exigir_encontrado("Usuário", ator_id, usuarios.obter(ator_id))
