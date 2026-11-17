"""Base de dados do legado e registro dos cenários de caracterização.

**Base inicial.** Um repositório novo do legado nasce com 2 cargos, 3 usuários e 3 equipamentos
(``persistencia/repositorio.py::_popular_exemplo``). Os identificadores abaixo valem para qualquer
adaptador da fachada; um adaptador futuro deve reproduzir esta base.

**Registro.** Cada comportamento caracterizado é um :class:`Cenario` (``CAR-nn``) classificado em
uma de quatro naturezas (:class:`Classe`). Os testes se ligam ao registro pelo marcador
``@pytest.mark.cenario("CAR-nn")``; ``test_rastreabilidade.py`` garante que registro e testes
coincidem.
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
    DEFEITO_LEGADO = "defeito_legado"  # exclusivo do legado; não será reproduzido
    NAO_VERIFICAVEL = "nao_verificavel"  # ainda não pode ser verificado no legado


@dataclass(frozen=True)
class Cenario:
    """Um comportamento do legado caracterizado por um ou mais testes (marcador ``cenario``).

    ``motivo`` só se aplica a :attr:`Classe.NAO_VERIFICAVEL`: explica por que não há teste.
    """

    id: str
    grupo: str
    titulo: str
    classe: Classe
    referencias: tuple[str, ...] = ()
    motivo: str = ""


P = Classe.PRESERVAR
M = Classe.MODIFICAR
D = Classe.DEFEITO_LEGADO
N = Classe.NAO_VERIFICAVEL

# A numeração CAR-nn é própria desta operação. A matriz CAR-01..CAR-53 do plano técnico não
# consta do repositório (docs/ nem planejamento/); a correspondência com ela NÃO foi verificada.
CENARIOS: tuple[Cenario, ...] = (
    # --- abertura e ciclo de vida (test_abertura.py)
    Cenario("CAR-01", "abertura", "Abertura cria OS Aberta com histórico de abertura", P),
    Cenario("CAR-02", "abertura", "Qualquer perfil com abrir_os abre OS", P),
    Cenario("CAR-03", "abertura", "Criticidades Baixa, Média, Alta e Crítica", P),
    Cenario("CAR-04", "abertura", "Numeração sequencial; recusa não consome número", P),
    Cenario("CAR-05", "abertura", "Equipamento inativo recusa a abertura", P),
    Cenario("CAR-06", "abertura", "Abertura sem permissão; permissão antes do equipamento", P),
    Cenario("CAR-07", "abertura", "Ciclo completo: 11 registros na ordem esperada", P),
    Cenario("CAR-08", "abertura", "Status percorre as etapas do fluxo feliz", P),
    Cenario("CAR-09", "abertura", "Recusa nunca altera estado nem histórico", P),
    # --- atribuição (test_atribuicao.py)
    Cenario("CAR-10", "atribuicao", "Atribuição inicial leva a Atribuída", P),
    Cenario("CAR-11", "atribuicao", "Reatribuição troca o técnico e preserva dados", P),
    Cenario("CAR-12", "atribuicao", "Atribuir ao mesmo técnico é recusado", P),
    Cenario("CAR-13", "atribuicao", "Atribuir a quem não é técnico é recusado", P),
    Cenario("CAR-14", "atribuicao", "Atribuir exige a permissão atribuir_os", P),
    Cenario("CAR-15", "atribuicao", "Estados que permitem atribuir/reatribuir", P),
    Cenario("CAR-16", "atribuicao", "Estados que impedem atribuir/reatribuir", P),
    Cenario(
        "CAR-17",
        "atribuicao",
        "Atribuição a técnico Ausente aceita pelo domínio",
        M,
        ("AUD-09", "D-03"),
    ),
    Cenario(
        "CAR-18",
        "atribuicao",
        "Ser técnico depende da permissão apontar_reparo",
        M,
        ("AUD-20", "D-02"),
    ),
    # --- aprovação, reprovação e cancelamento (test_gestor.py)
    Cenario("CAR-19", "gestor", "Aprovar conclui a OS e fixa a data de conclusão", P),
    Cenario("CAR-20", "gestor", "Reprovar devolve a OS ao técnico em execução", P),
    Cenario("CAR-21", "gestor", "Cancelar vale para qualquer OS não encerrada", P),
    Cenario("CAR-22", "gestor", "aprovar_os é uma só permissão: aprovar, reprovar, cancelar", P),
    # --- histórico (test_historico.py)
    Cenario("CAR-23", "historico", "Histórico numerado de 1 a N, por OS", P),
    Cenario("CAR-24", "historico", "Ordem de inclusão; datas não regridem", P),
    Cenario("CAR-25", "historico", "Tipo, autor e conteúdo de cada registro", P),
    Cenario("CAR-26", "historico", "Reprovação e reatribuição só acrescentam registros", P),
    Cenario("CAR-27", "historico", "Datas de abertura, registros e conclusão vêm do relógio", P),
    Cenario("CAR-28", "historico", "Histórico por equipamento e persistência", P),
    Cenario(
        "CAR-90", "historico", "Datas são texto dd/mm/aaaa hh:mm sem fuso", M, ("AUD-07", "D-11")
    ),
    # --- execução técnica (test_tecnico.py)
    Cenario("CAR-29", "tecnico", "Diagnóstico registra parecer e causa sem mudar status", P),
    Cenario("CAR-30", "tecnico", "Diagnóstico: estados, responsável e ordem das verificações", P),
    Cenario("CAR-31", "tecnico", "Reparo: horas, intervenções e peças acumulam", P),
    Cenario("CAR-32", "tecnico", "Reparo: recusas de horas, peças, estado e responsável", P),
    Cenario("CAR-33", "tecnico", "Tabela completa 8x8 de transições do técnico", P),
    Cenario(
        "CAR-34", "tecnico", "Finalizar reparo sem diagnóstico é aceito", M, ("AUD-21", "D-06")
    ),
    Cenario("CAR-35", "tecnico", "Conclusão com teste aprovado submete para aprovação", P),
    Cenario("CAR-36", "tecnico", "Conclusão com teste reprovado mantém Reparo Finalizado", P),
    Cenario("CAR-37", "tecnico", "Conclusão: diagnóstico, estado, responsável e permissão", P),
    # --- observação (test_observacao.py)
    Cenario("CAR-38", "observacao", "Observação cria registro Apontamento sem mudar status", P),
    Cenario(
        "CAR-39", "observacao", "Qualquer usuário com a permissão inclui observação", M, ("D-04",)
    ),
    Cenario("CAR-40", "observacao", "Observação exige registrar_apontamento", P),
    # --- disponibilidade (test_disponibilidade.py): D-05, cenários 1 a 10
    Cenario("CAR-41", "disponibilidade", "D-05 #1 sem OS ativas: Disponível", P, ("D-05",)),
    Cenario("CAR-42", "disponibilidade", "D-05 #2 OS Atribuída: Disponível", P, ("D-05",)),
    Cenario(
        "CAR-43",
        "disponibilidade",
        "D-05 #3 Em Execução: Em atendimento só após a rotina",
        M,
        ("D-05", "AUD-13"),
    ),
    Cenario("CAR-44", "disponibilidade", "D-05 #4 só Aguardando Peça: Disponível", P, ("D-05",)),
    Cenario(
        "CAR-45",
        "disponibilidade",
        "D-05 #5 Em Execução e Aguardando Peça: Em atendimento",
        P,
        ("D-05",),
    ),
    Cenario("CAR-46", "disponibilidade", "D-05 #6 ausência manual prevalece", P, ("D-05",)),
    Cenario(
        "CAR-47",
        "disponibilidade",
        "D-05 #7 ausência removida: recalcula só após a rotina",
        M,
        ("D-05", "AUD-13"),
    ),
    Cenario(
        "CAR-48",
        "disponibilidade",
        "D-05 #8 Reparo Finalizado libera só após a rotina",
        M,
        ("D-05", "AUD-13"),
    ),
    Cenario(
        "CAR-49",
        "disponibilidade",
        "D-05 #9 reatribuição reflete só após a rotina",
        M,
        ("D-05", "AUD-13"),
    ),
    Cenario(
        "CAR-50",
        "disponibilidade",
        "D-05 #10 consulta após transição está desatualizada",
        M,
        ("D-05", "AUD-13"),
    ),
    Cenario(
        "CAR-51",
        "disponibilidade",
        "Disponibilidade manual e rotina de atualização",
        M,
        ("D-05", "AUD-09"),
    ),
    Cenario("CAR-52", "disponibilidade", "A rotina só recalcula técnicos", P),
    Cenario("CAR-53", "disponibilidade", "Carga = OS ativas atribuídas ao técnico", P),
    Cenario("CAR-54", "disponibilidade", "Técnico ausente continua técnico e com carga", P),
    # --- permissões (test_permissoes.py)
    Cenario("CAR-55", "permissoes", "Perfis padrão e matriz de permissões", P),
    Cenario("CAR-56", "permissoes", "Permissões do cargo valem para todos os seus usuários", P),
    Cenario("CAR-57", "permissoes", "Operações técnicas exigem ser o responsável", P),
    Cenario("CAR-58", "permissoes", "Gestor e técnico não operam o lado do outro", P),
    Cenario("CAR-59", "permissoes", "Cada operação técnica depende da sua permissão", P),
    Cenario(
        "CAR-60",
        "permissoes",
        "Sem permissões: nada opera e ninguém é técnico",
        M,
        ("AUD-20", "D-02"),
    ),
    # --- cadastros (test_cadastros.py)
    Cenario("CAR-61", "cadastros", "Cadastro de usuário: próximo id e disponibilidade inicial", P),
    Cenario("CAR-62", "cadastros", "Novo técnico recebe OS; novo gestor não", P),
    Cenario("CAR-63", "cadastros", "Edição de usuário e mudança de cargo", P),
    Cenario("CAR-64", "cadastros", "Exclusão sem histórico; autoexclusão recusada", P),
    Cenario("CAR-65", "cadastros", "Usuário com histórico em OS não é excluído", P),
    Cenario("CAR-66", "cadastros", "Cadastro e edição de equipamento", P),
    Cenario("CAR-67", "cadastros", "Inativar e reativar equipamento", P),
    Cenario("CAR-68", "cadastros", "Excluir equipamento sem OS", P),
    Cenario("CAR-69", "cadastros", "Equipamento com OS não é excluído", P),
    Cenario("CAR-70", "cadastros", "Cargos fixos e persistência dos cadastros", P),
    # --- defeitos conhecidos (test_legado_defeitos.py)
    Cenario(
        "CAR-71", "defeitos", "Domínio aceita o gestor remover o próprio acesso", D, ("AUD-09",)
    ),
    Cenario(
        "CAR-72",
        "defeitos",
        "Disponibilidade de qualquer um alterável por qualquer um",
        D,
        ("AUD-09",),
    ),
    Cenario(
        "CAR-73", "defeitos", "Equipamentos e exclusão de usuário sem permissão", D, ("AUD-02",)
    ),
    Cenario("CAR-74", "defeitos", "Permissão com nome errado: negada em silêncio", D, ("AUD-03",)),
    Cenario(
        "CAR-75", "defeitos", "Ids de usuário e equipamento são reaproveitados", M, ("AUD-05",)
    ),
    Cenario(
        "CAR-76",
        "defeitos",
        "Duas instâncias: número duplicado e perda de dados",
        D,
        ("AUD-04", "AUD-05"),
    ),
    Cenario("CAR-77", "defeitos", "Carga do JSON apaga vínculos sem aviso", D, ("AUD-08",)),
    Cenario(
        "CAR-78",
        "defeitos",
        "Construtor grava; a interface decide quando salvar",
        D,
        ("AUD-10", "AUD-16"),
    ),
    Cenario(
        "CAR-79",
        "defeitos",
        "Observação aceita em OS encerrada, de qualquer usuário",
        M,
        ("AUD-11", "D-04"),
    ),
    Cenario("CAR-80", "defeitos", "Textos vazios e zero hora aceitos pelo domínio", M, ("AUD-12",)),
    Cenario(
        "CAR-81",
        "defeitos",
        "Reprodução do Apêndice E da auditoria (disponibilidade)",
        M,
        ("AUD-13", "D-05"),
    ),
    Cenario(
        "CAR-82",
        "defeitos",
        "Conceder apontar_reparo ao gestor o torna técnico",
        M,
        ("AUD-20", "D-02"),
    ),
    Cenario(
        "CAR-83",
        "defeitos",
        "Finalizar sem diagnóstico exige caminho indireto",
        M,
        ("AUD-21", "D-06"),
    ),
    # --- CLI (test_cli_fumaca.py)
    Cenario("CAR-84", "cli", "CLI inicia, mostra o login, cria dados na cópia e encerra", P),
    Cenario("CAR-85", "cli", "Login rejeita entradas inválidas", P),
    Cenario("CAR-86", "cli", "Login só pelo ID, sem senha", D, ("AUD-01", "D-01")),
    Cenario("CAR-87", "cli", "Menu montado conforme as permissões", P),
    Cenario("CAR-88", "cli", "Abrir OS pela CLI e persistir na cópia", P),
    Cenario(
        "CAR-89", "cli", "Confirmação de técnico ausente existe só na tela", M, ("AUD-09", "D-03")
    ),
    # --- requisitos que ainda não podem ser verificados contra o legado (sem teste)
    Cenario(
        "NV-01",
        "nao_verificavel",
        "Papel explícito Gestor/Técnico (D-02)",
        N,
        ("D-02",),
        "O legado não tem papel: a identidade é a permissão apontar_reparo (CAR-18, CAR-60).",
    ),
    Cenario(
        "NV-02",
        "nao_verificavel",
        "Usuário ativo/inativo",
        N,
        ("AUD-10", "AUD-08"),
        "Usuario não tem campo ativo; só há exclusão, bloqueada por histórico (CAR-64, CAR-65).",
    ),
    Cenario(
        "NV-03",
        "nao_verificavel",
        "Instantes UTC e apresentação em America/Sao_Paulo (D-11)",
        N,
        ("D-11",),
        "O legado grava texto sem fuso (CAR-90); não há conversão nem fuso para comparar.",
    ),
    Cenario(
        "NV-04",
        "nao_verificavel",
        "Validação obrigatória de entradas no domínio",
        N,
        ("AUD-12",),
        "O legado não valida no domínio; a validação está só na tela (CAR-80).",
    ),
    Cenario(
        "NV-05",
        "nao_verificavel",
        "Hierarquia de erros (401/403/404/409/422)",
        N,
        ("AUD-14",),
        "O legado tem uma só exceção; só a categoria derivada do texto é observável.",
    ),
    Cenario(
        "NV-06",
        "nao_verificavel",
        "Incompatibilidade entre main.py e app/",
        N,
        ("AUD-06", "AUD-18"),
        "app/ não tem ponto de entrada nem é importada; exercitá-la exigiria reconfigurar "
        "seus caminhos de dados.",
    ),
    Cenario(
        "NV-07",
        "nao_verificavel",
        "Autenticação por senha, sessão e expiração",
        N,
        ("D-01", "AUD-01"),
        "Não há senha no legado e D-01 está pendente (CAR-86 registra a ausência).",
    ),
    Cenario(
        "NV-08",
        "nao_verificavel",
        "Concorrência segura e transações",
        N,
        ("AUD-04", "D-12"),
        "Só a perda de atualização do JSON é caracterizável (CAR-76); transações são da Fase 03.",
    ),
    Cenario(
        "NV-09",
        "nao_verificavel",
        "Prazo e OS atrasada",
        N,
        ("D-15",),
        "Não há prazo no modelo atual e D-15 está pendente.",
    ),
)

CENARIOS_POR_ID: dict[str, Cenario] = {c.id: c for c in CENARIOS}
