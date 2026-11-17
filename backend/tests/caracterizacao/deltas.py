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

DLT-12 a DLT-17 foram **aprovados expressamente** em 2026-11-17 (``APROVACAO_REGULARIZACAO_D``) e
registram, além dos campos de sempre, a justificativa, a camada responsável e o teste do
comportamento legado (``testes_legado``). Os deltas da Operação E vêm de decisões aprovadas em
2026-11-15 e foram implementados após a autorização da Operação E (``APROVACAO_OPERACAO_E``) e
registram os mesmos campos. Os identificadores anteriores não foram alterados.
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

APROVACAO_OPERACAO_E = (
    "Decisões aprovadas em 2026-11-15 (docs/DECISOES_APROVADAS.md: D-02 a D-06 e as melhorias "
    "5.1 e 5.2; docs/adr/0009); implementação da Operação E autorizada em 2026-11-17"
)

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
)

DELTAS_POR_ID: dict[str, Delta] = {d.id: d for d in DELTAS}
