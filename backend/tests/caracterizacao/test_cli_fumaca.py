"""Testes de fumaça da CLI legada, numa cópia temporária isolada (ver ``cli_isolada.py``).

Mostram que a CLI da Entrega 1 continua executável (D-10) e fixam alguns comportamentos que só
existem na interface (login por ID sem senha, menu por permissão, confirmação ao atribuir a
técnico ausente). Nada aqui toca o ``dados/`` real.
"""

import re
from pathlib import Path

import pytest

from tests.caracterizacao.cli_isolada import CliIsolada

DESPEDIDA = "Dados salvos. Até logo!"


@pytest.fixture
def cli(tmp_path: Path) -> CliIsolada:
    return CliIsolada(tmp_path)


@pytest.mark.cenario("CAR-84")
def test_cli_inicia_mostra_o_login_e_encerra_com_zero(cli: CliIsolada) -> None:
    assert cli.copia_e_fiel_ao_original()
    execucao = cli.executar(["0"])

    assert execucao.codigo == 0, execucao.erro
    assert execucao.erro == ""
    assert "SISTEMA DE MANUTENÇÃO DE EQUIPAMENTOS — LOGIN" in execucao.saida
    for linha in ("[1] Ana Souza", "[2] Bruno Lima", "[3] Carla Mendes", "[0] Sair do sistema"):
        assert linha in execucao.saida
    assert DESPEDIDA in execucao.saida


@pytest.mark.cenario("CAR-84")
def test_cli_cria_os_dados_de_exemplo_apenas_na_copia(cli: CliIsolada) -> None:
    assert not cli.arquivo_de_dados.exists()
    cli.executar(["0"])
    dados = cli.dados()
    assert [u["nome"] for u in dados["usuarios"]] == ["Ana Souza", "Bruno Lima", "Carla Mendes"]
    assert [e["nome"] for e in dados["equipamentos"]] == [
        "Torno CNC",
        "Compressor de Ar",
        "Empilhadeira Elétrica",
    ]
    assert dados["ordens"] == []
    assert sorted(p.name for p in cli.arquivo_de_dados.parent.iterdir()) == ["dados.json"]


@pytest.mark.cenario("CAR-84")
def test_cli_encerra_com_elegancia_quando_a_entrada_acaba(cli: CliIsolada) -> None:
    execucao = cli.executar([])  # EOF imediato no login
    assert execucao.codigo == 0, execucao.erro
    assert DESPEDIDA in execucao.saida


@pytest.mark.cenario("CAR-85")
def test_cli_rejeita_entradas_invalidas_no_login(cli: CliIsolada) -> None:
    execucao = cli.executar(["abc", "99", "0"])
    assert execucao.codigo == 0, execucao.erro
    assert "! Digite um número inteiro." in execucao.saida
    assert "! Usuário não encontrado." in execucao.saida


@pytest.mark.cenario("CAR-86")
def test_aud01_login_e_so_pelo_id_sem_senha_e_o_gestor_ve_o_menu_de_gestao(cli: CliIsolada) -> None:
    """AUD-01: digitar o ID basta para assumir o cargo de Gestor."""
    execucao = cli.executar(["1", "0", "0"])  # login como Ana, "0" volta ao login, "0" sai
    assert execucao.codigo == 0, execucao.erro
    assert "Usuário: Ana Souza  |  Cargo: Gestor" in execucao.saida
    assert "senha" not in execucao.saida.lower()
    for rotulo in (
        "Abrir chamado (nova OS)",
        "Gerenciar equipamentos",
        "Gerenciar usuários",
        "Permissões dos cargos",
        "Atribuir / reatribuir OS",
        "Aprovar / encerrar / cancelar OS",
    ):
        assert rotulo in execucao.saida
    assert "Registrar diagnóstico" not in execucao.saida


@pytest.mark.cenario("CAR-87")
def test_cli_monta_o_menu_do_tecnico_conforme_as_permissoes(cli: CliIsolada) -> None:
    execucao = cli.executar(["2", "99", "0", "0"])
    assert execucao.codigo == 0, execucao.erro
    assert "Usuário: Bruno Lima  |  Cargo: Técnico" in execucao.saida
    for rotulo in (
        "Registrar diagnóstico",
        "Apontar reparo (horas, intervenções, peças)",
        "Atualizar status da OS",
        "Conclusão técnica da OS",
    ):
        assert rotulo in execucao.saida
    for ausente in ("Gerenciar equipamentos", "Atribuir / reatribuir OS", "Aprovar / encerrar"):
        assert ausente not in execucao.saida
    assert "! Opção inválida." in execucao.saida  # "99" não está no menu


@pytest.mark.cenario("CAR-88")
def test_cli_abre_uma_os_e_a_persiste_na_copia(cli: CliIsolada) -> None:
    menu = cli.executar(["1", "0", "0"]).saida
    assert re.search(r"^\s*3\. Abrir chamado \(nova OS\)$", menu, re.MULTILINE)

    # login Ana; abrir chamado (3); equipamento 1; falha; criticidade 3 (Alta); ENTER; sair; sair
    execucao = cli.executar(["1", "3", "1", "Bomba sem pressão", "3", "", "0", "0"])
    assert execucao.codigo == 0, execucao.erro
    assert "✓ OS nº 1 aberta." in execucao.saida

    ordens = cli.dados()["ordens"]
    assert len(ordens) == 1
    ordem = ordens[0]
    assert (ordem["numero"], ordem["status"], ordem["falha"]) == (1, "Aberta", "Bomba sem pressão")
    assert (ordem["criticidade"], ordem["equipamento_id"], ordem["aberta_por_id"]) == ("Alta", 1, 1)
    assert [s["tipo"] for s in ordem["servicos"]] == ["Abertura"]
    assert re.fullmatch(r"\d{2}/\d{2}/\d{4} \d{2}:\d{2}", ordem["data_abertura"])


@pytest.mark.cenario("CAR-88")
def test_cli_reabre_com_os_dados_gravados_e_consulta_a_os(cli: CliIsolada) -> None:
    cli.executar(["1", "3", "1", "Bomba sem pressão", "3", "", "0", "0"])

    # login Ana; consultar OS (2); filtro "Todas" (1); detalhes da OS 1; ENTER; sair; sair
    execucao = cli.executar(["1", "2", "1", "1", "", "0", "0"])
    assert execucao.codigo == 0, execucao.erro
    assert "ORDEM DE SERVIÇO Nº 1" in execucao.saida
    assert "Falha relatada:     Bomba sem pressão" in execucao.saida
    assert "Status:             Aberta" in execucao.saida
    assert "Criticidade:        Alta" in execucao.saida


@pytest.mark.cenario("CAR-89")
def test_cli_pede_confirmacao_so_na_tela_ao_atribuir_a_tecnico_ausente(cli: CliIsolada) -> None:
    """AUD-09/D-03: a confirmação é da interface; o domínio aceita a atribuição sem ela."""
    # Bruno (2) marca-se como Ausente: "Alterar minha disponibilidade" (6), opção 3 = Ausente
    menu_bruno = cli.executar(["2", "0", "0"]).saida
    assert re.search(r"^\s*6\. Alterar minha disponibilidade$", menu_bruno, re.MULTILINE)
    cli.executar(["2", "6", "3", "0", "0"])
    bruno = next(u for u in cli.dados()["usuarios"] if u["id"] == 2)
    assert bruno["disponibilidade"] == "Ausente"

    # Ana abre uma OS e tenta atribuí-la a Bruno (menu 10), respondendo "n" à confirmação
    menu_ana = cli.executar(["1", "0", "0"]).saida
    assert re.search(r"^\s*10\. Atribuir / reatribuir OS$", menu_ana, re.MULTILINE)
    recusada = cli.executar(["1", "3", "1", "Falha", "2", "", "10", "1", "2", "n", "0", "0"])
    assert recusada.codigo == 0, recusada.erro
    assert "Técnico está ausente. Atribuir mesmo assim? (s/n):" in recusada.saida
    ordem = cli.dados()["ordens"][0]
    assert (ordem["status"], ordem["tecnico_atribuido_id"]) == ("Aberta", None)

    # respondendo "s", a atribuição é feita
    aceita = cli.executar(["1", "10", "1", "2", "s", "0", "0"])
    assert aceita.codigo == 0, aceita.erro
    assert "✓ OS 1 atribuída a Bruno Lima." in aceita.saida
    ordem = cli.dados()["ordens"][0]
    assert (ordem["status"], ordem["tecnico_atribuido_id"]) == ("Atribuída", 2)
