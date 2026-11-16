"""Base de dados do legado e registro dos cenários de caracterização.

**Base inicial.** Um repositório novo do legado nasce com 2 cargos, 3 usuários e 3 equipamentos
(``persistencia/repositorio.py::_popular_exemplo``). Os identificadores abaixo valem para qualquer
adaptador da fachada; um adaptador futuro deve reproduzir esta base.
"""

from dataclasses import dataclass
from enum import StrEnum

# Cargos
CARGO_GESTOR = 1
CARGO_TECNICO = 2

# Usuários (a base inicial)
ANA = 1  # Gestor
BRUNO = 2  # Técnico
CARLA = 3  # Técnico

# Equipamentos
TORNO = 1
COMPRESSOR = 2
EMPILHADEIRA = 3

# Permissões do legado (``models/permissoes.py``), na ordem do sistema
PERMISSOES_DO_SISTEMA = (
    "ver_equipamentos",
    "ver_os",
    "abrir_os",
    "ver_disponibilidade",
    "registrar_apontamento",
    "diagnosticar",
    "apontar_reparo",
    "atualizar_status",
    "concluir_os",
    "gerir_equipamentos",
    "gerir_usuarios",
    "atribuir_os",
    "aprovar_os",
)
PERMISSOES_PADRAO_TECNICO = PERMISSOES_DO_SISTEMA[:9]
PERMISSOES_PADRAO_GESTOR = (*PERMISSOES_DO_SISTEMA[:5], *PERMISSOES_DO_SISTEMA[9:])

# Valores textuais usados pelo legado (enums)
STATUS_ABERTA = "Aberta"
STATUS_ATRIBUIDA = "Atribuída"
STATUS_EM_EXECUCAO = "Em Execução"
STATUS_AGUARDANDO_PECA = "Aguardando Peça"
STATUS_REPARO_FINALIZADO = "Reparo Finalizado"
STATUS_AGUARDANDO_APROVACAO = "Aguardando Aprovação"
STATUS_CONCLUIDA = "Concluída"
STATUS_CANCELADA = "Cancelada"

DISPONIVEL = "Disponível"
EM_ATENDIMENTO = "Em atendimento"
AUSENTE = "Ausente"

BAIXA = "Baixa"
MEDIA = "Média"
ALTA = "Alta"
CRITICA = "Crítica"


class Classe(StrEnum):
    """Natureza de um comportamento caracterizado (item 3 da autorização da Operação B)."""

    PRESERVAR = "preservar"  # a nova implementação deve reproduzir
    MODIFICAR = "modificar_por_decisao"  # muda por decisão aprovada; ver deltas.py
    DEFEITO_LEGADO = "defeito_legado"  # não será reproduzido na nova arquitetura
    NAO_VERIFICAVEL = "nao_verificavel"  # ainda não pode ser verificado no legado


@dataclass(frozen=True)
class Cenario:
    id: str
    grupo: str
    titulo: str
    classe: Classe
    referencias: tuple[str, ...] = ()
