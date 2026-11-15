"""Funções exclusivas do Técnico: diagnóstico, apontamento de reparo,
atualização de status e conclusão técnica da OS."""

from app.constantes import STATUS_TECNICO
from app.entrada import titulo, pausar, ler, ler_float, escolher, confirmar
from app.modulos.ordens import escolher_os


def _minhas_os(ctx, status_validos):
    return lambda o: o["tecnico_id"] == ctx.usuario["id"] and o["status"] in status_validos


def diagnosticar(ctx):
    titulo("REGISTRO DE DIAGNÓSTICO")
    o = escolher_os(ctx, _minhas_os(ctx, ["Atribuída", "Em Execução", "Aguardando Peça"]),
                    "Você não possui OS atribuídas para diagnóstico.")
    if not o:
        return
    o["diagnostico"] = ler("Parecer técnico inicial", padrao=o["diagnostico"] or None)
    o["causa_raiz"] = ler("Causa-raiz identificada", padrao=o["causa_raiz"] or None)
    ctx.registrar_servico(o, "Diagnóstico", f"{o['diagnostico']} | Causa-raiz: {o['causa_raiz']}")
    print("  ✓ Diagnóstico registrado.")


def apontar_reparo(ctx):
    titulo("APONTAMENTO DE REPARO")
    o = escolher_os(ctx, _minhas_os(ctx, ["Atribuída", "Em Execução", "Aguardando Peça"]),
                    "Você não possui OS em andamento.")
    if not o:
        return
    horas = ler_float("Horas trabalhadas neste apontamento")
    intervencao = ler("Intervenção realizada")
    pecas = []
    while confirmar("Adicionar peça/material utilizado?"):
        pecas.append({"descricao": ler("  Descrição"), "quantidade": ler_float("  Quantidade", 0.01)})
    o["horas_trabalhadas"] += horas
    o["intervencoes"].append(intervencao)
    o["pecas"].extend(pecas)
    if o["status"] == "Atribuída":
        o["status"] = "Em Execução"
        ctx.registrar_servico(o, "Status", "Atribuída → Em Execução")
    txt_pecas = ", ".join(f"{p['quantidade']:g}x {p['descricao']}" for p in pecas) or "nenhuma"
    ctx.registrar_servico(o, "Reparo", f"{intervencao} ({horas:g} h; peças: {txt_pecas})")
    ctx.atualizar_disponibilidade(ctx.usuario["id"])
    print("  ✓ Apontamento registrado.")


def atualizar_status(ctx):
    titulo("ATUALIZAÇÃO DE STATUS")
    o = escolher_os(ctx, _minhas_os(ctx, ["Atribuída"] + STATUS_TECNICO),
                    "Você não possui OS com status alterável.")
    if not o:
        return
    print(f"  Status atual: {o['status']}")
    novo = escolher("Novo status", [s for s in STATUS_TECNICO if s != o["status"]])
    if novo == "Reparo Finalizado" and not o["intervencoes"]:
        print("  ! Registre ao menos uma intervenção antes de finalizar o reparo.")
        return pausar()
    ctx.registrar_servico(o, "Status", f"{o['status']} → {novo}")
    o["status"] = novo
    ctx.atualizar_disponibilidade(ctx.usuario["id"])
    print("  ✓ Status atualizado.")


def concluir_tecnico(ctx):
    titulo("CONCLUSÃO TÉCNICA DA OS")
    o = escolher_os(ctx, _minhas_os(ctx, ["Reparo Finalizado"]),
                    "Nenhuma OS sua com status 'Reparo Finalizado'.")
    if not o:
        return
    if not o["diagnostico"]:
        print("  ! Registre o diagnóstico antes de concluir.")
        return pausar()
    teste = ler("Descreva o teste funcional realizado")
    if not confirmar("O equipamento passou no teste funcional?"):
        ctx.registrar_servico(o, "Teste funcional", f"Reprovado: {teste}")
        print("  OS permanece em 'Reparo Finalizado'. Registre novas intervenções se necessário.")
        return pausar()
    o["teste_funcional"] = teste
    o["status"] = "Aguardando Aprovação"
    ctx.registrar_servico(o, "Conclusão técnica", f"Teste aprovado: {teste}. Enviada para aprovação.")
    ctx.atualizar_disponibilidade(ctx.usuario["id"])
    print("  ✓ OS submetida para aprovação do gestor.")
