"""``OrdemServico.restaurar``: reconstituição fiel, sem aplicar regras de negócio."""

import pytest

from manutencao.domain.enums import StatusOS
from manutencao.domain.ordem_servico import OrdemServico
from tests.dominio.fabrica import Mundo, instantaneo


def _restaurar(origem: OrdemServico) -> OrdemServico:
    return OrdemServico.restaurar(
        numero=origem.numero,
        equipamento=origem.equipamento,
        falha=origem.falha,
        criticidade=origem.criticidade,
        aberta_por=origem.aberta_por,
        data_abertura=origem.data_abertura,
        status=origem.status,
        tecnico_atribuido=origem.tecnico_atribuido,
        diagnostico=origem.diagnostico,
        causa_raiz=origem.causa_raiz,
        teste_funcional=origem.teste_funcional,
        motivo_cancelamento=origem.motivo_cancelamento,
        data_conclusao=origem.data_conclusao,
        servicos=origem.servicos,
    )


@pytest.mark.parametrize("status", list(StatusOS))
def test_restaurar_reproduz_tudo_o_que_a_os_expoe_em_cada_estado(status: StatusOS) -> None:
    """Horas, intervenções e peças derivam do histórico e batem com o original."""
    original = Mundo().em_status(status)
    assert instantaneo(_restaurar(original)) == instantaneo(original)


def test_a_os_restaurada_continua_operavel_e_acrescenta_ao_historico() -> None:
    mundo = Mundo()
    original = mundo.atribuida()
    restaurada = _restaurar(original)
    restaurada.registrar_diagnostico(mundo.bruno, "Rolamento", "Graxa", quando=mundo.quando())
    assert [s.numero for s in restaurada.servicos] == [1, 2, 3, 4]
    assert len(original.servicos) == 3  # a original não foi tocada


def test_restaurar_nao_registra_nada_no_historico_nem_valida_transicoes() -> None:
    mundo = Mundo()
    original = mundo.concluida()
    restaurada = _restaurar(original)
    assert restaurada.servicos == original.servicos
    # as regras seguem valendo depois de restaurar: uma OS concluída não aceita nova aprovação
    with pytest.raises(Exception, match="Operação não permitida"):
        restaurada.aprovar(mundo.ana, quando=mundo.quando())
