"""Módulo de Equipamentos: visualização (todos) e gestão do inventário (gestor)."""

from app.entrada import titulo, pausar, ler, ler_int, confirmar


def listar_equipamentos(ctx, apenas_ativos=False):
    lista = [e for e in ctx.db["equipamentos"] if e["ativo"] or not apenas_ativos]
    if not lista:
        print("  Nenhum equipamento cadastrado.")
        return lista
    print(f"\n  {'ID':<4}{'Nome':<24}{'Modelo':<14}{'Setor':<14}{'Situação'}")
    for e in lista:
        print(f"  {e['id']:<4}{e['nome'][:23]:<24}{e['modelo'][:13]:<14}{e['setor'][:13]:<14}"
              f"{'Ativo' if e['ativo'] else 'Inativo'}")
    return lista


def detalhar_equipamento(ctx, e):
    titulo(f"Equipamento #{e['id']} — {e['nome']}")
    print(f"  Fabricante:      {e['fabricante']}")
    print(f"  Modelo:          {e['modelo']}")
    print(f"  Nº de série:     {e['num_serie']}")
    print(f"  Setor:           {e['setor']}")
    print(f"  Aquisição:       {e['data_aquisicao']}")
    print(f"  Situação:        {'Ativo' if e['ativo'] else 'Inativo'}")
    ordens = [o for o in ctx.db["ordens"] if o["equipamento_id"] == e["id"]]
    print(f"\n  Ordens de serviço ({len(ordens)}):")
    for o in ordens:
        print(f"   - OS {o['numero']:>3} | {o['status']:<20} | {o['falha'][:40]}")
    hist = [s for s in ctx.db["servicos"] if s["equipamento_id"] == e["id"]]
    print(f"\n  Histórico de intervenções ({len(hist)}):")
    for s in hist:
        print(f"   {s['data']} | OS {s['os_numero']} | {ctx.nome_usuario(s['usuario_id'])} | "
              f"{s['tipo']}: {s['descricao']}")


def ver_equipamentos(ctx):
    titulo("EQUIPAMENTOS")
    if not listar_equipamentos(ctx):
        return pausar()
    eid = ler_int("\nID para ver detalhes (ENTER volta)", permitir_vazio=True)
    if eid is not None:
        e = ctx.buscar("equipamentos", eid)
        detalhar_equipamento(ctx, e) if e else print("  ! Não encontrado.")
        pausar()


def cadastrar_equipamento(ctx):
    print("\n  Novo equipamento")
    e = {
        "id": ctx.prox_id("equipamento"),
        "nome": ler("Nome"),
        "fabricante": ler("Fabricante"),
        "modelo": ler("Modelo"),
        "num_serie": ler("Nº de série"),
        "setor": ler("Setor"),
        "data_aquisicao": ler("Data de aquisição (dd/mm/aaaa)", obrigatorio=False),
        "ativo": True,
    }
    ctx.db["equipamentos"].append(e)
    print(f"  ✓ Equipamento #{e['id']} cadastrado.")


def editar_equipamento(e):
    for campo, rot in [("nome", "Nome"), ("fabricante", "Fabricante"), ("modelo", "Modelo"),
                       ("num_serie", "Nº de série"), ("setor", "Setor"),
                       ("data_aquisicao", "Data de aquisição")]:
        e[campo] = ler(rot, padrao=e[campo])
    print("  ✓ Equipamento atualizado.")


def excluir_equipamento(ctx, e):
    if any(o["equipamento_id"] == e["id"] for o in ctx.db["ordens"]):
        print("  ! Equipamento possui OS vinculadas; use Inativar para preservar o histórico.")
    elif confirmar(f"Excluir '{e['nome']}' definitivamente?"):
        ctx.db["equipamentos"].remove(e)
        print("  ✓ Equipamento excluído.")


def gerir_equipamentos(ctx):
    while True:
        titulo("GERENCIAR EQUIPAMENTOS")
        listar_equipamentos(ctx)
        print("\n  1. Cadastrar  2. Editar  3. Inativar/Reativar  4. Excluir  0. Voltar")
        op = ler_int("Opção")
        if op == 0:
            return
        if op == 1:
            cadastrar_equipamento(ctx)
        elif op in (2, 3, 4):
            e = ctx.buscar("equipamentos", ler_int("ID do equipamento"))
            if not e:
                print("  ! Não encontrado.")
            elif op == 2:
                editar_equipamento(e)
            elif op == 3:
                e["ativo"] = not e["ativo"]
                print(f"  ✓ Equipamento {'reativado' if e['ativo'] else 'inativado'}.")
            else:
                excluir_equipamento(ctx, e)
        ctx.salvar()
