"""Erros da camada de aplicação: o que não nasce numa entidade.

O domínio levanta :class:`manutencao.domain.erros.DominioError` (regras da OS, permissões). Aqui
ficam as recusas que dependem de **olhar mais de um agregado** (excluir equipamento com OS, excluir
usuário com histórico) ou de **encontrar** algo (identificador inexistente, id já emitido). Cada
erro carrega um código estável; a borda (API, Fase 04) traduzirá a classe em uma resposta
(``NaoEncontradoError`` -> 404, ``RegraDeAplicacaoError`` e ``IdentificadorJaEmitidoError`` ->
409, ``NaoAutenticadoError`` -> 401, ``EntradaInvalidaError`` -> 422). As mensagens das regras são
as do legado.
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
    # Regularização da Operação E (REG-E-01, REG-E-04)
    ULTIMO_GESTOR = "ultimo_gestor"
    USUARIO_COM_OS_ATIVAS = "usuario_com_os_ativas"
    # Autenticação (D-01)
    NAO_AUTENTICADO = "nao_autenticado"
    CREDENCIAIS_INVALIDAS = "credenciais_invalidas"
    MUITAS_TENTATIVAS = "muitas_tentativas"
    LOGIN_EM_USO = "login_em_uso"
    ENTRADA_INVALIDA = "entrada_invalida"
    SENHA_ATUAL_INCORRETA = "senha_atual_incorreta"


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


class EntradaInvalidaError(AplicacaoError):
    """Um dado de entrada da aplicação (login, senha) não atende à política (HTTP 422)."""

    def __init__(self, mensagem: str) -> None:
        super().__init__(CodigoErroAplicacao.ENTRADA_INVALIDA, mensagem)


class NaoAutenticadoError(AplicacaoError):
    """Não há sessão válida (HTTP 401). Não diz **por que** (expirada, inexistente, revogada)."""

    def __init__(self, mensagem: str = "Autenticação necessária.") -> None:
        super().__init__(CodigoErroAplicacao.NAO_AUTENTICADO, mensagem)


class CredenciaisInvalidasError(NaoAutenticadoError):
    """Login recusado. A mensagem é única para login desconhecido, senha errada e usuário
    inativo: a resposta não revela quais logins existem."""

    def __init__(self) -> None:
        super().__init__("Credenciais inválidas.")
        self.codigo = CodigoErroAplicacao.CREDENCIAIS_INVALIDAS


class MuitasTentativasError(AplicacaoError):
    """Limite de tentativas de login excedido (HTTP 429)."""

    def __init__(self, segundos: int) -> None:
        super().__init__(
            CodigoErroAplicacao.MUITAS_TENTATIVAS,
            "Muitas tentativas de login; aguarde antes de tentar novamente.",
        )
        self.segundos = segundos


class SenhaAtualIncorretaError(EntradaInvalidaError):
    """A senha atual informada ao trocar a senha não confere (HTTP 422, **não** 401).

    Não é falta de autenticação: o usuário **está** autenticado. Responder 401 faria o cliente
    descartar a sessão válida por um erro de digitação.
    """

    def __init__(self) -> None:
        super().__init__("A senha atual informada está incorreta.")
        self.codigo = CodigoErroAplicacao.SENHA_ATUAL_INCORRETA
