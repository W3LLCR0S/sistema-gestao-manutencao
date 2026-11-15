"""Enumerações usadas pelas classes do domínio."""

from enum import Enum


class StatusOS(Enum):
    ABERTA = "Aberta"
    ATRIBUIDA = "Atribuída"
    EM_EXECUCAO = "Em Execução"
    AGUARDANDO_PECA = "Aguardando Peça"
    REPARO_FINALIZADO = "Reparo Finalizado"
    AGUARDANDO_APROVACAO = "Aguardando Aprovação"
    CONCLUIDA = "Concluída"
    CANCELADA = "Cancelada"

    def __str__(self):
        return self.value


# Status que o técnico pode definir manualmente
STATUS_TECNICO = (StatusOS.EM_EXECUCAO, StatusOS.AGUARDANDO_PECA, StatusOS.REPARO_FINALIZADO)
STATUS_FINAIS = (StatusOS.CONCLUIDA, StatusOS.CANCELADA)


class Criticidade(Enum):
    BAIXA = "Baixa"
    MEDIA = "Média"
    ALTA = "Alta"
    CRITICA = "Crítica"

    def __str__(self):
        return self.value


class Disponibilidade(Enum):
    DISPONIVEL = "Disponível"
    EM_ATENDIMENTO = "Em atendimento"
    AUSENTE = "Ausente"

    def __str__(self):
        return self.value


class TipoServico(Enum):
    ABERTURA = "Abertura"
    ATRIBUICAO = "Atribuição"
    REATRIBUICAO = "Reatribuição"
    DIAGNOSTICO = "Diagnóstico"
    REPARO = "Reparo"
    MUDANCA_STATUS = "Mudança de status"
    APONTAMENTO = "Apontamento"
    TESTE_FUNCIONAL = "Teste funcional"
    CONCLUSAO_TECNICA = "Conclusão técnica"
    ENCERRAMENTO = "Encerramento"
    REPROVACAO = "Reprovação"
    CANCELAMENTO = "Cancelamento"

    def __str__(self):
        return self.value
