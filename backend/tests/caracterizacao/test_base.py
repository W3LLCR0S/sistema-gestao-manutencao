"""Infraestrutura da caracterização: isolamento, relógio fixo e base inicial do legado.

Estes testes não descrevem regras de negócio (não têm identificador de cenário): garantem que o
ambiente de caracterização é seguro e determinístico.
"""

import importlib
import json
import sys
from pathlib import Path

import pytest

from tests.caracterizacao.adaptador_legado import AdaptadorLegado, categorizar
from tests.caracterizacao.cenarios import (
    ANA,
    BRUNO,
    CARGO_GESTOR,
    CARGO_TECNICO,
    CARLA,
    DISPONIVEL,
    PERMISSOES_PADRAO_GESTOR,
    PERMISSOES_PADRAO_TECNICO,
)
from tests.caracterizacao.fachada import Fachada, Recusa, RelogioFixo
from tests.caracterizacao.fluxos import os_aberta
from tests.guardas_ambiente import DIRETORIO_DADOS, RAIZ_REPOSITORIO


def test_base_inicial_do_legado(f: Fachada) -> None:
    usuarios = {u.id: u for u in f.usuarios()}
    assert [(u.id, u.nome, u.cargo, u.disponibilidade) for u in usuarios.values()] == [
        (ANA, "Ana Souza", "Gestor", DISPONIVEL),
        (BRUNO, "Bruno Lima", "Técnico", DISPONIVEL),
        (CARLA, "Carla Mendes", "Técnico", DISPONIVEL),
    ]
    assert [(e.id, e.nome, e.modelo, e.ativo) for e in f.equipamentos()] == [
        (1, "Torno CNC", "GL 240", True),
        (2, "Compressor de Ar", "CSW 40", True),
        (3, "Empilhadeira Elétrica", "PT 1650", True),
    ]
    cargos = {c.id: c for c in f.cargos()}
    assert cargos[CARGO_GESTOR].permissoes == PERMISSOES_PADRAO_GESTOR
    assert cargos[CARGO_TECNICO].permissoes == PERMISSOES_PADRAO_TECNICO
    assert f.tecnicos() == (BRUNO, CARLA)
    assert f.todas_as_os() == ()


def test_repositorio_legado_recebe_caminho_temporario_explicito(
    adaptador: AdaptadorLegado, caminho_base: Path, tmp_path: Path
) -> None:
    assert Path(adaptador.repo.caminho) == caminho_base
    assert tmp_path in Path(adaptador.repo.caminho).parents
    assert DIRETORIO_DADOS not in Path(adaptador.repo.caminho).parents
    assert caminho_base.is_file()  # o construtor semeou e gravou no caminho temporário


def test_adaptador_recusa_caminho_dentro_de_dados() -> None:
    with pytest.raises(ValueError, match="dados/"):
        AdaptadorLegado(DIRETORIO_DADOS / "qualquer.json")


def test_legado_nao_deixa_a_raiz_no_sys_path(f: Fachada) -> None:
    assert str(RAIZ_REPOSITORIO) not in sys.path


def test_relogio_fixo_controla_as_datas_do_legado(f: Fachada, relogio: RelogioFixo) -> None:
    numero = os_aberta(f)
    os_ = f.os(numero)
    assert os_ is not None
    assert os_.data_abertura == "10/03/2026 09:00"
    assert os_.historico[0].data == "10/03/2026 09:00"
    relogio.avancar(hours=2, minutes=5)
    f.cancelar(numero, ANA, "teste")
    cancelada = f.os(numero)
    assert cancelada is not None
    assert cancelada.data_conclusao == "10/03/2026 11:05"


def test_relogio_do_legado_e_restaurado_ao_fechar(caminho_base: Path) -> None:
    adaptador = AdaptadorLegado(caminho_base)  # carrega o legado e instala o relógio controlado
    servico = importlib.import_module("models.servico")
    controlado = servico.datetime
    assert controlado.now() == adaptador.relogio.agora()
    adaptador.fechar()
    assert servico.datetime is not controlado
    assert servico.datetime.now().year >= 2025  # volta a ler o relógio do sistema


def test_arquivo_json_isolado_e_independente_do_real(adaptador: AdaptadorLegado) -> None:
    dados = json.loads(adaptador.caminho.read_text(encoding="utf-8"))
    assert [u["nome"] for u in dados["usuarios"]] == ["Ana Souza", "Bruno Lima", "Carla Mendes"]


@pytest.mark.parametrize(
    ("mensagem", "categoria"),
    [
        ("Sem permissão: Abrir chamados (OS).", Recusa.SEM_PERMISSAO),
        ("Esta OS não está atribuída a você.", Recusa.NAO_RESPONSAVEL),
        ("Operação não permitida com a OS em 'Concluída'.", Recusa.ESTADO_INVALIDO),
        ("Mensagem que nenhuma regra conhecida produz.", Recusa.DESCONHECIDA),
    ],
)
def test_categorizacao_das_recusas_por_mensagem(mensagem: str, categoria: Recusa) -> None:
    assert categorizar(mensagem) is categoria
