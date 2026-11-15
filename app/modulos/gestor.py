"""Funções exclusivas do Gestor sobre as OS: atribuição/reatribuição,
aprovação, encerramento e cancelamento."""

from app.constantes import STATUS_FINAIS
from app.entrada import titulo, pausar, ler, ler_int, confirmar, agora
from app.modulos.ordens import escolher_os, detalhar_os


def atribuir_os(ctx):
    titulo("ATRIBUIÇÃO / REATRIBUIÇÃO DE OS")
    o = escolher_os(ctx, lambda o: o["status"] not in STATUS_FINAIS + ["Aguardando Aprovação"],
                    "Não há OS pendentes de atribuição.")
    if not o:
        return
    tecnicos = ctx.tecnicos()
    if not tecnicos:
        print("  ! Nenhum técnico cadastrado.")
        return pausar()
    # técnicos ordenados pela carga de trabalho (balanceamento)
    print(f"\n  {'ID':<4}{'Técnico':<22}{'Status':<17}{'OS ativas'}")
    for t in sorted(tecnicos, key=lambda t: ctx.carga(t["id"])):
        print(f"  {t['id']:<4}{t['nome'][:21]:<22}{t['disponibilidade']:<17}{ctx.carga(t['id'])}")
    t = ctx.buscar("usuarios", ler_int("ID do técnico"))
    if not t or t not in tecnicos:
        print("  ! Técnico inválido.")
        return pausar()
    if t["id"] == o["tecnico_id"]:
        print("  ! OS já está atribuída a este técnico.")
        return pausar()
    if t["disponibilidade"] == "Ausente" and not confirmar("Técnico está ausente. Atribuir mesmo assim?"):
        return
    anterior = o["tecnico_id"]
    o["tecnico_id"] = t["id"]
    if o["status"] == "Aberta":
        o["status"] = "Atribuída"
    if anterior:
        ctx.registrar_servico(o, "Reatribuição", f"{ctx.nome_usuario(anterior)} → {t['nome']}")
        ctx.atualizar_disponibilidade(anterior)
    else:
        ctx.registrar_servico(o, "Atribuição", f"Atribuída a {t['nome']}")
    ctx.atualizar_disponibilidade(t["id"])
    print(f"  ✓ OS {o['numero']} atribuída a {t['nome']}.")


def validar_e_encerrar(ctx):
    o = escolher_os(ctx, lambda o: o["status"] == "Aguardando Aprovação",
                    "Nenhuma OS aguardando aprovação.")
    if not o:
        return
    detalhar_os(ctx, o)
    if confirmar("\nAprovar o reparo e encerrar formalmente a OS?"):
        o["status"] = "Concluída"
        o["data_conclusao"] = agora()
        ctx.registrar_servico(o, "Encerramento", "Reparo validado e OS encerrada pelo gestor.")
        print("  ✓ OS concluída.")
    else:
        motivo = ler("Motivo da reprovação")
        o["status"] = "Em Execução"
        ctx.registrar_servico(o, "Reprovação", f"Devolvida ao técnico: {motivo}")
        print("  OS devolvida ao técnico (Em Execução).")
    if o["tecnico_id"]:
        ctx.atualizar_disponibilidade(o["tecnico_id"])


def cancelar_os(ctx):
    o = escolher_os(ctx, lambda o: o["status"] not in STATUS_FINAIS, "Nenhuma OS ativa.")
    if not o:
        return
    motivo = ler("Motivo do cancelamento")
    if confirmar(f"Cancelar a OS {o['numero']}?"):
        o["status"] = "Cancelada"
        o["motivo_cancelamento"] = motivo
        o["data_conclusao"] = agora()
        ctx.registrar_servico(o, "Cancelamento", motivo)
        if o["tecnico_id"]:
            ctx.atualizar_disponibilidade(o["tecnico_id"])
        print("  ✓ OS cancelada.")


def aprovar_os(ctx):
    titulo("APROVAÇÃO E ENCERRAMENTO")
    print("  1. Validar reparo e encerrar OS")
    print("  2. Cancelar OS indevida")
    op = ler_int("Opção")
    if op == 1:
        validar_e_encerrar(ctx)
    elif op == 2:
        cancelar_os(ctx)
