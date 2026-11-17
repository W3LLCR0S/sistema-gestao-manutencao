"""Registro de deltas: o que muda em relação ao legado, por decisão já aprovada.

Segue ADR-0006 (seção "Deltas de comportamento"): para cada mudança, o comportamento atual (com
o(s) cenário(s) que o caracterizam), o comportamento aprovado e a decisão que o autorizou.

O legado continua com o comportamento descrito em ``legado``; os cenários listados em ``cenarios``
verificam esse comportamento antigo no adaptador do legado. Um delta só passa a ``IMPLEMENTADO``
quando (1) o código está concluído, (2) há testes específicos aprovados, (3) a comparação com o
legado existe e (4) esta rastreabilidade aponta a ``evidencia``: ``arquivo::teste``, relativos a
``backend/tests/``. ``test_rastreabilidade.py`` confere o estado esperado de **cada** delta e que a
evidência existe.

Estado atual: DLT-07 (datas UTC) e DLT-11 (permissões tipadas), da Operação C, DLT-10 (IDs
monotônicos), da Operação D, e DLT-12 a DLT-17 (autorização nos serviços, regularização da
Operação D) estão implementados. DLT-01 a DLT-06, DLT-08 e DLT-09 são da Operação E.

DLT-12 a DLT-17 foram **aprovados expressamente** em 2026-11-17 (``APROVACAO_REGULARIZACAO_D``) e
registram, além dos campos de sempre, a justificativa, a camada responsável e o teste do
comportamento legado (``testes_legado``). Os identificadores anteriores não foram alterados.
"""

from dataclasses import dataclass
from enum import StrEnum


class StatusDelta(StrEnum):
    NAO_IMPLEMENTADO = "nao_implementado"
    IMPLEMENTADO = "implementado"


@dataclass(frozen=True)
class Delta:
    id: str
    decisao: str  # identificador em docs/DECISOES_APROVADAS.md (ou a melhoria aprovada)
    regra: str
    legado: str  # comportamento atual, caracterizado pelos testes
    aprovado: str  # comportamento futuro aprovado
    cenarios: tuple[str, ...]  # CAR-nn que verificam o comportamento legado
    operacao_prevista: str  # onde a FASE_02 prevê a aplicação (indicativo, sem autorização)
    status: StatusDelta = StatusDelta.NAO_IMPLEMENTADO
    evidencia: tuple[str, ...] = ()  # "arquivo::teste" que comprovam a implementação
    # Campos exigidos a partir do DLT-12 (aprovação de 2026-11-17); vazios nos anteriores.
    justificativa: str = ""
    camada: str = ""  # camada responsável: domain, application, infrastructure...
    testes_legado: tuple[str, ...] = ()  # "arquivo::teste" que mostram o comportamento antigo
    aprovacao: str = ""  # data e referência da aprovação


APROVACAO_REGULARIZACAO_D = (
    "2026-11-17: autorização expressa do usuário (alternativa B) para regularizar a Operação D; "
    "DLT-12 a DLT-17 em docs/DECISOES_APROVADAS.md, seção 7, e docs/adr/0006"
)

_LEG = "caracterizacao/test_legado_defeitos.py::"
_PAR = "caracterizacao/test_autorizacao_servicos.py::"
_APL = "aplicacao/test_autorizacao.py::"

DELTAS: tuple[Delta, ...] = (
    Delta(
        "DLT-01",
        "D-02",
        "Identidade de técnico",
        "É técnico quem tem a permissão apontar_reparo; retirá-la tira o usuário da lista de "
        "técnicos e da atribuição; concedê-la ao Gestor o torna atribuível.",
        "Gestor e Técnico são papéis explícitos, independentes das permissões; permissão "
        "técnica não torna Gestor em Técnico e retirar apontar_reparo não destitui o Técnico.",
        ("CAR-18", "CAR-60", "CAR-82"),
        "E",
    ),
    Delta(
        "DLT-02",
        "D-03",
        "Atribuição a técnico Ausente",
        "O domínio aceita; só a tela da CLI pede confirmação.",
        "Recusada por padrão (conflito de regra); aceita com confirmação explícita validada na "
        "camada de aplicação; o histórico registra a atribuição a técnico ausente.",
        ("CAR-17", "CAR-89"),
        "E",
    ),
    Delta(
        "DLT-03",
        "D-04",
        "Observação em OS Concluída ou Cancelada",
        "Aceita de qualquer usuário com registrar_apontamento; o histórico encerrado cresce.",
        "Recusada (OS encerrada é imutável); observação não é diagnóstico nem reparo.",
        ("CAR-79",),
        "E",
    ),
    Delta(
        "DLT-04",
        "D-04",
        "Quem pode registrar observação em OS ativa",
        "Qualquer usuário com registrar_apontamento, sem vínculo com a OS.",
        "Gestor, técnico responsável e quem abriu a OS; técnico que não é responsável nem autor "
        "da abertura é recusado (salvo se também for Gestor autorizado).",
        ("CAR-39", "CAR-79"),
        "E",
    ),
    Delta(
        "DLT-05",
        "D-05",
        "Disponibilidade dos técnicos",
        "Valor armazenado, só atualizado pela rotina da interface; consultas logo após uma "
        "transição devolvem o valor antigo.",
        "Derivada das OS (só Em Execução caracteriza atendimento) a cada consulta, sem rotina; "
        "ausência manual prevalece.",
        ("CAR-43", "CAR-47", "CAR-48", "CAR-49", "CAR-50", "CAR-51", "CAR-81"),
        "E",
    ),
    Delta(
        "DLT-06",
        "D-06",
        "Diagnóstico antes de Reparo Finalizado",
        "Finalizar exige só intervenção; sem diagnóstico, conclusão e diagnóstico ficam "
        "bloqueados até voltar o status.",
        "Diagnóstico exigido antes da transição para Reparo Finalizado, com erro claro e sem "
        "alterar status nem histórico.",
        ("CAR-34", "CAR-83"),
        "E",
    ),
    Delta(
        "DLT-07",
        "D-11",
        "Datas e fuso horário",
        "Texto dd/mm/aaaa hh:mm sem fuso, lido do relógio do sistema pelo domínio.",
        "Instantes com fuso armazenados em UTC; relógio fornecido pela aplicação; datetime "
        "ingênuo rejeitado; apresentação em America/Sao_Paulo (Fase 04).",
        ("CAR-90",),
        "C",
        StatusDelta.IMPLEMENTADO,
        (
            "dominio/test_tempo.py::test_datetime_ingenuo_e_rejeitado",
            "dominio/test_tempo.py::test_toda_operacao_guarda_em_utc_os_registros_que_cria",
            "dominio/test_tempo.py::test_instante_ingenuo_e_recusado_sem_alterar_nada",
            "dominio/test_tempo.py::test_a_recusa_funcional_vence_o_instante_ingenuo",
            "dominio/test_tempo.py::test_nenhum_modulo_do_dominio_consulta_o_relogio_nem_converte_fusos",
            "caracterizacao/test_adaptador_dominio.py::test_datas_do_dominio_normalizadas_batem_com_as_do_legado",
        ),
    ),
    Delta(
        "DLT-08",
        "Validações obrigatórias (AUD-12)",
        "Campos obrigatórios e valores mínimos",
        "O domínio aceita falha, intervenção, diagnóstico, motivo e nomes vazios ou só espaços "
        "e 0 hora; recusa horas negativas e peça com quantidade não positiva.",
        "Campos obrigatórios vazios ou só espaços rejeitados; apontamento com duração menor ou "
        "igual a zero rejeitado; quantidade de peça positiva preservada.",
        ("CAR-80",),
        "E",
    ),
    Delta(
        "DLT-09",
        "Usuário ativo/inativo",
        "Desativação de usuários",
        "Não existe o campo ativo; um usuário só pode ser excluído se não tiver histórico.",
        "Campo ativo; usuário inativo não autentica nem opera e não é atribuível; o histórico "
        "preserva a referência; sem reatribuição automática.",
        ("CAR-64", "CAR-65"),
        "E",
    ),
    Delta(
        "DLT-10",
        "IDs monotônicos (AUD-05)",
        "Identificadores de usuário e equipamento",
        "max()+1: excluir o maior id faz o próximo cadastro reutilizá-lo.",
        "Identificadores monotônicos, sem reutilização após exclusão.",
        ("CAR-75",),
        "D",
        StatusDelta.IMPLEMENTADO,
        (
            "contrato/test_contrato_identificadores.py::test_excluir_o_maior_id_nao_o_reaproveita",
            "contrato/test_contrato_identificadores.py::test_adicionar_id_de_objeto_excluido_e_recusado",
            "contrato/test_contrato_identificadores.py::test_adicionar_id_em_uso_e_recusado_sem_colisao",
            "contrato/test_contrato_identificadores.py::test_id_e_estavel_depois_de_atualizacoes",
            "contrato/test_contrato_identificadores.py::test_sequencias_sao_independentes_por_tipo",
            "aplicacao/test_servico_de_equipamentos.py::test_excluir_equipamento_sem_os_o_remove_e_o_id_nao_volta",
            "aplicacao/test_servico_de_usuarios.py::test_excluir_usuario_sem_historico_o_remove_e_o_id_nao_volta",
            "caracterizacao/test_adaptador_servicos.py::test_dlt10_unica_diferenca_de_ids_o_legado_reaproveita_e_os_servicos_nao",
            "caracterizacao/test_adaptador_servicos.py::test_dlt10_excluir_um_id_do_meio_nao_o_reaproveita_nem_no_legado",
        ),
    ),
    Delta(
        "DLT-11",
        "AUD-03 (permissões tipadas)",
        "Nomes de permissão",
        "Texto livre: um nome errado é negado em silêncio; nomes desconhecidos são ignorados "
        "ao definir permissões do cargo.",
        "Permissões tipadas: nome inválido é erro detectável, não negação silenciosa.",
        ("CAR-74",),
        "C",
        StatusDelta.IMPLEMENTADO,
        (
            "dominio/test_permissoes.py::test_de_nome_recusa_nome_invalido_com_erro_detectavel",
            "dominio/test_permissoes.py::test_definir_recusa_texto_e_nao_altera_o_conjunto",
            "dominio/test_permissoes.py::test_tem_recusa_texto_solto_mesmo_quando_o_nome_existe",
            "caracterizacao/test_adaptador_dominio.py::test_permissoes_tipadas_so_divergem_do_legado_nos_nomes_invalidos",
        ),
    ),
    Delta(
        "DLT-12",
        "Regularização D (AUD-09)",
        "Autoproteção do gestor",
        "O gestor pode trocar o próprio cargo por um sem gestão, remover do próprio cargo "
        "gerir_usuarios ou reduzir as permissões do próprio cargo; só a tela da CLI o impedia.",
        "O serviço recusa (AUTOREMOCAO_DE_ACESSO_DE_GESTAO) a troca do próprio cargo por um sem "
        "gerir_usuarios e a redução das permissões do próprio cargo que o deixe sem ela, sem "
        "alterar o estado; alterações que preservam a autorização são permitidas.",
        ("CAR-71",),
        "D",
        StatusDelta.IMPLEMENTADO,
        (
            f"{_APL}test_dlt12_gestor_nao_troca_o_proprio_cargo_por_um_sem_gestao",
            f"{_APL}test_dlt12_gestor_nao_remove_do_proprio_cargo_o_acesso_de_gestao",
            f"{_APL}test_dlt12_reduzir_as_permissoes_do_proprio_cargo_so_e_recusado_se_perder_a_gestao",
            f"{_APL}test_dlt12_alteracoes_que_preservam_a_autorizacao_sao_permitidas",
            f"{_APL}test_dlt12_a_protecao_e_so_do_proprio_gestor_outros_usuarios_podem_perder_o_acesso",
            f"{_PAR}test_dlt12_o_legado_permite_retirar_o_proprio_acesso_e_os_servicos_recusam",
            f"{_PAR}test_dlt12_reduzir_as_permissoes_do_proprio_cargo_o_legado_permite_e_os_servicos_recusam",
        ),
        "Evita o bloqueio total da gestão (nenhum gestor restante) por engano; a regra existia só "
        "na interface (AUD-09) e deve valer para qualquer interface.",
        "application",
        (f"{_LEG}test_aud09_dominio_aceita_o_gestor_remover_o_proprio_acesso_de_gestao",),
        APROVACAO_REGULARIZACAO_D,
    ),
    Delta(
        "DLT-13",
        "Regularização D (AUD-02)",
        "Autorização para operações de gestão",
        "Equipamentos e exclusão de usuário eram operados sem identidade nem permissão; só o "
        "menu da CLI exigia gerir_equipamentos e gerir_usuarios.",
        "O serviço exige gerir_equipamentos (equipamentos) e gerir_usuarios (usuários e cargos) "
        "antes de qualquer mutação; a recusa não altera repositórios nem consome identificadores; "
        "nenhuma permissão nova.",
        ("CAR-73",),
        "D",
        StatusDelta.IMPLEMENTADO,
        (
            f"{_APL}test_dlt13_gestao_de_equipamentos_exige_gerir_equipamentos",
            f"{_APL}test_dlt13_gestao_de_usuarios_e_cargos_exige_gerir_usuarios",
            f"{_APL}test_dlt13_exclusao_de_usuario_exige_gerir_usuarios",
            f"{_APL}test_dlt13_a_recusa_nao_consome_identificadores",
            f"{_APL}test_dlt13_com_autorizacao_valida_a_gestao_e_permitida",
            f"{_APL}test_dlt13_nenhuma_permissao_nova_foi_criada",
            f"{_PAR}test_dlt13_gestao_sem_permissao_o_legado_aceita_e_os_servicos_recusam",
            f"{_PAR}test_dlt13_exclusao_de_usuario_sem_permissao_o_legado_aceita_e_os_servicos_recusam",
        ),
        "Preserva a permissão efetiva da CLI (o menu) e a impõe no servidor, como exige a "
        "autorização central (ADR-0003); sem ela, uma API chamaria o repositório sem checar.",
        "application",
        (
            f"{_LEG}test_aud02_equipamentos_sao_geridos_sem_identidade_nem_permissao",
            f"{_LEG}test_aud02_exclusao_de_usuario_nao_confere_a_permissao_do_solicitante",
        ),
        APROVACAO_REGULARIZACAO_D,
    ),
    Delta(
        "DLT-14",
        "Regularização D (AUD-02)",
        "Autorização para operações de leitura",
        "As consultas não verificavam permissão alguma no Repositorio; só o menu escondia as "
        "telas (ver_equipamentos, ver_os, ver_disponibilidade; gerir_usuarios para usuários).",
        "Os serviços exigem ver_equipamentos, ver_os e ver_disponibilidade nas consultas "
        "correspondentes e gerir_usuarios para consultar usuários e cargos; nenhuma regra de "
        "visibilidade nova e nenhuma ampliação de permissões.",
        ("CAR-91",),
        "D",
        StatusDelta.IMPLEMENTADO,
        (
            f"{_APL}test_dlt14_consulta_sem_a_permissao_correspondente_e_recusada",
            f"{_APL}test_dlt14_com_a_permissao_correspondente_a_consulta_e_permitida",
            f"{_APL}test_dlt14_uma_permissao_de_leitura_nao_amplia_as_demais",
            f"{_APL}test_dlt14_atores_distintos_a_mesma_consulta_depende_de_quem_pede",
            f"{_APL}test_dlt14_as_permissoes_padrao_do_legado_continuam_dando_as_mesmas_leituras",
            f"{_PAR}test_dlt14_o_legado_le_sem_permissao_e_os_servicos_recusam",
            f"{_PAR}test_dlt14_cada_leitura_exige_a_sua_permissao_e_nenhuma_outra",
        ),
        "Uma API sem a verificação exporia dados a quem o menu da CLI escondia; a regra é a "
        "efetiva do legado, agora no servidor.",
        "application",
        (f"{_LEG}test_aud02_consultas_nao_exigem_permissao_de_leitura_no_legado",),
        APROVACAO_REGULARIZACAO_D,
    ),
    Delta(
        "DLT-15",
        "Regularização D (AUD-09)",
        "Alteração manual da disponibilidade de terceiros",
        "Qualquer usuário alterava a disponibilidade de qualquer outro: a tela só mostrava "
        "'minha disponibilidade' e o domínio não tinha regra.",
        "O usuário altera a própria disponibilidade; quem tem gerir_usuarios altera a de outro; "
        "quem não tem é recusado sem mutação. Só trata de quem pode alterar o valor manual: a "
        "disponibilidade derivada (D-05) segue não implementada.",
        ("CAR-72",),
        "D",
        StatusDelta.IMPLEMENTADO,
        (
            f"{_APL}test_dlt15_usuario_altera_a_propria_disponibilidade",
            f"{_APL}test_dlt15_gestor_altera_a_disponibilidade_de_outro",
            f"{_APL}test_dlt15_sem_permissao_nao_altera_a_disponibilidade_de_terceiros",
            f"{_APL}test_dlt15_a_autorizacao_vem_antes_de_procurar_o_alvo",
            f"{_APL}test_dlt15_o_alvo_nunca_e_o_ator_quem_pede_e_quem_e_alterado_sao_distintos",
            f"{_APL}test_dlt15_nao_deriva_a_disponibilidade_so_decide_quem_pode_o_ajuste_manual",
            f"{_PAR}test_dlt15_alteracao_propria_e_aceita_no_legado_e_nos_servicos",
            f"{_PAR}test_dlt15_terceiro_por_gestor_autorizado_e_aceito_no_legado_e_nos_servicos",
            f"{_PAR}test_dlt15_terceiro_sem_autorizacao_o_legado_aceita_e_os_servicos_recusam",
            f"{_PAR}test_dlt15_o_alvo_nao_e_usado_como_ator_implicito",
        ),
        "Impede que um usuário mude a disponibilidade de colegas (que afeta a atribuição de "
        "OS), mantendo a autonomia de cada um sobre a própria e a do gestor sobre a equipe.",
        "application",
        (
            f"{_LEG}test_aud09_qualquer_usuario_altera_a_disponibilidade_de_qualquer_outro",
            f"{_LEG}test_aud09_o_proprio_usuario_e_o_gestor_tambem_alteram_a_disponibilidade",
        ),
        APROVACAO_REGULARIZACAO_D,
    ),
    Delta(
        "DLT-16",
        "Regularização D (AUD-02)",
        "Precedência da autorização",
        "A exclusão de usuário conferia autoexclusão e histórico sem olhar a permissão; um "
        "técnico sem permissão recebia a recusa da regra funcional.",
        "A autorização é a primeira verificação funcional dos casos de uso protegidos, antes de "
        "procurar o recurso e de autoexclusão e histórico; uma tentativa sem permissão é "
        "recusada por autorização mesmo com outro impedimento. A ordem interna das regras de "
        "domínio não muda.",
        ("CAR-93", "CAR-64", "CAR-65"),
        "D",
        StatusDelta.IMPLEMENTADO,
        (
            f"{_APL}test_dlt16_sem_permissao_e_autoexclusao_a_recusa_e_por_autorizacao",
            f"{_APL}test_dlt16_sem_permissao_e_historico_a_recusa_e_por_autorizacao",
            f"{_APL}test_dlt16_sem_permissao_e_equipamento_com_os_a_recusa_e_por_autorizacao",
            f"{_APL}test_dlt16_sem_permissao_e_recurso_inexistente_a_recusa_e_por_autorizacao",
            f"{_APL}test_dlt16_com_permissao_o_recurso_inexistente_e_o_erro_de_nao_encontrado",
            f"{_APL}test_dlt16_as_regras_do_dominio_preservam_a_ordem_com_permissao",
            f"{_APL}test_dlt16_operacao_de_os_sem_permissao_e_recusada_antes_de_procurar_o_resto",
            f"{_PAR}test_dlt16_sem_permissao_e_autoexclusao_legado_recusa_pela_regra_e_servicos_por_autorizacao",
            f"{_PAR}test_dlt16_sem_permissao_e_historico_legado_recusa_pela_regra_e_servicos_por_autorizacao",
            f"{_PAR}test_dlt16_com_permissao_a_precedencia_das_regras_de_dominio_e_a_do_legado",
        ),
        "Quem não pode agir não deve aprender nada sobre o estado do sistema (existência de "
        "recurso, histórico de um usuário) pela ordem das recusas.",
        "application",
        (f"{_LEG}test_aud02_exclusao_confere_autoexclusao_e_historico_sem_olhar_a_permissao",),
        APROVACAO_REGULARIZACAO_D,
    ),
    Delta(
        "DLT-17",
        "Regularização D (AUD-02)",
        "Ator inexistente",
        "As operações de gestão não recebiam nem consultavam o solicitante: um solicitante "
        "inexistente era indiferente.",
        "Os serviços recusam a operação quando o ator não existe, com o erro tipado "
        "NaoEncontradoError (entidade 'Usuário'); não há administrador padrão nem criação "
        "implícita de usuário. Não é autenticação (reservada à etapa própria).",
        ("CAR-92",),
        "D",
        StatusDelta.IMPLEMENTADO,
        (
            f"{_APL}test_dlt17_ator_inexistente_e_recusado_em_toda_operacao_com_o_erro_tipado",
            f"{_APL}test_dlt17_nao_cria_usuario_nem_consome_identificador",
            f"{_APL}test_dlt17_o_ator_inexistente_nao_vira_administrador",
            f"{_APL}test_dlt17_a_inexistencia_do_ator_prevalece_sobre_qualquer_outro_impedimento",
            f"{_PAR}test_dlt17_ator_inexistente_o_legado_ignora_e_os_servicos_recusam",
            f"{_PAR}test_dlt17_ator_inexistente_nao_cria_usuario_nem_o_substitui_por_administrador",
        ),
        "Sem ator não há autorização a avaliar; trocá-lo por um administrador ou criá-lo "
        "concederia poderes a quem não existe.",
        "application",
        (f"{_LEG}test_aud02_operacoes_de_gestao_ignoram_quem_pede_inclusive_um_inexistente",),
        APROVACAO_REGULARIZACAO_D,
    ),
)

DELTAS_POR_ID: dict[str, Delta] = {d.id: d for d in DELTAS}
