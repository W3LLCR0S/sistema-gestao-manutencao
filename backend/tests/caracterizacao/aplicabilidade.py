"""Aplicabilidade dos cenários de caracterização ao **domínio puro** (Operação C6).

Os cenários CAR-nn foram escritos contra a fachada comportamental. O adaptador do domínio
(``adaptador_dominio.py``) executa todos os que o domínio puro consegue responder sozinho. Os
demais dependem de uma responsabilidade que **ainda não existe** no domínio puro (persistência,
identificadores, regras de exclusão, disponibilidade derivada, interface de linha de comando...).
Este módulo é o registro explícito desses casos: para cada um, o ID do cenário, a responsabilidade
ausente, a camada futura que a assumirá e a justificativa.

Como o registro é verificado (``test_aplicabilidade.py``):

* **em execução**: quando um teste do domínio chama uma operação que o adaptador não tem, o teste
  é pulado *só se* o par (cenário, responsabilidade) estiver aqui; caso contrário ele **falha**.
  Um ``skip`` nunca esconde um teste que falha por outro motivo;
* **estaticamente**: o conjunto de cenários cujos testes usam uma operação ausente (ou não usam a
  fachada, como a CLI) coincide exatamente com o registro, e cada linha cita uma responsabilidade
  que de fato falta no adaptador.

``SUBSTITUIDOS_POR_DELTA`` é outra coisa: cenários que o domínio **responde de forma diferente por
decisão aprovada e já implementada** (delta). O teste legado continua valendo para o adaptador do
legado; para o domínio, a evidência é o teste novo do comportamento aprovado.
"""

from dataclasses import dataclass
from enum import StrEnum


class Responsabilidade(StrEnum):
    """Responsabilidade que o domínio puro não tem (e que não deve ter)."""

    CADASTRO_E_IDENTIFICADORES = "cadastro_e_identificadores"
    REGRAS_DE_EXCLUSAO = "regras_de_exclusao"
    DISPONIBILIDADE_DERIVADA = "disponibilidade_derivada"
    PERSISTENCIA = "persistencia"
    INTERFACE_DE_LINHA_DE_COMANDO = "interface_de_linha_de_comando"


class Camada(StrEnum):
    """Camada futura (ADR-0002, ADR-0008) que assumirá a responsabilidade."""

    APLICACAO = "application"
    INFRAESTRUTURA = "infrastructure"
    APRESENTACAO = "apresentacao"


@dataclass(frozen=True)
class Inaplicavel:
    cenario: str  # CAR-nn
    responsabilidade: Responsabilidade
    camada: Camada
    justificativa: str

    @property
    def motivo(self) -> str:
        return (
            f"{self.cenario}: depende de '{self.responsabilidade.value}' "
            f"({self.camada.value}); {self.justificativa}"
        )


_CAMADA: dict[Responsabilidade, Camada] = {
    Responsabilidade.CADASTRO_E_IDENTIFICADORES: Camada.APLICACAO,
    Responsabilidade.REGRAS_DE_EXCLUSAO: Camada.APLICACAO,
    Responsabilidade.DISPONIBILIDADE_DERIVADA: Camada.APLICACAO,
    Responsabilidade.PERSISTENCIA: Camada.INFRAESTRUTURA,
    Responsabilidade.INTERFACE_DE_LINHA_DE_COMANDO: Camada.APRESENTACAO,
}

_BASE: dict[Responsabilidade, str] = {
    Responsabilidade.CADASTRO_E_IDENTIFICADORES: (
        "O domínio recebe entidades já criadas; quem atribui o próximo identificador e guarda o "
        "cadastro é o repositório (portas e implementação em memória na Operação D; IDs "
        "monotônicos: DLT-10)."
    ),
    Responsabilidade.REGRAS_DE_EXCLUSAO: (
        "Excluir exige olhar todas as OS e o cadastro; essa regra pertence ao repositório e ao "
        "serviço de aplicação (Operação D), não a uma entidade isolada."
    ),
    Responsabilidade.DISPONIBILIDADE_DERIVADA: (
        "A rotina que recalcula a disponibilidade percorre as OS de todos os técnicos; hoje vive "
        "no repositório e vira serviço de aplicação (Operação D; a regra derivada é o DLT-05, "
        "Operação E)."
    ),
    Responsabilidade.PERSISTENCIA: (
        "Gravar, recarregar e conviver com outra instância sobre o arquivo JSON é persistência "
        "(PostgreSQL/SQLAlchemy na Fase 03); o domínio não serializa nada."
    ),
    Responsabilidade.INTERFACE_DE_LINHA_DE_COMANDO: (
        "A CLI legada é preservada e não é conectada à nova arquitetura (D-10); a interação com "
        "o usuário será da API e da interface web (Fase 04)."
    ),
}


def _linha(cenario: str, responsabilidade: Responsabilidade, detalhe: str) -> Inaplicavel:
    return Inaplicavel(
        cenario,
        responsabilidade,
        _CAMADA[responsabilidade],
        f"{detalhe} {_BASE[responsabilidade]}",
    )


_CAD = Responsabilidade.CADASTRO_E_IDENTIFICADORES
_EXC = Responsabilidade.REGRAS_DE_EXCLUSAO
_DISP = Responsabilidade.DISPONIBILIDADE_DERIVADA
_PERS = Responsabilidade.PERSISTENCIA
_CLI = Responsabilidade.INTERFACE_DE_LINHA_DE_COMANDO

# Um cenário pode ter testes aplicáveis e outros não: só os que chamam a operação ausente são
# pulados; os demais rodam contra o domínio. As linhas abaixo são exatamente as dependências.
REGISTRO: tuple[Inaplicavel, ...] = (
    _linha("CAR-28", _PERS, "O teste grava e recarrega a base para conferir o histórico."),
    _linha("CAR-39", _CAD, "O teste cadastra um usuário novo para exercitar a observação."),
    _linha("CAR-41", _DISP, "O cenário D-05 nº 1 consulta a disponibilidade após a rotina."),
    _linha("CAR-42", _DISP, "O cenário D-05 nº 2 consulta a disponibilidade após a rotina."),
    _linha("CAR-43", _DISP, "O cenário D-05 nº 3 compara antes e depois da rotina."),
    _linha("CAR-44", _DISP, "O cenário D-05 nº 4 consulta a disponibilidade após a rotina."),
    _linha("CAR-45", _DISP, "O cenário D-05 nº 5 consulta a disponibilidade após a rotina."),
    _linha("CAR-46", _DISP, "O cenário D-05 nº 6 aplica a rotina sobre um técnico ausente."),
    _linha("CAR-47", _DISP, "O cenário D-05 nº 7 compara antes e depois da rotina."),
    _linha("CAR-48", _DISP, "O cenário D-05 nº 8 compara antes e depois da rotina."),
    _linha("CAR-49", _DISP, "O cenário D-05 nº 9 compara antes e depois da rotina."),
    _linha("CAR-50", _DISP, "O cenário D-05 nº 10 consulta antes de qualquer rotina."),
    _linha("CAR-51", _DISP, "Os testes aplicam a rotina e conferem o que ela sobrescreve."),
    _linha("CAR-51", _PERS, "Um dos testes grava e recarrega a base."),
    _linha("CAR-52", _DISP, "O teste confere que a rotina só recalcula técnicos."),
    _linha("CAR-54", _DISP, "O teste confere carga e lista de um técnico ausente após a rotina."),
    _linha("CAR-56", _CAD, "O teste cadastra um usuário novo do cargo."),
    _linha("CAR-61", _CAD, "O cenário é o próprio cadastro de usuário (próximo id)."),
    _linha("CAR-62", _CAD, "O cenário cadastra um técnico e um gestor."),
    _linha("CAR-64", _CAD, "O cenário cadastra o usuário que será excluído."),
    _linha("CAR-64", _EXC, "O cenário é a exclusão de usuário e a recusa da autoexclusão."),
    _linha("CAR-65", _CAD, "O cenário cadastra usuários que terão histórico."),
    _linha("CAR-65", _EXC, "O cenário é a recusa de excluir usuário com histórico."),
    _linha("CAR-66", _CAD, "O cenário é o próprio cadastro de equipamento (próximo id)."),
    _linha("CAR-68", _EXC, "O cenário é a exclusão de equipamento sem OS."),
    _linha("CAR-69", _EXC, "O cenário é a recusa de excluir equipamento com OS."),
    _linha("CAR-70", _CAD, "Um dos testes cadastra para conferir a persistência dos cadastros."),
    _linha("CAR-70", _PERS, "Um dos testes grava e recarrega as permissões do cargo."),
    _linha("CAR-73", _CAD, "Os testes cadastram equipamento e usuário sem exigir permissão."),
    _linha("CAR-73", _EXC, "Os testes excluem usuário e equipamento sem exigir permissão."),
    _linha("CAR-75", _CAD, "O cenário cadastra após uma exclusão para ver o id reaproveitado."),
    _linha("CAR-75", _EXC, "O cenário exclui o maior id (e um id do meio) antes de cadastrar."),
    _linha("CAR-76", _PERS, "O cenário usa duas instâncias do repositório sobre o mesmo arquivo."),
    _linha("CAR-77", _PERS, "O cenário apaga vínculos ao carregar um arquivo inconsistente."),
    _linha("CAR-78", _PERS, "O cenário é o construtor que grava e a interface que decide salvar."),
    _linha(
        "CAR-79", _CAD, "O teste cadastra um usuário para registrar observação em OS encerrada."
    ),
    _linha("CAR-80", _CAD, "Um dos testes cadastra com textos vazios (validação só na tela)."),
    _linha("CAR-81", _DISP, "O cenário reproduz o Apêndice E da auditoria, que usa a rotina."),
    _linha("CAR-84", _CLI, "Os testes executam a CLI legada em subprocesso."),
    _linha("CAR-85", _CLI, "O teste executa o login da CLI legada."),
    _linha("CAR-86", _CLI, "O teste executa o login por ID da CLI legada."),
    _linha("CAR-87", _CLI, "O teste confere o menu montado pela CLI legada."),
    _linha("CAR-88", _CLI, "Os testes abrem e consultam uma OS pela CLI legada."),
    _linha("CAR-89", _CLI, "O teste confere a confirmação de técnico ausente na tela da CLI."),
)

# Cenários que o domínio responde de outro modo, por decisão aprovada JÁ implementada. O teste do
# legado continua valendo para o adaptador do legado; para o domínio, a evidência são os testes
# novos listados (nome do teste em ``tests/dominio``), conferidos por ``test_aplicabilidade.py``.
SUBSTITUIDOS_POR_DELTA: dict[str, tuple[str, tuple[str, ...]]] = {
    "CAR-74": (
        "DLT-11",
        (
            "test_de_nome_recusa_nome_invalido_com_erro_detectavel",
            "test_definir_recusa_texto_e_nao_altera_o_conjunto",
        ),
    ),
}

REGISTRO_POR_PAR: dict[tuple[str, Responsabilidade], Inaplicavel] = {
    (i.cenario, i.responsabilidade): i for i in REGISTRO
}


def decidir(cenarios: tuple[str, ...], responsabilidade: Responsabilidade) -> Inaplicavel | None:
    """A linha do registro que justifica pular um teste destes cenários, ou ``None``.

    ``None`` significa que o teste exige uma responsabilidade ausente **sem** estar registrado: ele
    deve falhar, nunca ser pulado.
    """
    for cenario in cenarios:
        linha = REGISTRO_POR_PAR.get((cenario, responsabilidade))
        if linha is not None:
            return linha
    return None
