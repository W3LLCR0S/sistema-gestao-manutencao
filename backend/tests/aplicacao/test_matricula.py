"""Cadastro de usuários e matrícula: geração pelo sistema, unicidade e colisões (aplicação)."""

from typing import Any

import pytest

from manutencao.application.erros import CodigoErroAplicacao, RegraDeAplicacaoError
from manutencao.domain.enums import Papel
from manutencao.domain.erros import CodigoErro, PermissaoNegadaError, ViolacaoDeRegraError
from manutencao.domain.matricula import matricula_valida
from manutencao.domain.usuario import Usuario
from tests.apoio.ambiente import ANA, BRUNO, CARGO_TECNICO, Ambiente, criar_ambiente


@pytest.fixture
def amb() -> Ambiente:
    return criar_ambiente()


class _Envoltorio:
    """Repete tudo no repositório real; as subclasses mudam só o que o teste quer provocar."""

    def __init__(self, base: Any) -> None:
        self._base = base

    def __getattr__(self, nome: str) -> Any:
        return getattr(self._base, nome)


def _trocar_repositorio(amb: Ambiente, falso: Any) -> None:
    amb.servico_usuarios._usuarios = falso


def test_a_base_inicial_tem_as_matriculas_combinadas(amb: Ambiente) -> None:
    mapa = {u.nome.split()[0]: u.matricula for u in amb.usuarios.listar()}
    assert mapa == {"Ana": "KM482731", "Bruno": "RT095624", "Carla": "VX716309"}


def test_cadastrar_gera_matricula_valida_unica_e_persistida(amb: Ambiente) -> None:
    novo = amb.servico_usuarios.cadastrar(ANA, "Diego Rocha", CARGO_TECNICO, papel=Papel.TECNICO)
    assert matricula_valida(novo.matricula)
    gravado = amb.usuarios.obter(novo.id)
    assert gravado is not None
    assert gravado.matricula == novo.matricula
    todas = [u.matricula for u in amb.usuarios.listar()]
    assert len(todas) == len(set(todas)) == 4


def test_muitos_cadastros_nunca_repetem_matricula(amb: Ambiente) -> None:
    for i in range(60):
        amb.servico_usuarios.cadastrar(ANA, f"Pessoa {i}", CARGO_TECNICO, papel=Papel.TECNICO)
    todas = [u.matricula for u in amb.usuarios.listar()]
    assert len(todas) == len(set(todas)) == 63


def test_cadastro_recusado_nao_gera_matricula_nem_gasta_id(amb: Ambiente) -> None:
    proximo = amb.usuarios.proximo_id()
    with pytest.raises(PermissaoNegadaError):
        amb.servico_usuarios.cadastrar(BRUNO, "X", CARGO_TECNICO, papel=Papel.TECNICO)
    with pytest.raises(ViolacaoDeRegraError):
        amb.servico_usuarios.cadastrar(ANA, "   ", CARGO_TECNICO, papel=Papel.TECNICO)
    assert amb.usuarios.proximo_id() == proximo
    assert len(amb.usuarios.listar()) == 3


def test_colisao_na_verificacao_sorteia_de_novo(amb: Ambiente) -> None:
    class ColideAntes(_Envoltorio):
        restantes = 7
        consultas = 0

        def matricula_existe(self, matricula: str) -> bool:
            self.consultas += 1
            if self.restantes > 0:
                self.restantes -= 1
                return True
            return bool(self._base.matricula_existe(matricula))

    falso = ColideAntes(amb.usuarios)
    _trocar_repositorio(amb, falso)
    novo = amb.servico_usuarios.cadastrar(ANA, "Diego", CARGO_TECNICO, papel=Papel.TECNICO)
    assert matricula_valida(novo.matricula)
    assert falso.consultas >= 8  # 7 colisões e a candidata livre


def test_colisao_somente_na_gravacao_tenta_outra_matricula(amb: Ambiente) -> None:
    """Corrida: a candidata passou na verificação, mas outro cadastro a gravou antes (UNIQUE)."""

    class Corrida(_Envoltorio):
        falhas = 2

        def __init__(self, base: Any) -> None:
            super().__init__(base)
            self.recusadas: list[str | None] = []

        def adicionar(self, usuario: Usuario) -> None:
            if self.falhas:
                self.falhas -= 1
                self.recusadas.append(usuario.matricula)
                raise RegraDeAplicacaoError(
                    CodigoErroAplicacao.MATRICULA_EM_USO, "Essa matrícula já está em uso."
                )
            self._base.adicionar(usuario)

    corrida = Corrida(amb.usuarios)
    _trocar_repositorio(amb, corrida)
    novo = amb.servico_usuarios.cadastrar(ANA, "Diego", CARGO_TECNICO, papel=Papel.TECNICO)
    assert corrida.falhas == 0
    assert len(corrida.recusadas) == 2
    assert novo.matricula not in corrida.recusadas  # sorteou outra depois da colisão
    assert len(amb.usuarios.listar()) == 4


def test_colisoes_sem_fim_na_gravacao_falham_com_erro_de_conflito(amb: Ambiente) -> None:
    class SempreColide(_Envoltorio):
        def adicionar(self, usuario: Usuario) -> None:
            raise RegraDeAplicacaoError(
                CodigoErroAplicacao.MATRICULA_EM_USO, "Essa matrícula já está em uso."
            )

    _trocar_repositorio(amb, SempreColide(amb.usuarios))
    with pytest.raises(RegraDeAplicacaoError) as erro:
        amb.servico_usuarios.cadastrar(ANA, "Diego", CARGO_TECNICO, papel=Papel.TECNICO)
    assert erro.value.codigo is CodigoErroAplicacao.MATRICULA_EM_USO
    assert len(amb.usuarios.listar()) == 3


def test_outro_erro_de_gravacao_nao_e_confundido_com_colisao(amb: Ambiente) -> None:
    class Quebra(_Envoltorio):
        chamadas = 0

        def adicionar(self, usuario: Usuario) -> None:
            self.chamadas += 1
            raise RegraDeAplicacaoError(CodigoErroAplicacao.ULTIMO_GESTOR, "outro erro")

    falso = Quebra(amb.usuarios)
    _trocar_repositorio(amb, falso)
    with pytest.raises(RegraDeAplicacaoError) as erro:
        amb.servico_usuarios.cadastrar(ANA, "Diego", CARGO_TECNICO, papel=Papel.TECNICO)
    assert erro.value.codigo is CodigoErroAplicacao.ULTIMO_GESTOR
    assert falso.chamadas == 1  # sem nova tentativa


def test_geracao_esgotada_levanta_erro_claro(amb: Ambiente) -> None:
    class Lotado(_Envoltorio):
        def matricula_existe(self, matricula: str) -> bool:
            return True

    _trocar_repositorio(amb, Lotado(amb.usuarios))
    with pytest.raises(ViolacaoDeRegraError) as erro:
        amb.servico_usuarios.cadastrar(ANA, "Diego", CARGO_TECNICO, papel=Papel.TECNICO)
    assert erro.value.codigo is CodigoErro.MATRICULA_INDISPONIVEL
    assert len(amb.usuarios.listar()) == 3


def test_editar_dados_cargo_papel_e_situacao_preserva_a_matricula(amb: Ambiente) -> None:
    antes = amb.usuarios.obter(BRUNO)
    assert antes is not None
    amb.servico_usuarios.atualizar_dados(ANA, BRUNO, nome="Bruno L.", email="b@x.com")
    amb.servico_usuarios.alterar_cargo(ANA, BRUNO, 1)
    amb.servico_usuarios.alterar_papel(ANA, BRUNO, Papel.GESTOR)
    amb.servico_usuarios.desativar(ANA, BRUNO)
    amb.servico_usuarios.reativar(ANA, BRUNO)
    depois = amb.usuarios.obter(BRUNO)
    assert depois is not None
    assert depois.matricula == antes.matricula == "RT095624"


def test_consulta_da_matricula_exige_permissao_de_gestao(amb: Ambiente) -> None:
    assert amb.servico_usuarios.consultar(ANA, BRUNO).matricula == "RT095624"
    assert [u.matricula for u in amb.servico_usuarios.listar(ANA)][:1] == ["KM482731"]
    with pytest.raises(PermissaoNegadaError):
        amb.servico_usuarios.consultar(BRUNO, ANA)
    with pytest.raises(PermissaoNegadaError):
        amb.servico_usuarios.listar(BRUNO)
