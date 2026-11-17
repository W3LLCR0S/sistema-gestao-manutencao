"""O mesmo roteiro no legado e nos serviços, com o mesmo relógio fixo (fixture ``par``)."""

from dataclasses import dataclass

from tests.caracterizacao.adaptador_legado import AdaptadorLegado
from tests.caracterizacao.adaptador_servicos import AdaptadorServicos
from tests.caracterizacao.fachada import RelogioFixo


@dataclass
class Par:
    """Dois adaptadores independentes: as operações são aplicadas a ambos e comparadas."""

    legado: AdaptadorLegado
    servicos: AdaptadorServicos
    relogio: RelogioFixo
