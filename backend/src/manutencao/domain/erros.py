"""Hierarquia de erros do domínio (ADR-0003; substitui a exceção única do legado, AUD-14).

Cada erro carrega um :class:`CodigoErro` estável. A camada ``api`` traduzirá a **classe** em uma
resposta (``PermissaoNegadaError`` -> 403, ``ConflitoDeEstadoError`` -> 409, ``ViolacaoDeRegraError`` -> 422);
o **código** identifica a regra violada sem depender do texto da mensagem. As mensagens são as do
legado, que continuam sendo o comportamento observado.

Erros que não nascem no domínio (não autenticado, não encontrado) pertencem à aplicação e à
borda e serão introduzidos com os casos de uso (Operação D).
"""

from enum import StrEnum


class CodigoErro(StrEnum):
    """Regra de domínio que motivou a recusa."""

    SEM_PERMISSAO = "sem_permissao"
    NAO_RESPONSAVEL = "nao_responsavel"
    ESTADO_INVALIDO = "estado_invalido"
    OS_ENCERRADA = "os_encerrada"
    JA_ATRIBUIDA = "ja_atribuida"
    JA_NESSE_STATUS = "ja_nesse_status"
    EQUIPAMENTO_INATIVO = "equipamento_inativo"
    NAO_E_TECNICO = "nao_e_tecnico"
    STATUS_NAO_PERMITIDO = "status_nao_permitido"
    SEM_INTERVENCAO = "sem_intervencao"
    SEM_DIAGNOSTICO = "sem_diagnostico"
    HORAS_NEGATIVAS = "horas_negativas"
    QUANTIDADE_INVALIDA = "quantidade_invalida"
    PERMISSAO_INVALIDA = "permissao_invalida"
    INSTANTE_INVALIDO = "instante_invalido"


class DominioError(Exception):
    """Base de todos os erros de regra do domínio."""

    def __init__(self, codigo: CodigoErro, mensagem: str) -> None:
        super().__init__(mensagem)
        self.codigo = codigo
        self.mensagem = mensagem


class PermissaoNegadaError(DominioError):
    """O usuário não tem a permissão exigida ou a OS pertence a outro técnico."""


class ConflitoDeEstadoError(DominioError):
    """A operação não é válida para o estado atual da OS."""


class ViolacaoDeRegraError(DominioError):
    """Um valor ou uma combinação de valores viola uma regra de domínio."""
