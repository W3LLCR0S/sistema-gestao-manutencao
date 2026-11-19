"""Migração 0003 (matrícula) sobre um banco **com dados** na revisão 0002.

Garante: os três usuários fictícios recebem as matrículas combinadas; os demais, matrículas
aleatórias válidas e únicas; nada é apagado nem alterado (senhas, cargos, permissões,
equipamentos, OS, históricos, sessões); a migração é reversível e idempotente.
"""

import re
from collections.abc import Iterator
from contextlib import contextmanager

import pytest
from sqlalchemy import Connection, create_engine, inspect, text
from sqlalchemy.engine import URL

from manutencao.infrastructure.postgres import migracoes
from tests.apoio.postgres import banco_temporario

FICTICIAS = {"ana": "KM482731", "bruno": "RT095624", "carla": "VX716309"}
HASH_ANA = "$argon2id$v=19$m=65536,t=3,p=4$hash-de-ana"
FORMATO = re.compile(r"^[A-Z]{2}[0-9]{6}$")


@contextmanager
def _conexao(url: URL) -> Iterator[Connection]:
    engine = create_engine(url)
    try:
        with engine.begin() as conexao:
            yield conexao
    finally:
        engine.dispose()


def _popular_na_0002(url: URL) -> None:
    """Esquema 0002 com 3 usuários fictícios (com login), 1 extra com login, 1 sem credencial."""
    migracoes.aplicar(url, "0002")
    with _conexao(url) as c:
        c.execute(text("INSERT INTO cargos (id, nome) VALUES (1, 'Gestor'), (2, 'Técnico')"))
        c.execute(
            text(
                "INSERT INTO cargo_permissoes VALUES (1, 'gerir_usuarios'), (1, 'ver_os'),"
                " (2, 'ver_os')"
            )
        )
        c.execute(
            text(
                "INSERT INTO usuarios (id, nome, cargo_id, email, escala, disponibilidade, papel,"
                " ativo) VALUES"
                " (1,'Ana Souza',1,'ana@empresa.com','Seg-Sex','Disponível','Gestor',true),"
                " (2,'Bruno Lima',2,'bruno@empresa.com','Seg-Sex','Disponível','Técnico',true),"
                " (3,'Carla Mendes',2,'carla@empresa.com','Seg-Sex','Ausente','Técnico',true),"
                " (4,'Diego Rocha',2,'d@x.com','','Disponível','Técnico',true),"
                " (5,'Eva Lima',2,'','','Disponível','Técnico',false)"
            )
        )
        c.execute(
            text(
                "INSERT INTO credenciais (usuario_id, login, senha_hash) VALUES"
                " (1,'ana',:h1),(2,'bruno','h2'),(3,'carla','h3'),(4,'diego.rocha','h4')"
            ),
            {"h1": HASH_ANA},
        )
        c.execute(text("INSERT INTO equipamentos VALUES (1,'Torno CNC','GL 240',true)"))
        c.execute(
            text(
                "INSERT INTO ordens_servico (numero, equipamento_id, equipamento_snapshot, falha,"
                " criticidade, aberta_por_id, aberta_por_snapshot, data_abertura, status,"
                " diagnostico, causa_raiz, teste_funcional, motivo_cancelamento)"
                " VALUES (1,1,'{}','Vibração','Alta',1,'{}',now(),'Aberta','','','','')"
            )
        )
        c.execute(
            text(
                "INSERT INTO servicos_os (os_numero, numero, tipo, descricao, responsavel_id, data,"
                " horas) VALUES (1,1,'Abertura','OS aberta',1,now(),0)"
            )
        )
        c.execute(
            text("INSERT INTO sessoes VALUES ('abc', 1, 'csrf', now(), now() + interval '1 hour')")
        )


def _estado(url: URL) -> dict[str, object]:
    with _conexao(url) as c:
        return {
            "usuarios": c.execute(
                text(
                    "SELECT id, nome, cargo_id, email, escala, disponibilidade, papel, ativo"
                    " FROM usuarios ORDER BY id"
                )
            ).all(),
            "cargos": c.execute(text("SELECT * FROM cargos ORDER BY id")).all(),
            "permissoes": c.execute(text("SELECT * FROM cargo_permissoes ORDER BY 1, 2")).all(),
            "equipamentos": c.execute(text("SELECT * FROM equipamentos")).all(),
            "ordens": c.execute(text("SELECT numero, falha, status FROM ordens_servico")).all(),
            "historico": c.execute(
                text("SELECT os_numero, numero, tipo, descricao FROM servicos_os")
            ).all(),
            "hashes": c.execute(
                text("SELECT usuario_id, senha_hash FROM credenciais ORDER BY 1")
            ).all(),
            "sessoes": c.execute(text("SELECT id_hash, usuario_id FROM sessoes")).all(),
        }


def _matriculas(url: URL) -> dict[int, str]:
    with _conexao(url) as c:
        linhas = c.execute(text("SELECT id, matricula FROM usuarios")).all()
        return {int(i): str(m) for i, m in linhas}


def test_upgrade_atribui_as_matriculas_combinadas_e_gera_as_demais(
    url_do_servidor_de_teste: URL,
) -> None:
    with banco_temporario(url_do_servidor_de_teste) as url:
        _popular_na_0002(url)
        migracoes.aplicar(url)
        assert migracoes.revisao_atual(url) == "0003"
        m = _matriculas(url)
        assert (m[1], m[2], m[3]) == (FICTICIAS["ana"], FICTICIAS["bruno"], FICTICIAS["carla"])
        for geradas in (m[4], m[5]):  # o usuário com login e o sem credencial
            assert FORMATO.match(geradas)
            assert geradas not in FICTICIAS.values()
        assert len(set(m.values())) == 5


def test_upgrade_preserva_senhas_cargos_permissoes_equipamentos_os_e_sessoes(
    url_do_servidor_de_teste: URL,
) -> None:
    with banco_temporario(url_do_servidor_de_teste) as url:
        _popular_na_0002(url)
        antes = _estado(url)
        migracoes.aplicar(url)
        assert _estado(url) == antes
        with _conexao(url) as c:
            hash_ana = c.execute(
                text("SELECT senha_hash FROM credenciais WHERE usuario_id = 1")
            ).scalar_one()
        assert hash_ana == HASH_ANA  # a senha é a mesma; só a identificação mudou


def test_login_antigo_fica_so_como_registro_sem_unicidade(
    url_do_servidor_de_teste: URL,
) -> None:
    with banco_temporario(url_do_servidor_de_teste) as url:
        _popular_na_0002(url)
        migracoes.aplicar(url)
        engine = create_engine(url)
        try:
            colunas = {c["name"]: c for c in inspect(engine).get_columns("credenciais")}
        finally:
            engine.dispose()
        assert "login" not in colunas
        assert colunas["login_legado"]["nullable"] is True
        with _conexao(url) as c:
            linhas = c.execute(text("SELECT usuario_id, login_legado FROM credenciais")).all()
            legados = {int(i): login for i, login in linhas}
            assert legados[1] == "ana"
            # contas novas não têm login: a unicidade antiga não impede NULL repetido
            c.execute(
                text(
                    "INSERT INTO usuarios (id, nome, cargo_id, email, escala, disponibilidade,"
                    " papel, ativo, matricula) VALUES (6,'N',2,'','','Disponível','Técnico',true,"
                    "'AB123456'), (7,'O',2,'','','Disponível','Técnico',true,'AB123457')"
                )
            )
            c.execute(
                text("INSERT INTO credenciais (usuario_id, senha_hash) VALUES (6,'x'),(7,'y')")
            )


def test_aplicar_de_novo_e_inofensivo_e_nao_muda_as_matriculas(
    url_do_servidor_de_teste: URL,
) -> None:
    with banco_temporario(url_do_servidor_de_teste) as url:
        _popular_na_0002(url)
        migracoes.aplicar(url)
        antes = _matriculas(url)
        migracoes.aplicar(url)
        assert _matriculas(url) == antes


def test_corpo_do_upgrade_e_idempotente_mesmo_reexecutado(url_do_servidor_de_teste: URL) -> None:
    """Reexecuta o ``upgrade()`` sobre um banco já migrado (como após uma falha parcial)."""
    import importlib.util

    from alembic.operations import Operations
    from alembic.runtime.migration import MigrationContext

    arquivo = migracoes.DIRETORIO_DAS_MIGRACOES / "versions" / "0003_matricula.py"
    spec = importlib.util.spec_from_file_location("migracao_0003", arquivo)
    assert spec is not None
    assert spec.loader is not None
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    with banco_temporario(url_do_servidor_de_teste) as url:
        _popular_na_0002(url)
        migracoes.aplicar(url)
        antes = _matriculas(url)
        engine = create_engine(url)
        try:
            with engine.begin() as conexao:
                contexto = MigrationContext.configure(conexao)
                with Operations.context(contexto):
                    modulo.upgrade()
        finally:
            engine.dispose()
        assert _matriculas(url) == antes
        assert migracoes.revisao_atual(url) == "0003"


def test_retomada_apos_falha_parcial_preenche_so_o_que_falta(
    url_do_servidor_de_teste: URL,
) -> None:
    """Coluna criada e parcialmente preenchida: o upgrade completa sem trocar o que já existe."""
    import importlib.util

    from alembic.operations import Operations
    from alembic.runtime.migration import MigrationContext

    arquivo = migracoes.DIRETORIO_DAS_MIGRACOES / "versions" / "0003_matricula.py"
    spec = importlib.util.spec_from_file_location("migracao_0003b", arquivo)
    assert spec is not None
    assert spec.loader is not None
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    with banco_temporario(url_do_servidor_de_teste) as url:
        _popular_na_0002(url)
        with _conexao(url) as c:
            c.execute(text("ALTER TABLE usuarios ADD COLUMN matricula VARCHAR(8)"))
            c.execute(text("UPDATE usuarios SET matricula = 'QQ111111' WHERE id = 4"))
        engine = create_engine(url)
        try:
            with (
                engine.begin() as conexao,
                Operations.context(MigrationContext.configure(conexao)),
            ):
                modulo.upgrade()
        finally:
            engine.dispose()
        m = _matriculas(url)
        assert m[4] == "QQ111111"  # preservada
        assert (m[1], m[2], m[3]) == tuple(FICTICIAS.values())
        assert FORMATO.match(m[5])


def test_downgrade_devolve_o_login_e_preserva_os_dados(url_do_servidor_de_teste: URL) -> None:
    with banco_temporario(url_do_servidor_de_teste) as url:
        _popular_na_0002(url)
        antes = _estado(url)
        migracoes.aplicar(url)
        migracoes.reverter(url, "-1")
        assert migracoes.revisao_atual(url) == "0002"
        assert _estado(url)["hashes"] == antes["hashes"]
        assert {k: v for k, v in _estado(url).items() if k != "usuarios"} == {
            k: v for k, v in antes.items() if k != "usuarios"
        }
        with _conexao(url) as c:
            linhas = c.execute(text("SELECT usuario_id, login FROM credenciais")).all()
            logins = {int(i): str(login) for i, login in linhas}
        assert logins == {1: "ana", 2: "bruno", 3: "carla", 4: "diego.rocha"}
        engine = create_engine(url)
        try:
            assert "matricula" not in {c["name"] for c in inspect(engine).get_columns("usuarios")}
        finally:
            engine.dispose()
        migracoes.aplicar(url)  # e a subida de novo reaplica as matrículas combinadas
        m = _matriculas(url)
        assert (m[1], m[2], m[3]) == tuple(FICTICIAS.values())


def test_migrar_banco_vazio_nao_falha_e_cria_as_restricoes(url_do_servidor_de_teste: URL) -> None:
    with banco_temporario(url_do_servidor_de_teste) as url:
        migracoes.aplicar(url)
        engine = create_engine(url)
        try:
            inspetor = inspect(engine)
            unicas = {u["name"] for u in inspetor.get_unique_constraints("usuarios")}
            checks = {c["name"] for c in inspetor.get_check_constraints("usuarios")}
            coluna = {c["name"]: c for c in inspetor.get_columns("usuarios")}["matricula"]
        finally:
            engine.dispose()
        assert "uq_usuarios_matricula" in unicas
        assert "ck_usuarios_matricula_formato" in checks
        assert coluna["nullable"] is False


def test_conflito_com_matricula_combinada_ja_usada_aborta_sem_alterar(
    url_do_servidor_de_teste: URL,
) -> None:
    with banco_temporario(url_do_servidor_de_teste) as url:
        _popular_na_0002(url)
        with _conexao(url) as c:
            c.execute(text("ALTER TABLE usuarios ADD COLUMN matricula VARCHAR(8)"))
            c.execute(text("UPDATE usuarios SET matricula = 'KM482731' WHERE id = 5"))
        with pytest.raises(RuntimeError, match="KM482731"):
            migracoes.aplicar(url)
        assert migracoes.revisao_atual(url) == "0002"  # a transação foi desfeita
