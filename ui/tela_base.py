"""Classe base das telas, com listagens reutilizadas por todas elas."""

from __future__ import annotations

from typing import Callable, Optional, TYPE_CHECKING

from models import OrdemServico, Equipamento
from ui.entrada import titulo, pausar, ler_int

if TYPE_CHECKING:
    from ui.aplicacao import Aplicacao


class TelaBase:
    def __init__(self, app: Aplicacao):
        self.app = app

    @property
    def repo(self):
        return self.app.repo

    @property
    def usuario(self):
        return self.app.usuario

    # ------------------------ equipamentos ------------------------
    def listar_equipamentos(self, apenas_ativos: bool = False) -> list[Equipamento]:
        lista = [e for e in self.repo.equipamentos if e.ativo or not apenas_ativos]
        if not lista:
            print("  Nenhum equipamento cadastrado.")
            return lista
        print(f"\n  {'ID':<4}{'Nome':<26}{'Modelo':<16}{'Situação'}")
        for e in lista:
            print(f"  {e.id:<4}{e.nome[:25]:<26}{e.modelo[:15]:<16}{e.situacao}")
        return lista

    # ------------------------ ordens de serviço ------------------------
    def listar_os(self, ordens: list[OrdemServico]) -> None:
        if not ordens:
            print("  Nenhuma OS encontrada.")
            return
        print(f"\n  {'Nº':<5}{'Equipamento':<22}{'Criticidade':<12}{'Status':<22}{'Técnico'}")
        for o in ordens:
            tecnico = o.tecnico_atribuido.nome if o.tecnico_atribuido else "—"
            print(f"  {o.numero:<5}{o.equipamento.nome[:21]:<22}{str(o.criticidade):<12}"
                  f"{str(o.status):<22}{tecnico}")

    def escolher_os(self, filtro: Callable[[OrdemServico], bool], vazio_msg: str) -> Optional[OrdemServico]:
        ordens = [o for o in self.repo.ordens if filtro(o)]
        if not ordens:
            print(f"  {vazio_msg}")
            pausar()
            return None
        self.listar_os(ordens)
        n = ler_int("\nNº da OS (ENTER cancela)", permitir_vazio=True)
        escolhida = next((o for o in ordens if o.numero == n), None)
        if n is not None and not escolhida:
            print("  ! OS não está na lista.")
        return escolhida

    def detalhar_os(self, o: OrdemServico) -> None:
        titulo(f"ORDEM DE SERVIÇO Nº {o.numero}")
        print(f"  Equipamento:        {o.equipamento.nome} (#{o.equipamento.id})")
        print(f"  Falha relatada:     {o.falha}")
        print(f"  Criticidade:        {o.criticidade}")
        print(f"  Status:             {o.status}")
        print(f"  Aberta por:         {o.aberta_por or '—'} em {o.data_abertura}")
        print(f"  Técnico atribuído:  {o.tecnico_atribuido or '—'}")
        print(f"  Diagnóstico:        {o.diagnostico or '—'}")
        print(f"  Causa-raiz:         {o.causa_raiz or '—'}")
        print(f"  Horas trabalhadas:  {o.horas_trabalhadas:.1f} h")
        print("  Intervenções realizadas:")
        for i in o.intervencoes_realizadas or ["—"]:
            print(f"     - {i}")
        print("  Peças/materiais utilizados:")
        for p in o.pecas_utilizadas or ["—"]:
            print(f"     - {p}")
        if o.teste_funcional:
            print(f"  Teste funcional:    {o.teste_funcional}")
        if o.data_conclusao:
            print(f"  Encerrada em:       {o.data_conclusao}")
        if o.motivo_cancelamento:
            print(f"  Motivo cancelamento: {o.motivo_cancelamento}")
        print(f"\n  Serviços da OS ({len(o.servicos)}):")
        for s in o.servicos:
            print(f"   {s}")
