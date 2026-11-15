"""Tela com as funções exclusivas do Técnico."""

from models import PecaMaterial, StatusOS, STATUS_TECNICO
from ui.entrada import titulo, pausar, ler, ler_float, escolher, confirmar
from ui.tela_base import TelaBase

EM_ANDAMENTO = (StatusOS.ATRIBUIDA, StatusOS.EM_EXECUCAO, StatusOS.AGUARDANDO_PECA)


class TelaTecnico(TelaBase):

    def _minhas(self, *status):
        return lambda o: o.esta_com(self.usuario) and o.status in status

    def diagnosticar(self):
        titulo("REGISTRO DE DIAGNÓSTICO")
        o = self.escolher_os(self._minhas(*EM_ANDAMENTO), "Você não possui OS em andamento.")
        if not o:
            return
        parecer = ler("Parecer técnico inicial", padrao=o.diagnostico or None)
        causa = ler("Causa-raiz identificada", padrao=o.causa_raiz or None)
        o.registrar_diagnostico(self.usuario, parecer, causa)
        print("  ✓ Diagnóstico registrado.")

    def apontar_reparo(self):
        titulo("APONTAMENTO DE REPARO")
        o = self.escolher_os(self._minhas(*EM_ANDAMENTO), "Você não possui OS em andamento.")
        if not o:
            return
        horas = ler_float("Horas trabalhadas neste apontamento")
        intervencao = ler("Intervenção realizada")
        pecas = []
        while confirmar("Adicionar peça/material utilizado?"):
            pecas.append(PecaMaterial(ler("  Descrição"), ler_float("  Quantidade", 0.01)))
        o.apontar_reparo(self.usuario, horas, intervencao, pecas)
        print("  ✓ Reparo registrado.")

    def atualizar_status(self):
        titulo("ATUALIZAÇÃO DE STATUS")
        o = self.escolher_os(self._minhas(StatusOS.ATRIBUIDA, *STATUS_TECNICO),
                             "Você não possui OS com status alterável.")
        if not o:
            return
        print(f"  Status atual: {o.status}")
        novo = escolher("Novo status", [s for s in STATUS_TECNICO if s != o.status])
        o.alterar_status(self.usuario, novo)
        print("  ✓ Status atualizado.")

    def concluir(self):
        titulo("CONCLUSÃO TÉCNICA DA OS")
        o = self.escolher_os(self._minhas(StatusOS.REPARO_FINALIZADO),
                             "Nenhuma OS sua com status 'Reparo Finalizado'.")
        if not o:
            return
        teste = ler("Descreva o teste funcional realizado")
        passou = confirmar("O equipamento passou no teste funcional?")
        if o.concluir_tecnicamente(self.usuario, teste, passou):
            print("  ✓ OS submetida para aprovação do gestor.")
        else:
            print("  OS permanece em 'Reparo Finalizado'. Registre novas intervenções se necessário.")
            pausar()
