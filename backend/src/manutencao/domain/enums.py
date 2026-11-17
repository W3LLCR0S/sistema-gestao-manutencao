"""Enumerações do domínio. Os valores textuais são os do legado (``models/enums.py``)."""

from enum import StrEnum


class StatusOS(StrEnum):
    ABERTA = "Aberta"
    ATRIBUIDA = "Atribuída"
    EM_EXECUCAO = "Em Execução"
    AGUARDANDO_PECA = "Aguardando Peça"
    REPARO_FINALIZADO = "Reparo Finalizado"
    AGUARDANDO_APROVACAO = "Aguardando Aprovação"
    CONCLUIDA = "Concluída"
    CANCELADA = "Cancelada"


class Criticidade(StrEnum):
    BAIXA = "Baixa"
    MEDIA = "Média"
    ALTA = "Alta"
    CRITICA = "Crítica"


class Disponibilidade(StrEnum):
    DISPONIVEL = "Disponível"
    EM_ATENDIMENTO = "Em atendimento"
    AUSENTE = "Ausente"


class TipoServico(StrEnum):
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
