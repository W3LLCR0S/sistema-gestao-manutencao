"""Módulo de Usuários, Cargos e Permissões (gestor)."""

from app.constantes import PERMISSOES, DISPONIBILIDADES
from app.entrada import titulo, ler, ler_int, escolher, confirmar


# ============================== USUÁRIOS ==============================
def listar_usuarios(ctx):
    print(f"\n  {'ID':<4}{'Nome':<22}{'Cargo':<12}{'E-mail':<24}{'Disponibilidade'}")
    for u in ctx.db["usuarios"]:
        c = ctx.cargo_de(u)
        print(f"  {u['id']:<4}{u['nome'][:21]:<22}{(c['nome'] if c else '—')[:11]:<12}"
              f"{u['email'][:23]:<24}{u['disponibilidade']}")


def escolher_cargo(ctx, permitir_vazio=False):
    nomes = [c["nome"] for c in ctx.db["cargos"]]
    nome = escolher("Cargo", nomes, permitir_vazio)
    return ctx.buscar("cargos", nome, "nome") if nome else None


def cadastrar_usuario(ctx):
    print("\n  Novo usuário")
    nome = ler("Nome")
    email = ler("E-mail", obrigatorio=False)
    escala = ler("Escala (ex.: Seg-Sex 08h-17h)", obrigatorio=False)
    cargo = escolher_cargo(ctx)
    u = {"id": ctx.prox_id("usuario"), "nome": nome, "cargo_id": cargo["id"],
         "email": email, "escala": escala, "disponibilidade": "Disponível"}
    ctx.db["usuarios"].append(u)
    print(f"  ✓ Usuário #{u['id']} cadastrado como {cargo['nome']}.")


def editar_usuario(ctx, u):
    u["nome"] = ler("Nome", padrao=u["nome"])
    u["email"] = ler("E-mail", padrao=u["email"])
    u["escala"] = ler("Escala", padrao=u["escala"])
    print(f"  Cargo atual: {ctx.cargo_de(u)['nome']}")
    novo = escolher_cargo(ctx, permitir_vazio=True)
    if novo:
        if u is ctx.usuario and "gerir_usuarios" not in novo["permissoes"]:
            print("  ! Você não pode remover o próprio acesso de gestão.")
        else:
            u["cargo_id"] = novo["id"]
    print(f"  Disponibilidade atual: {u['disponibilidade']}")
    disp = escolher("Disponibilidade", DISPONIBILIDADES, permitir_vazio=True)
    if disp:
        u["disponibilidade"] = disp
    print("  ✓ Usuário atualizado.")


def excluir_usuario(ctx, u):
    if u is ctx.usuario:
        print("  ! Você não pode excluir o próprio usuário.")
    elif ctx.carga(u["id"]):
        print("  ! Usuário possui OS ativas. Reatribua-as antes de excluir.")
    elif confirmar(f"Excluir '{u['nome']}'?"):
        ctx.db["usuarios"].remove(u)
        print("  ✓ Usuário excluído.")


def gerir_usuarios(ctx):
    while True:
        titulo("GERENCIAR USUÁRIOS")
        listar_usuarios(ctx)
        print("\n  1. Cadastrar  2. Editar  3. Excluir  0. Voltar")
        op = ler_int("Opção")
        if op == 0:
            return
        if op == 1:
            cadastrar_usuario(ctx)
        elif op in (2, 3):
            u = ctx.buscar("usuarios", ler_int("ID do usuário"))
            if not u:
                print("  ! Não encontrado.")
            elif op == 2:
                editar_usuario(ctx, u)
            else:
                excluir_usuario(ctx, u)
        ctx.salvar()


# ============================== CARGOS ==============================
def listar_cargos(ctx):
    for c in ctx.db["cargos"]:
        print(f"\n  [{c['id']}] {c['nome']}")
        for p in c["permissoes"]:
            print(f"      • {PERMISSOES.get(p, p)}")


def selecionar_permissoes(ctx, cargo, novo):
    """Pede ao usuário os números das permissões. Retorna a lista ou None se nada mudar."""
    chaves = list(PERMISSOES)
    print("\n  Permissões disponíveis:")
    for i, k in enumerate(chaves, 1):
        marca = "x" if k in cargo["permissoes"] else " "
        print(f"   [{marca}] {i:>2}. {PERMISSOES[k]}")
    txt = ler("Números das permissões separados por vírgula",
              obrigatorio=novo, padrao=None if novo else "")
    if not txt:
        return None
    try:
        return [chaves[int(x) - 1] for x in txt.split(",") if x.strip()]
    except (ValueError, IndexError):
        print("  ! Seleção inválida.")
        return None


def salvar_cargo(ctx, novo):
    if novo:
        cargo = {"id": ctx.prox_id("cargo"), "nome": ler("Nome do cargo"), "permissoes": []}
    else:
        cargo = ctx.buscar("cargos", ler_int("ID do cargo"))
        if not cargo:
            print("  ! Não encontrado.")
            return
    sel = selecionar_permissoes(ctx, cargo, novo)
    if sel is not None:
        if not novo and cargo["id"] == ctx.usuario["cargo_id"] and "gerir_usuarios" not in sel:
            print("  ! Você não pode remover do seu próprio cargo o acesso de gestão.")
            return
        cargo["permissoes"] = sel
    if novo:
        ctx.db["cargos"].append(cargo)
    print(f"  ✓ Cargo '{cargo['nome']}' salvo.")


def excluir_cargo(ctx):
    cargo = ctx.buscar("cargos", ler_int("ID do cargo"))
    if not cargo:
        print("  ! Não encontrado.")
    elif any(u["cargo_id"] == cargo["id"] for u in ctx.db["usuarios"]):
        print("  ! Há usuários com este cargo.")
    elif confirmar(f"Excluir o cargo '{cargo['nome']}'?"):
        ctx.db["cargos"].remove(cargo)
        print("  ✓ Cargo excluído.")


def gerir_cargos(ctx):
    while True:
        titulo("CARGOS E PERMISSÕES")
        listar_cargos(ctx)
        print("\n  1. Criar cargo  2. Editar permissões  3. Excluir cargo  0. Voltar")
        op = ler_int("Opção")
        if op == 0:
            return
        if op == 1:
            salvar_cargo(ctx, novo=True)
        elif op == 2:
            salvar_cargo(ctx, novo=False)
        elif op == 3:
            excluir_cargo(ctx)
        ctx.salvar()
