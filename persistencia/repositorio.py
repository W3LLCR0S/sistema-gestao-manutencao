"""Classe Repositorio: guarda os objetos em memória e salva/carrega do arquivo JSON.

Os objetos são convertidos para JSON só na hora de gravar (to_dict) e
reconstruídos como objetos na hora de ler (from_dict).
"""

from __future__ import annotations

import json
import os
from typing import Optional

from models import (Cargo, Permissoes, Usuario, Equipamento, OrdemServico,
                    Disponibilidade, StatusOS, RegraNegocioError)

ARQUIVO_PADRAO = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                              "dados", "dados.json")


class Repositorio:
    def __init__(self, caminho: str = ARQUIVO_PADRAO):
        self.caminho = caminho
        self.cargos: list[Cargo] = []
        self.usuarios: list[Usuario] = []
        self.equipamentos: list[Equipamento] = []
        self.ordens: list[OrdemServico] = []
        if os.path.exists(caminho):
            self.carregar()
        else:
            self._popular_exemplo()
            self.salvar()

    # ============================ arquivo ============================
    def carregar(self) -> None:
        with open(self.caminho, encoding="utf-8") as f:
            dados = json.load(f)
        self.cargos = [Cargo.from_dict(d) for d in dados["cargos"]]
        cargos = {c.id: c for c in self.cargos}
        self.usuarios = [Usuario.from_dict(d, cargos) for d in dados["usuarios"]]
        self.equipamentos = [Equipamento.from_dict(d) for d in dados["equipamentos"]]
        usuarios = {u.id: u for u in self.usuarios}
        equipamentos = {e.id: e for e in self.equipamentos}
        self.ordens = [OrdemServico.from_dict(d, usuarios, equipamentos) for d in dados["ordens"]]

    def salvar(self) -> None:
        dados = {
            "cargos": [c.to_dict() for c in self.cargos],
            "usuarios": [u.to_dict() for u in self.usuarios],
            "equipamentos": [e.to_dict() for e in self.equipamentos],
            "ordens": [o.to_dict() for o in self.ordens],
        }
        os.makedirs(os.path.dirname(self.caminho), exist_ok=True)
        tmp = self.caminho + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(dados, f, ensure_ascii=False, indent=2)
        os.replace(tmp, self.caminho)

    def _popular_exemplo(self) -> None:
        # Cargos fixos do sistema; o gestor pode apenas ajustar as permissões deles
        gestor = Cargo(1, "Gestor", Permissoes.padrao_gestor())
        tecnico = Cargo(2, "Técnico", Permissoes.padrao_tecnico())
        self.cargos = [gestor, tecnico]
        self.usuarios = [
            Usuario(1, "Ana Souza", gestor, "ana@empresa.com", "Seg-Sex 08h-17h"),
            Usuario(2, "Bruno Lima", tecnico, "bruno@empresa.com", "Seg-Sex 07h-16h"),
            Usuario(3, "Carla Mendes", tecnico, "carla@empresa.com", "Seg-Sex 13h-22h"),
        ]
        self.equipamentos = [
            Equipamento(1, "Torno CNC", "GL 240"),
            Equipamento(2, "Compressor de Ar", "CSW 40"),
            Equipamento(3, "Empilhadeira Elétrica", "PT 1650"),
        ]

    # ============================ ids ============================
    @staticmethod
    def _proximo(valores) -> int:
        return max(valores, default=0) + 1

    def proximo_id_usuario(self) -> int:
        return self._proximo(u.id for u in self.usuarios)

    def proximo_id_equipamento(self) -> int:
        return self._proximo(e.id for e in self.equipamentos)

    def proximo_numero_os(self) -> int:
        return self._proximo(o.numero for o in self.ordens)

    # ============================ buscas ============================
    def buscar_cargo(self, id: int) -> Optional[Cargo]:
        return next((c for c in self.cargos if c.id == id), None)

    def buscar_usuario(self, id: int) -> Optional[Usuario]:
        return next((u for u in self.usuarios if u.id == id), None)

    def buscar_equipamento(self, id: int) -> Optional[Equipamento]:
        return next((e for e in self.equipamentos if e.id == id), None)

    def buscar_os(self, numero: int) -> Optional[OrdemServico]:
        return next((o for o in self.ordens if o.numero == numero), None)

    def tecnicos(self) -> list[Usuario]:
        return [u for u in self.usuarios if u.e_tecnico]

    def ordens_do_equipamento(self, equipamento: Equipamento) -> list[OrdemServico]:
        return [o for o in self.ordens if o.equipamento is equipamento]

    def carga(self, tecnico: Usuario) -> int:
        """Número de OS ativas atribuídas ao técnico."""
        return sum(1 for o in self.ordens if o.esta_com(tecnico) and not o.encerrada)

    # ============================ disponibilidade ============================
    def atualizar_disponibilidades(self) -> None:
        """Técnico com OS em execução = 'Em atendimento'; sem OS em execução = 'Disponível'.
        Quem está 'Ausente' só muda manualmente."""
        for t in self.tecnicos():
            if t.disponibilidade == Disponibilidade.AUSENTE:
                continue
            em_campo = any(o.esta_com(t) and o.status == StatusOS.EM_EXECUCAO for o in self.ordens)
            t.disponibilidade = Disponibilidade.EM_ATENDIMENTO if em_campo else Disponibilidade.DISPONIVEL

    # ============================ inclusão / remoção ============================
    def adicionar_usuario(self, usuario: Usuario) -> None:
        self.usuarios.append(usuario)

    def adicionar_equipamento(self, equipamento: Equipamento) -> None:
        self.equipamentos.append(equipamento)

    def adicionar_os(self, os_: OrdemServico) -> None:
        self.ordens.append(os_)

    def remover_equipamento(self, equipamento: Equipamento) -> None:
        if self.ordens_do_equipamento(equipamento):
            raise RegraNegocioError("Equipamento possui OS vinculadas; use Inativar para preservar o histórico.")
        self.equipamentos.remove(equipamento)

    def _usuario_tem_historico(self, u: Usuario) -> bool:
        return any(o.tecnico_atribuido is u or o.aberta_por is u or
                   any(s.responsavel is u for s in o.servicos) for o in self.ordens)

    def remover_usuario(self, usuario: Usuario, solicitante: Usuario) -> None:
        if usuario is solicitante:
            raise RegraNegocioError("Você não pode excluir o próprio usuário.")
        if self._usuario_tem_historico(usuario):
            raise RegraNegocioError("Usuário possui histórico em OS; não pode ser excluído.")
        self.usuarios.remove(usuario)
