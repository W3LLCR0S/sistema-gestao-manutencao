"""Tela de Ordens de Serviço — funções compartilhadas (gestor e técnico):
consulta com filtros, abertura de chamado, apontamentos e disponibilidade."""

from models import OrdemServico, StatusOS, Criticidade, Disponibilidade
from ui.entrada import titulo, pausar, ler, ler_int, escolher
from ui.tela_base import TelaBase


class TelaOrdens(TelaBase):

    def consultar(self):
        titulo("CONSULTA DE ORDENS DE SERVIÇO")
        ordens = self._filtrar()
        self.listar_os(ordens)
        if ordens:
            n = ler_int("\nNº da OS para detalhes (ENTER volta)", permitir_vazio=True)
            if n is not None:
                o = self.repo.buscar_os(n)
                self.detalhar_os(o) if o else print("  ! OS não encontrada.")
        pausar()

    def _filtrar(self):
        filtro = escolher("Filtro", ["Todas", "Em aberto", "Encerradas (concluídas/canceladas)",
                                     "Por status", "Por equipamento", "Por técnico", "Por criticidade"])
        ordens = self.repo.ordens
        if filtro == "Em aberto":
            return [o for o in ordens if not o.encerrada]
        if filtro.startswith("Encerradas"):
            return [o for o in ordens if o.encerrada]
        if filtro == "Por status":
            status = escolher("Status", StatusOS)
            return [o for o in ordens if o.status == status]
        if filtro == "Por equipamento":
            self.listar_equipamentos()
            eq = self.repo.buscar_equipamento(ler_int("ID do equipamento"))
            return [o for o in ordens if o.equipamento is eq]
        if filtro == "Por técnico":
            tecnico = escolher("Técnico", self.repo.tecnicos())
            return [o for o in ordens if o.esta_com(tecnico)]
        if filtro == "Por criticidade":
            crit = escolher("Criticidade", Criticidade)
            return [o for o in ordens if o.criticidade == crit]
        return list(ordens)

    def abrir(self):
        titulo("ABERTURA DE CHAMADO")
        if not self.listar_equipamentos(apenas_ativos=True):
            return pausar()
        eq = self.repo.buscar_equipamento(ler_int("ID do equipamento afetado"))
        if not eq:
            print("  ! Equipamento não encontrado.")
            return pausar()
        falha = ler("Descrição da falha / problema")
        criticidade = escolher("Criticidade", Criticidade)
        os_ = OrdemServico.abrir(self.repo.proximo_numero_os(), eq, falha, criticidade, self.usuario)
        self.repo.adicionar_os(os_)
        print(f"  ✓ OS nº {os_.numero} aberta.")
        pausar()

    def incluir_apontamento(self):
        titulo("INCLUIR APONTAMENTO NO HISTÓRICO")
        o = self.escolher_os(lambda o: True, "Nenhuma OS cadastrada.")
        if o:
            o.adicionar_apontamento(self.usuario, ler("Descrição do apontamento"))
            print("  ✓ Apontamento registrado.")

    # ------------------------ disponibilidade ------------------------
    def ver_disponibilidade(self):
        titulo("DISPONIBILIDADE DOS TÉCNICOS")
        print(f"\n  {'ID':<4}{'Técnico':<22}{'Escala':<20}{'Status':<17}{'OS ativas'}")
        for t in self.repo.tecnicos():
            print(f"  {t.id:<4}{t.nome[:21]:<22}{t.escala[:19]:<20}"
                  f"{str(t.disponibilidade):<17}{self.repo.carga(t)}")
        pausar()

    def alterar_minha_disponibilidade(self):
        print(f"\n  Status atual: {self.usuario.disponibilidade}")
        self.usuario.disponibilidade = escolher("Novo status", Disponibilidade)
        print("  ✓ Disponibilidade atualizada.")
