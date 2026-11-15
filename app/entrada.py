"""Funções de entrada e saída no terminal."""

from datetime import datetime


def agora():
    return datetime.now().strftime("%d/%m/%Y %H:%M")


def titulo(txt):
    print("\n" + "=" * 60)
    print(f" {txt}")
    print("=" * 60)


def pausar():
    input("\nPressione ENTER para continuar...")


def ler(msg, obrigatorio=True, padrao=None):
    sufixo = f" [{padrao}]" if padrao not in (None, "") else ""
    while True:
        txt = input(f"{msg}{sufixo}: ").strip()
        if not txt and padrao is not None:
            return padrao
        if txt or not obrigatorio:
            return txt
        print("  ! Campo obrigatório.")


def ler_int(msg, permitir_vazio=False):
    while True:
        txt = input(f"{msg}: ").strip()
        if not txt and permitir_vazio:
            return None
        try:
            return int(txt)
        except ValueError:
            print("  ! Digite um número inteiro.")


def ler_float(msg, minimo=0.0):
    while True:
        txt = input(f"{msg}: ").strip().replace(",", ".")
        try:
            v = float(txt)
            if v < minimo:
                raise ValueError
            return v
        except ValueError:
            print(f"  ! Digite um número maior ou igual a {minimo}.")


def escolher(msg, opcoes, permitir_vazio=False):
    """Mostra opções numeradas e devolve a opção escolhida (ou None)."""
    for i, op in enumerate(opcoes, 1):
        print(f"  {i}. {op}")
    while True:
        n = ler_int(msg + (" (ENTER p/ manter)" if permitir_vazio else ""), permitir_vazio)
        if n is None:
            return None
        if 1 <= n <= len(opcoes):
            return opcoes[n - 1]
        print("  ! Opção inválida.")


def confirmar(msg):
    return input(f"{msg} (s/n): ").strip().lower() in ("s", "sim")
