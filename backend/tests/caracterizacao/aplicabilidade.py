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
# novos listados (``arquivo::teste`` relativos a ``backend/tests``; sem ``::``, o teste é de
# ``dominio/test_permissoes.py``), conferidos por ``test_aplicabilidade.py``.
_DOM_E = "dominio/test_operacao_e.py::"
SUBSTITUIDOS_POR_DELTA: dict[str, tuple[str, tuple[str, ...]]] = {
    "CAR-74": (
        "DLT-11",
        (
            "test_de_nome_recusa_nome_invalido_com_erro_detectavel",
            "test_definir_recusa_texto_e_nao_altera_o_conjunto",
        ),
    ),
    "CAR-17": (
        "DLT-02",
        (
            f"{_DOM_E}test_dlt02_atribuir_a_tecnico_ausente_sem_confirmacao_e_recusado_sem_alterar_a_os",
            f"{_DOM_E}test_dlt02_com_confirmacao_a_atribuicao_e_aceita_e_o_historico_registra_a_ausencia",
        ),
    ),
    "CAR-18": (
        "DLT-01",
        (
            f"{_DOM_E}test_dlt01_o_papel_nao_depende_das_permissoes",
            f"{_DOM_E}test_dlt01_tecnico_sem_apontar_reparo_continua_atribuivel_e_e_negado_ao_apontar",
        ),
    ),
    "CAR-34": (
        "DLT-06",
        (
            f"{_DOM_E}test_dlt06_finalizar_sem_diagnostico_e_recusado_sem_alterar_status_nem_historico",
        ),
    ),
    "CAR-60": ("DLT-01", (f"{_DOM_E}test_dlt01_o_papel_nao_depende_das_permissoes",)),
    "CAR-63": ("DLT-01", (f"{_DOM_E}test_dlt01_o_papel_nao_depende_das_permissoes",)),
    "CAR-80": (
        "DLT-08",
        (
            f"{_DOM_E}test_dlt08_abrir_com_falha_vazia_ou_so_espacos_e_recusado",
            f"{_DOM_E}test_dlt08_apontamento_com_zero_hora_e_recusado_e_a_os_continua_atribuida",
        ),
    ),
    "CAR-82": (
        "DLT-01",
        (
            f"{_DOM_E}test_dlt01_gestor_com_permissoes_tecnicas_nao_recebe_atribuicao",
            f"{_DOM_E}test_dlt01_o_papel_nao_depende_das_permissoes",
        ),
    ),
    "CAR-83": (
        "DLT-06",
        (
            f"{_DOM_E}test_dlt06_finalizar_sem_diagnostico_e_recusado_sem_alterar_status_nem_historico",
            "dominio/test_ordem_servico.py::test_conclusao_sem_diagnostico_e_recusada_mesmo_com_teste_reprovado",
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


# ====================================================================== adaptador dos serviços
# O adaptador dos serviços de aplicação (Operação D7) responde ao que o domínio puro não respondia:
# cadastro e identificadores, exclusão e disponibilidade. Só faltam a ele a persistência em arquivo
# (JSON, que o novo backend não tem: D-10) e a interface de linha de comando (que a D-10 mantém
# fora da nova arquitetura). O registro abaixo é, portanto, o **subconjunto** do registro do domínio
# que ainda é inaplicável; as demais linhas passaram a ser executadas pelos serviços.

RESPONSABILIDADES_AUSENTES_DOS_SERVICOS = frozenset(
    {Responsabilidade.PERSISTENCIA, Responsabilidade.INTERFACE_DE_LINHA_DE_COMANDO}
)

REGISTRO_SERVICOS: tuple[Inaplicavel, ...] = tuple(
    linha for linha in REGISTRO if linha.responsabilidade in RESPONSABILIDADES_AUSENTES_DOS_SERVICOS
)

REGISTRO_SERVICOS_POR_PAR: dict[tuple[str, Responsabilidade], Inaplicavel] = {
    (i.cenario, i.responsabilidade): i for i in REGISTRO_SERVICOS
}


def decidir_servicos(
    cenarios: tuple[str, ...], responsabilidade: Responsabilidade
) -> Inaplicavel | None:
    """A linha do registro dos serviços que justifica pular um teste, ou ``None`` (deve falhar)."""
    for cenario in cenarios:
        linha = REGISTRO_SERVICOS_POR_PAR.get((cenario, responsabilidade))
        if linha is not None:
            return linha
    return None


@dataclass(frozen=True)
class NaoReproduzido:
    """Um cenário que os serviços respondem de outro modo, **por um delta aprovado e implementado**.

    Não é um ``skip``: o cenário não roda contra os serviços (a variante não é gerada) porque o
    comportamento que ele fixa no legado deixou de existir por decisão registrada em
    ``deltas.py``. Só pode haver exclusão quando (``test_adaptador_servicos.py`` confere cada item):

    * ``delta`` é um delta aprovado, já ``IMPLEMENTADO``, e lista este cenário em ``cenarios``;
    * o comportamento antigo continua testado (o teste do cenário segue rodando no legado);
    * o comportamento novo tem teste específico (``evidencias``, ``arquivo::teste`` relativos a
      ``backend/tests/``);
    * a divergência é exatamente a autorizada: a comparação lado a lado só difere no que o delta
      descreve.

    Não existe exclusão genérica por "defeito do legado": toda exclusão cita um delta.
    """

    cenario: str
    delta: str  # DLT-nn
    justificativa: str
    evidencias: tuple[str, ...]


_APLICACAO = "aplicacao/test_servico_de_"
_AUTORIZACAO = "aplicacao/test_autorizacao.py::"
_PAR = "caracterizacao/test_autorizacao_servicos.py::"

NAO_REPRODUZIDOS_PELOS_SERVICOS: dict[str, NaoReproduzido] = {
    "CAR-71": NaoReproduzido(
        "CAR-71",
        "DLT-12",
        "Autoproteção do gestor: o legado permite retirar o próprio acesso de gestão (só a tela "
        "da CLI o impedia). Nos serviços, trocar o próprio cargo ou reduzir as permissões do "
        "próprio cargo de modo a perder gerir_usuarios é recusado, sem alterar o estado.",
        (
            f"{_AUTORIZACAO}test_dlt12_gestor_nao_troca_o_proprio_cargo_por_um_sem_gestao",
            f"{_AUTORIZACAO}test_dlt12_gestor_nao_remove_do_proprio_cargo_o_acesso_de_gestao",
            f"{_PAR}test_dlt12_o_legado_permite_retirar_o_proprio_acesso_e_os_servicos_recusam",
        ),
    ),
    "CAR-72": NaoReproduzido(
        "CAR-72",
        "DLT-15",
        "Disponibilidade manual de terceiros: no legado qualquer um altera a de qualquer um. Nos "
        "serviços, o usuário altera a própria; só quem tem gerir_usuarios altera a de outro; sem "
        "essa permissão a recusa ocorre sem mutação.",
        (
            f"{_AUTORIZACAO}test_dlt15_usuario_altera_a_propria_disponibilidade",
            f"{_AUTORIZACAO}test_dlt15_gestor_altera_a_disponibilidade_de_outro",
            f"{_AUTORIZACAO}test_dlt15_sem_permissao_nao_altera_a_disponibilidade_de_terceiros",
            f"{_PAR}test_dlt15_terceiro_sem_autorizacao_o_legado_aceita_e_os_servicos_recusam",
        ),
    ),
    "CAR-73": NaoReproduzido(
        "CAR-73",
        "DLT-13",
        "Autorização de gestão: no legado equipamentos e exclusão de usuário eram operados sem "
        "identidade nem permissão (só o menu da CLI exigia). Os serviços exigem gerir_equipamentos "
        "e gerir_usuarios antes de qualquer mutação; a recusa não altera repositórios nem consome "
        "identificadores.",
        (
            f"{_AUTORIZACAO}test_dlt13_gestao_de_equipamentos_exige_gerir_equipamentos",
            f"{_AUTORIZACAO}test_dlt13_gestao_de_usuarios_e_cargos_exige_gerir_usuarios",
            f"{_AUTORIZACAO}test_dlt13_exclusao_de_usuario_exige_gerir_usuarios",
            f"{_PAR}test_dlt13_gestao_sem_permissao_o_legado_aceita_e_os_servicos_recusam",
        ),
    ),
    "CAR-91": NaoReproduzido(
        "CAR-91",
        "DLT-14",
        "Autorização de leitura: no legado nenhuma consulta verificava permissão (só o menu "
        "escondia as telas). Os serviços exigem ver_equipamentos, ver_os, ver_disponibilidade e, "
        "para usuários e cargos, gerir_usuarios, sem ampliar permissões.",
        (
            f"{_AUTORIZACAO}test_dlt14_consulta_sem_a_permissao_correspondente_e_recusada",
            f"{_AUTORIZACAO}test_dlt14_com_a_permissao_correspondente_a_consulta_e_permitida",
            f"{_PAR}test_dlt14_o_legado_le_sem_permissao_e_os_servicos_recusam",
        ),
    ),
    "CAR-92": NaoReproduzido(
        "CAR-92",
        "DLT-17",
        "Ator inexistente: o legado não recebe nem consulta o solicitante das operações de "
        "gestão. Os serviços recusam um ator inexistente com NaoEncontradoError, sem criar "
        "usuário nem substituí-lo por um administrador.",
        (
            f"{_AUTORIZACAO}test_dlt17_ator_inexistente_e_recusado_em_toda_operacao_com_o_erro_tipado",
            f"{_AUTORIZACAO}test_dlt17_nao_cria_usuario_nem_consome_identificador",
            f"{_PAR}test_dlt17_ator_inexistente_o_legado_ignora_e_os_servicos_recusam",
        ),
    ),
    "CAR-93": NaoReproduzido(
        "CAR-93",
        "DLT-16",
        "Precedência: o legado conferia autoexclusão e histórico sem olhar a permissão. Nos "
        "serviços a autorização é a primeira verificação funcional, antes de autoexclusão, "
        "histórico e recurso inexistente; a ordem interna das regras de domínio não muda.",
        (
            f"{_AUTORIZACAO}test_dlt16_sem_permissao_e_autoexclusao_a_recusa_e_por_autorizacao",
            f"{_AUTORIZACAO}test_dlt16_sem_permissao_e_historico_a_recusa_e_por_autorizacao",
            f"{_PAR}test_dlt16_sem_permissao_e_autoexclusao_legado_recusa_pela_regra_e_servicos_por_autorizacao",
        ),
    ),
    "CAR-74": NaoReproduzido(
        "CAR-74",
        "DLT-11",
        "Permissões tipadas: um nome inválido é erro detectável, não negação silenciosa; ao "
        "definir as permissões de um cargo, o valor inválido recusa tudo e nada muda.",
        (
            f"{_APLICACAO}usuarios.py::test_permissao_com_nome_invalido_e_erro_e_nada_muda",
            "dominio/test_permissoes.py::test_de_nome_recusa_nome_invalido_com_erro_detectavel",
        ),
    ),
    "CAR-75": NaoReproduzido(
        "CAR-75",
        "DLT-10",
        "Identificadores monotônicos: excluir o maior id não o libera para o cadastro seguinte "
        "(o legado usava max()+1 e o reaproveitava).",
        (
            "contrato/test_contrato_identificadores.py::test_excluir_o_maior_id_nao_o_reaproveita",
            f"{_APLICACAO}equipamentos.py::test_excluir_equipamento_sem_os_o_remove_e_o_id_nao_volta",
            f"{_APLICACAO}usuarios.py::test_excluir_usuario_sem_historico_o_remove_e_o_id_nao_volta",
        ),
    ),
}

_AOE = "aplicacao/test_operacao_e.py::"
_CMP = "caracterizacao/test_operacao_e_servicos.py::"


def _e(
    cenario: str, delta: str, justificativa: str, *evidencias: str
) -> tuple[str, NaoReproduzido]:
    return cenario, NaoReproduzido(cenario, delta, justificativa, evidencias)


_DISPONIBILIDADE_DERIVADA = (
    "Disponibilidade derivada (D-05): no legado o valor só muda pela rotina da interface e a "
    "consulta logo após uma transição devolve o valor antigo. Os serviços derivam das OS a cada "
    "consulta, sem rotina nem gravação, e a ausência manual prevalece."
)
_ROTULO_E = (
    f"{_AOE}test_dlt05_03_uma_os_em_execucao_caracteriza_atendimento_sem_rotina",
    f"{_CMP}test_dlt05_o_legado_so_atualiza_apos_a_rotina_e_os_servicos_derivam_na_hora",
)

NAO_REPRODUZIDOS_PELOS_SERVICOS.update(
    dict(
        (
            _e(
                "CAR-17",
                "DLT-02",
                "Técnico ausente (D-03): o legado aceita a atribuição (só a tela da CLI pedia "
                "confirmação). Os serviços a recusam, salvo confirmação explícita, e registram "
                "a atribuição a técnico ausente no histórico.",
                f"{_AOE}test_dlt02_atribuir_a_tecnico_ausente_sem_confirmacao_e_recusado_sem_mutacao",
                f"{_CMP}test_dlt02_atribuir_a_tecnico_ausente_o_legado_aceita_e_os_servicos_recusam",
            ),
            _e(
                "CAR-18",
                "DLT-01",
                "Papéis explícitos (D-02): no legado ser técnico é ter a permissão apontar_reparo. "
                "Nos serviços o papel é guardado à parte e a lista de técnicos independe das "
                "permissões do cargo.",
                f"{_AOE}test_dlt01_a_lista_de_tecnicos_depende_do_papel_e_nao_das_permissoes",
                f"{_CMP}test_dlt01_retirar_apontar_reparo_tira_o_tecnico_da_lista_no_legado_e_nao_nos_servicos",
            ),
            _e(
                "CAR-34",
                "DLT-06",
                "Diagnóstico obrigatório (D-06): o legado finaliza o reparo sem diagnóstico. Os "
                "serviços recusam a transição para Reparo Finalizado sem diagnóstico, sem "
                "alterar status nem histórico.",
                f"{_AOE}test_dlt06_finalizar_sem_diagnostico_e_recusado_pelo_servico_sem_mutacao",
                f"{_CMP}test_dlt06_finalizar_sem_diagnostico_o_legado_aceita_e_os_servicos_recusam",
            ),
            _e(
                "CAR-39",
                "DLT-04",
                "Quem observa (D-04): o legado aceita a observação de qualquer usuário com a "
                "permissão. Os serviços exigem vínculo com a OS (gestor, responsável ou quem a "
                "abriu) e recusam um terceiro sem alterar nada.",
                f"{_AOE}test_dlt04_quem_nao_tem_vinculo_com_a_os_e_recusado_sem_mutacao",
                f"{_CMP}test_dlt04_observacao_de_terceiro_o_legado_aceita_e_os_servicos_recusam",
            ),
            _e("CAR-43", "DLT-05", _DISPONIBILIDADE_DERIVADA, *_ROTULO_E),
            _e("CAR-47", "DLT-05", _DISPONIBILIDADE_DERIVADA, *_ROTULO_E),
            _e("CAR-48", "DLT-05", _DISPONIBILIDADE_DERIVADA, *_ROTULO_E),
            _e("CAR-49", "DLT-05", _DISPONIBILIDADE_DERIVADA, *_ROTULO_E),
            _e("CAR-50", "DLT-05", _DISPONIBILIDADE_DERIVADA, *_ROTULO_E),
            _e("CAR-51", "DLT-05", _DISPONIBILIDADE_DERIVADA, *_ROTULO_E),
            _e("CAR-52", "DLT-05", _DISPONIBILIDADE_DERIVADA, *_ROTULO_E),
            _e("CAR-81", "DLT-05", _DISPONIBILIDADE_DERIVADA, *_ROTULO_E),
            _e(
                "CAR-60",
                "DLT-01",
                "Papéis explícitos (D-02): no legado, sem permissões ninguém é técnico. Nos "
                "serviços os técnicos continuam técnicos e atribuíveis, e a permissão negada "
                "continua recusando a operação.",
                f"{_AOE}test_dlt01_a_lista_de_tecnicos_depende_do_papel_e_nao_das_permissoes",
                f"{_CMP}test_dlt01_retirar_apontar_reparo_tira_o_tecnico_da_lista_no_legado_e_nao_nos_servicos",
            ),
            _e(
                "CAR-63",
                "DLT-01",
                "Papéis explícitos (D-02): no legado trocar o cargo move o usuário entre técnicos "
                "e gestores. Nos serviços o cargo traz as permissões e o papel não muda; mudar o "
                "papel é operação explícita.",
                f"{_AOE}test_dlt01_o_gestor_altera_o_papel_por_uma_operacao_explicita",
                f"{_CMP}test_dlt01_mudar_o_cargo_move_o_usuario_no_legado_e_so_as_permissoes_nos_servicos",
            ),
            _e(
                "CAR-79",
                "DLT-03",
                "OS encerrada imutável (D-04): o legado aceita observação em OS Concluída ou "
                "Cancelada. Os serviços a recusam de qualquer usuário, sem alterar a OS nem o "
                "histórico.",
                f"{_AOE}test_dlt03_observacao_em_os_concluida_ou_cancelada_e_recusada_pelo_servico",
                f"{_CMP}test_dlt03_observacao_em_os_encerrada_o_legado_aceita_e_os_servicos_recusam",
            ),
            _e(
                "CAR-80",
                "DLT-08",
                "Validações obrigatórias (AUD-12): o legado aceita textos vazios e zero hora (só a "
                "tela validava). Os serviços recusam campos obrigatórios vazios e duração menor "
                "ou igual a zero, sem criar registro algum.",
                f"{_AOE}test_dlt08_abrir_com_falha_vazia_nao_cria_a_os_nem_consome_o_numero",
                f"{_CMP}test_dlt08_textos_vazios_e_zero_hora_o_legado_aceita_e_os_servicos_recusam",
            ),
            _e(
                "CAR-82",
                "DLT-01",
                "Papéis explícitos (D-02): no legado conceder apontar_reparo ao gestor o torna "
                "técnico atribuível. Nos serviços o gestor, mesmo com permissões técnicas, não "
                "aparece entre os técnicos nem recebe atribuição.",
                f"{_AOE}test_dlt01_gestor_com_permissoes_tecnicas_nao_aparece_nem_recebe_atribuicao",
                f"{_CMP}test_dlt01_conceder_apontar_reparo_ao_gestor_o_torna_atribuivel_no_legado_e_nao_nos_servicos",
            ),
            _e(
                "CAR-83",
                "DLT-06",
                "Diagnóstico obrigatório (D-06): no legado finalizar sem diagnóstico exige um "
                "caminho indireto para voltar. Nos serviços a finalização sem diagnóstico é "
                "recusada e o estado problemático deixa de existir.",
                f"{_AOE}test_dlt06_o_diagnostico_registrado_depois_destrava_a_finalizacao",
                f"{_CMP}test_dlt06_finalizar_sem_diagnostico_o_legado_aceita_e_os_servicos_recusam",
            ),
        )
    )
)
