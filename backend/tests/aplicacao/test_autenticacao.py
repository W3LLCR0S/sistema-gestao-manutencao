"""Serviço de autenticação, limitador, contas e painel (aplicação, repositórios em memória)."""

from datetime import timedelta

import pytest

from manutencao.application.erros import (
    CredenciaisInvalidasError,
    EntradaInvalidaError,
    MuitasTentativasError,
    NaoAutenticadoError,
    NaoEncontradoError,
    RegraDeAplicacaoError,
)
from manutencao.application.servicos.autenticacao import (
    hash_do_token,
    normalizar_matricula,
    validar_senha,
)
from manutencao.application.servicos.limitador import LimitadorDeTentativas
from manutencao.composicao.aplicacao import Aplicacao, criar_aplicacao_em_memoria
from manutencao.domain.enums import Criticidade, Papel
from manutencao.domain.erros import PermissaoNegadaError
from manutencao.domain.matricula import matricula_valida
from manutencao.infrastructure.seguranca import HasherArgon2
from tests.apoio.ambiente import ANA, BRUNO, CARLA
from tests.apoio.api import (
    HASHER_RAPIDO,
    MAT_ANA,
    MAT_BRUNO,
    MAT_CARLA,
    MATRICULA_DESCONHECIDA,
    SENHA,
    semear_com_acesso,
)
from tests.apoio.relogio import RelogioFixo


@pytest.fixture
def relogio() -> RelogioFixo:
    return RelogioFixo()


@pytest.fixture
def app(relogio: RelogioFixo) -> Aplicacao:
    aplicacao = criar_aplicacao_em_memoria(relogio=relogio, hasher=HASHER_RAPIDO)
    semear_com_acesso(aplicacao)
    return aplicacao


# ----------------------------------------------------------------------------------- login
def test_login_valido_devolve_sessao_com_expiracao_e_csrf(
    app: Aplicacao, relogio: RelogioFixo
) -> None:
    iniciada = app.autenticacao.login(MAT_ANA, SENHA)
    assert iniciada.usuario.id == ANA
    assert iniciada.sessao.expira_em == relogio.agora() + timedelta(hours=8)
    assert iniciada.sessao.csrf
    assert len(iniciada.token) >= 40  # 256 bits em base64 url-safe


def test_token_nao_e_guardado_e_representacoes_nao_o_revelam(app: Aplicacao) -> None:
    iniciada = app.autenticacao.login(MAT_ANA, SENHA)
    assert app.sessoes.obter(iniciada.token) is None
    assert app.sessoes.obter(hash_do_token(iniciada.token)) is not None
    assert iniciada.token not in repr(iniciada)
    assert iniciada.token not in repr(iniciada.sessao)
    credencial = app.credenciais.obter_por_usuario(ANA)
    assert credencial is not None
    assert credencial.senha_hash not in repr(credencial)


def test_a_senha_e_guardada_como_hash_argon2id(app: Aplicacao) -> None:
    credencial = app.credenciais.obter_por_usuario(ANA)
    assert credencial is not None
    assert credencial.senha_hash.startswith("$argon2id$")
    assert SENHA not in credencial.senha_hash


def test_hashes_da_mesma_senha_diferem_por_sal(app: Aplicacao) -> None:
    a, b = app.credenciais.obter_por_usuario(BRUNO), app.credenciais.obter_por_usuario(CARLA)
    assert a is not None
    assert b is not None
    assert a.senha_hash != b.senha_hash  # mesma senha, sais diferentes


@pytest.mark.parametrize(
    ("matricula", "senha"),
    [
        (MAT_ANA, "errada-errada-1"),
        (MATRICULA_DESCONHECIDA, SENHA),
        ("", SENHA),
        (MAT_ANA, ""),
        ("   ", SENHA),
        ("ana", SENHA),  # o nome de usuário antigo
        ("bruno", SENHA),
        (MAT_ANA.lower(), SENHA),  # minúsculas violam o formato
        (MAT_ANA[:-1], SENHA),
        (MAT_ANA + "0", SENHA),
    ],
)
def test_login_recusado_levanta_sempre_o_mesmo_erro(
    app: Aplicacao, matricula: str, senha: str
) -> None:
    with pytest.raises(CredenciaisInvalidasError) as erro:
        app.autenticacao.login(matricula, senha)
    assert erro.value.mensagem == "Credenciais inválidas."


def test_usuario_inativo_nao_entra_mesmo_com_a_senha_certa(app: Aplicacao) -> None:
    app.container.servico_usuarios.desativar(ANA, CARLA)
    with pytest.raises(CredenciaisInvalidasError):
        app.autenticacao.login(MAT_CARLA, SENHA)


def test_login_de_usuario_inexistente_gasta_o_mesmo_trabalho_de_hash() -> None:
    """Sem conta, o servidor ainda verifica um hash: o tempo não revela se a matrícula existe."""

    class Espiao(HasherArgon2):
        def __init__(self) -> None:
            super().__init__(time_cost=1, memory_cost=8, parallelism=1)
            self.verificacoes = 0

        def verificar(self, senha_hash: str, senha: str) -> bool:
            self.verificacoes += 1
            return super().verificar(senha_hash, senha)

    espiao = Espiao()
    aplicacao = criar_aplicacao_em_memoria(hasher=espiao)
    semear_com_acesso(aplicacao)
    antes = espiao.verificacoes
    with pytest.raises(CredenciaisInvalidasError):
        aplicacao.autenticacao.login(MATRICULA_DESCONHECIDA, SENHA)
    assert espiao.verificacoes == antes + 1
    with pytest.raises(CredenciaisInvalidasError):
        aplicacao.autenticacao.login(MAT_ANA, "errada-errada-1")
    assert espiao.verificacoes == antes + 2


def test_hash_com_parametros_antigos_e_renovado_no_login(relogio: RelogioFixo) -> None:
    fraco = HasherArgon2(time_cost=1, memory_cost=8, parallelism=1)
    forte = HasherArgon2(time_cost=2, memory_cost=16, parallelism=1)
    aplicacao = criar_aplicacao_em_memoria(relogio=relogio, hasher=fraco)
    semear_com_acesso(aplicacao)
    antigo = aplicacao.credenciais.obter_por_usuario(ANA)
    assert antigo is not None
    # mesmo armazenamento, serviço com parâmetros mais fortes
    from manutencao.application.servicos.autenticacao import ServicoDeAutenticacao
    from manutencao.infrastructure.memoria import SemTransacao

    servico = ServicoDeAutenticacao(
        aplicacao.credenciais,
        aplicacao.sessoes,
        aplicacao.container.usuarios,
        forte,
        relogio,
        SemTransacao(),
    )
    servico.login(MAT_ANA, SENHA)
    novo = aplicacao.credenciais.obter_por_usuario(ANA)
    assert novo is not None
    assert novo.senha_hash != antigo.senha_hash
    assert forte.verificar(novo.senha_hash, SENHA)


# ------------------------------------------------------------------------------- autenticar
def test_autenticar_devolve_o_usuario_com_o_cargo_atual(app: Aplicacao) -> None:
    iniciada = app.autenticacao.login(MAT_BRUNO, SENHA)
    autenticacao = app.autenticacao.autenticar(iniciada.token)
    assert autenticacao.usuario.id == BRUNO
    assert autenticacao.usuario.papel is Papel.TECNICO


@pytest.mark.parametrize("token", [None, "", "inexistente"])
def test_autenticar_sem_sessao_valida(app: Aplicacao, token: str | None) -> None:
    with pytest.raises(NaoAutenticadoError):
        app.autenticacao.autenticar(token)


def test_sessao_expirada_nao_autentica_e_e_apagada(app: Aplicacao, relogio: RelogioFixo) -> None:
    iniciada = app.autenticacao.login(MAT_ANA, SENHA)
    relogio.avancar(hours=8)  # exatamente na expiração: já vencida
    with pytest.raises(NaoAutenticadoError):
        app.autenticacao.autenticar(iniciada.token)
    assert app.sessoes.obter(hash_do_token(iniciada.token)) is None


def test_usuario_desativado_perde_a_sessao_na_proxima_requisicao(app: Aplicacao) -> None:
    iniciada = app.autenticacao.login(MAT_CARLA, SENHA)
    app.container.servico_usuarios.desativar(ANA, CARLA)
    with pytest.raises(NaoAutenticadoError):
        app.autenticacao.autenticar(iniciada.token)
    assert app.sessoes.obter(hash_do_token(iniciada.token)) is None


def test_usuario_excluido_perde_a_sessao(app: Aplicacao) -> None:
    iniciada = app.autenticacao.login(MAT_CARLA, SENHA)
    app.container.usuarios.remover(CARLA)
    with pytest.raises(NaoAutenticadoError):
        app.autenticacao.autenticar(iniciada.token)


def test_login_apaga_as_sessoes_vencidas(app: Aplicacao, relogio: RelogioFixo) -> None:
    velha = app.autenticacao.login(MAT_ANA, SENHA)
    relogio.avancar(hours=9)
    app.autenticacao.login(MAT_BRUNO, SENHA)
    assert app.sessoes.obter(hash_do_token(velha.token)) is None


def test_logout_revoga_e_e_idempotente(app: Aplicacao) -> None:
    iniciada = app.autenticacao.login(MAT_ANA, SENHA)
    app.autenticacao.logout(iniciada.token)
    app.autenticacao.logout(iniciada.token)
    app.autenticacao.logout(None)
    with pytest.raises(NaoAutenticadoError):
        app.autenticacao.autenticar(iniciada.token)


# -------------------------------------------------------------------------------- credenciais
def test_somente_quem_tem_gerir_usuarios_define_credencial(app: Aplicacao) -> None:
    with pytest.raises(PermissaoNegadaError):
        app.autenticacao.definir_credencial(BRUNO, CARLA, "uma-senha-longa-1")
    app.autenticacao.definir_credencial(ANA, CARLA, "uma-senha-longa-1")
    assert app.autenticacao.login(MAT_CARLA, "uma-senha-longa-1").usuario.id == CARLA


def test_definir_credencial_de_usuario_inexistente(app: Aplicacao) -> None:
    with pytest.raises(NaoEncontradoError):
        app.autenticacao.definir_credencial(ANA, 99, "uma-senha-longa-1")


def test_redefinir_a_senha_nao_muda_a_matricula(app: Aplicacao) -> None:
    app.autenticacao.definir_credencial(ANA, ANA, "outra-senha-longa-1")
    iniciada = app.autenticacao.login(MAT_ANA, "outra-senha-longa-1")
    assert iniciada.usuario.id == ANA
    assert iniciada.usuario.matricula == MAT_ANA


@pytest.mark.parametrize("senha", ["", "curta", "x" * 9, "x" * 129])
def test_senha_fora_da_politica(senha: str) -> None:
    with pytest.raises(EntradaInvalidaError):
        validar_senha(senha)


def test_senha_valida_nos_limites() -> None:
    validar_senha("x" * 10)
    validar_senha("x" * 128)
    validar_senha("a senha com espaços e acentuação ç")


def test_normalizar_matricula_so_remove_espacos_das_pontas() -> None:
    assert normalizar_matricula("  KM482731 ") == "KM482731"
    assert normalizar_matricula("km482731") == "km482731"  # não corrige maiúsculas


@pytest.mark.parametrize("senha", ["KM482731", "xxkm482731xx", "KM482731-senha-longa"])
def test_senha_nao_pode_ser_nem_conter_a_matricula(senha: str) -> None:
    with pytest.raises(EntradaInvalidaError):
        validar_senha(senha, "KM482731")


def test_senha_que_nao_contem_a_matricula_passa() -> None:
    validar_senha("uma-senha-longa-1", "KM482731")


def test_credencial_administrativa_exige_usuario_existente(app: Aplicacao) -> None:
    with pytest.raises(NaoEncontradoError):
        app.autenticacao.definir_credencial_administrativa(99, "uma-senha-longa-1")


def test_redefinir_credencial_revoga_as_sessoes(app: Aplicacao) -> None:
    iniciada = app.autenticacao.login(MAT_BRUNO, SENHA)
    app.autenticacao.definir_credencial(ANA, BRUNO, "outra-senha-longa-1")
    with pytest.raises(NaoAutenticadoError):
        app.autenticacao.autenticar(iniciada.token)


# ------------------------------------------------------------------------------------ contas
def test_cadastrar_gera_matricula_valida_e_unica(app: Aplicacao) -> None:
    usuario = app.contexto.contas.cadastrar(ANA, "Diego Rocha", 2, papel=Papel.TECNICO)
    assert matricula_valida(usuario.matricula)
    assert usuario.matricula not in (MAT_ANA, MAT_BRUNO, MAT_CARLA)
    assert app.container.usuarios.obter(usuario.id).matricula == usuario.matricula  # type: ignore[union-attr]


def test_cadastrar_com_acesso_cria_usuario_e_credencial_e_entra_pela_matricula(
    app: Aplicacao,
) -> None:
    usuario = app.contexto.contas.cadastrar(
        ANA, "Diego Rocha", 2, "d@x.com", "Seg-Sex", papel=Papel.TECNICO, senha=SENHA
    )
    assert usuario.matricula is not None
    assert app.autenticacao.login(usuario.matricula, SENHA).usuario.id == usuario.id


def test_cadastrar_sem_acesso_e_permitido(app: Aplicacao) -> None:
    usuario = app.contexto.contas.cadastrar(ANA, "Eva Lima", 2, papel=Papel.TECNICO)
    assert app.credenciais.obter_por_usuario(usuario.id) is None


def test_senha_fraca_nao_deixa_usuario_pela_metade(app: Aplicacao) -> None:
    antes = len(app.container.usuarios.listar())
    with pytest.raises(EntradaInvalidaError):
        app.contexto.contas.cadastrar(ANA, "Eva", 2, papel=Papel.TECNICO, senha="curta")
    assert len(app.container.usuarios.listar()) == antes
    # e o próximo id não foi gasto
    assert app.container.usuarios.proximo_id() == antes + 1


def test_cadastrar_exige_a_permissao_antes_de_validar(app: Aplicacao) -> None:
    with pytest.raises(PermissaoNegadaError):
        app.contexto.contas.cadastrar(BRUNO, "Eva", 2, papel=Papel.TECNICO, senha="x")


def test_desativar_revoga_as_sessoes(app: Aplicacao) -> None:
    iniciada = app.autenticacao.login(MAT_CARLA, SENHA)
    app.contexto.contas.desativar(ANA, CARLA)
    assert app.sessoes.obter(hash_do_token(iniciada.token)) is None


def test_desativar_recusado_nao_revoga_sessoes(app: Aplicacao) -> None:
    app.container.servico_ordens.abrir(CARLA, 1, "falha", Criticidade.BAIXA)
    app.container.servico_ordens.atribuir(ANA, 1, CARLA)  # Carla tem OS ativa
    iniciada = app.autenticacao.login(MAT_CARLA, SENHA)
    with pytest.raises(RegraDeAplicacaoError):
        app.contexto.contas.desativar(ANA, CARLA)
    assert app.autenticacao.autenticar(iniciada.token).usuario.id == CARLA


def test_excluir_remove_credencial_e_a_matricula_deixa_de_entrar(app: Aplicacao) -> None:
    app.contexto.contas.excluir(ANA, CARLA)
    assert app.credenciais.obter_por_usuario(CARLA) is None
    assert app.container.usuarios.obter_por_matricula(MAT_CARLA) is None
    with pytest.raises(CredenciaisInvalidasError):
        app.autenticacao.login(MAT_CARLA, SENHA)


# ----------------------------------------------------------------------------------- limitador
def test_limitador_bloqueia_apos_o_maximo_e_libera_depois_da_janela(relogio: RelogioFixo) -> None:
    limitador = LimitadorDeTentativas(relogio, maximo=3, janela=timedelta(minutes=10))
    for _ in range(3):
        limitador.verificar("k")
        limitador.registrar_falha("k")
    with pytest.raises(MuitasTentativasError) as erro:
        limitador.verificar("k")
    assert 0 < erro.value.segundos <= 600
    relogio.avancar(minutes=11)
    limitador.verificar("k")


def test_limitador_chaves_independentes_e_limpar(relogio: RelogioFixo) -> None:
    limitador = LimitadorDeTentativas(relogio, maximo=1)
    limitador.registrar_falha("a")
    with pytest.raises(MuitasTentativasError):
        limitador.verificar("a")
    limitador.verificar("b")
    limitador.limpar("a")
    limitador.verificar("a")


def test_limitador_nao_cresce_sem_limite(relogio: RelogioFixo) -> None:
    from manutencao.application.servicos import limitador as modulo

    limitador = LimitadorDeTentativas(relogio)
    for i in range(modulo.MAXIMO_DE_CHAVES + 5):
        limitador.registrar_falha(f"chave-{i}")
    assert len(limitador._falhas) <= modulo.MAXIMO_DE_CHAVES


# -------------------------------------------------------------------------------------- painel
def test_painel_conta_por_status_criticidade_e_mostra_recentes(app: Aplicacao) -> None:
    os_ = app.container.servico_ordens
    os_.abrir(ANA, 1, "a", Criticidade.ALTA)
    os_.abrir(BRUNO, 2, "b", Criticidade.BAIXA)
    os_.atribuir(ANA, 2, BRUNO)
    os_.abrir(CARLA, 3, "c", Criticidade.ALTA)
    os_.cancelar(ANA, 3, "duplicada")
    painel = app.contexto.painel.consultar(BRUNO)
    assert (painel.total, painel.em_aberto, painel.encerradas) == (3, 2, 1)
    assert painel.minhas_em_aberto == 1
    por_status = dict(painel.por_status)
    assert por_status[next(s for s in por_status if s.value == "Aberta")] == 1
    assert sum(por_status.values()) == 3
    assert [o.numero for o in painel.recentes] == [3, 2, 1]
    assert painel.tecnicos is not None
    assert {t.id for t in painel.tecnicos} == {BRUNO, CARLA}


def test_painel_exige_ver_os_e_omite_disponibilidade_sem_permissao(app: Aplicacao) -> None:
    from manutencao.domain.permissoes import Permissao

    tecnico = app.container.cargos.obter(2)
    assert tecnico is not None
    permissoes = [p for p in tecnico.permissoes.ativas() if p is not Permissao.VER_DISPONIBILIDADE]
    app.container.servico_usuarios.definir_permissoes_do_cargo(ANA, 2, permissoes)
    assert app.contexto.painel.consultar(BRUNO).tecnicos is None
    sem_os = [p for p in permissoes if p is not Permissao.VER_OS]
    app.container.servico_usuarios.definir_permissoes_do_cargo(ANA, 2, sem_os)
    with pytest.raises(PermissaoNegadaError):
        app.contexto.painel.consultar(BRUNO)


def test_painel_vazio(app: Aplicacao) -> None:
    painel = app.contexto.painel.consultar(ANA)
    assert (painel.total, painel.em_aberto, painel.encerradas, painel.recentes) == (0, 0, 0, ())
