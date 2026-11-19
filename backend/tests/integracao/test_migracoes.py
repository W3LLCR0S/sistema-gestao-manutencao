"""Migrações Alembic: reproduzíveis, reversíveis e idênticas aos modelos (sem desvio de esquema)."""

import pytest
from alembic.autogenerate import compare_metadata
from alembic.runtime.migration import MigrationContext
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import URL
from sqlalchemy.exc import DataError, IntegrityError

from manutencao.infrastructure.postgres import Banco, migracoes
from manutencao.infrastructure.postgres.modelos import Base
from tests.apoio.postgres import banco_temporario

TABELAS = {
    "alembic_version",
    "sequencias",
    "cargos",
    "cargo_permissoes",
    "usuarios",
    "equipamentos",
    "ordens_servico",
    "servicos_os",
    "pecas_servico",
    "credenciais",
    "sessoes",
}


def _tabelas(url: URL) -> set[str]:
    engine = create_engine(url)
    try:
        return set(inspect(engine).get_table_names())
    finally:
        engine.dispose()


def test_migrar_um_banco_vazio_cria_o_esquema_e_registra_a_revisao(
    url_do_servidor_de_teste: URL,
) -> None:
    with banco_temporario(url_do_servidor_de_teste) as url:
        assert migracoes.revisao_atual(url) is None
        migracoes.aplicar(url)
        assert migracoes.revisao_atual(url) == migracoes.revisao_mais_recente()
        assert _tabelas(url) == TABELAS


def test_aplicar_duas_vezes_e_inofensivo(url_do_servidor_de_teste: URL) -> None:
    with banco_temporario(url_do_servidor_de_teste) as url:
        migracoes.aplicar(url)
        migracoes.aplicar(url)
        assert migracoes.revisao_atual(url) == migracoes.revisao_mais_recente()


def test_as_sequencias_nascem_zeradas(url_do_servidor_de_teste: URL) -> None:
    with banco_temporario(url_do_servidor_de_teste) as url:
        migracoes.aplicar(url)
        engine = create_engine(url)
        try:
            with engine.connect() as conexao:
                linhas = dict(
                    conexao.execute(text("SELECT entidade, ultimo FROM sequencias")).tuples().all()
                )
        finally:
            engine.dispose()
        assert linhas == {"cargo": 0, "equipamento": 0, "usuario": 0, "ordem_servico": 0}


def test_reverter_desfaz_o_esquema_e_reaplicar_o_recria(url_do_servidor_de_teste: URL) -> None:
    """Rollback documentado: ``reverter(base)`` remove tudo; a migração é reproduzível."""
    with banco_temporario(url_do_servidor_de_teste) as url:
        migracoes.aplicar(url)
        migracoes.reverter(url, "base")
        assert migracoes.revisao_atual(url) is None
        assert _tabelas(url) == {"alembic_version"}
        migracoes.aplicar(url)
        assert _tabelas(url) == TABELAS


def test_os_modelos_e_as_migracoes_descrevem_o_mesmo_esquema(
    url_do_banco_de_teste: URL,
) -> None:
    """Sem desvio: nenhuma diferença entre ``Base.metadata`` e o banco migrado."""
    engine = create_engine(url_do_banco_de_teste)
    try:
        with engine.connect() as conexao:
            contexto = MigrationContext.configure(conexao, opts={"compare_type": True})
            diferencas = compare_metadata(contexto, Base.metadata)
    finally:
        engine.dispose()
    assert diferencas == []


def test_restricoes_do_banco_recusam_valores_invalidos(
    banco_limpo: Banco, url_do_banco_de_teste: URL
) -> None:
    """O banco, não só o código, protege a integridade (CHECK e chaves estrangeiras)."""
    usuario = (
        "INSERT INTO usuarios (id, nome, cargo_id, email, escala, disponibilidade, papel, ativo,"
        " matricula) VALUES ({id},'x',{cargo},'','','{disp}','{papel}',true,'{matricula}')"
    )
    invalidos = {
        "cargo inexistente": usuario.format(
            id=1, cargo=99, disp="Disponível", papel="Gestor", matricula="AA000001"
        ),
        "papel inválido": usuario.format(
            id=1, cargo=1, disp="Disponível", papel="Chefe", matricula="AA000001"
        ),
        "disponibilidade inválida": usuario.format(
            id=1, cargo=1, disp="Folga", papel="Gestor", matricula="AA000001"
        ),
        "matrícula em minúsculas": usuario.format(
            id=1, cargo=1, disp="Disponível", papel="Gestor", matricula="aa000001"
        ),
        "matrícula curta": usuario.format(
            id=1, cargo=1, disp="Disponível", papel="Gestor", matricula="AA00001"
        ),
        "matrícula longa": usuario.format(
            id=1, cargo=1, disp="Disponível", papel="Gestor", matricula="AA0000011"
        ),
        "matrícula com letras no lugar dos dígitos": usuario.format(
            id=1, cargo=1, disp="Disponível", papel="Gestor", matricula="AAB00001"
        ),
        "permissão inexistente": "INSERT INTO cargo_permissoes VALUES (1, 'voar')",
        "status de OS inválido": (
            "INSERT INTO ordens_servico VALUES (1,1,'{}','f','Alta',1,'{}',now(),'Perdida',"
            "NULL,NULL,'','','','',NULL)"
        ),
    }
    engine = create_engine(url_do_banco_de_teste)
    try:
        with engine.begin() as conexao:
            conexao.execute(text("INSERT INTO cargos (id, nome) VALUES (1, 'Gestor')"))
        for motivo, comando in invalidos.items():
            with pytest.raises((IntegrityError, DataError)), engine.begin() as conexao:
                conexao.execute(text(comando))
            assert motivo  # cada recusa é uma restrição diferente
        with engine.begin() as conexao:
            assert conexao.scalar(text("SELECT count(*) FROM usuarios")) == 0
        # RESTRICT: não se apaga um cargo que tem usuário.
        with engine.begin() as conexao:
            conexao.execute(
                text(
                    usuario.format(
                        id=1, cargo=1, disp="Disponível", papel="Gestor", matricula="AA000001"
                    )
                )
            )
        with pytest.raises(IntegrityError), engine.begin() as conexao:
            conexao.execute(text("DELETE FROM cargos WHERE id = 1"))
        # UNIQUE: duas pessoas não compartilham a matrícula
        with pytest.raises(IntegrityError), engine.begin() as conexao:
            conexao.execute(
                text(
                    usuario.format(
                        id=2, cargo=1, disp="Disponível", papel="Gestor", matricula="AA000001"
                    )
                )
            )
    finally:
        engine.dispose()


def test_reverter_a_0002_preserva_o_esquema_da_0001_e_os_dados(
    url_do_servidor_de_teste: URL,
) -> None:
    """A migração de autenticação é aditiva: desfazê-la não toca em usuários nem em OS."""
    with banco_temporario(url_do_servidor_de_teste) as url:
        migracoes.aplicar(url, "0001")
        engine = create_engine(url)
        try:
            with engine.begin() as conexao:
                conexao.execute(text("INSERT INTO cargos (id, nome) VALUES (1, 'Gestor')"))
                conexao.execute(
                    text("INSERT INTO usuarios VALUES (1,'x',1,'','','Disponível','Gestor',true)")
                )
        finally:
            engine.dispose()
        migracoes.aplicar(url, "0002")
        assert migracoes.revisao_atual(url) == "0002"
        migracoes.reverter(url, "-1")
        assert migracoes.revisao_atual(url) == "0001"
        assert _tabelas(url) == TABELAS - {"credenciais", "sessoes"}
        engine = create_engine(url)
        try:
            with engine.connect() as conexao:
                assert conexao.execute(text("SELECT count(*) FROM usuarios")).scalar_one() == 1
        finally:
            engine.dispose()
