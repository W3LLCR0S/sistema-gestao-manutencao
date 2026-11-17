"""Configuração do banco por variáveis de ambiente: sem credencial no código, senha oculta."""

from pathlib import Path

import pytest

from manutencao.infrastructure.postgres.configuracao import (
    ConfiguracaoDoBanco,
    ConfiguracaoInvalidaError,
    carregar_arquivo_env,
)

SENHA = "s3nh4-secreta"


def test_url_completa_usa_o_driver_psycopg() -> None:
    config = ConfiguracaoDoBanco.do_ambiente(
        {"MANUTENCAO_DATABASE_URL": f"postgresql://app:{SENHA}@db.local:5433/manut"}
    )
    assert config.url.drivername == "postgresql+psycopg"
    assert (config.url.host, config.url.port, config.url.database) == ("db.local", 5433, "manut")
    assert config.url.password == SENHA


def test_partes_com_valores_padrao() -> None:
    config = ConfiguracaoDoBanco.do_ambiente(
        {"MANUTENCAO_DB_NAME": "manut", "MANUTENCAO_DB_USER": "app"}
    )
    assert (config.url.host, config.url.port) == ("localhost", 5432)
    assert config.url.password is None


def test_url_tem_precedencia_sobre_as_partes() -> None:
    config = ConfiguracaoDoBanco.do_ambiente(
        {
            "MANUTENCAO_DATABASE_URL": "postgresql://a@h/b1",
            "MANUTENCAO_DB_NAME": "outro",
            "MANUTENCAO_DB_USER": "x",
        }
    )
    assert config.url.database == "b1"


def test_a_senha_nunca_aparece_em_repr_ou_str() -> None:
    config = ConfiguracaoDoBanco.do_ambiente(
        {"MANUTENCAO_DB_NAME": "m", "MANUTENCAO_DB_USER": "u", "MANUTENCAO_DB_PASSWORD": SENHA}
    )
    assert SENHA not in repr(config)
    assert SENHA not in str(config)
    assert config.url.password == SENHA  # mas a conexão a recebe


@pytest.mark.parametrize(
    "ambiente",
    [
        {},
        {"MANUTENCAO_DB_NAME": "m"},
        {"MANUTENCAO_DB_USER": "u"},
        {"MANUTENCAO_DB_NAME": "m", "MANUTENCAO_DB_USER": "u", "MANUTENCAO_DB_PORT": "abc"},
        {"MANUTENCAO_DATABASE_URL": "isto não é uma url"},
        {"MANUTENCAO_DATABASE_URL": "mysql://u:p@h/b"},
        {"MANUTENCAO_DATABASE_URL": "postgresql://u@h"},
    ],
)
def test_configuracao_invalida_e_recusada_sem_vazar_a_senha(ambiente: dict[str, str]) -> None:
    with pytest.raises(ConfiguracaoInvalidaError) as erro:
        ConfiguracaoDoBanco.do_ambiente({**ambiente, "MANUTENCAO_DB_PASSWORD": SENHA})
    assert SENHA not in str(erro.value)


def test_arquivo_env_define_so_o_que_falta_e_devolve_apenas_nomes(tmp_path: Path) -> None:
    arquivo = tmp_path / ".env"
    arquivo.write_text(
        "# comentário\n\nMANUTENCAO_DB_NAME=manut\nMANUTENCAO_DB_USER='app'\n"
        f'MANUTENCAO_DB_PASSWORD="{SENHA}"\nsem_igual\n',
        encoding="utf-8",
    )
    ambiente = {"MANUTENCAO_DB_NAME": "ja_definido"}
    definidas = carregar_arquivo_env(arquivo, ambiente)
    assert definidas == ["MANUTENCAO_DB_USER", "MANUTENCAO_DB_PASSWORD"]
    assert ambiente["MANUTENCAO_DB_NAME"] == "ja_definido"  # o ambiente prevalece
    assert ambiente["MANUTENCAO_DB_USER"] == "app"  # aspas removidas
    assert SENHA not in " ".join(definidas)


def test_arquivo_env_inexistente_nao_e_erro(tmp_path: Path) -> None:
    assert carregar_arquivo_env(tmp_path / "nao-existe.env", {}) == []
