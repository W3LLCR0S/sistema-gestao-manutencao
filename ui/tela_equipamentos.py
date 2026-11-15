"""Tela de Equipamentos: visualização (todos) e gestão do inventário (gestor)."""

from models import Equipamento, RegraNegocioError
from ui.entrada import titulo, pausar, ler, ler_int, confirmar
from ui.tela_base import TelaBase


class TelaEquipamentos(TelaBase):

    def visualizar(self):
        titulo("EQUIPAMENTOS")
        if not self.listar_equipamentos():
            return pausar()
        eid = ler_int("\nID para ver detalhes (ENTER volta)", permitir_vazio=True)
        if eid is not None:
            e = self.repo.buscar_equipamento(eid)
            self.detalhar(e) if e else print("  ! Não encontrado.")
            pausar()

    def detalhar(self, e: Equipamento):
        titulo(f"Equipamento #{e.id} — {e.nome}")
        print(f"  Modelo:          {e.modelo}")
        print(f"  Situação:        {e.situacao}")
        ordens = self.repo.ordens_do_equipamento(e)
        print(f"\n  Ordens de serviço ({len(ordens)}):")
        for o in ordens:
            print(f"   - OS {o.numero:>3} | {str(o.status):<20} | {o.falha[:40]}")
        print("\n  Histórico de intervenções:")
        for o in ordens:
            for s in o.servicos:
                print(f"   OS {o.numero} {s}")

    # ------------------------ gestor ------------------------
    def gerenciar(self):
        self.usuario.exigir("gerir_equipamentos")
        while True:
            titulo("GERENCIAR EQUIPAMENTOS")
            self.listar_equipamentos()
            print("\n  1. Cadastrar  2. Editar  3. Inativar/Reativar  4. Excluir  0. Voltar")
            op = ler_int("Opção")
            if op == 0:
                return
            if op == 1:
                self._cadastrar()
            elif op in (2, 3, 4):
                e = self.repo.buscar_equipamento(ler_int("ID do equipamento"))
                if not e:
                    print("  ! Não encontrado.")
                elif op == 2:
                    self._editar(e)
                elif op == 3:
                    e.reativar() if not e.ativo else e.inativar()
                    print(f"  ✓ Equipamento {'reativado' if e.ativo else 'inativado'}.")
                elif confirmar(f"Excluir '{e.nome}' definitivamente?"):
                    try:
                        self.repo.remover_equipamento(e)
                        print("  ✓ Equipamento excluído.")
                    except RegraNegocioError as erro:
                        print(f"  ! {erro}")
            self.repo.salvar()

    def _cadastrar(self):
        print("\n  Novo equipamento")
        e = Equipamento(
            id=self.repo.proximo_id_equipamento(),
            nome=ler("Nome"),
            modelo=ler("Modelo"),
        )
        self.repo.adicionar_equipamento(e)
        print(f"  ✓ Equipamento #{e.id} cadastrado.")

    def _editar(self, e: Equipamento):
        e.nome = ler("Nome", padrao=e.nome)
        e.modelo = ler("Modelo", padrao=e.modelo)
        print("  ✓ Equipamento atualizado.")
