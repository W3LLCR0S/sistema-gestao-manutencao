"""Módulo de Ordens de Serviço — funções compartilhadas (gestor e técnico):
listagem, detalhes, consulta com filtros, abertura de chamado e apontamentos."""

from app.constantes import STATUS_OS, STATUS_FINAIS, CRITICIDADES
from app.entrada import titulo, pausar, ler, ler_int, escolher, agora
from app.modulos.equipamentos import listar_equipamentos


def listar_os(ctx, ordens):
    if not ordens:
        print("  Nenhuma OS encontrada.")
        return
    print(f"\n  {'Nº':<5}{'Equipamento':<22}{'Criticidade':<12}{'Status':<22}{'Técnico'}")
    for o in ordens:
        print(f"  {o['numero']:<5}{ctx.nome_equip(o['equipamento_id'])[:21]:<22}"
              f"{o['criticidade']:<12}{o['status']:<22}{ctx.nome_usuario(o['tecnico_id'])}")


def detalhar_os(ctx, o):
    titulo(f"ORDEM DE SERVIÇO Nº {o['numero']}")
    print(f"  Equipamento:        {ctx.nome_equip(o['equipamento_id'])} (#{o['equipamento_id']})")
    print(f"  Falha relatada:     {o['falha']}")
    print(f"  Criticidade:        {o['criticidade']}")
    print(f"  Status:             {o['status']}")
    print(f"  Aberta por:         {ctx.nome_usuario(o['aberta_por'])} em {o['data_abertura']}")
    print(f"  Técnico atribuído:  {ctx.nome_usuario(o['tecnico_id'])}")
    print(f"  Diagnóstico:        {o['diagnostico'] or '—'}")
    print(f"  Causa-raiz:         {o['causa_raiz'] or '—'}")
    print(f"  Horas trabalhadas:  {o['horas_trabalhadas']:.1f} h")
    print("  Intervenções realizadas:")
    for i in o["intervencoes"] or ["—"]:
        print(f"     - {i}")
    print("  Peças/materiais utilizados:")
    for p in o["pecas"] or [None]:
        print(f"     - {p['quantidade']:g}x {p['descricao']}" if p else "     - —")
    if o.get("teste_funcional"):
        print(f"  Teste funcional:    {o['teste_funcional']}")
    if o.get("data_conclusao"):
        print(f"  Encerrada em:       {o['data_conclusao']}")
    if o.get("motivo_cancelamento"):
        print(f"  Motivo cancelamento: {o['motivo_cancelamento']}")
    hist = [s for s in ctx.db["servicos"] if s["os_numero"] == o["numero"]]
    print(f"\n  Histórico ({len(hist)} registros):")
    for s in hist:
        print(f"   {s['data']} | {ctx.nome_usuario(s['usuario_id'])} | {s['tipo']}: {s['descricao']}")


def escolher_os(ctx, filtro, vazio_msg):
    """Lista as OS que passam no filtro e pede o número de uma delas."""
    ordens = [o for o in ctx.db["ordens"] if filtro(o)]
    if not ordens:
        print(f"  {vazio_msg}")
        pausar()
        return None
    listar_os(ctx, ordens)
    n = ler_int("\nNº da OS (ENTER cancela)", permitir_vazio=True)
    o = next((x for x in ordens if x["numero"] == n), None)
    if n is not None and not o:
        print("  ! OS não está na lista.")
    return o


def filtrar_os(ctx):
    filtro = escolher("Filtro", ["Todas", "Em aberto (não encerradas)", "Encerradas (concluídas/canceladas)",
                                 "Por status", "Por equipamento", "Por técnico", "Por criticidade"])
    ordens = ctx.db["ordens"]
    if filtro.startswith("Em aberto"):
        return [o for o in ordens if o["status"] not in STATUS_FINAIS]
    if filtro.startswith("Encerradas"):
        return [o for o in ordens if o["status"] in STATUS_FINAIS]
    if filtro == "Por status":
        st = escolher("Status", STATUS_OS)
        return [o for o in ordens if o["status"] == st]
    if filtro == "Por equipamento":
        listar_equipamentos(ctx)
        eid = ler_int("ID do equipamento")
        return [o for o in ordens if o["equipamento_id"] == eid]
    if filtro == "Por técnico":
        for t in ctx.tecnicos():
            print(f"  [{t['id']}] {t['nome']}")
        tid = ler_int("ID do técnico")
        return [o for o in ordens if o["tecnico_id"] == tid]
    if filtro == "Por criticidade":
        cr = escolher("Criticidade", CRITICIDADES)
        return [o for o in ordens if o["criticidade"] == cr]
    return ordens


def consultar_os(ctx):
    titulo("CONSULTA DE ORDENS DE SERVIÇO")
    ordens = filtrar_os(ctx)
    listar_os(ctx, ordens)
    if ordens:
        n = ler_int("\nNº da OS para detalhes (ENTER volta)", permitir_vazio=True)
        if n is not None:
            o = ctx.buscar("ordens", n, "numero")
            detalhar_os(ctx, o) if o else print("  ! OS não encontrada.")
    pausar()


def abrir_os(ctx):
    titulo("ABERTURA DE CHAMADO")
    if not listar_equipamentos(ctx, apenas_ativos=True):
        return pausar()
    e = ctx.buscar("equipamentos", ler_int("ID do equipamento afetado"))
    if not e or not e["ativo"]:
        print("  ! Equipamento inválido ou inativo.")
        return pausar()
    falha = ler("Descrição da falha / problema")
    crit = escolher("Criticidade", CRITICIDADES)
    o = {
        "numero": ctx.prox_id("os"),
        "equipamento_id": e["id"],
        "falha": falha,
        "criticidade": crit,
        "status": "Aberta",
        "aberta_por": ctx.usuario["id"],
        "data_abertura": agora(),
        "tecnico_id": None,
        "diagnostico": "",
        "causa_raiz": "",
        "horas_trabalhadas": 0.0,
        "intervencoes": [],
        "pecas": [],
        "teste_funcional": "",
        "data_conclusao": None,
        "motivo_cancelamento": "",
    }
    ctx.db["ordens"].append(o)
    ctx.registrar_servico(o, "Abertura", f"[{crit}] {falha}")
    print(f"  ✓ OS nº {o['numero']} aberta.")
    pausar()


def registrar_observacao(ctx):
    titulo("INCLUIR APONTAMENTO NO HISTÓRICO")
    o = escolher_os(ctx, lambda o: True, "Nenhuma OS cadastrada.")
    if o:
        ctx.registrar_servico(o, "Apontamento", ler("Descrição do apontamento"))
        print("  ✓ Apontamento registrado.")
