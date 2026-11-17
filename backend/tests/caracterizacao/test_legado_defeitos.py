"""Defeitos conhecidos do legado, reproduzidos como são (nada aqui é corrigido).

Cada teste **descreve** o comportamento atual e o rotula com o achado da auditoria
(``docs/AUDITORIA_ARQUITETURAL.md``). Quando a nova arquitetura mudar o comportamento, o teste
correspondente é substituído (delta em ``deltas.py``) ou, se o defeito for exclusivamente do
legado, deixa de ser executado contra o novo código.

Os testes marcados como *descartáveis* dependem de detalhes internos do legado (formato do JSON
ou de duas instâncias do repositório) e serão removidos junto com ``models/`` e ``persistencia/``.
"""

import json
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path

import pytest

from tests.caracterizacao.adaptador_legado import AdaptadorLegado
from tests.caracterizacao.cenarios import (
    ALTA,
    ANA,
    BAIXA,
    BRUNO,
    CARGO_GESTOR,
    CARGO_TECNICO,
    CARLA,
    DISPONIVEL,
    EM_ATENDIMENTO,
    EMPILHADEIRA,
    PERMISSOES_PADRAO_GESTOR,
    PERMISSOES_PADRAO_TECNICO,
    STATUS_AGUARDANDO_PECA,
    STATUS_CANCELADA,
    STATUS_CONCLUIDA,
    STATUS_EM_EXECUCAO,
    STATUS_REPARO_FINALIZADO,
    TORNO,
)
from tests.caracterizacao.fachada import Fachada, Peca, Recusa, RelogioFixo
from tests.caracterizacao.fluxos import (
    aceitar,
    os_aberta,
    os_atribuida,
    os_cancelada,
    os_concluida,
    os_snap,
    recusada,
)


@contextmanager
def segunda_instancia(caminho: Path, relogio: RelogioFixo) -> Iterator[AdaptadorLegado]:
    """Outra instância do legado sobre o MESMO arquivo temporário."""
    outra = AdaptadorLegado(caminho, relogio)
    try:
        yield outra
    finally:
        outra.fechar()


# ============================================================ AUD-09: regras só na interface


@pytest.mark.cenario("CAR-71")
def test_aud09_dominio_aceita_o_gestor_remover_o_proprio_acesso_de_gestao(f: Fachada) -> None:
    """Só ``ui/tela_usuarios.py`` bloqueia isso (linhas 58 e 104); o domínio não impede."""
    f.editar_usuario(ANA, cargo=CARGO_TECNICO)
    assert not f.usuario_pode(ANA, "gerir_usuarios")

    f.editar_usuario(ANA, cargo=CARGO_GESTOR)
    f.definir_permissoes_cargo(CARGO_GESTOR, ())
    assert not f.usuario_pode(ANA, "gerir_usuarios")  # nenhum gestor pode mais gerir usuários


@pytest.mark.cenario("CAR-72")
def test_aud09_qualquer_usuario_altera_a_disponibilidade_de_qualquer_outro(f: Fachada) -> None:
    """A tela só mostra "minha disponibilidade"; o domínio não tem regra (nem permissão)."""
    f.definir_permissoes_cargo(CARGO_TECNICO, ())
    f.definir_disponibilidade(CARLA, "Ausente")  # nenhuma permissão e nenhum solicitante
    carla = f.usuario(CARLA)
    assert carla is not None
    assert carla.disponibilidade == "Ausente"


# ================================================= AUD-02: autorização desigual (só OS exige)


@pytest.mark.cenario("CAR-73")
def test_aud02_equipamentos_sao_geridos_sem_identidade_nem_permissao(f: Fachada) -> None:
    """``Repositorio.remover_equipamento`` e ``Equipamento.inativar`` não recebem usuário."""
    f.definir_permissoes_cargo(CARGO_GESTOR, ())
    f.definir_permissoes_cargo(CARGO_TECNICO, ())  # ninguém tem gerir_equipamentos
    novo = f.cadastrar_equipamento("Prensa", "P1")
    f.inativar_equipamento(novo)
    f.editar_equipamento(novo, nome="Prensa 2", modelo="P2")
    aceitar(f.remover_equipamento(novo))
    assert f.equipamento(novo) is None


@pytest.mark.cenario("CAR-73")
def test_aud02_exclusao_de_usuario_nao_confere_a_permissao_do_solicitante(f: Fachada) -> None:
    novo = f.cadastrar_usuario("Diego", CARGO_TECNICO)
    assert not f.usuario_pode(BRUNO, "gerir_usuarios")
    aceitar(f.remover_usuario(novo, BRUNO))  # um técnico exclui um usuário
    assert f.usuario(novo) is None


# ======================================================= AUD-03: permissões por texto livre


@pytest.mark.cenario("CAR-74")
def test_aud03_permissao_com_nome_errado_e_negada_em_silencio(f: Fachada) -> None:
    assert f.usuario_pode(ANA, "aprovar_os") is True
    assert f.usuario_pode(ANA, "aprovar_oss") is False  # erro de digitação: sem erro, só False
    resultado = recusada(f.exigir_permissao(ANA, "aprovar_oss"), Recusa.SEM_PERMISSAO)
    assert resultado.mensagem == "Sem permissão: aprovar_oss."  # cai no nome cru, sem descrição


@pytest.mark.cenario("CAR-74")
def test_aud03_definir_permissoes_ignora_silenciosamente_nomes_desconhecidos(f: Fachada) -> None:
    f.definir_permissoes_cargo(CARGO_TECNICO, ("ver_os", "voar", "aprovar_oss"))
    cargo = next(c for c in f.cargos() if c.id == CARGO_TECNICO)
    assert cargo.permissoes == ("ver_os",)  # sem erro: os nomes inexistentes somem


# ====================================================== AUD-05 / AUD-04: ids e concorrência


@pytest.mark.cenario("CAR-75")
def test_aud05_ids_de_usuario_e_equipamento_sao_reaproveitados_apos_exclusao(f: Fachada) -> None:
    """``max()+1``: excluir o maior id faz o próximo cadastro reutilizá-lo (delta: monotônico)."""
    usuario = f.cadastrar_usuario("Diego", CARGO_TECNICO)
    aceitar(f.remover_usuario(usuario, ANA))
    assert f.cadastrar_usuario("Outro", CARGO_TECNICO) == usuario

    equipamento = f.cadastrar_equipamento("Prensa", "P1")
    aceitar(f.remover_equipamento(equipamento))
    assert f.cadastrar_equipamento("Furadeira", "F1") == equipamento


@pytest.mark.cenario("CAR-75")
def test_aud05_excluir_um_id_do_meio_nao_o_reaproveita(f: Fachada) -> None:
    """O reaproveitamento só ocorre com o maior id; ids do meio ficam como lacuna."""
    aceitar(f.remover_equipamento(2))
    assert f.cadastrar_equipamento("Nova", "N1") == EMPILHADEIRA + 1
    assert [e.id for e in f.equipamentos()] == [TORNO, EMPILHADEIRA, EMPILHADEIRA + 1]


@pytest.mark.cenario("CAR-76")
def test_aud04_aud05_duas_instancias_geram_o_mesmo_numero_e_a_ultima_a_gravar_vence(
    adaptador: AdaptadorLegado, relogio: RelogioFixo, caminho_base: Path
) -> None:
    """Descartável: perda de atualização e numeração duplicada (Apêndice A, item C)."""
    with segunda_instancia(caminho_base, relogio) as outra:
        numero_a = int(aceitar(adaptador.abrir_os(ANA, TORNO, "A", BAIXA)).valor)
        numero_b = int(aceitar(outra.abrir_os(ANA, EMPILHADEIRA, "B", ALTA)).valor)
        assert numero_a == numero_b == 1  # número duplicado

        adaptador.salvar_e_recarregar()
        outra.salvar_e_recarregar()  # grava por cima da gravação da primeira

        assert [(o.numero, o.falha) for o in outra.todas_as_os()] == [(1, "B")]
        assert [(o.numero, o.falha) for o in adaptador.todas_as_os()] == [
            (1, "A")
        ]  # ainda em memória


# ==================================================== AUD-08: vínculos silenciosamente nulos


@pytest.mark.cenario("CAR-77")
def test_aud08_arquivo_sem_o_usuario_perde_o_vinculo_sem_aviso(
    adaptador: AdaptadorLegado, relogio: RelogioFixo, caminho_base: Path
) -> None:
    """Descartável: ``usuarios.get(...)`` devolve None em vez de falhar (formato do JSON)."""
    numero = os_atribuida(adaptador, tecnico=BRUNO)  # aberta por Carla
    adaptador.salvar_e_recarregar()
    dados = json.loads(caminho_base.read_text(encoding="utf-8"))
    dados["usuarios"] = [u for u in dados["usuarios"] if u["id"] != CARLA]
    caminho_base.write_text(json.dumps(dados), encoding="utf-8")

    with segunda_instancia(caminho_base, relogio) as recarregada:
        os_ = os_snap(recarregada, numero)
        assert os_.aberta_por_id is None  # vínculo apagado sem erro
        assert os_.historico[0].responsavel_id is None
        assert os_.tecnico_id == BRUNO  # os demais vínculos permanecem


@pytest.mark.cenario("CAR-77")
def test_aud08_arquivo_sem_o_equipamento_falha_ao_carregar(
    adaptador: AdaptadorLegado, relogio: RelogioFixo, caminho_base: Path
) -> None:
    """Descartável: para o equipamento, ao contrário do usuário, a carga levanta ``KeyError``."""
    os_aberta(adaptador)
    adaptador.salvar_e_recarregar()
    dados = json.loads(caminho_base.read_text(encoding="utf-8"))
    dados["equipamentos"] = [e for e in dados["equipamentos"] if e["id"] != TORNO]
    caminho_base.write_text(json.dumps(dados), encoding="utf-8")

    with pytest.raises(KeyError):
        AdaptadorLegado(caminho_base, relogio)


# ===================================== AUD-10 / AUD-16: construtor grava, interface controla


@pytest.mark.cenario("CAR-78")
def test_aud10_construtor_semeia_e_grava_o_arquivo_quando_ele_nao_existe(
    tmp_path: Path, relogio: RelogioFixo
) -> None:
    caminho = tmp_path / "novo.json"
    assert not caminho.exists()
    adaptador = AdaptadorLegado(caminho, relogio)
    try:
        assert caminho.is_file()  # efeito colateral no construtor
        assert len(adaptador.usuarios()) == 3
    finally:
        adaptador.fechar()


@pytest.mark.cenario("CAR-78")
def test_aud16_operacoes_nao_gravam_no_arquivo_a_interface_decide_quando_salvar(
    adaptador: AdaptadorLegado, caminho_base: Path
) -> None:
    antes = caminho_base.read_text(encoding="utf-8")
    os_aberta(adaptador)
    assert caminho_base.read_text(encoding="utf-8") == antes  # nada gravado ainda
    adaptador.repo.salvar()
    assert caminho_base.read_text(encoding="utf-8") != antes


# ==================================== AUD-11: apontamento em OS encerrada e por qualquer um


@pytest.mark.cenario("CAR-79")
@pytest.mark.parametrize(
    ("construir", "status"),
    [
        (os_concluida, STATUS_CONCLUIDA),
        (lambda f: os_cancelada(f, atribuida=True), STATUS_CANCELADA),
    ],
)
def test_aud11_observacao_e_aceita_em_os_encerrada_de_qualquer_usuario_com_permissao(
    f: Fachada, construir: Callable[[Fachada], int], status: str
) -> None:
    numero = construir(f)
    tecnico_estranho = f.cadastrar_usuario("Diego", CARGO_TECNICO)  # sem relação com a OS
    antes = os_snap(f, numero)
    assert antes.status == status

    aceitar(f.adicionar_observacao(numero, tecnico_estranho, "Comentário tardio"))
    aceitar(f.adicionar_observacao(numero, CARLA, "Quem abriu também comenta"))

    depois = os_snap(f, numero)
    assert depois.status == status  # o status não muda
    assert len(depois.historico) == len(antes.historico) + 2  # mas o histórico "encerrado" cresce
    assert [s.responsavel_id for s in depois.historico[-2:]] == [tecnico_estranho, CARLA]


# ================================================ AUD-12: validações só na interface (CLI)


@pytest.mark.cenario("CAR-80")
@pytest.mark.parametrize("falha", ["", "   "])
def test_aud12_abertura_aceita_falha_vazia_ou_so_espacos(f: Fachada, falha: str) -> None:
    numero = int(aceitar(f.abrir_os(CARLA, TORNO, falha, BAIXA)).valor)
    assert os_snap(f, numero).falha == falha


@pytest.mark.cenario("CAR-80")
def test_aud12_apontamento_aceita_zero_hora_e_intervencao_vazia(f: Fachada) -> None:
    numero = os_atribuida(f)
    aceitar(f.apontar_reparo(numero, BRUNO, 0.0, "", (Peca("", 1),)))
    os_ = os_snap(f, numero)
    assert (os_.horas_trabalhadas, os_.intervencoes) == (0.0, ("",))
    assert os_.status == STATUS_EM_EXECUCAO
    assert os_.pecas[0].descricao == ""


@pytest.mark.cenario("CAR-80")
def test_aud12_demais_textos_obrigatorios_na_tela_sao_aceitos_vazios(f: Fachada) -> None:
    numero = os_atribuida(f)
    aceitar(f.registrar_diagnostico(numero, BRUNO, "", ""))
    aceitar(f.adicionar_observacao(numero, CARLA, ""))
    aceitar(f.cancelar(numero, ANA, ""))
    novo = f.cadastrar_usuario("", CARGO_TECNICO)
    equipamento = f.cadastrar_equipamento("", "")
    os_ = os_snap(f, numero)
    assert os_.status == STATUS_CANCELADA
    assert os_.motivo_cancelamento == ""
    snap = f.usuario(novo)
    assert snap is not None
    assert snap.nome == ""
    assert f.equipamento(equipamento) is not None


@pytest.mark.cenario("CAR-80")
def test_aud12_validacoes_que_o_dominio_ja_aplica_sao_preservadas(f: Fachada) -> None:
    """Contraste: horas negativas e peça com quantidade não positiva já são recusadas."""
    numero = os_atribuida(f)
    recusada(f.apontar_reparo(numero, BRUNO, -1.0, "i"), Recusa.HORAS_NEGATIVAS)
    recusada(f.apontar_reparo(numero, BRUNO, 1.0, "i", (Peca("x", 0),)), Recusa.QUANTIDADE_INVALIDA)


# ================================================ AUD-13: disponibilidade desatualizada


@pytest.mark.cenario("CAR-81")
def test_aud13_reproducao_do_apendice_e_da_auditoria(f: Fachada) -> None:
    numero = aceitar(f.abrir_os(ANA, TORNO, "x", BAIXA)).valor
    aceitar(f.atribuir(numero, BRUNO, ANA))
    aceitar(f.apontar_reparo(numero, BRUNO, 1.0, "i"))
    assert _disp(f, BRUNO) == DISPONIVEL  # ainda não recalculado
    f.atualizar_disponibilidades()
    assert _disp(f, BRUNO) == EM_ATENDIMENTO
    aceitar(f.alterar_status(numero, BRUNO, STATUS_AGUARDANDO_PECA))
    f.atualizar_disponibilidades()
    assert _disp(f, BRUNO) == DISPONIVEL  # "Aguardando Peça" não conta como atendimento


def _disp(f: Fachada, usuario: int) -> str:
    snap = f.usuario(usuario)
    assert snap is not None
    return snap.disponibilidade


# ================================================== AUD-20: técnico é uma permissão editável


@pytest.mark.cenario("CAR-82")
def test_aud20_conceder_apontar_reparo_ao_gestor_o_transforma_em_tecnico_atribuivel(
    f: Fachada,
) -> None:
    assert ANA not in f.tecnicos()
    f.definir_permissoes_cargo(CARGO_GESTOR, (*PERMISSOES_PADRAO_GESTOR, "apontar_reparo"))
    assert ANA in f.tecnicos()
    numero = os_aberta(f)
    aceitar(f.atribuir(numero, ANA, ANA))  # a gestora atribui a OS a si mesma
    assert os_snap(f, numero).tecnico_id == ANA


@pytest.mark.cenario("CAR-82")
def test_aud20_retirar_apontar_reparo_dos_tecnicos_os_tira_da_lista_mas_nao_das_os(
    f: Fachada,
) -> None:
    numero = os_atribuida(f, tecnico=BRUNO)
    f.definir_permissoes_cargo(
        CARGO_TECNICO, tuple(p for p in PERMISSOES_PADRAO_TECNICO if p != "apontar_reparo")
    )
    assert f.tecnicos() == ()
    assert os_snap(f, numero).tecnico_id == BRUNO  # a OS continua com quem deixou de ser "técnico"


# ================================================== AUD-21: finalizar sem diagnóstico


@pytest.mark.cenario("CAR-83")
def test_aud21_finalizar_sem_diagnostico_exige_um_caminho_indireto(f: Fachada) -> None:
    numero = os_atribuida(f)
    aceitar(f.apontar_reparo(numero, BRUNO, 1.0, "troca"))
    aceitar(f.alterar_status(numero, BRUNO, STATUS_REPARO_FINALIZADO))

    recusada(f.concluir_tecnicamente(numero, BRUNO, "ok", True), Recusa.SEM_DIAGNOSTICO)
    resultado = recusada(f.registrar_diagnostico(numero, BRUNO, "p", "c"), Recusa.ESTADO_INVALIDO)
    assert resultado.mensagem == "Operação não permitida com a OS em 'Reparo Finalizado'."

    # a saída é voltar o status, diagnosticar e finalizar de novo
    aceitar(f.alterar_status(numero, BRUNO, STATUS_EM_EXECUCAO))
    aceitar(f.registrar_diagnostico(numero, BRUNO, "p", "c"))
    aceitar(f.alterar_status(numero, BRUNO, STATUS_REPARO_FINALIZADO))
    aceitar(f.concluir_tecnicamente(numero, BRUNO, "ok", True))

    tipos = os_snap(f, numero).tipos_do_historico
    assert tipos.count("Mudança de status") == 6  # 3 a mais do que o caminho direto
    assert tipos.count("Diagnóstico") == 1
