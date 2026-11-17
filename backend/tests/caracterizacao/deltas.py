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
monotônicos), da Operação D, DLT-12 a DLT-17 (autorização nos serviços, regularização da Operação
D) e DLT-01 a DLT-06, DLT-08 e DLT-09 (regras de negócio, Operação E) estão implementados.
DLT-18 a DLT-23 (regularização da Operação E: REG-E-01 a REG-E-06) também; REG-E-07 e REG-E-08
são correções de rastreabilidade, sem delta de comportamento (``REGULARIZACOES_E``).

DLT-12 a DLT-17 foram **aprovados expressamente** em 2026-11-17 (``APROVACAO_REGULARIZACAO_D``) e
registram, além dos campos de sempre, a justificativa, a camada responsável e o teste do
comportamento legado (``testes_legado``). Os deltas da Operação E vêm de decisões aprovadas em
2026-11-15 e foram implementados após a autorização da Operação E (``APROVACAO_OPERACAO_E``) e
registram os mesmos campos. Os identificadores anteriores não foram alterados.

Os DLT-18 a DLT-23 vêm da regularização da Operação E (``APROVACAO_REGULARIZACAO_E``) e dão a cada
decisão ``REG-E-nn`` um registro definitivo (``Delta.regularizacao``); a tabela
``REGULARIZACOES_E`` liga as oito decisões ao seu identificador definitivo. Nenhum identificador
anterior foi renumerado.
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
    regularizacao: str = ""  # REG-E-nn que o delta registra (DLT-18 a DLT-23)


APROVACAO_REGULARIZACAO_D = (
    "2026-11-17: autorização expressa do usuário (alternativa B) para regularizar a Operação D; "
    "DLT-12 a DLT-17 em docs/DECISOES_APROVADAS.md, seção 7, e docs/adr/0006"
)

APROVACAO_OPERACAO_E = (
    "Decisões aprovadas em 2026-11-15 (docs/DECISOES_APROVADAS.md: D-02 a D-06 e as melhorias "
    "5.1 e 5.2; docs/adr/0009); implementação da Operação E autorizada em 2026-11-17"
)

APROVACAO_REGULARIZACAO_E = (
    "2026-11-17: autorização expressa do usuário (regularização da Operação E, REG-E-01 a "
    "REG-E-08); docs/DECISOES_APROVADAS.md, seção 9, docs/adr/0006 e docs/adr/0009"
)

_RGA = "aplicacao/test_regularizacao_e.py::"
_RGD = "dominio/test_regularizacao_e.py::"
_RGC = "caracterizacao/test_regularizacao_e_servicos.py::"
_DOM = "dominio/test_operacao_e.py::"
_ORD = "dominio/test_ordem_servico.py::"
_ENT = "dominio/test_entidades.py::"
_AOE = "aplicacao/test_operacao_e.py::"
_CMP = "caracterizacao/test_operacao_e_servicos.py::"
_ADS = "caracterizacao/test_adaptador_servicos.py::"
_ADD = "caracterizacao/test_adaptador_dominio.py::"
_CAD = "caracterizacao/test_cadastros.py::"
_ATR = "caracterizacao/test_atribuicao.py::"
_DSP = "caracterizacao/test_disponibilidade.py::"
_OBS = "caracterizacao/test_observacao.py::"
_TEC = "caracterizacao/test_tecnico.py::"
_PRM = "caracterizacao/test_permissoes.py::"
_LEG = "caracterizacao/test_legado_defeitos.py::"
_PAR = "caracterizacao/test_autorizacao_servicos.py::"
_APL = "aplicacao/test_autorizacao.py::"

DELTAS: tuple[Delta, ...] = (
    Delta(
        "DLT-01",
        "D-02",
        "Identidade de técnico",
        "É técnico quem tem a permissão apontar_reparo; retirá-la tira o usuário da lista de "
        "técnicos e da atribuição; concedê-la ao Gestor o torna atribuível; trocar o cargo move o "
        "usuário entre técnicos e gestores.",
        "Gestor e Técnico são papéis explícitos, independentes das permissões: permissão "
        "técnica não torna Gestor em Técnico, retirar apontar_reparo não destitui o Técnico e "
        "trocar o cargo não muda o papel. Mudar o papel é uma operação explícita, restrita ao "
        "Gestor, que não reatribui OS.",
        ("CAR-18", "CAR-60", "CAR-63", "CAR-82"),
        "E",
        StatusDelta.IMPLEMENTADO,
        (
            f"{_DOM}test_dlt01_o_papel_e_obrigatorio_e_explicito",
            f"{_DOM}test_dlt01_o_papel_nao_depende_das_permissoes",
            f"{_DOM}test_dlt01_tecnico_sem_apontar_reparo_continua_atribuivel_e_e_negado_ao_apontar",
            f"{_DOM}test_dlt01_gestor_com_permissoes_tecnicas_nao_recebe_atribuicao",
            f"{_ENT}test_e_tecnico_depende_so_do_papel_e_nao_de_apontar_reparo",
            f"{_ENT}test_gestor_nao_vira_tecnico_ao_receber_apontar_reparo",
            f"{_AOE}test_dlt01_a_lista_de_tecnicos_depende_do_papel_e_nao_das_permissoes",
            f"{_AOE}test_dlt01_tecnico_sem_apontar_reparo_e_atribuivel_e_e_negado_ao_apontar",
            f"{_AOE}test_dlt01_gestor_com_permissoes_tecnicas_nao_aparece_nem_recebe_atribuicao",
            f"{_AOE}test_dlt01_o_cadastro_guarda_o_papel_informado",
            f"{_AOE}test_dlt01_o_gestor_altera_o_papel_por_uma_operacao_explicita",
            f"{_AOE}test_dlt01_alterar_papel_e_restrito_ao_gestor_mesmo_com_a_permissao_de_gerir_usuarios",
            f"{_AOE}test_dlt01_um_gestor_sem_a_permissao_de_gerir_usuarios_tambem_e_recusado",
            f"{_AOE}test_dlt01_ninguem_deixa_de_ser_gestor_por_conta_propria",
            f"{_AOE}test_dlt01_mudar_o_papel_nao_reatribui_as_os",
            f"{_AOE}test_dlt01_alterar_papel_segue_a_precedencia_da_autorizacao",
            "aplicacao/test_servico_de_usuarios.py::test_alterar_o_cargo_muda_as_permissoes_mas_nao_o_papel",
            f"{_CMP}test_dlt01_retirar_apontar_reparo_tira_o_tecnico_da_lista_no_legado_e_nao_nos_servicos",
            f"{_CMP}test_dlt01_conceder_apontar_reparo_ao_gestor_o_torna_atribuivel_no_legado_e_nao_nos_servicos",
            f"{_CMP}test_dlt01_mudar_o_cargo_move_o_usuario_no_legado_e_so_as_permissoes_nos_servicos",
            f"{_CMP}test_dlt01_o_que_nao_depende_do_papel_e_igual_nos_dois",
            f"{_ADD}test_dlt01_retirar_apontar_reparo_destitui_o_tecnico_no_legado_e_nao_no_dominio",
        ),
        "A identidade (quem é) e a autorização (o que pode) deixam de se confundir: editar uma "
        "permissão não pode destituir um técnico nem promover um gestor (AUD-20).",
        "domain",
        (
            f"{_ATR}test_tecnico_deixa_de_ser_atribuivel_se_perder_a_permissao_apontar_reparo",
            f"{_PRM}test_usuario_sem_nenhuma_permissao_nao_opera_nada",
            f"{_CAD}test_alterar_o_cargo_move_o_usuario_entre_tecnicos_e_gestores",
            f"{_LEG}test_aud20_conceder_apontar_reparo_ao_gestor_o_transforma_em_tecnico_atribuivel",
            f"{_LEG}test_aud20_retirar_apontar_reparo_dos_tecnicos_os_tira_da_lista_mas_nao_das_os",
        ),
        APROVACAO_OPERACAO_E,
    ),
    Delta(
        "DLT-02",
        "D-03",
        "Atribuição a técnico Ausente",
        "O domínio aceita; só a tela da CLI pede confirmação.",
        "Recusada por padrão (conflito de regra); aceita com confirmação explícita, dado da "
        "operação validado no caso de uso e só de quem pode atribuir; o histórico registra a "
        "atribuição (e a reatribuição) a técnico ausente.",
        ("CAR-17", "CAR-89"),
        "E",
        StatusDelta.IMPLEMENTADO,
        (
            f"{_DOM}test_dlt02_atribuir_a_tecnico_ausente_sem_confirmacao_e_recusado_sem_alterar_a_os",
            f"{_DOM}test_dlt02_com_confirmacao_a_atribuicao_e_aceita_e_o_historico_registra_a_ausencia",
            f"{_DOM}test_dlt02_a_reatribuicao_a_tecnico_ausente_segue_a_mesma_regra",
            f"{_DOM}test_dlt02_a_confirmacao_nao_substitui_a_permissao_de_atribuir",
            f"{_AOE}test_dlt02_atribuir_a_tecnico_ausente_sem_confirmacao_e_recusado_sem_mutacao",
            f"{_AOE}test_dlt02_com_confirmacao_explicita_a_atribuicao_e_aceita_e_registrada",
            f"{_AOE}test_dlt02_a_reatribuicao_a_tecnico_ausente_segue_a_mesma_regra",
            f"{_AOE}test_dlt02_a_confirmacao_nao_e_aceita_de_quem_nao_pode_atribuir",
            f"{_CMP}test_dlt02_atribuir_a_tecnico_ausente_o_legado_aceita_e_os_servicos_recusam",
            f"{_CMP}test_dlt02_com_confirmacao_os_servicos_aceitam_e_registram_a_ausencia_no_historico",
            f"{_CMP}test_dlt02_tecnico_presente_e_igual_nos_dois",
        ),
        "Uma chamada direta à API não pode contornar a regra só por não haver a tela de "
        "confirmação (AUD-09): a recusa e a confirmação pertencem ao caso de uso.",
        "domain",
        (
            f"{_ATR}test_atribuir_a_tecnico_ausente_e_aceito_pelo_dominio",
            f"{_ATR}test_reatribuir_a_tecnico_ausente_tambem_e_aceito",
        ),
        APROVACAO_OPERACAO_E,
    ),
    Delta(
        "DLT-03",
        "D-04",
        "Observação em OS Concluída ou Cancelada",
        "Aceita de qualquer usuário com registrar_apontamento; o histórico encerrado cresce.",
        "Recusada (OS encerrada é imutável), de qualquer usuário; a OS e o histórico não "
        "mudam. Observação não é diagnóstico nem reparo.",
        ("CAR-79",),
        "E",
        StatusDelta.IMPLEMENTADO,
        (
            f"{_DOM}test_dlt03_observacao_em_os_concluida_ou_cancelada_e_recusada_para_todos",
            f"{_ORD}test_observacao_em_os_encerrada_e_recusada",
            f"{_AOE}test_dlt03_observacao_em_os_concluida_ou_cancelada_e_recusada_pelo_servico",
            f"{_CMP}test_dlt03_observacao_em_os_encerrada_o_legado_aceita_e_os_servicos_recusam",
        ),
        "Um histórico encerrado deixa de ser confiável se continua a receber registros (AUD-11).",
        "domain",
        (
            f"{_LEG}test_aud11_observacao_e_aceita_em_os_encerrada_de_qualquer_usuario_com_permissao",
        ),
        APROVACAO_OPERACAO_E,
    ),
    Delta(
        "DLT-04",
        "D-04",
        "Quem pode registrar observação em OS ativa",
        "Qualquer usuário com registrar_apontamento, sem vínculo com a OS.",
        "Gestor, técnico responsável e quem abriu a OS (todos com registrar_apontamento); "
        "terceiro é recusado por falta de vínculo, antes de olhar o estado. O autor da abertura "
        "não ganha capacidade técnica e a observação nunca muda o status.",
        ("CAR-39", "CAR-79"),
        "E",
        StatusDelta.IMPLEMENTADO,
        (
            f"{_DOM}test_dlt04_gestor_responsavel_e_autor_da_abertura_observam_em_os_ativa",
            f"{_DOM}test_dlt04_tecnico_sem_vinculo_com_a_os_e_recusado_mesmo_em_os_encerrada",
            f"{_DOM}test_dlt04_a_permissao_registrar_apontamento_continua_exigida",
            f"{_DOM}test_dlt04_o_autor_da_abertura_nao_ganha_capacidade_tecnica",
            f"{_AOE}test_dlt04_gestor_responsavel_e_autor_da_abertura_observam_e_o_status_nao_muda",
            f"{_AOE}test_dlt04_quem_nao_tem_vinculo_com_a_os_e_recusado_sem_mutacao",
            f"{_AOE}test_dlt04_o_autor_da_abertura_nao_executa_operacoes_tecnicas",
            f"{_CMP}test_dlt04_observacao_de_terceiro_o_legado_aceita_e_os_servicos_recusam",
            f"{_CMP}test_dlt04_gestor_responsavel_e_autor_da_abertura_observam_igual_nos_dois",
        ),
        "Observar é um ato de acompanhamento de quem tem relação com a OS; ampliar direitos além "
        "do aprovado daria capacidade técnica a quem só abriu o chamado.",
        "domain",
        (f"{_OBS}test_observacao_de_quem_nao_e_responsavel_nem_abriu_a_os_e_aceita",),
        APROVACAO_OPERACAO_E,
    ),
    Delta(
        "DLT-05",
        "D-05",
        "Disponibilidade dos técnicos",
        "Valor armazenado, só atualizado pela rotina da interface; consultas logo após uma "
        "transição devolvem o valor antigo.",
        "Derivada das OS a cada consulta, sem rotina nem gravação: só Em Execução caracteriza "
        "atendimento (Aguardando Peça não) e a ausência manual prevalece.",
        ("CAR-43", "CAR-47", "CAR-48", "CAR-49", "CAR-50", "CAR-51", "CAR-52", "CAR-81"),
        "E",
        StatusDelta.IMPLEMENTADO,
        (
            f"{_DOM}test_dlt05_a_ausencia_manual_prevalece_e_so_em_execucao_caracteriza_atendimento",
            f"{_AOE}test_dlt05_01_sem_os_ativas_e_nao_ausente_o_tecnico_esta_disponivel",
            f"{_AOE}test_dlt05_02_uma_os_atribuida_nao_caracteriza_atendimento",
            f"{_AOE}test_dlt05_03_uma_os_em_execucao_caracteriza_atendimento_sem_rotina",
            f"{_AOE}test_dlt05_04_uma_os_aguardando_peca_sozinha_nao_caracteriza_atendimento",
            f"{_AOE}test_dlt05_05_em_execucao_e_aguardando_peca_juntas_caracterizam_atendimento",
            f"{_AOE}test_dlt05_06_a_ausencia_manual_prevalece_sobre_o_estado_derivado",
            f"{_AOE}test_dlt05_07_removida_a_ausencia_o_valor_e_recalculado_sem_acao_extra",
            f"{_AOE}test_dlt05_08_ao_finalizar_o_reparo_o_tecnico_fica_disponivel_sem_rotina",
            f"{_AOE}test_dlt05_09_a_reatribuicao_reflete_nos_dois_tecnicos_imediatamente",
            f"{_AOE}test_dlt05_10_a_consulta_logo_apos_a_transicao_ja_traz_o_valor_correto",
            f"{_AOE}test_dlt05_a_derivacao_nao_grava_nada_nem_depende_de_rotina",
            f"{_AOE}test_dlt05_a_autorizacao_para_alterar_a_ausencia_de_terceiros_e_a_do_dlt15",
            f"{_CMP}test_dlt05_o_legado_so_atualiza_apos_a_rotina_e_os_servicos_derivam_na_hora",
            f"{_CMP}test_dlt05_depois_da_rotina_do_legado_os_dois_mostram_o_mesmo_valor",
            f"{_ADS}test_dlt05_a_disponibilidade_so_se_atualiza_apos_a_rotina_no_legado_e_na_hora_nos_servicos",
        ),
        "Um valor gravado por rotina da interface fica desatualizado e acoplado a ela (AUD-13); "
        "derivar das OS mantém a regra da Entrega 1 sem depender de processo algum.",
        "application",
        (
            f"{_DSP}test_d05_03_os_em_execucao_so_vira_em_atendimento_apos_a_rotina",
            f"{_DSP}test_d05_07_remover_a_ausencia_so_recalcula_apos_a_rotina",
            f"{_DSP}test_d05_08_reparo_finalizado_so_libera_o_tecnico_apos_a_rotina",
            f"{_DSP}test_d05_09_reatribuicao_so_se_reflete_nos_dois_tecnicos_apos_a_rotina",
            f"{_DSP}test_d05_10_consulta_logo_apos_uma_transicao_devolve_valor_desatualizado",
            f"{_DSP}test_rotina_sobrescreve_disponibilidade_manual_exceto_ausente",
            f"{_DSP}test_rotina_so_recalcula_tecnicos_e_nunca_altera_o_gestor",
            f"{_LEG}test_aud13_reproducao_do_apendice_e_da_auditoria",
        ),
        APROVACAO_OPERACAO_E,
    ),
    Delta(
        "DLT-06",
        "D-06",
        "Diagnóstico antes de Reparo Finalizado",
        "Finalizar exige só intervenção; sem diagnóstico, conclusão e diagnóstico ficam "
        "bloqueados até voltar o status.",
        "Diagnóstico exigido antes da transição para Reparo Finalizado, com erro claro e sem "
        "alterar status nem histórico; a intervenção continua exigida (e verificada primeiro) e "
        "as demais transições não mudam.",
        ("CAR-34", "CAR-83"),
        "E",
        StatusDelta.IMPLEMENTADO,
        (
            f"{_DOM}test_dlt06_finalizar_sem_diagnostico_e_recusado_sem_alterar_status_nem_historico",
            f"{_DOM}test_dlt06_com_diagnostico_a_finalizacao_segue_exigindo_intervencao_e_funciona",
            f"{_DOM}test_dlt06_a_falta_de_intervencao_continua_sendo_verificada_primeiro",
            f"{_DOM}test_dlt06_o_diagnostico_nao_e_exigido_nas_demais_transicoes",
            f"{_DOM}test_dlt06_o_fluxo_completo_e_a_volta_do_reparo_finalizado_continuam_validos",
            f"{_ORD}test_conclusao_sem_diagnostico_e_recusada_mesmo_com_teste_reprovado",
            f"{_AOE}test_dlt06_finalizar_sem_diagnostico_e_recusado_pelo_servico_sem_mutacao",
            f"{_AOE}test_dlt06_com_diagnostico_a_finalizacao_e_o_fluxo_completo_funcionam",
            f"{_AOE}test_dlt06_o_diagnostico_registrado_depois_destrava_a_finalizacao",
            f"{_CMP}test_dlt06_finalizar_sem_diagnostico_o_legado_aceita_e_os_servicos_recusam",
            f"{_CMP}test_dlt06_com_diagnostico_o_resultado_e_o_estado_sao_iguais_nos_dois",
            f"{_CMP}test_dlt06_a_falta_de_intervencao_continua_com_a_mesma_recusa_nos_dois",
            f"{_ADD}test_dlt06_o_estado_sem_diagnostico_existe_no_legado_e_e_inalcancavel_no_dominio",
            f"{_ADS}test_dlt06_o_estado_sem_diagnostico_existe_no_legado_e_e_inalcancavel_nos_servicos",
        ),
        "Sem diagnóstico a OS chega a Reparo Finalizado e fica sem saída (a conclusão e o próprio"
        " diagnóstico são recusados até o status voltar): AUD-21.",
        "domain",
        (
            f"{_TEC}test_finalizar_reparo_sem_diagnostico_e_aceito",
            f"{_LEG}test_aud21_finalizar_sem_diagnostico_exige_um_caminho_indireto",
        ),
        APROVACAO_OPERACAO_E,
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
        "Campos obrigatórios vazios ou só espaços rejeitados (falha, parecer e causa-raiz do "
        "diagnóstico, intervenção, motivos de reprovação e cancelamento, nomes de usuário e "
        "equipamento); apontamento com duração menor ou igual a zero (ou não finita) rejeitado; "
        "horas negativas e quantidade de peça positiva preservadas.",
        ("CAR-80",),
        "E",
        StatusDelta.IMPLEMENTADO,
        (
            f"{_DOM}test_dlt08_abrir_com_falha_vazia_ou_so_espacos_e_recusado",
            f"{_DOM}test_dlt08_o_texto_valido_e_guardado_exatamente_como_foi_informado",
            f"{_DOM}test_dlt08_diagnostico_com_campo_vazio_e_recusado_sem_alterar_a_os",
            f"{_DOM}test_dlt08_apontamento_com_zero_hora_e_recusado_e_a_os_continua_atribuida",
            f"{_DOM}test_dlt08_horas_nao_numericas_ou_infinitas_sao_recusadas",
            f"{_DOM}test_dlt08_horas_negativas_continuam_com_a_recusa_e_a_mensagem_do_legado",
            f"{_DOM}test_dlt08_apontamento_com_intervencao_vazia_e_recusado",
            f"{_DOM}test_dlt08_a_quantidade_de_peca_positiva_e_preservada",
            f"{_DOM}test_dlt08_motivos_de_reprovacao_e_de_cancelamento_vazios_sao_recusados",
            f"{_DOM}test_dlt08_a_autorizacao_e_a_regra_de_estado_vem_antes_da_validacao",
            f"{_AOE}test_dlt08_abrir_com_falha_vazia_nao_cria_a_os_nem_consome_o_numero",
            f"{_AOE}test_dlt08_cadastrar_usuario_ou_equipamento_sem_nome_nao_consome_identificador",
            f"{_AOE}test_dlt08_editar_o_nome_para_vazio_e_recusado_e_o_nome_antigo_fica",
            f"{_AOE}test_dlt08_apontamento_invalido_nao_altera_a_os_nem_inicia_a_execucao",
            f"{_AOE}test_dlt08_peca_com_quantidade_nao_positiva_continua_recusada",
            f"{_AOE}test_dlt08_diagnostico_reprovacao_e_cancelamento_vazios_sao_recusados",
            f"{_AOE}test_dlt08_a_autorizacao_vem_antes_da_validacao",
            f"{_CMP}test_dlt08_textos_vazios_e_zero_hora_o_legado_aceita_e_os_servicos_recusam",
            f"{_CMP}test_dlt08_com_valores_validos_o_resultado_e_o_estado_sao_iguais_nos_dois",
            f"{_CMP}test_dlt08_horas_negativas_e_quantidade_de_peca_continuam_iguais_nos_dois",
        ),
        "As validações só existiam na interface (AUD-12): uma API as contornaria. A regra vale no"
        " servidor, para qualquer interface, e uma entrada inválida não cria registro algum.",
        "domain",
        (
            f"{_LEG}test_aud12_abertura_aceita_falha_vazia_ou_so_espacos",
            f"{_LEG}test_aud12_apontamento_aceita_zero_hora_e_intervencao_vazia",
            f"{_LEG}test_aud12_demais_textos_obrigatorios_na_tela_sao_aceitos_vazios",
        ),
        APROVACAO_OPERACAO_E,
    ),
    Delta(
        "DLT-09",
        "Usuário ativo/inativo",
        "Desativação de usuários",
        "Não existe o campo ativo; um usuário só pode ser excluído se não tiver histórico.",
        "Campo ativo (todos nascem ativos); usuário inativo não opera, não é atribuível e sai "
        "da lista de técnicos; nunca desativa a si mesmo; o histórico preserva a referência; sem "
        "reatribuição automática das OS dele.",
        ("CAR-64", "CAR-65"),
        "E",
        StatusDelta.IMPLEMENTADO,
        (
            f"{_DOM}test_dlt09_o_usuario_nasce_ativo_e_pode_ser_desativado_e_reativado",
            f"{_DOM}test_dlt09_usuario_inativo_nao_opera_nenhuma_operacao_da_os",
            f"{_DOM}test_dlt09_usuario_inativo_nao_tem_permissao_efetiva",
            f"{_DOM}test_dlt09_tecnico_inativo_nao_e_atribuivel",
            f"{_DOM}test_dlt09_o_historico_preserva_a_referencia_a_quem_foi_desativado",
            f"{_AOE}test_dlt09_os_usuarios_nascem_ativos",
            f"{_AOE}test_dlt09_desativar_exige_gerir_usuarios_e_a_recusa_nao_altera_nada",
            f"{_AOE}test_dlt09_ninguem_desativa_a_si_mesmo",
            f"{_AOE}test_dlt09_desativar_e_reativar_sao_idempotentes_e_guardados",
            f"{_AOE}test_dlt09_usuario_inativo_nao_opera_nenhum_caso_de_uso",
            f"{_AOE}test_dlt09_o_ator_inativo_e_recusado_antes_da_verificacao_de_permissao",
            f"{_AOE}test_dlt09_tecnico_inativo_sai_da_lista_e_nao_recebe_os",
            f"{_AOE}test_dlt09_desativar_preserva_o_historico_e_nao_reatribui_as_os",
            f"{_AOE}test_dlt09_usuario_com_historico_continua_sem_poder_ser_excluido_mas_pode_ser_desativado",
            f"{_AOE}test_dlt09_reativar_restaura_a_operacao",
            f"{_CMP}test_dlt09_o_legado_nao_tem_o_conceito_de_ativo_e_so_exclui_quem_nao_tem_historico",
            f"{_CMP}test_dlt09_nos_servicos_o_usuario_com_historico_e_desativado_sem_perder_a_referencia",
            f"{_CMP}test_dlt09_sem_desativacao_as_os_sao_iguais_nos_dois",
        ),
        "Quem deixa a empresa não pode ser excluído (o histórico o cita), mas não deve mais "
        "operar nem receber trabalho; o tratamento das OS dele é uma decisão futura, não "
        "automática.",
        "domain",
        (
            f"{_CAD}test_excluir_usuario_sem_historico_o_remove",
            f"{_CAD}test_autor_de_apenas_uma_observacao_tambem_tem_historico",
        ),
        APROVACAO_OPERACAO_E,
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
    Delta(
        "DLT-18",
        "REG-E-01 (regularização da Operação E)",
        "Proteção do último gestor administrativamente apto",
        "Nada impede que o sistema fique sem quem administre usuários: o último gestor pode ser "
        "excluído, ter o cargo trocado ou o cargo sem a permissão gerir_usuarios (só a "
        "autoproteção "
        "do próprio gestor, na tela, e o DLT-12 o impedem de agir contra si mesmo).",
        "Gestor administrativamente apto é quem tem o papel Gestor, está ativo e tem "
        "gerir_usuarios. "
        "Desativar, excluir, mudar o papel, mudar o cargo ou alterar as permissões de um cargo "
        "(considerando todos os usuários que o compartilham) é recusado, com conflito tipado "
        "(ultimo_gestor) e sem mutação, quando eliminaria o último gestor apto. Não cria usuário, "
        "não concede permissão e não há recuperação administrativa.",
        ("CAR-71",),
        "E",
        StatusDelta.IMPLEMENTADO,
        (
            f"{_RGA}test_dlt18_o_gestor_apto_e_papel_gestor_ativo_e_com_gerir_usuarios",
            f"{_RGA}test_dlt18_um_unico_gestor_apto_nao_pode_ser_desativado",
            f"{_RGA}test_dlt18_com_dois_gestores_aptos_um_deles_pode_ser_desativado",
            f"{_RGA}test_dlt18_o_gestor_sem_gerir_usuarios_nao_conta_como_outro_gestor",
            f"{_RGA}test_dlt18_o_gestor_inativo_nao_conta_como_outro_gestor",
            f"{_RGA}test_dlt18_o_tecnico_com_gerir_usuarios_nao_conta_como_gestor",
            f"{_RGA}test_dlt18_alterar_o_cargo_do_ultimo_gestor_para_um_sem_gestao_e_recusado",
            f"{_RGA}test_dlt18_alterar_o_cargo_para_um_que_preserva_a_gestao_e_aceito",
            f"{_RGA}test_dlt18_retirar_gerir_usuarios_de_um_cargo_compartilhado_considera_todos_os_usuarios",
            f"{_RGA}test_dlt18_o_cargo_compartilhado_pode_perder_a_gestao_se_outro_gestor_permanece",
            f"{_RGA}test_dlt18_alterar_permissoes_do_cargo_preservando_a_gestao_e_aceito",
            f"{_RGA}test_dlt18_o_gestor_apto_tambem_nao_e_excluido_quando_e_o_ultimo",
            f"{_RGA}test_dlt18_mudar_o_papel_de_outro_gestor_preserva_quem_age",
            f"{_RGA}test_dlt18_sem_nenhum_gestor_apto_antes_a_regra_nao_impede_o_que_nao_o_elimina",
            f"{_RGA}test_dlt18_a_recusa_nao_cria_usuario_nem_concede_permissao",
            f"{_RGA}test_dlt18_a_autorizacao_e_a_primeira_verificacao",
            f"{_RGD}test_dlt18_o_gestor_apto_exige_papel_gestor_ativo_e_gerir_usuarios",
            f"{_RGD}test_dlt18_o_tecnico_com_gerir_usuarios_nao_e_gestor_administrativo",
            f"{_RGC}test_dlt18_eliminar_o_unico_gestor_o_legado_aceita_e_os_servicos_recusam",
            f"{_RGC}test_dlt18_com_outro_gestor_apto_a_operacao_e_aceita_nos_dois",
        ),
        "O sistema não pode perder, por uma operação comum, a última pessoa capaz de administrar "
        "usuários e permissões: sem recuperação administrativa, o estado seria irreversível.",
        "application",
        (f"{_LEG}test_aud09_dominio_aceita_o_gestor_remover_o_proprio_acesso_de_gestao",),
        APROVACAO_REGULARIZACAO_E,
        "REG-E-01",
    ),
    Delta(
        "DLT-19",
        "REG-E-02 (regularização da Operação E)",
        "Alteração de papel: Gestor ativo com gerir_usuarios (ratificação)",
        "O papel era a permissão apontar_reparo e mudava com o cargo (AUD-20); não havia operação "
        "de alterar o papel.",
        "Ratificada a regra do DLT-01: alterar o papel exige, ao mesmo tempo, o papel Gestor, o "
        "usuário ativo e a permissão gerir_usuarios; uma só condição não basta. A exigência de "
        "papel Gestor não se estende às demais operações de gestão, que dependem só de permissão. "
        "A precedência de autorização (DLT-16, DLT-17) é preservada.",
        ("CAR-63",),
        "E",
        StatusDelta.IMPLEMENTADO,
        (
            f"{_RGA}test_dlt19_alterar_o_papel_exige_gestor_ativo_com_gerir_usuarios",
            f"{_RGA}test_dlt19_a_exigencia_de_papel_gestor_nao_se_estende_as_outras_operacoes_de_gestao",
            f"{_RGA}test_dlt19_a_precedencia_de_autorizacao_e_mantida",
            f"{_AOE}test_dlt01_alterar_papel_e_restrito_ao_gestor_mesmo_com_a_permissao_de_gerir_usuarios",
            f"{_AOE}test_dlt01_um_gestor_sem_a_permissao_de_gerir_usuarios_tambem_e_recusado",
            f"{_DOM}test_dlt01_o_papel_nao_depende_das_permissoes",
            f"{_CMP}test_dlt01_mudar_o_cargo_move_o_usuario_no_legado_e_so_as_permissoes_nos_servicos",
        ),
        "O papel é uma identidade administrativa: quem o altera precisa ser, ele próprio, um "
        "gestor "
        "em condições de administrar. Ratifica a regra já implementada e a delimita.",
        "application",
        (f"{_CAD}test_alterar_o_cargo_move_o_usuario_entre_tecnicos_e_gestores",),
        APROVACAO_REGULARIZACAO_E,
        "REG-E-02",
    ),
    Delta(
        "DLT-20",
        "REG-E-03 (regularização da Operação E)",
        "Autoproteção estendida: papel Gestor e conta própria (ratificação)",
        "Só a tela impedia o gestor de excluir a si mesmo e de retirar o próprio acesso de gestão; "
        "não havia papel nem desativação.",
        "Ratificadas as proteções já implementadas: um gestor não retira de si mesmo o papel "
        "Gestor e ninguém desativa a própria conta. Complementam o DLT-12, com o erro tipado "
        "autoremocao_de_acesso_de_gestao (adequado: perder o papel ou a conta é perder o próprio "
        "acesso) e sem mutação. Nenhuma outra restrição de autoproteção foi criada.",
        ("CAR-71", "CAR-64"),
        "E",
        StatusDelta.IMPLEMENTADO,
        (
            f"{_RGA}test_dlt20_um_gestor_nao_retira_de_si_mesmo_o_papel_gestor",
            f"{_RGA}test_dlt20_ninguem_desativa_a_propria_conta",
            f"{_RGA}test_dlt20_a_autoprotecao_vem_antes_do_ultimo_gestor",
            f"{_RGA}test_dlt20_nao_ha_outras_restricoes_de_autoprotecao",
            f"{_AOE}test_dlt01_ninguem_deixa_de_ser_gestor_por_conta_propria",
            f"{_AOE}test_dlt09_ninguem_desativa_a_si_mesmo",
            f"{_PAR}test_dlt12_o_legado_permite_retirar_o_proprio_acesso_e_os_servicos_recusam",
        ),
        "Uma conta que se desativa, ou um gestor que se rebaixa, não tem como desfazer a própria "
        "ação sem outro gestor: a recusa evita o autobloqueio. Ratifica o comportamento existente.",
        "application",
        (
            f"{_LEG}test_aud09_dominio_aceita_o_gestor_remover_o_proprio_acesso_de_gestao",
            f"{_CAD}test_gestor_nao_pode_excluir_o_proprio_usuario",
        ),
        APROVACAO_REGULARIZACAO_E,
        "REG-E-03",
    ),
    Delta(
        "DLT-21",
        "REG-E-04 (regularização da Operação E)",
        "OS ativas impedem desativar e deixar o papel Técnico",
        "No legado o papel é a permissão: trocar o cargo do técnico o tira da lista e deixa a OS "
        "com quem já não é técnico; não há desativação. Nenhuma regra relaciona a mudança com as "
        "OS sob a responsabilidade do usuário.",
        "Quem tem OS ativa (fora de Concluída e Cancelada) atribuída a si não é desativado nem "
        "deixa o papel Técnico: conflito tipado (usuario_com_os_ativas), sem mutação, com "
        "usuário, OS, histórico e identificadores preservados. Nada é reatribuído nem cancelado, "
        "o histórico não é alterado e a mudança de cargo que preserva o papel Técnico não é "
        "impedida. A política completa de transferência continua pendente.",
        ("CAR-63",),
        "E",
        StatusDelta.IMPLEMENTADO,
        (
            f"{_RGA}test_dlt21_usuario_com_os_ativa_nao_e_desativado",
            f"{_RGA}test_dlt21_tecnico_com_os_ativa_nao_muda_de_papel",
            f"{_RGA}test_dlt21_com_a_os_encerrada_a_desativacao_e_a_mudanca_de_papel_sao_aceitas",
            f"{_RGA}test_dlt21_usuario_sem_os_e_desativado_e_muda_de_papel",
            f"{_RGA}test_dlt21_so_conta_a_os_sob_responsabilidade_do_usuario",
            f"{_RGA}test_dlt21_a_mudanca_de_cargo_que_preserva_o_papel_tecnico_nao_e_impedida",
            f"{_RGA}test_dlt21_o_gestor_resolve_as_os_a_mao_e_entao_desativa",
            f"{_RGA}test_dlt21_desativar_quem_ja_esta_inativo_continua_idempotente",
            f"{_RGA}test_dlt21_a_autorizacao_vem_antes_da_regra_das_os",
            f"{_RGA}test_dlt21_nao_cancela_nem_reatribui_automaticamente",
            f"{_AOE}test_dlt01_mudar_o_papel_nao_reatribui_as_os",
            f"{_AOE}test_dlt09_desativar_preserva_o_historico_e_nao_reatribui_as_os",
            f"{_DOM}test_dlt01_o_papel_nao_depende_das_permissoes",
            f"{_RGC}test_dlt21_trocar_o_tecnico_de_papel_com_os_ativa_o_legado_aceita_e_os_servicos_recusam",
            f"{_RGC}test_dlt21_com_a_os_encerrada_a_desativacao_e_aceita_nos_servicos",
        ),
        "Desativar ou rebaixar quem tem OS em andamento deixaria a OS com um responsável que não "
        "pode agir: o gestor deve resolver a OS antes, sem automatismos.",
        "application",
        (f"{_CAD}test_alterar_o_cargo_move_o_usuario_entre_tecnicos_e_gestores",),
        APROVACAO_REGULARIZACAO_E,
        "REG-E-04",
    ),
    Delta(
        "DLT-22",
        "REG-E-05 (regularização da Operação E)",
        "Campos obrigatórios: observação e descrição de peça",
        "O domínio aceita texto de observação e descrição de peça vazios ou só com espaços (só a "
        "tela os exigia).",
        "Ampliação do DLT-08: o texto da observação de OS e a descrição da peça utilizada são "
        "obrigatórios (texto não vazio depois de remover os espaços das extremidades). Modelo do "
        "equipamento, teste funcional, e-mail e escala seguem opcionais. A observação é validada "
        "depois da permissão, do vínculo e do estado; na peça, a quantidade antes da descrição; "
        "nenhuma recusa deixa mutação parcial.",
        ("CAR-80",),
        "E",
        StatusDelta.IMPLEMENTADO,
        (
            f"{_RGA}test_dlt22_observacao_vazia_ou_so_com_espacos_e_recusada_sem_mutacao",
            f"{_RGA}test_dlt22_observacao_valida_e_aceita_e_guardada_como_informada",
            f"{_RGA}test_dlt22_precedencia_autorizacao_vinculo_estado_e_so_depois_o_conteudo",
            f"{_RGA}test_dlt22_peca_com_descricao_vazia_e_recusada_e_a_os_nao_inicia_a_execucao",
            f"{_RGA}test_dlt22_uma_peca_invalida_entre_varias_recusa_o_apontamento_inteiro",
            f"{_RGA}test_dlt22_peca_valida_e_aceita_com_o_texto_como_informado",
            f"{_RGA}test_dlt22_a_ordem_herdada_de_pecas_e_horas_e_preservada",
            f"{_RGA}test_dlt22_os_campos_nao_listados_continuam_opcionais",
            "aplicacao/test_campos_obrigatorios.py::test_a_tabela_cobre_exatamente_os_campos_documentados",
            "aplicacao/test_campos_obrigatorios.py::test_campo_obrigatorio_vazio_ou_so_com_espacos_e_recusado_sem_mutacao",
            "aplicacao/test_campos_obrigatorios.py::test_campo_sem_validacao_continua_aceitando_o_vazio",
            f"{_RGD}test_dlt22_observacao_vazia_ou_so_com_espacos_e_recusada_sem_alterar_a_os",
            f"{_RGD}test_dlt22_observacao_com_texto_e_aceita_e_guardada_exatamente_como_informada",
            f"{_RGD}test_dlt22_precedencia_permissao_vinculo_estado_e_depois_o_conteudo",
            f"{_RGD}test_dlt22_o_instante_invalido_nao_mascara_a_recusa_do_conteudo",
            f"{_RGD}test_dlt22_peca_com_descricao_vazia_ou_so_com_espacos_e_recusada",
            f"{_RGD}test_dlt22_peca_valida_guarda_a_descricao_como_informada",
            f"{_RGD}test_dlt22_a_quantidade_e_verificada_antes_da_descricao",
            f"{_RGD}test_dlt22_peca_invalida_nao_inicia_a_execucao_da_os",
            f"{_RGD}test_dlt22_os_campos_do_delta_anterior_continuam_validados",
            f"{_RGC}test_dlt22_observacao_vazia_o_legado_aceita_e_os_servicos_recusam",
            f"{_RGC}test_dlt22_peca_sem_descricao_o_legado_aceita_e_os_servicos_recusam",
            f"{_RGC}test_dlt22_com_texto_valido_o_resultado_e_o_estado_sao_iguais_nos_dois",
            f"{_RGC}test_dlt22_quantidade_nao_positiva_continua_igual_nos_dois",
        ),
        "A interface legada já exigia estes dois textos (ui/tela_ordens.py, ui/tela_tecnico.py); "
        "a regra deve valer no servidor, para qualquer interface, como os demais campos do DLT-08.",
        "domain",
        (
            f"{_LEG}test_aud12_apontamento_aceita_zero_hora_e_intervencao_vazia",
            f"{_LEG}test_aud12_demais_textos_obrigatorios_na_tela_sao_aceitos_vazios",
        ),
        APROVACAO_REGULARIZACAO_E,
        "REG-E-05",
    ),
    Delta(
        "DLT-23",
        "REG-E-06 (regularização da Operação E)",
        "Disponibilidade manual: só Disponível e Ausente; Em atendimento é derivado",
        "O valor manual aceita qualquer disponibilidade, inclusive Em atendimento, e a "
        "autorização das duas vias de alteração não era única.",
        "A disponibilidade manual aceita exclusivamente Disponível e Ausente (recusa de domínio, "
        "sem mutação); Em atendimento é derivado das OS. ServicoDeUsuarios.definir_disponibilidade "
        "e ServicoDeDisponibilidade.alterar_disponibilidade delegam à mesma política (DLT-15): "
        "a própria, livre; a de terceiros, com gerir_usuarios. A ausência manual continua "
        "prevalecendo sobre a derivada; sem rotina em segundo plano.",
        ("CAR-51", "CAR-52"),
        "E",
        StatusDelta.IMPLEMENTADO,
        (
            f"{_RGA}test_dlt23_disponivel_e_ausente_sao_aceitos_como_valor_manual",
            f"{_RGA}test_dlt23_em_atendimento_nao_pode_ser_gravado_manualmente",
            f"{_RGA}test_dlt23_em_atendimento_e_exclusivamente_derivado_das_os",
            f"{_RGA}test_dlt23_o_usuario_altera_a_propria_disponibilidade_sem_permissao_de_gestao",
            f"{_RGA}test_dlt23_o_gestor_autorizado_altera_a_de_terceiros",
            f"{_RGA}test_dlt23_terceiro_sem_autorizacao_e_recusado_sem_mutacao",
            f"{_RGA}test_dlt23_ator_inexistente_e_inativo_sao_recusados",
            f"{_RGA}test_dlt23_as_duas_vias_decidem_igual_e_deixam_o_mesmo_estado",
            f"{_RGA}test_dlt23_as_duas_vias_delegam_a_mesma_politica_sem_duplicar_a_autorizacao",
            f"{_RGD}test_dlt23_so_disponivel_e_ausente_sao_valores_manuais",
            f"{_RGD}test_dlt23_em_atendimento_e_recusado_como_valor_manual",
            f"{_RGD}test_dlt23_um_valor_desconhecido_tambem_e_recusado",
            f"{_RGD}test_dlt23_o_usuario_grava_disponivel_e_ausente_e_recusa_em_atendimento_sem_mutacao",
            f"{_RGD}test_dlt23_em_atendimento_continua_sendo_derivado_e_a_ausencia_prevalece",
            f"{_RGC}test_dlt23_em_atendimento_manual_o_legado_aceita_e_os_servicos_recusam",
            f"{_RGC}test_dlt23_disponivel_e_ausente_manuais_sao_iguais_nos_dois",
            f"{_RGC}test_dlt23_a_ausencia_manual_prevalece_sobre_a_os_em_execucao_nos_servicos",
        ),
        "Gravar Em atendimento à mão contradiria a derivação das OS (D-05) e permitiria um valor "
        "que o próximo cálculo desmente; duas implementações da autorização poderiam divergir.",
        "domain",
        (
            f"{_DSP}test_disponibilidade_manual_e_aceita_para_qualquer_usuario_sem_permissao",
            f"{_DSP}test_rotina_so_recalcula_tecnicos_e_nunca_altera_o_gestor",
        ),
        APROVACAO_REGULARIZACAO_E,
        "REG-E-06",
    ),
)

DELTAS_POR_ID: dict[str, Delta] = {d.id: d for d in DELTAS}


@dataclass(frozen=True)
class Regularizacao:
    """Uma decisão de regularização da Operação E (REG-E-nn) e o seu registro definitivo.

    ``registro`` é o identificador definitivo: um ``DLT-nn`` (decisões que mudam ou ratificam
    comportamento) ou o próprio ``REG-E-nn`` (correções de rastreabilidade, sem delta). Os nove
    itens exigidos na aprovação são: identificador, regra anterior, regra aprovada, justificativa,
    camada responsável, testes, evidência de implementação, data e situação final.
    """

    id: str
    titulo: str
    registro: str
    regra_anterior: str
    regra_aprovada: str
    justificativa: str
    camada: str
    testes: tuple[str, ...]  # ``arquivo::teste`` relativos a ``backend/tests/``
    implementacao: tuple[str, ...]  # caminhos relativos a ``backend/``
    data: str
    situacao: str


_SRC = "src/manutencao/"
_REGULARIZACAO_DATA = "2026-11-17"
_IMPLEMENTADA = "Implementada e testada"

REGULARIZACOES_E: tuple[Regularizacao, ...] = (
    Regularizacao(
        "REG-E-01",
        "Proteção do último gestor",
        "DLT-18",
        "Nada impedia o sistema de ficar sem gestor administrativamente apto.",
        DELTAS_POR_ID["DLT-18"].aprovado,
        DELTAS_POR_ID["DLT-18"].justificativa,
        "application (com a condição de gestor apto no domínio)",
        DELTAS_POR_ID["DLT-18"].evidencia,
        (
            f"{_SRC}application/servicos/usuarios.py",
            f"{_SRC}domain/usuario.py",
            f"{_SRC}application/erros.py",
        ),
        _REGULARIZACAO_DATA,
        _IMPLEMENTADA,
    ),
    Regularizacao(
        "REG-E-02",
        "Alteração de papel (ratificação)",
        "DLT-19",
        "alterar_papel exigia papel Gestor e gerir_usuarios (DLT-01), sem decisão expressa.",
        DELTAS_POR_ID["DLT-19"].aprovado,
        DELTAS_POR_ID["DLT-19"].justificativa,
        "application",
        DELTAS_POR_ID["DLT-19"].evidencia,
        (f"{_SRC}application/servicos/usuarios.py",),
        _REGULARIZACAO_DATA,
        "Ratificada (já implementada) e testada",
    ),
    Regularizacao(
        "REG-E-03",
        "Autoproteção estendida (ratificação)",
        "DLT-20",
        "Ninguém se rebaixava de Gestor nem desativava a própria conta, sem decisão expressa.",
        DELTAS_POR_ID["DLT-20"].aprovado,
        DELTAS_POR_ID["DLT-20"].justificativa,
        "application",
        DELTAS_POR_ID["DLT-20"].evidencia,
        (f"{_SRC}application/servicos/usuarios.py",),
        _REGULARIZACAO_DATA,
        "Ratificada (já implementada) e testada",
    ),
    Regularizacao(
        "REG-E-04",
        "Ordens de serviço ativas",
        "DLT-21",
        "Desativar ou mudar o papel de quem tinha OS ativas era aceito, sem reatribuição.",
        DELTAS_POR_ID["DLT-21"].aprovado,
        DELTAS_POR_ID["DLT-21"].justificativa,
        "application",
        DELTAS_POR_ID["DLT-21"].evidencia,
        (f"{_SRC}application/servicos/usuarios.py", f"{_SRC}application/erros.py"),
        _REGULARIZACAO_DATA,
        _IMPLEMENTADA,
    ),
    Regularizacao(
        "REG-E-05",
        "Campos obrigatórios (observação e peça)",
        "DLT-22",
        "Observação e descrição de peça vazias eram aceitas (DLT-08 não as cobria).",
        DELTAS_POR_ID["DLT-22"].aprovado,
        DELTAS_POR_ID["DLT-22"].justificativa,
        "domain",
        DELTAS_POR_ID["DLT-22"].evidencia,
        (f"{_SRC}domain/ordem_servico.py", f"{_SRC}domain/peca_material.py"),
        _REGULARIZACAO_DATA,
        _IMPLEMENTADA,
    ),
    Regularizacao(
        "REG-E-06",
        "Disponibilidade manual e derivada",
        "DLT-23",
        "O valor manual aceitava Em atendimento e as duas vias tinham regras próprias.",
        DELTAS_POR_ID["DLT-23"].aprovado,
        DELTAS_POR_ID["DLT-23"].justificativa,
        "domain e application",
        DELTAS_POR_ID["DLT-23"].evidencia,
        (
            f"{_SRC}domain/disponibilidade.py",
            f"{_SRC}domain/usuario.py",
            f"{_SRC}application/servicos/politica_de_disponibilidade.py",
            f"{_SRC}application/servicos/disponibilidade.py",
            f"{_SRC}application/servicos/usuarios.py",
        ),
        _REGULARIZACAO_DATA,
        _IMPLEMENTADA,
    ),
    Regularizacao(
        "REG-E-07",
        "Rastreabilidade do CAR-37",
        "REG-E-07",
        "O teste do CAR-37 que só roda no legado (conclusão sem diagnóstico) não tinha o vínculo "
        "com o DLT-06 registrado, e a exclusão da variante podia ser lida como a do cenário todo.",
        "O vínculo com o DLT-06 está registrado em VARIANTES_SOMENTE_NO_LEGADO "
        "(aplicabilidade.py) e conferido por teste: só a variante é tratada à parte; o cenário "
        "segue executado em todos os adaptadores e as expectativas do legado ficam intactas.",
        "Evita que a exclusão de uma variante seja lida como divergência do cenário inteiro e "
        "deixa explícito por que o estado não é comparável: o DLT-06 o torna inalcançável.",
        "tests (caracterização)",
        (
            "caracterizacao/test_rastreabilidade.py::test_a_variante_so_no_legado_do_car_37_esta_ligada_ao_dlt_06",
            "caracterizacao/test_rastreabilidade.py::test_o_car_37_nao_e_classificado_como_divergente_nem_excluido_por_inteiro",
            "caracterizacao/test_rastreabilidade.py::test_toda_variante_so_no_legado_e_um_teste_do_legado_com_o_marcador_do_cenario",
        ),
        ("tests/caracterizacao/aplicabilidade.py", "tests/caracterizacao/test_tecnico.py"),
        _REGULARIZACAO_DATA,
        "Registrada e testada",
    ),
    Regularizacao(
        "REG-E-08",
        "Docstring do CAR-80",
        "REG-E-08",
        "O docstring do teste do legado do CAR-80 afirmava que o domínio e os serviços recusam "
        "textos que ainda aceitavam (observação, descrição de peça).",
        "Os docstrings e a documentação listam exatamente os campos validados e os não "
        "validados, a partir de tests/apoio/campos.py, conferido campo a campo nos serviços.",
        "Documentação que diz o que o código faz: o texto não pode esconder uma divergência.",
        "tests (caracterização)",
        (
            "aplicacao/test_campos_obrigatorios.py::test_a_tabela_cobre_exatamente_os_campos_documentados",
            "aplicacao/test_campos_obrigatorios.py::test_campo_obrigatorio_vazio_ou_so_com_espacos_e_recusado_sem_mutacao",
            "aplicacao/test_campos_obrigatorios.py::test_campo_sem_validacao_continua_aceitando_o_vazio",
            "caracterizacao/test_rastreabilidade.py::test_a_documentacao_lista_exatamente_os_campos_obrigatorios_e_os_nao_validados",
        ),
        ("tests/apoio/campos.py", "tests/caracterizacao/test_legado_defeitos.py"),
        _REGULARIZACAO_DATA,
        "Corrigido e testado",
    ),
)

REGULARIZACOES_POR_ID: dict[str, Regularizacao] = {r.id: r for r in REGULARIZACOES_E}
