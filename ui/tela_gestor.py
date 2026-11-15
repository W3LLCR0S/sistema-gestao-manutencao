"""Tela com as funções exclusivas do Gestor sobre as OS."""

from models import StatusOS, Disponibilidade
from ui.entrada import titulo, pausar, ler, ler_int, confirmar
from ui.tela_base import TelaBase


class TelaGestor(TelaBase):

    def atribuir(self):
        titulo("ATRIBUIÇÃO / REATRIBUIÇÃO DE OS")
        o = self.escolher_os(lambda o: not o.encerrada and o.status != StatusOS.AGUARDANDO_APROVACAO,
                             "Não há OS pendentes de atribuição.")
        if not o:
            return
        tecnicos = sorted(self.repo.tecnicos(), key=self.repo.carga)   # balanceamento de carga
        if not tecnicos:
            print("  ! Nenhum técnico cadastrado.")
            return pausar()
        print(f"\n  {'ID':<4}{'Técnico':<22}{'Status':<17}{'OS ativas'}")
        for t in tecnicos:
            print(f"  {t.id:<4}{t.nome[:21]:<22}{str(t.disponibilidade):<17}{self.repo.carga(t)}")
        tecnico = self.repo.buscar_usuario(ler_int("ID do técnico"))
        if not tecnico:
            print("  ! Técnico não encontrado.")
            return pausar()
        if tecnico.disponibilidade == Disponibilidade.AUSENTE and \
                not confirmar("Técnico está ausente. Atribuir mesmo assim?"):
            return
        o.atribuir(tecnico, self.usuario)
        print(f"  ✓ OS {o.numero} atribuída a {tecnico}.")

    def aprovar_ou_cancelar(self):
        titulo("APROVAÇÃO E ENCERRAMENTO")
        print("  1. Validar reparo e encerrar OS")
        print("  2. Cancelar OS indevida")
        op = ler_int("Opção")
        if op == 1:
            self._validar()
        elif op == 2:
            self._cancelar()

    def _validar(self):
        o = self.escolher_os(lambda o: o.status == StatusOS.AGUARDANDO_APROVACAO,
                             "Nenhuma OS aguardando aprovação.")
        if not o:
            return
        self.detalhar_os(o)
        if confirmar("\nAprovar o reparo e encerrar formalmente a OS?"):
            o.aprovar(self.usuario)
            print("  ✓ OS concluída.")
        else:
            o.reprovar(self.usuario, ler("Motivo da reprovação"))
            print("  OS devolvida ao técnico (Em Execução).")

    def _cancelar(self):
        o = self.escolher_os(lambda o: not o.encerrada, "Nenhuma OS ativa.")
        if not o:
            return
        motivo = ler("Motivo do cancelamento")
        if confirmar(f"Cancelar a OS {o.numero}?"):
            o.cancelar(self.usuario, motivo)
            print("  ✓ OS cancelada.")
