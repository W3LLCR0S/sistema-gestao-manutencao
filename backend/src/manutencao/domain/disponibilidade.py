"""Disponibilidade derivada das OS (D-05, DLT-05).

A disponibilidade de atendimento **não é gravada por rotina**: sai das OS do técnico a cada
consulta. Regra aprovada:

* a **ausência** é um estado manual, guardado à parte (``Usuario.disponibilidade``), e **tem
  precedência** sobre o estado derivado;
* sem ausência, uma OS **Em Execução** caracteriza ``Em atendimento``;
* ``Aguardando Peça`` (e qualquer outro status) **não** caracteriza atendimento;
* sem ausência e sem OS em execução, o técnico está ``Disponível``.

Nenhum SLA nem regra de ocupação nova.
"""

from manutencao.domain.enums import Disponibilidade


def derivar_disponibilidade(manual: Disponibilidade, ha_os_em_execucao: bool) -> Disponibilidade:
    """O valor efetivo, a partir do valor manual guardado e das OS do técnico."""
    if manual is Disponibilidade.AUSENTE:
        return Disponibilidade.AUSENTE
    return Disponibilidade.EM_ATENDIMENTO if ha_os_em_execucao else Disponibilidade.DISPONIVEL
