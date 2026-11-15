"""Constantes do sistema: permissões, status, criticidades e disponibilidades."""

PERMISSOES = {
    "ver_equipamentos": "Visualizar equipamentos",
    "ver_os": "Consultar ordens de serviço",
    "abrir_os": "Abrir chamados (OS)",
    "ver_disponibilidade": "Consultar disponibilidade dos técnicos",
    "registrar_observacao": "Incluir apontamentos no histórico",
    "diagnosticar": "Registrar diagnóstico",
    "apontar_reparo": "Registrar horas, intervenções e peças",
    "atualizar_status": "Atualizar status operacional da OS",
    "concluir_tecnico": "Conclusão técnica da OS",
    "gerir_equipamentos": "Cadastrar/editar/inativar/excluir equipamentos",
    "gerir_usuarios": "Gerenciar usuários, cargos e permissões",
    "atribuir_os": "Atribuir/reatribuir OS a técnicos",
    "aprovar_os": "Aprovar, cancelar e encerrar OS",
}

PERM_COMUNS = ["ver_equipamentos", "ver_os", "abrir_os", "ver_disponibilidade", "registrar_observacao"]
PERM_TECNICO = PERM_COMUNS + ["diagnosticar", "apontar_reparo", "atualizar_status", "concluir_tecnico"]
PERM_GESTOR = PERM_COMUNS + ["gerir_equipamentos", "gerir_usuarios", "atribuir_os", "aprovar_os"]

STATUS_OS = ["Aberta", "Atribuída", "Em Execução", "Aguardando Peça",
             "Reparo Finalizado", "Aguardando Aprovação", "Concluída", "Cancelada"]
STATUS_TECNICO = ["Em Execução", "Aguardando Peça", "Reparo Finalizado"]
STATUS_FINAIS = ["Concluída", "Cancelada"]

CRITICIDADES = ["Baixa", "Média", "Alta", "Crítica"]
DISPONIBILIDADES = ["Disponível", "Em atendimento", "Ausente"]
