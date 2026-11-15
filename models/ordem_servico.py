"""Classe OrdemServico: número, status, diagnóstico, horas trabalhadas,
intervenções realizadas, peças/materiais utilizados, técnico atribuído
e a lista de serviços (histórico) executados na OS.

Todas as regras do ciclo de vida da OS ficam nos métodos desta classe.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from models.enums import StatusOS, Criticidade, TipoServico, STATUS_TECNICO, STATUS_FINAIS
from models.equipamento import Equipamento
from models.excecoes import RegraNegocioError
from models.peca_material import PecaMaterial
from models.servico import Servico
from models.usuario import Usuario


def _agora() -> str:
    return datetime.now().strftime("%d/%m/%Y %H:%M")


class OrdemServico:
    def __init__(self, numero: int, equipamento: Equipamento, falha: str, criticidade: Criticidade,
                 aberta_por: Optional[Usuario],
                 status: StatusOS = StatusOS.ABERTA,
                 diagnostico: str = "",
                 causa_raiz: str = "",
                 horas_trabalhadas: float = 0.0,
                 intervencoes_realizadas: Optional[list[str]] = None,
                 pecas_utilizadas: Optional[list[PecaMaterial]] = None,
                 tecnico_atribuido: Optional[Usuario] = None,
                 data_abertura: Optional[str] = None,
                 data_conclusao: Optional[str] = None,
                 teste_funcional: str = "",
                 motivo_cancelamento: str = "",
                 servicos: Optional[list[Servico]] = None):
        # Atributos da tree
        self.numero = numero
        self.status = status
        self.diagnostico = diagnostico
        self.horas_trabalhadas = horas_trabalhadas
        self.intervencoes_realizadas = intervencoes_realizadas or []
        self.pecas_utilizadas = pecas_utilizadas or []
        self.tecnico_atribuido = tecnico_atribuido
        # Atributos complementares
        self.equipamento = equipamento
        self.falha = falha
        self.criticidade = criticidade
        self.causa_raiz = causa_raiz
        self.aberta_por = aberta_por
        self.data_abertura = data_abertura or _agora()
        self.data_conclusao = data_conclusao
        self.teste_funcional = teste_funcional
        self.motivo_cancelamento = motivo_cancelamento
        self.servicos = servicos or []          # histórico: lista de Servico

    # ======================== consultas ========================
    @property
    def encerrada(self) -> bool:
        return self.status in STATUS_FINAIS

    def esta_com(self, tecnico: Usuario) -> bool:
        return self.tecnico_atribuido is tecnico

    # ======================== auxiliares ========================
    def _registrar_servico(self, tipo: TipoServico, descricao: str, responsavel: Usuario,
                           horas: float = 0.0, pecas: Optional[list[PecaMaterial]] = None) -> Servico:
        servico = Servico(len(self.servicos) + 1, tipo, descricao, responsavel, horas=horas, pecas=pecas)
        self.servicos.append(servico)
        return servico

    def _mudar_status(self, novo: StatusOS, responsavel: Usuario) -> None:
        self._registrar_servico(TipoServico.MUDANCA_STATUS, f"{self.status} → {novo}", responsavel)
        self.status = novo

    def _exigir_status(self, *validos: StatusOS) -> None:
        if self.status not in validos:
            raise RegraNegocioError(f"Operação não permitida com a OS em '{self.status}'.")

    def _exigir_tecnico_da_os(self, tecnico: Usuario) -> None:
        if not self.esta_com(tecnico):
            raise RegraNegocioError("Esta OS não está atribuída a você.")

    # ======================== abertura (todos) ========================
    @classmethod
    def abrir(cls, numero: int, equipamento: Equipamento, falha: str,
              criticidade: Criticidade, usuario: Usuario) -> OrdemServico:
        usuario.exigir("abrir_os")
        if not equipamento.ativo:
            raise RegraNegocioError("Não é possível abrir OS para equipamento inativo.")
        os_ = cls(numero, equipamento, falha, criticidade, usuario)
        os_._registrar_servico(TipoServico.ABERTURA, f"[{criticidade}] {falha}", usuario)
        return os_

    def adicionar_apontamento(self, usuario: Usuario, texto: str) -> None:
        usuario.exigir("registrar_apontamento")
        self._registrar_servico(TipoServico.APONTAMENTO, texto, usuario)

    # ======================== técnico ========================
    def registrar_diagnostico(self, tecnico: Usuario, parecer: str, causa_raiz: str) -> None:
        tecnico.exigir("diagnosticar")
        self._exigir_tecnico_da_os(tecnico)
        self._exigir_status(StatusOS.ATRIBUIDA, StatusOS.EM_EXECUCAO, StatusOS.AGUARDANDO_PECA)
        self.diagnostico = parecer
        self.causa_raiz = causa_raiz
        self._registrar_servico(TipoServico.DIAGNOSTICO, f"{parecer} | Causa-raiz: {causa_raiz}", tecnico)

    def apontar_reparo(self, tecnico: Usuario, horas: float, intervencao: str,
                       pecas: list[PecaMaterial]) -> None:
        tecnico.exigir("apontar_reparo")
        self._exigir_tecnico_da_os(tecnico)
        self._exigir_status(StatusOS.ATRIBUIDA, StatusOS.EM_EXECUCAO, StatusOS.AGUARDANDO_PECA)
        if horas < 0:
            raise RegraNegocioError("Horas trabalhadas não podem ser negativas.")
        if self.status == StatusOS.ATRIBUIDA:
            self._mudar_status(StatusOS.EM_EXECUCAO, tecnico)
        self.horas_trabalhadas += horas
        self.intervencoes_realizadas.append(intervencao)
        self.pecas_utilizadas.extend(pecas)
        self._registrar_servico(TipoServico.REPARO, intervencao, tecnico, horas=horas, pecas=list(pecas))

    def alterar_status(self, tecnico: Usuario, novo: StatusOS) -> None:
        tecnico.exigir("atualizar_status")
        self._exigir_tecnico_da_os(tecnico)
        self._exigir_status(StatusOS.ATRIBUIDA, *STATUS_TECNICO)
        if novo not in STATUS_TECNICO:
            raise RegraNegocioError(f"O técnico não pode definir o status '{novo}'.")
        if novo == self.status:
            raise RegraNegocioError("A OS já está nesse status.")
        if novo == StatusOS.REPARO_FINALIZADO and not self.intervencoes_realizadas:
            raise RegraNegocioError("Registre ao menos uma intervenção antes de finalizar o reparo.")
        self._mudar_status(novo, tecnico)

    def concluir_tecnicamente(self, tecnico: Usuario, teste: str, passou_no_teste: bool) -> bool:
        """Submete a OS para encerramento. Retorna False se o teste funcional falhou."""
        tecnico.exigir("concluir_os")
        self._exigir_tecnico_da_os(tecnico)
        self._exigir_status(StatusOS.REPARO_FINALIZADO)
        if not self.diagnostico:
            raise RegraNegocioError("Registre o diagnóstico antes de concluir.")
        if not passou_no_teste:
            self._registrar_servico(TipoServico.TESTE_FUNCIONAL, f"Reprovado: {teste}", tecnico)
            return False
        self.teste_funcional = teste
        self._registrar_servico(TipoServico.CONCLUSAO_TECNICA, f"Teste aprovado: {teste}", tecnico)
        self._mudar_status(StatusOS.AGUARDANDO_APROVACAO, tecnico)
        return True

    # ======================== gestor ========================
    def atribuir(self, tecnico: Usuario, gestor: Usuario) -> Optional[Usuario]:
        """Atribui/reatribui a OS. Retorna o técnico anterior (ou None)."""
        gestor.exigir("atribuir_os")
        if self.encerrada or self.status == StatusOS.AGUARDANDO_APROVACAO:
            raise RegraNegocioError(f"Não é possível atribuir uma OS em '{self.status}'.")
        if not tecnico.e_tecnico:
            raise RegraNegocioError(f"{tecnico.nome} não é técnico.")
        if self.esta_com(tecnico):
            raise RegraNegocioError("A OS já está atribuída a este técnico.")
        anterior = self.tecnico_atribuido
        self.tecnico_atribuido = tecnico
        if anterior:
            self._registrar_servico(TipoServico.REATRIBUICAO, f"{anterior.nome} → {tecnico.nome}", gestor)
        else:
            self._registrar_servico(TipoServico.ATRIBUICAO, f"Atribuída a {tecnico.nome}", gestor)
        if self.status == StatusOS.ABERTA:
            self._mudar_status(StatusOS.ATRIBUIDA, gestor)
        return anterior

    def aprovar(self, gestor: Usuario) -> None:
        gestor.exigir("aprovar_os")
        self._exigir_status(StatusOS.AGUARDANDO_APROVACAO)
        self.data_conclusao = _agora()
        self._registrar_servico(TipoServico.ENCERRAMENTO, "Reparo validado e OS encerrada.", gestor)
        self._mudar_status(StatusOS.CONCLUIDA, gestor)

    def reprovar(self, gestor: Usuario, motivo: str) -> None:
        gestor.exigir("aprovar_os")
        self._exigir_status(StatusOS.AGUARDANDO_APROVACAO)
        self._registrar_servico(TipoServico.REPROVACAO, f"Devolvida ao técnico: {motivo}", gestor)
        self._mudar_status(StatusOS.EM_EXECUCAO, gestor)

    def cancelar(self, gestor: Usuario, motivo: str) -> None:
        gestor.exigir("aprovar_os")
        if self.encerrada:
            raise RegraNegocioError("A OS já está encerrada.")
        self.motivo_cancelamento = motivo
        self.data_conclusao = _agora()
        self._registrar_servico(TipoServico.CANCELAMENTO, motivo, gestor)
        self._mudar_status(StatusOS.CANCELADA, gestor)

    # ======================== persistência ========================
    def to_dict(self) -> dict:
        return {
            "numero": self.numero,
            "status": self.status.value,
            "diagnostico": self.diagnostico,
            "horas_trabalhadas": self.horas_trabalhadas,
            "intervencoes_realizadas": self.intervencoes_realizadas,
            "pecas_utilizadas": [p.to_dict() for p in self.pecas_utilizadas],
            "tecnico_atribuido_id": self.tecnico_atribuido.id if self.tecnico_atribuido else None,
            "equipamento_id": self.equipamento.id,
            "falha": self.falha,
            "criticidade": self.criticidade.value,
            "causa_raiz": self.causa_raiz,
            "aberta_por_id": self.aberta_por.id if self.aberta_por else None,
            "data_abertura": self.data_abertura,
            "data_conclusao": self.data_conclusao,
            "teste_funcional": self.teste_funcional,
            "motivo_cancelamento": self.motivo_cancelamento,
            "servicos": [s.to_dict() for s in self.servicos],
        }

    @classmethod
    def from_dict(cls, d: dict, usuarios: dict[int, Usuario],
                  equipamentos: dict[int, Equipamento]) -> OrdemServico:
        return cls(
            numero=d["numero"],
            equipamento=equipamentos[d["equipamento_id"]],
            falha=d["falha"],
            criticidade=Criticidade(d["criticidade"]),
            aberta_por=usuarios.get(d["aberta_por_id"]),
            status=StatusOS(d["status"]),
            diagnostico=d["diagnostico"],
            causa_raiz=d["causa_raiz"],
            horas_trabalhadas=d["horas_trabalhadas"],
            intervencoes_realizadas=d["intervencoes_realizadas"],
            pecas_utilizadas=[PecaMaterial.from_dict(p) for p in d["pecas_utilizadas"]],
            tecnico_atribuido=usuarios.get(d["tecnico_atribuido_id"]),
            data_abertura=d["data_abertura"],
            data_conclusao=d["data_conclusao"],
            teste_funcional=d["teste_funcional"],
            motivo_cancelamento=d["motivo_cancelamento"],
            servicos=[Servico.from_dict(s, usuarios) for s in d["servicos"]],
        )
