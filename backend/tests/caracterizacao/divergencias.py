"""Divergências autorizadas entre o legado e o novo comportamento nas comparações lado a lado.

As comparações de ``test_adaptador_dominio.py`` e ``test_adaptador_servicos.py`` rodam **a mesma
operação em todos os estados** no legado e no novo código e exigem resultado e estado idênticos.
Desde a Operação E há diferenças **aprovadas** (deltas implementados). Para que elas nunca virem uma
exceção genérica, cada uma é um par (estado, operação) **nomeado aqui**, com o delta que a autoriza
e a recusa exata que o novo comportamento produz:

* o legado **aceita** a operação (é o comportamento caracterizado);
* o novo código **recusa com exatamente** a categoria declarada, e a recusa não altera estado
  nenhum (conferido pelo teste);
* todo par fora desta tabela continua exigindo igualdade total. Se um par da tabela deixar de
  divergir, o teste falha: a tabela não admite entrada sobrando.

``estado_sem_disponibilidade`` é a outra divergência, só dos serviços: a disponibilidade dos
técnicos é derivada das OS (D-05, DLT-05), enquanto o legado só a atualiza quando a rotina roda.
Antes da rotina compara-se tudo **menos** a disponibilidade; depois dela, tudo, inclusive.
"""

from dataclasses import replace

from tests.caracterizacao.cenarios import ANA, BRUNO, CARLA
from tests.caracterizacao.fachada import Recusa

# (construtor de estado, nome da operação) -> (delta que autoriza, recusa do novo comportamento)
DIVERGENCIAS_AUTORIZADAS: dict[tuple[str, str], tuple[str, Recusa]] = {}


def _autorizar(
    delta: str, recusa: Recusa, construtores: tuple[str, ...], operacoes: tuple[str, ...]
) -> None:
    for construtor in construtores:
        for operacao in operacoes:
            assert (construtor, operacao) not in DIVERGENCIAS_AUTORIZADAS, (construtor, operacao)
            DIVERGENCIAS_AUTORIZADAS[(construtor, operacao)] = (delta, recusa)


def _observacao(usuario: int) -> str:
    return f"observação de {usuario}"


# DLT-03 (D-04): OS Concluída ou Cancelada é imutável; o legado aceitava a observação.
_autorizar(
    "DLT-03",
    Recusa.OS_ENCERRADA,
    ("concluida", "cancelada_atribuida"),
    tuple(_observacao(u) for u in (ANA, BRUNO, CARLA)),
)
_autorizar("DLT-03", Recusa.OS_ENCERRADA, ("cancelada",), (_observacao(ANA), _observacao(CARLA)))

# DLT-04 (D-04): sem vínculo com a OS (nem gestor, nem responsável, nem quem a abriu), recusa. A
# autorização vem antes do estado: um terceiro numa OS encerrada também é recusado por vínculo.
_autorizar("DLT-04", Recusa.SEM_VINCULO_COM_A_OS, ("aberta", "cancelada"), (_observacao(BRUNO),))

# DLT-08: zero hora no apontamento (o legado só recusava horas negativas).
_autorizar(
    "DLT-08",
    Recusa.HORAS_NAO_POSITIVAS,
    ("atribuida", "em_execucao", "aguardando_peca"),
    ("reparo zero hora",),
)

# DLT-06 (D-06): finalizar o reparo exige o diagnóstico. As OS Em Execução e Aguardando Peça do
# roteiro têm intervenção, mas não diagnóstico.
_autorizar(
    "DLT-06",
    Recusa.SEM_DIAGNOSTICO,
    ("em_execucao", "aguardando_peca"),
    ("status Reparo Finalizado",),
)

# Estados que o legado alcança e o novo comportamento não: o diagnóstico passou a ser pré-condição
# de Reparo Finalizado (DLT-06), então "Reparo Finalizado sem diagnóstico" não pode ser construído.
INALCANCAVEIS_NO_NOVO: dict[str, str] = {"reparo_finalizado_sem_diagnostico": "DLT-06"}


def estado_sem_disponibilidade(
    estado: tuple[object, ...],
) -> tuple[object, ...]:
    """O ``estado`` da fachada sem a disponibilidade dos usuários (a derivação é a DLT-05)."""
    os_, usuarios, equipamentos, cargos, tecnicos = estado
    assert isinstance(usuarios, tuple)
    return (
        os_,
        tuple(replace(u, disponibilidade="") for u in usuarios),
        equipamentos,
        cargos,
        tecnicos,
    )
