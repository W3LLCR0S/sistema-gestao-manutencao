"""Registro de deltas: o que muda em relação ao legado, por decisão já aprovada.

Segue ADR-0006 (seção "Deltas de comportamento"): para cada mudança, o comportamento atual (com
o(s) cenário(s) que o caracterizam), o comportamento aprovado e a decisão que o autorizou.

O legado continua com o comportamento descrito em ``legado``; os cenários listados em ``cenarios``
verificam esse comportamento antigo no adaptador do legado. Um delta só passa a ``IMPLEMENTADO``
quando (1) o código está concluído, (2) há testes específicos aprovados, (3) a comparação com o
legado existe e (4) esta rastreabilidade aponta a ``evidencia``: ``arquivo::teste``, relativos a
``backend/tests/``. ``test_rastreabilidade.py`` confere o estado esperado de **cada** delta e que a
evidência existe.

Estado atual: DLT-07 (datas UTC) e DLT-11 (permissões tipadas), da Operação C, e DLT-10 (IDs
monotônicos), da Operação D, estão implementados. Os demais são da Operação E.
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
)

DELTAS_POR_ID: dict[str, Delta] = {d.id: d for d in DELTAS}
