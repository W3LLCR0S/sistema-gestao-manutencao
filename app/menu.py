"""Login e menu principal. As opções exibidas dependem das permissões do cargo."""

from app.entrada import titulo, ler_int
from app.modulos import equipamentos, usuarios, disponibilidade, ordens, tecnico, gestor

# (permissão, rótulo, função) — função None indica cabeçalho de seção
ITENS_MENU = [
    ("Funções compartilhadas", None, None),
    ("ver_equipamentos", "Visualizar equipamentos", equipamentos.ver_equipamentos),
    ("ver_os", "Consultar ordens de serviço", ordens.consultar_os),
    ("abrir_os", "Abrir chamado (nova OS)", ordens.abrir_os),
    ("ver_disponibilidade", "Disponibilidade dos técnicos", disponibilidade.ver_disponibilidade),
    ("registrar_observacao", "Incluir apontamento no histórico de uma OS", ordens.registrar_observacao),
    (None, "Alterar minha disponibilidade", disponibilidade.alterar_minha_disponibilidade),
    ("Técnico", None, None),
    ("diagnosticar", "Registrar diagnóstico", tecnico.diagnosticar),
    ("apontar_reparo", "Apontar reparo (horas, intervenções, peças)", tecnico.apontar_reparo),
    ("atualizar_status", "Atualizar status da OS", tecnico.atualizar_status),
    ("concluir_tecnico", "Conclusão técnica da OS", tecnico.concluir_tecnico),
    ("Gestor", None, None),
    ("gerir_equipamentos", "Gerenciar equipamentos", equipamentos.gerir_equipamentos),
    ("gerir_usuarios", "Gerenciar usuários", usuarios.gerir_usuarios),
    ("gerir_usuarios", "Gerenciar cargos e permissões", usuarios.gerir_cargos),
    ("atribuir_os", "Atribuir / reatribuir OS", gestor.atribuir_os),
    ("aprovar_os", "Aprovar / encerrar / cancelar OS", gestor.aprovar_os),
]


def login(ctx):
    titulo("SISTEMA DE MANUTENÇÃO DE EQUIPAMENTOS — LOGIN")
    for u in ctx.db["usuarios"]:
        c = ctx.cargo_de(u)
        print(f"  [{u['id']}] {u['nome']:<20} {c['nome'] if c else '—'}")
    print("  [0] Sair do sistema")
    while True:
        uid = ler_int("ID do usuário")
        if uid == 0:
            return False
        u = ctx.buscar("usuarios", uid)
        if u:
            ctx.usuario = u
            return True
        print("  ! Usuário não encontrado.")


def menu_principal(ctx):
    while True:
        cargo = ctx.cargo_de(ctx.usuario)
        titulo(f"Usuário: {ctx.usuario['nome']}  |  Cargo: {cargo['nome'] if cargo else '—'}")
        acoes, secao_pendente = {}, None
        for perm, rotulo, func in ITENS_MENU:
            if func is None:
                secao_pendente = perm
                continue
            if perm is None or ctx.pode(perm):
                if secao_pendente:
                    print(f"\n -- {secao_pendente} --")
                    secao_pendente = None
                n = len(acoes) + 1
                acoes[n] = func
                print(f"  {n:>2}. {rotulo}")
        print("\n   0. Trocar usuário / sair")
        op = ler_int("Opção")
        if op == 0:
            return
        if op in acoes:
            acoes[op](ctx)
            ctx.salvar()
        else:
            print("  ! Opção inválida.")
