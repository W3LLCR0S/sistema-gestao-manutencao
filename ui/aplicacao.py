"""Classe Aplicacao: login, menu por permissão e laço principal."""

from __future__ import annotations

from typing import Optional

from models import Usuario, RegraNegocioError
from persistencia import Repositorio
from ui.entrada import titulo, ler_int
from ui.tela_equipamentos import TelaEquipamentos
from ui.tela_usuarios import TelaUsuarios
from ui.tela_ordens import TelaOrdens
from ui.tela_tecnico import TelaTecnico
from ui.tela_gestor import TelaGestor


class Aplicacao:
    def __init__(self):
        self.repo = Repositorio()
        self.usuario: Optional[Usuario] = None

        equipamentos = TelaEquipamentos(self)
        usuarios = TelaUsuarios(self)
        ordens = TelaOrdens(self)
        tecnico = TelaTecnico(self)
        gestor = TelaGestor(self)

        # (acesso necessário, rótulo, ação). Ação None = título de seção.
        self.itens_menu = [
            ("Funções compartilhadas", None, None),
            ("ver_equipamentos", "Visualizar equipamentos", equipamentos.visualizar),
            ("ver_os", "Consultar ordens de serviço", ordens.consultar),
            ("abrir_os", "Abrir chamado (nova OS)", ordens.abrir),
            ("ver_disponibilidade", "Disponibilidade dos técnicos", ordens.ver_disponibilidade),
            ("registrar_apontamento", "Incluir apontamento no histórico de uma OS", ordens.incluir_apontamento),
            (None, "Alterar minha disponibilidade", ordens.alterar_minha_disponibilidade),
            ("Técnico", None, None),
            ("diagnosticar", "Registrar diagnóstico", tecnico.diagnosticar),
            ("apontar_reparo", "Apontar reparo (horas, intervenções, peças)", tecnico.apontar_reparo),
            ("atualizar_status", "Atualizar status da OS", tecnico.atualizar_status),
            ("concluir_os", "Conclusão técnica da OS", tecnico.concluir),
            ("Gestor", None, None),
            ("gerir_equipamentos", "Gerenciar equipamentos", equipamentos.gerenciar),
            ("gerir_usuarios", "Gerenciar usuários", usuarios.gerenciar_usuarios),
            ("gerir_usuarios", "Permissões dos cargos", usuarios.gerenciar_cargos),
            ("atribuir_os", "Atribuir / reatribuir OS", gestor.atribuir),
            ("aprovar_os", "Aprovar / encerrar / cancelar OS", gestor.aprovar_ou_cancelar),
        ]

    # ------------------------------------------------------------------
    def executar(self):
        try:
            while self.login():
                self.menu()
        except (KeyboardInterrupt, EOFError):
            print()
        finally:
            self.repo.salvar()
            print("Dados salvos. Até logo!")

    def login(self) -> bool:
        titulo("SISTEMA DE MANUTENÇÃO DE EQUIPAMENTOS — LOGIN")
        for u in self.repo.usuarios:
            print(f"  [{u.id}] {u.nome:<20} {u.cargo}")
        print("  [0] Sair do sistema")
        while True:
            uid = ler_int("ID do usuário")
            if uid == 0:
                return False
            u = self.repo.buscar_usuario(uid)
            if u:
                self.usuario = u
                return True
            print("  ! Usuário não encontrado.")

    def menu(self):
        while True:
            titulo(f"Usuário: {self.usuario.nome}  |  Cargo: {self.usuario.cargo}")
            acoes, secao = {}, None
            for acesso, rotulo, acao in self.itens_menu:
                if acao is None:
                    secao = acesso
                    continue
                if acesso is None or self.usuario.pode(acesso):
                    if secao:
                        print(f"\n -- {secao} --")
                        secao = None
                    acoes[len(acoes) + 1] = acao
                    print(f"  {len(acoes):>2}. {rotulo}")
            print("\n   0. Trocar usuário / sair")
            op = ler_int("Opção")
            if op == 0:
                return
            if op not in acoes:
                print("  ! Opção inválida.")
                continue
            try:
                acoes[op]()
            except RegraNegocioError as erro:
                print(f"  ! {erro}")
            self.repo.atualizar_disponibilidades()
            self.repo.salvar()
