"""Erros da camada de aplicação: o que não nasce numa entidade.

O domínio levanta :class:`manutencao.domain.erros.DominioError` (regras da OS, permissões). Aqui
ficam as recusas que dependem de **olhar mais de um agregado** (excluir equipamento com OS, excluir
usuário com histórico) ou de **encontrar** algo (identificador inexistente, id já emitido). Cada
erro carrega um código estável; a borda (API, Fase 04) traduzirá a classe em uma resposta
(``NaoEncontradoError`` -> 404, ``RegraDeAplicacaoError`` e ``IdentificadorJaEmitidoError`` ->
409). As mensagens das regras são as do legado.
"""

from enum import StrEnum


class CodigoErroAplicacao(StrEnum):
    """Regra de aplicação que motivou a recusa."""

    NAO_ENCONTRADO = "nao_encontrado"
    IDENTIFICADOR_JA_EMITIDO = "identificador_ja_emitido"
    EQUIPAMENTO_COM_OS = "equipamento_com_os"
    USUARIO_COM_HISTORICO = "usuario_com_historico"
    AUTOEXCLUSAO = "autoexclusao"
    AUTOREMOCAO_DE_ACESSO_DE_GESTAO = "autoremocao_de_acesso_de_gestao"


class AplicacaoError(Exception):
    """Base dos erros da camada de aplicação."""

    def __init__(self, codigo: CodigoErroAplicacao, mensagem: str) -> None:
        super().__init__(mensagem)
        self.codigo = codigo
        self.mensagem = mensagem


class NaoEncontradoError(AplicacaoError):
    """Não existe o objeto com o identificador informado."""

    def __init__(self, entidade: str, identificador: int) -> None:
        super().__init__(
            CodigoErroAplicacao.NAO_ENCONTRADO, f"{entidade} {identificador} não encontrado(a)."
        )
        self.entidade = entidade
        self.identificador = identificador


class IdentificadorJaEmitidoError(AplicacaoError):
    """O identificador já foi emitido por esta sequência (em uso ou de um objeto excluído)."""

    def __init__(self, entidade: str, identificador: int) -> None:
        super().__init__(
            CodigoErroAplicacao.IDENTIFICADOR_JA_EMITIDO,
            f"O identificador {identificador} de {entidade} já foi emitido e não é reutilizado.",
        )
        self.entidade = entidade
        self.identificador = identificador


class RegraDeAplicacaoError(AplicacaoError):
    """Uma regra que atravessa agregados recusou a operação."""
