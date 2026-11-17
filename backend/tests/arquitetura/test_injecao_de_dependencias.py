"""Regras de injeção de dependências (D6, ADR-0005), por análise estática (``ast``).

* os serviços e as portas não importam repositórios concretos nem a composição;
* o domínio não conhece a aplicação nem a infraestrutura;
* só a raiz de composição escolhe implementações (importa ``infrastructure``);
* não há Service Locator nem singleton global mutável.
"""

import ast

import pytest

from tests.arquitetura.analise_imports import ArquivoFonte, coletar_importacoes, listar_fontes
from tests.guardas_ambiente import RAIZ_BACKEND

FONTES = listar_fontes(RAIZ_BACKEND / "src")
SERVICOS_E_PORTAS = [
    f
    for f in FONTES
    if f.modulo.startswith(("manutencao.application.servicos", "manutencao.application.portas"))
]
DOMINIO = [f for f in FONTES if f.camada == "domain"]
COM_ESTADO = [f for f in FONTES if f.camada in {"application", "infrastructure", "composicao"}]


def _importados(fonte: ArquivoFonte) -> set[str]:
    texto = fonte.caminho.read_text(encoding="utf-8")
    return {i.modulo for i in coletar_importacoes(texto, fonte.modulo, fonte.eh_pacote)}


def test_a_varredura_enxerga_servicos_portas_e_dominio() -> None:
    nomes = {f.modulo.rsplit(".", 1)[-1] for f in SERVICOS_E_PORTAS}
    assert {"ordens", "equipamentos", "usuarios", "disponibilidade", "repositorios"} <= nomes
    assert len(DOMINIO) >= 10


@pytest.mark.parametrize("fonte", SERVICOS_E_PORTAS, ids=lambda f: f.modulo)
def test_servicos_e_portas_nao_importam_implementacoes_concretas(fonte: ArquivoFonte) -> None:
    proibidos = ("manutencao.infrastructure", "manutencao.composicao", "manutencao.api")
    achados = [m for m in _importados(fonte) if m.startswith(proibidos)]
    assert achados == []


@pytest.mark.parametrize("fonte", DOMINIO, ids=lambda f: f.modulo)
def test_dominio_nao_importa_aplicacao_nem_infraestrutura(fonte: ArquivoFonte) -> None:
    proibidos = (
        "manutencao.application",
        "manutencao.infrastructure",
        "manutencao.composicao",
        "manutencao.api",
    )
    assert [m for m in _importados(fonte) if m.startswith(proibidos)] == []


def test_so_a_raiz_de_composicao_importa_a_infraestrutura() -> None:
    """A raiz de composição é a fábrica e o comando de administração do banco (que aplica as
    migrações); nenhum outro módulo, nem outro da própria composição, importa a infraestrutura."""
    quem = {
        f.modulo
        for f in FONTES
        if f.camada != "infrastructure"
        and any(m.startswith("manutencao.infrastructure") for m in _importados(f))
    }
    assert quem == {"manutencao.composicao.fabrica", "manutencao.composicao.banco"}


def test_a_infraestrutura_depende_das_portas_e_das_entidades_nao_dos_servicos() -> None:
    for fonte in FONTES:
        if fonte.camada != "infrastructure":
            continue
        assert not [
            m for m in _importados(fonte) if m.startswith("manutencao.application.servicos")
        ]


def _instancias_no_modulo(fonte: ArquivoFonte) -> list[str]:
    """Nomes atribuídos, no nível do módulo, ao resultado de uma chamada (um objeto criado)."""
    permitido = {"TypeVar"}
    achados: list[str] = []
    for no in ast.parse(fonte.caminho.read_text(encoding="utf-8")).body:
        valor = no.value if isinstance(no, ast.Assign | ast.AnnAssign) else None
        if isinstance(valor, ast.Call):
            funcao = valor.func
            nome = funcao.id if isinstance(funcao, ast.Name) else ast.unparse(funcao)
            if nome not in permitido:
                achados.append(f"{fonte.modulo}: {nome}(...)")
    return achados


@pytest.mark.parametrize("fonte", COM_ESTADO, ids=lambda f: f.modulo)
def test_nenhum_modulo_guarda_instancia_nem_estado_global(fonte: ArquivoFonte) -> None:
    arvore = ast.parse(fonte.caminho.read_text(encoding="utf-8"))
    assert not [n for n in ast.walk(arvore) if isinstance(n, ast.Global | ast.Nonlocal)]
    assert _instancias_no_modulo(fonte) == []


def test_nao_ha_localizador_de_servicos_nem_cache_de_instancia() -> None:
    suspeitos = ("lru_cache", "functools.cache", "get_container", "service_locator", "singleton")
    for fonte in FONTES:
        texto = fonte.caminho.read_text(encoding="utf-8").lower()
        assert not [s for s in suspeitos if s.lower() in texto], fonte.modulo


def test_o_detector_acusa_instancia_global(tmp_path_factory: pytest.TempPathFactory) -> None:
    pasta = tmp_path_factory.mktemp("fonte")
    arquivo = pasta / "ruim.py"
    arquivo.write_text("REPO = EquipamentosEmMemoria()\n\ndef f():\n    global REPO\n", "utf-8")
    fonte = ArquivoFonte(arquivo, "manutencao.composicao.ruim", False, "composicao")
    assert _instancias_no_modulo(fonte) == [
        "manutencao.composicao.ruim: EquipamentosEmMemoria(...)"
    ]
