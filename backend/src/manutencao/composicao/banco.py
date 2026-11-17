"""Administração do banco e do acesso por linha de comando (a partir de ``backend/``).

    python -m manutencao.composicao.banco estado
    python -m manutencao.composicao.banco migrar
    python -m manutencao.composicao.banco semear [--com-acesso]
    python -m manutencao.composicao.banco criar-gestor --nome NOME --login LOGIN [--email E]
    python -m manutencao.composicao.banco definir-acesso --usuario-id N --login LOGIN
    python -m manutencao.composicao.banco reverter [destino] --confirmo   # padrão: -1 (uma revisão)

A conexão vem das variáveis de ambiente (``MANUTENCAO_DATABASE_URL`` ou ``MANUTENCAO_DB_*``) e,
se existir, de ``backend/.env`` (ignorado pelo Git; ``MANUTENCAO_ENV_FILE`` indica outro).
Nenhum comando exibe a senha do banco. **Senhas de usuários** são pedidas ao terminal (sem eco) ou,
com ``--senha-stdin``, lidas da entrada padrão: nunca vão em argumento, variável ou arquivo.
``reverter`` **apaga dados** das tabelas desfeitas: exige ``--confirmo`` e só deve ser usado em
banco descartável ou depois de um backup (``pg_dump``; ver docs/PERSISTENCIA.md).
"""

import argparse
import getpass
import sys
from collections.abc import Callable, Sequence

from manutencao.application.erros import AplicacaoError
from manutencao.application.servicos.autenticacao import validar_senha
from manutencao.composicao import acesso
from manutencao.composicao.ambiente import carregar_ambiente_local
from manutencao.composicao.aplicacao import Aplicacao, criar_aplicacao_postgres
from manutencao.composicao.demonstracao import BancoNaoVazioError, semear_demonstracao
from manutencao.composicao.fabrica import criar_container_postgres
from manutencao.infrastructure.postgres import (
    Banco,
    ConfiguracaoDoBanco,
    ConfiguracaoInvalidaError,
    migracoes,
)

LOGINS_DA_DEMONSTRACAO = {1: "ana", 2: "bruno", 3: "carla"}


def _configuracao() -> ConfiguracaoDoBanco:
    carregar_ambiente_local()
    return ConfiguracaoDoBanco.do_ambiente()


def _ler_senha(*, da_entrada_padrao: bool, rotulo: str = "Senha") -> str:
    """A senha sem eco no terminal (pedida duas vezes) ou, com ``--senha-stdin``, de uma linha da
    entrada padrão. Nunca aparece em argumento, variável de ambiente nem saída."""
    if da_entrada_padrao:
        return sys.stdin.readline().rstrip("\r\n")
    senha = getpass.getpass(f"{rotulo}: ")
    if senha != getpass.getpass(f"{rotulo} (repita): "):
        raise ValueError("As senhas digitadas não conferem.")
    return senha


def _estado(config: ConfiguracaoDoBanco) -> int:
    atual = migracoes.revisao_atual(config.url)
    print(f"Banco: {config}")
    recente = migracoes.revisao_mais_recente()
    print(f"Revisão aplicada: {atual or '(nenhuma)'}; mais recente: {recente}")
    if atual is not None:
        banco = Banco(config.url)
        try:
            c = criar_container_postgres(banco)
            print(
                f"Cargos: {len(c.cargos.listar())}; usuários: {len(c.usuarios.listar())}; "
                f"equipamentos: {len(c.equipamentos.listar())}; OS: {c.ordens.contar()}"
            )
        finally:
            banco.encerrar()
    return 0


def _exigir_esquema_atual(config: ConfiguracaoDoBanco) -> bool:
    if migracoes.revisao_atual(config.url) != migracoes.revisao_mais_recente():
        print("O esquema não está atualizado: rode 'migrar' antes.", file=sys.stderr)
        return False
    return True


def _semear(config: ConfiguracaoDoBanco, *, com_acesso: bool, senha_stdin: bool) -> int:
    if not _exigir_esquema_atual(config):
        return 2
    senha = _ler_senha(da_entrada_padrao=senha_stdin) if com_acesso else ""
    if com_acesso:
        validar_senha(
            senha
        )  # antes de criar qualquer dado: uma recusa não deixa o banco pela metade
    banco = Banco(config.url)
    try:
        aplicacao = criar_aplicacao_postgres(banco)
        with aplicacao.unidade.transacao():
            resumo = semear_demonstracao(aplicacao.container)
            if com_acesso:
                for usuario_id, login in LOGINS_DA_DEMONSTRACAO.items():
                    acesso.definir_acesso(aplicacao.autenticacao, usuario_id, login, senha)
    except BancoNaoVazioError as erro:
        print(str(erro), file=sys.stderr)
        return 3
    finally:
        banco.encerrar()
    print(
        f"Demonstração criada: {resumo.cargos} cargos, {resumo.usuarios} usuários, "
        f"{resumo.equipamentos} equipamentos, {resumo.ordens} OS."
    )
    if com_acesso:
        print(
            "Acesso criado para os logins: "
            + ", ".join(LOGINS_DA_DEMONSTRACAO.values())
            + " (todos com a senha informada agora; só para demonstração)."
        )
    return 0


def _com_aplicacao(config: ConfiguracaoDoBanco, trabalho: Callable[[Aplicacao], str]) -> int:
    if not _exigir_esquema_atual(config):
        return 2
    banco = Banco(config.url)
    try:
        mensagem = trabalho(criar_aplicacao_postgres(banco))
    except (acesso.GestorJaExisteError, acesso.CargoDeGestaoAusenteError, ValueError) as erro:
        print(str(erro), file=sys.stderr)
        return 3
    except AplicacaoError as erro:
        print(erro.mensagem, file=sys.stderr)
        return 3
    finally:
        banco.encerrar()
    print(mensagem)
    return 0


def principal(argumentos: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m manutencao.composicao.banco")
    comandos = parser.add_subparsers(dest="comando", required=True)
    comandos.add_parser("estado", help="mostra a revisão do esquema e as contagens")
    comandos.add_parser("migrar", help="aplica as migrações até a revisão mais recente")
    semear = comandos.add_parser(
        "semear", help="cria os dados fictícios de demonstração (banco vazio)"
    )
    semear.add_argument(
        "--com-acesso",
        action="store_true",
        help="cria também o acesso dos 3 usuários fictícios (ana, bruno, carla) com uma senha",
    )
    semear.add_argument("--senha-stdin", action="store_true", help="lê a senha da entrada padrão")
    gestor = comandos.add_parser(
        "criar-gestor", help="cria o primeiro Gestor com login e senha (pedida sem eco)"
    )
    gestor.add_argument("--nome", required=True)
    gestor.add_argument("--login", required=True)
    gestor.add_argument("--email", default="")
    gestor.add_argument("--senha-stdin", action="store_true", help="lê a senha da entrada padrão")
    definir = comandos.add_parser(
        "definir-acesso", help="cria ou redefine login e senha de um usuário (revoga as sessões)"
    )
    definir.add_argument("--usuario-id", type=int, required=True)
    definir.add_argument("--login", required=True)
    definir.add_argument("--senha-stdin", action="store_true", help="lê a senha da entrada padrão")
    reverter = comandos.add_parser("reverter", help="desfaz migrações (APAGA dados dessas tabelas)")
    reverter.add_argument("destino", nargs="?", default="-1")
    reverter.add_argument("--confirmo", action="store_true", help="confirma a perda de dados")
    dado = parser.parse_args(argumentos)

    try:
        config = _configuracao()
    except ConfiguracaoInvalidaError as erro:
        print(f"Erro de configuração: {erro}", file=sys.stderr)
        return 1

    if dado.comando == "estado":
        return _estado(config)
    if dado.comando == "migrar":
        migracoes.aplicar(config.url)
        print(f"Esquema na revisão {migracoes.revisao_atual(config.url)}.")
        return 0
    if dado.comando == "semear":
        try:
            return _semear(config, com_acesso=dado.com_acesso, senha_stdin=dado.senha_stdin)
        except (ValueError, AplicacaoError) as erro:
            print(getattr(erro, "mensagem", str(erro)), file=sys.stderr)
            return 3
    if dado.comando in ("criar-gestor", "definir-acesso"):
        if not _exigir_esquema_atual(config):  # antes de pedir a senha
            return 2
        try:
            senha = _ler_senha(da_entrada_padrao=dado.senha_stdin)
        except ValueError as erro:
            print(str(erro), file=sys.stderr)
            return 3
        if dado.comando == "criar-gestor":

            def _criar(a: Aplicacao) -> str:
                usuario = acesso.criar_gestor_inicial(
                    a.container,
                    a.credenciais,
                    a.autenticacao,
                    a.unidade,
                    nome=dado.nome,
                    login=dado.login,
                    senha=senha,
                    email=dado.email,
                )
                return (
                    f"Gestor criado: usuário {usuario.id}, login '{dado.login.strip().casefold()}'."
                )

            return _com_aplicacao(config, _criar)

        def _definir(a: Aplicacao) -> str:
            acesso.definir_acesso(a.autenticacao, dado.usuario_id, dado.login, senha)
            return f"Acesso do usuário {dado.usuario_id} definido; as sessões dele foram revogadas."

        return _com_aplicacao(config, _definir)
    if not dado.confirmo:
        print(
            "'reverter' apaga dados: repita com --confirmo (e faça backup antes).", file=sys.stderr
        )
        return 2
    migracoes.reverter(config.url, dado.destino)
    print(f"Esquema na revisão {migracoes.revisao_atual(config.url) or '(base)'}.")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
