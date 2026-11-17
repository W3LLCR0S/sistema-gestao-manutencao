"""Campos de texto obrigatórios e opcionais no domínio e nos serviços (DLT-08, DLT-22; REG-E-05/08).

Fonte **única** da lista que a documentação e os docstrings repetem. ``test_campos_obrigatorios``
(``tests/aplicacao``) prova, campo a campo, que os serviços recusam texto vazio ou só com espaços
nos ``CAMPOS_OBRIGATORIOS`` e o aceitam nos ``CAMPOS_SEM_VALIDACAO``; ``test_rastreabilidade``
confere que ``docs/DECISOES_APROVADAS.md`` cita exatamente estes rótulos.
"""

# (rótulo, delta que o tornou obrigatório)
CAMPOS_OBRIGATORIOS: tuple[tuple[str, str], ...] = (
    ("descrição da falha", "DLT-08"),
    ("parecer técnico", "DLT-08"),
    ("causa-raiz", "DLT-08"),
    ("intervenção realizada", "DLT-08"),
    ("motivo da reprovação", "DLT-08"),
    ("motivo do cancelamento", "DLT-08"),
    ("nome do usuário", "DLT-08"),
    ("nome do equipamento", "DLT-08"),
    ("texto da observação", "DLT-22"),
    ("descrição da peça", "DLT-22"),
)

# Continuam opcionais: a regularização da Operação E não os torna obrigatórios (REG-E-05).
CAMPOS_SEM_VALIDACAO: tuple[str, ...] = (
    "modelo do equipamento",
    "teste funcional",
    "e-mail do usuário",
    "escala do usuário",
)
