"""Módulo de Disponibilidade dos técnicos (escala e status atual)."""

from app.constantes import DISPONIBILIDADES
from app.entrada import titulo, pausar, escolher


def ver_disponibilidade(ctx):
    titulo("DISPONIBILIDADE DOS TÉCNICOS")
    print(f"\n  {'ID':<4}{'Técnico':<22}{'Escala':<20}{'Status':<17}{'OS ativas'}")
    for t in ctx.tecnicos():
        print(f"  {t['id']:<4}{t['nome'][:21]:<22}{t['escala'][:19]:<20}"
              f"{t['disponibilidade']:<17}{ctx.carga(t['id'])}")
    pausar()


def alterar_minha_disponibilidade(ctx):
    print(f"\n  Status atual: {ctx.usuario['disponibilidade']}")
    ctx.usuario["disponibilidade"] = escolher("Novo status", DISPONIBILIDADES)
    print("  ✓ Disponibilidade atualizada.")
