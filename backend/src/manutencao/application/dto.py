"""Dados de entrada e projeções de leitura da camada de aplicação.

Só o que não é uma entidade: valores que chegam da borda antes de virarem objetos de domínio e
leituras que combinam mais de um agregado. Entidades continuam sendo devolvidas como estão
(cópias, ver ``portas.repositorios``); a borda as converte em esquemas próprios (Fase 04).
"""

from dataclasses import dataclass

from manutencao.domain.enums import Disponibilidade


@dataclass(frozen=True)
class PecaInformada:
    """Peça ou material informado ao apontar um reparo (a quantidade é validada no domínio)."""

    descricao: str
    quantidade: float


@dataclass(frozen=True)
class DisponibilidadeDoTecnico:
    """Uma linha da consulta de disponibilidade: o valor **derivado** e a carga de trabalho.

    ``disponibilidade`` é calculada a partir das OS a cada consulta (D-05): ausência manual,
    senão ``Em atendimento`` se há OS Em Execução, senão ``Disponível``.
    ``carga`` é o número de OS ativas (não encerradas) atribuídas ao técnico.
    """

    id: int
    nome: str
    escala: str
    disponibilidade: Disponibilidade
    carga: int
